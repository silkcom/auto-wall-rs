"""Bounded building RF experiment. train takes reference pairs; infer accepts image/model only."""
import argparse, hashlib, json, time
from pathlib import Path
import cv2
import numpy as np
from cave_segmentation.candidate import features as appearance, SCALE


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def features(image):
    base = appearance(image)
    gray = cv2.cvtColor(cv2.resize(image, (base.shape[1], base.shape[0]), interpolation=cv2.INTER_AREA), cv2.COLOR_BGR2GRAY).astype(np.float32) / 255
    parts = [base]
    for sigma in (1, 3):
        blur = cv2.GaussianBlur(gray, (0, 0), sigma)
        gx = cv2.Sobel(blur, cv2.CV_32F, 1, 0)
        gy = cv2.Sobel(blur, cv2.CV_32F, 0, 1)
        parts.extend([np.abs(gx)[..., None], np.abs(gy)[..., None], np.abs(gx+gy)[..., None], np.abs(gx-gy)[..., None]])
    return np.concatenate(parts, axis=2)


def labels(reference, shape):
    d = json.loads(Path(reference).read_text())
    res = d['resolution']; ppg = res['pixels_per_grid']; origin = res.get('map_origin', {'x': 0, 'y': 0})
    wall = np.zeros(shape, np.uint8); portal = wall.copy()
    def points(path):
        return np.rint([[(p['x']-origin['x'])*ppg/SCALE, (p['y']-origin['y'])*ppg/SCALE] for p in path]).astype(np.int32)
    for group in ('line_of_sight', 'objects_line_of_sight'):
        for path in d.get(group, []):
            if len(path) > 1:
                cv2.polylines(wall, [points(path)], False, 1, 3)
    for item in d.get('portals', []):
        if len(item.get('bounds', [])) > 1:
            cv2.polylines(portal, [points(item['bounds'])], False, 1, 3)
    # Thin targets, uncertain shoulders and wall/portal overlaps never become negatives.
    outer = cv2.dilate(wall | portal, np.ones((9, 9), np.uint8))
    y = np.zeros(shape, np.uint8); y[outer > 0] = 255
    y[wall > 0] = 1; y[portal > 0] = 2
    y[(cv2.dilate(wall, np.ones((3, 3), np.uint8)) > 0) & (cv2.dilate(portal, np.ones((3, 3), np.uint8)) > 0)] = 255
    return y


def train(config, model, out):
    rng = np.random.default_rng(42); xs=[]; ys=[]; sources=[]
    for source in json.loads(Path(config).read_text()):
        im = cv2.imread(source['image']); assert im is not None
        f = features(im); y = labels(source['reference'], f.shape[:2]); flat = y.ravel()
        count = {}
        for c in range(3):
            candidates = np.flatnonzero(flat == c)
            assert len(candidates), (source, c)
            ids = rng.choice(candidates, min(len(candidates), 16000), replace=False)
            xs.append(f.reshape(-1, f.shape[2])[ids]); ys.append(flat[ids].astype(np.int32)); count[str(c)] = len(ids)
        sources.append(dict(source, image_sha256=sha(source['image']), reference_sha256=sha(source['reference']), samples=count))
    cv2.setRNGSeed(42); rf = cv2.ml.RTrees_create(); rf.setMaxDepth(18); rf.setMinSampleCount(12); rf.setActiveVarCount(6); rf.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER, 65, 0))
    assert rf.train(np.concatenate(xs), cv2.ml.ROW_SAMPLE, np.concatenate(ys))
    rf.save(str(model)); Path(out).write_text(json.dumps({'sources': sources, 'model_sha256': sha(model), 'classes': ['background', 'wall-band', 'portal-band'], 'features': 31, 'validation': 'Training maps are development only; Conyberry is blind image-only test without ground truth.'}, indent=2))


def render_prediction(image, prediction):
    overlay=image.copy(); large=cv2.resize(prediction,(image.shape[1],image.shape[0]),interpolation=cv2.INTER_NEAREST)
    # Magenta is reserved for reference geometry in the review.
    for cls,color in [(1,(0,255,0)),(2,(66,174,255))]:
        overlay[large==cls]=(overlay[large==cls]*.35+np.array(color)*.65).astype(np.uint8)
    return overlay


def infer(image_path, model, out):
    start=time.perf_counter(); im=cv2.imread(str(image_path)); assert im is not None
    f=features(im); rf=cv2.ml.RTrees_load(str(model)); assert rf.getVarCount()==f.shape[2]
    flat=f.reshape(-1,f.shape[2]); probs=[]
    for i in range(0,len(flat),100000):
        votes=rf.getVotes(flat[i:i+100000],0); classes=votes[0]; assert np.array_equal(classes, [0,1,2]); counts=votes[1:].astype(np.float32); probs.append(counts/counts.sum(axis=1,keepdims=True))
    p=np.concatenate(probs).reshape(*f.shape[:2],3)
    # shortcut: thresholded bands are proposals, not centerlines or connected LOS geometry.
    pred=np.argmax(p,axis=2).astype(np.uint8); pred[np.max(p,axis=2)<.55]=0
    overlay=render_prediction(im,pred)
    out=Path(out); out.mkdir(parents=True,exist_ok=True)
    cv2.imwrite(str(out/'overlay.jpg'),overlay); cv2.imwrite(str(out/'classes.png'),pred)
    for c in (1,2): cv2.imwrite(str(out/f'probability-{c}.png'),np.rint(p[:,:,c]*255).astype(np.uint8))
    cv2.imwrite(str(out/'source.jpg'),im)
    report={'image':str(image_path),'image_sha256':sha(image_path),'model_sha256':sha(model),'shape':list(im.shape),'reference_read':False,'seconds':time.perf_counter()-start,'wall_band_fraction':float(np.mean(pred==1)),'portal_band_fraction':float(np.mean(pred==2)),'threshold':.55,'scale':SCALE}
    (out/'inference.json').write_text(json.dumps(report,indent=2)); print(json.dumps(report))


def selfcheck():
    import tempfile
    portal=render_prediction(np.zeros((1,1,3),np.uint8),np.full((1,1),2,np.uint8))[0,0]
    assert portal[2]>portal[1]>portal[0],"Predicted portals must be orange, not reference magenta"
    with tempfile.TemporaryDirectory() as tmp:
        ref=Path(tmp)/'r.json'; ref.write_text(json.dumps({'resolution':{'pixels_per_grid':4},'line_of_sight':[[{'x':2,'y':2},{'x':15,'y':2},{'x':15,'y':15}]],'portals':[{'bounds':[{'x':2,'y':18},{'x':10,'y':18}]}]}))
        y=labels(ref,(24,24)); assert y[10,7]==0 and y[2,8]==1 and y[18,6]==2 and y[10,2]==0
        assert features(np.zeros((96,96,3),np.uint8)).shape==(24,24,31)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__); sub=p.add_subparsers(dest='command',required=True)
    t=sub.add_parser('train'); t.add_argument('config'); t.add_argument('model'); t.add_argument('report')
    i=sub.add_parser('infer'); i.add_argument('image'); i.add_argument('model'); i.add_argument('out')
    sub.add_parser('selfcheck'); a=p.parse_args()
    if a.command=='train': train(a.config,a.model,a.report)
    elif a.command=='infer': infer(a.image,a.model,a.out)
    else: selfcheck()
