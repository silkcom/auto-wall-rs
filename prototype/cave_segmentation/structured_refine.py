"""Throwaway image/model-only refinement; run IMAGE MODEL OUTPUT_PREFIX.

No morphology or component removal: disconnected floor and rock survive.
"""
import argparse
import hashlib
import json
from pathlib import Path
import time
import cv2
import numpy as np
from candidate import SCALE, features


def probability(forest, f):
    flat = f.reshape(-1, f.shape[2])
    chunks = []
    for start in range(0, len(flat), 50000):
        votes = forest.getVotes(flat[start:start+50000], 0)
        classes = votes[0].astype(int)
        assert set(classes) == {0, 1}, classes
        counts = votes[1:].astype(np.float32)
        chunks.append(counts[:, np.flatnonzero(classes == 1)[0]] / counts.sum(axis=1))
    return np.concatenate(chunks).reshape(f.shape[:2])


def icm(p, small):
    # Contrast-sensitive Potts prior, checkerboard updates: local optimization only.
    color = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).astype(np.float32)/255
    dx = np.sum(np.diff(color, axis=1)**2, axis=2)
    dy = np.sum(np.diff(color, axis=0)**2, axis=2)
    beta = 1/(2*max(float((dx.mean()+dy.mean())/2), 1e-6))
    wx = .8*np.exp(-beta*dx); wy = .8*np.exp(-beta*dy)
    clipped = np.clip(p, .005, .995)
    unary0 = -np.log1p(-clipped); unary1 = -np.log(clipped)
    mask = p >= .5
    yy, xx = np.indices(p.shape)
    changes = []
    for _ in range(4):
        changed = 0
        for parity in (0, 1):
            c0 = unary0.copy(); c1 = unary1.copy()
            c0[:, :-1] += wx*mask[:, 1:]; c1[:, :-1] += wx*(~mask[:, 1:])
            c0[:, 1:] += wx*mask[:, :-1]; c1[:, 1:] += wx*(~mask[:, :-1])
            c0[:-1] += wy*mask[1:]; c1[:-1] += wy*(~mask[1:])
            c0[1:] += wy*mask[:-1]; c1[1:] += wy*(~mask[:-1])
            update = ((xx+yy)%2 == parity) & (p>.05) & (p<.95)
            new = c1<c0
            changed += int(np.count_nonzero(update & (mask != new)))
            mask[update] = new[update]
        changes.append(changed)
    return mask.astype(np.uint8), {'changes_per_iteration': changes, 'beta': beta, 'pairwise_weight': .8}


def grabcut(p, small):
    mask = np.where(p>=.5, cv2.GC_PR_FGD, cv2.GC_PR_BGD).astype(np.uint8)
    mask[p<=.05] = cv2.GC_BGD
    mask[p>=.95] = cv2.GC_FGD
    if not (np.any(mask==cv2.GC_BGD) and np.any(mask==cv2.GC_FGD)):
        return (p>=.5).astype(np.uint8), {'skipped': 'Missing confident seeds for both classes; unchanged RF prediction'}
    cv2.setRNGSeed(42)
    cv2.grabCut(small, mask, None, np.zeros((1,65), np.float64), np.zeros((1,65), np.float64), 4, cv2.GC_INIT_WITH_MASK)
    return np.isin(mask, [cv2.GC_FGD, cv2.GC_PR_FGD]).astype(np.uint8), {'iterations': 4, 'hard_seed_thresholds': [.05,.95]}


def save(im, mask, p, out, report):
    out = Path(out); out.mkdir(parents=True, exist_ok=True)
    overlay = im.copy(); walls = []
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    # No component-area threshold: small island topology is part of the experiment.
    for c in contours:
        points = cv2.approxPolyDP(c, .75, True).reshape(-1,2)*SCALE
        if len(points)<3: continue
        for a,b in zip(points,np.roll(points,-1,axis=0)):
            if any(a[j]==b[j] and a[j] in (0,(mask.shape[1-j]-1)*SCALE) for j in (0,1)): continue
            walls.append([int(a[0]),int(a[1]),int(b[0]),int(b[1])])
            cv2.line(overlay,tuple(a),tuple(b),(0,0,255),3)
    cv2.imwrite(str(out/'mask.png'),mask*255)
    cv2.imwrite(str(out/'probability.png'),np.rint(p*255).astype(np.uint8))
    cv2.imwrite(str(out/'overlay.jpg'),cv2.resize(overlay,None,fx=.25,fy=.25))
    (out/'walls.json').write_text(json.dumps({'walls':walls}))
    report.update(segments=len(walls),contours=len(contours),floor_fraction=float(mask.mean()), pixels_changed_from_rf=int(np.count_nonzero(mask!=(p>=.5))))
    (out/'inference.json').write_text(json.dumps(report,indent=2))
    print(json.dumps(report))


def main():
    parser=argparse.ArgumentParser(); parser.add_argument('image');parser.add_argument('model');parser.add_argument('output_prefix');args=parser.parse_args()
    start=time.perf_counter(); im=cv2.imread(args.image); assert im is not None
    f=features(im); forest=cv2.ml.RTrees_load(args.model); assert not forest.empty()
    p=probability(forest,f); assert np.isfinite(p).all() and p.min()>=0 and p.max()<=1
    small=cv2.resize(im,(p.shape[1],p.shape[0]),interpolation=cv2.INTER_AREA)
    shared=time.perf_counter()-start
    for name,solver in [('icm',icm),('grabcut',grabcut)]:
        t=time.perf_counter();mask,detail=solver(p,small)
        assert mask.shape==p.shape and set(np.unique(mask)).issubset({0,1})
        report={'variant':name,'image':str(Path(args.image).resolve()),'model_sha256':hashlib.sha256(Path(args.model).read_bytes()).hexdigest(),'reference_read':False,'inference_inputs':['image pixels','random forest model'],'feature_and_votes_seconds':shared,'solver_seconds':time.perf_counter()-t,'scale':SCALE,**detail}
        save(im,mask,p,args.output_prefix+'-'+name,report)


if __name__=='__main__': main()
