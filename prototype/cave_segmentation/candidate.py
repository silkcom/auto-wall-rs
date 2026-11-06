"""Throwaway reusable CPU candidate. Reference coordinates are train-only."""
import argparse, hashlib, json, time
from pathlib import Path
import cv2
import numpy as np
SCALE=4

def features(image):
    small=cv2.resize(image,None,fx=1/SCALE,fy=1/SCALE,interpolation=cv2.INTER_AREA)
    lab=cv2.cvtColor(small,cv2.COLOR_BGR2LAB).astype(np.float32)/255
    gray=cv2.cvtColor(small,cv2.COLOR_BGR2GRAY).astype(np.float32)/255
    parts=[lab]
    for k in (3,9,25):
        mean=cv2.blur(lab,(k,k)); parts.extend([mean,np.sqrt(np.maximum(cv2.blur(lab*lab,(k,k))-mean*mean,0))])
    gx=cv2.Sobel(gray,cv2.CV_32F,1,0);gy=cv2.Sobel(gray,cv2.CV_32F,0,1)
    parts.extend([cv2.magnitude(gx,gy)[:,:,None],gray[:,:,None]])
    return np.concatenate(parts,axis=2)

def reference_labels(reference,shape):
    d=json.load(open(reference)); ppg=d['resolution']['pixels_per_grid']; mask=np.zeros(shape,np.uint8)
    for group in ('line_of_sight','objects_line_of_sight'):
        for path in d.get(group,[]):
            points=np.array([[p['x']*ppg/SCALE,p['y']*ppg/SCALE] for p in path],np.int32)
            if len(points)>2 and path[0]==path[-1]:
                poly=np.zeros(shape,np.uint8);cv2.fillPoly(poly,[points],1);mask^=poly
    return mask

def open_reference_band(reference,shape):
    d=json.load(open(reference));ppg=d["resolution"]["pixels_per_grid"];band=np.zeros(shape,np.uint8)
    for group in ("line_of_sight","objects_line_of_sight"):
        for path in d.get(group,[]):
            if len(path)>1 and path[0]!=path[-1]:
                points=np.array([[p["x"]*ppg/SCALE,p["y"]*ppg/SCALE] for p in path],np.int32)
                cv2.polylines(band,[points],False,1,9)
    return band>0

def train(image,reference,model,out):
    t=time.perf_counter();im=cv2.imread(image);f=features(im);y=reference_labels(reference,f.shape[:2]); h,w=y.shape
    yy,xx=np.indices(y.shape); tile=128; guard=16
    # Tile identity partitions space; every boundary has a 64-original-pixel guard.
    core=(xx%tile>=guard)&(xx%tile<tile-guard)&(yy%tile>=guard)&(yy%tile<tile-guard)
    core &= ~open_reference_band(reference,y.shape)
    held=((xx//tile+2*(yy//tile))%4==0)&core;training=(~((xx//tile+2*(yy//tile))%4==0))&core
    # Exclude ambiguous 12-pixel band near human polygon boundaries from training.
    edge=cv2.morphologyEx(y,cv2.MORPH_GRADIENT,np.ones((7,7),np.uint8))>0
    rng=np.random.default_rng(42);indices=[]
    for cls in (0,1):
        eligible=np.flatnonzero(training&~edge&(y==cls));indices.extend(rng.choice(eligible,min(40000,len(eligible)),False))
    indices=np.array(indices);cv2.setRNGSeed(42);forest=cv2.ml.RTrees_create();forest.setMaxDepth(18);forest.setMinSampleCount(12);forest.setActiveVarCount(5);forest.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER,65,0));forest.train(f.reshape(-1,f.shape[2])[indices],cv2.ml.ROW_SAMPLE,y.ravel()[indices].astype(np.int32));forest.save(model)
    pred=forest.predict(f.reshape(-1,f.shape[2]))[1].reshape(y.shape).astype(np.uint8)
    def metrics(region):
        a=pred[region]>0;b=y[region]>0
        return {'pixels':int(a.size),'accuracy':float((a==b).mean()),'floor_iou':float((a&b).sum()/max(1,(a|b).sum()))}
    result={'train':metrics(training),'spatial_heldout':metrics(held),'seconds':time.perf_counter()-t,'scale':SCALE,'training_samples':len(indices),'features':f.shape[2],'warning':'One map only; spatial holdout is not independent-map validation.'}
    Path(out).mkdir(parents=True,exist_ok=True);cv2.imwrite(out+'/training-labels.png',y*255);cv2.imwrite(out+'/heldout-tiles.png',held.astype(np.uint8)*255);Path(out+'/training.json').write_text(json.dumps(result,indent=2));print(json.dumps(result))

def infer(image,model,out):
    t=time.perf_counter();im=cv2.imread(image);f=features(im);forest=cv2.ml.RTrees_load(model);pred=forest.predict(f.reshape(-1,f.shape[2]))[1].reshape(f.shape[:2]).astype(np.uint8)
    # Local morphology is image/model-only; no geographic seeds or coordinates.
    mask=cv2.morphologyEx(pred,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8))
    n,ids,stats,_=cv2.connectedComponentsWithStats(mask)
    mask=np.isin(ids,np.flatnonzero((stats[:,cv2.CC_STAT_AREA]>=120)&(np.arange(n)>0))).astype(np.uint8) if n>1 else np.zeros_like(mask)
    contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE);walls=[];overlay=im.copy()
    for c in contours:
        if cv2.contourArea(c)<80:continue
        p=cv2.approxPolyDP(c,1.5,True).reshape(-1,2)*SCALE
        for a,b in zip(p,np.roll(p,-1,axis=0)):
            # Raster clipping edges are not evidence of walls.
            if any(a[j]==b[j] and a[j] in (0,(f.shape[1-j]-1)*SCALE) for j in (0,1)):continue
            walls.append([int(a[0]),int(a[1]),int(b[0]),int(b[1])]);cv2.line(overlay,tuple(a),tuple(b),(0,0,255),3)
    Path(out).mkdir(parents=True,exist_ok=True);cv2.imwrite(out+'/raw-mask.png',pred*255);cv2.imwrite(out+'/mask.png',mask*255);cv2.imwrite(out+'/overlay.jpg',cv2.resize(overlay,None,fx=.25,fy=.25));Path(out+'/walls.json').write_text(json.dumps({'walls':walls}));report={'seconds':time.perf_counter()-t,'segments':len(walls),'image':str(Path(image).resolve()),'model_sha256':hashlib.sha256(Path(model).read_bytes()).hexdigest(),'inference_inputs':['image pixels','random forest model'],'reference_read':False,'floor_fraction':float(mask.mean())};Path(out+'/inference.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('mode',choices=['train','infer']);p.add_argument('image');p.add_argument('model');p.add_argument('out');p.add_argument('--reference');a=p.parse_args()
    if a.mode=='train':train(a.image,a.reference,a.model,a.out)
    else:infer(a.image,a.model,a.out)
