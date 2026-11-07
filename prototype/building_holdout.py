"""Frozen whole-graph spatial development split; never independent-map validation."""
import json
from pathlib import Path
import cv2
import numpy as np
from building_model import features, labels, sha, render_prediction

OUT=Path('/private/tmp/auto-wall-building-holdout')
IMAGE='/Users/josephlarsen/Sites/bagofmapping/static/images/partners/morvold/RestoredConyberryPhase3Large.jpg'
REF='/private/tmp/auto-wall-algorithm/conyberry-handdrawn-reference.dd2vtt'
GUARD=26 # 104 source pixels, covers both feature variants including resize support.

def context(image):
    f=features(image); gray=cv2.cvtColor(cv2.resize(image,(f.shape[1],f.shape[0]),interpolation=cv2.INTER_AREA),cv2.COLOR_BGR2GRAY).astype(np.float32)/255
    mean=cv2.blur(gray,(49,49)); std=np.sqrt(np.maximum(cv2.blur(gray*gray,(49,49))-mean*mean,0))
    return np.concatenate([f,mean[...,None],std[...,None]],2)

def freeze(shape):
    d=json.loads(Path(REF).read_text()); graph=np.zeros(shape,np.uint8); ppg=d['resolution']['pixels_per_grid']; origin=d['resolution'].get('map_origin',{'x':0,'y':0})
    paths=d.get('line_of_sight',[])+d.get('objects_line_of_sight',[])+[x['bounds'] for x in d.get('portals',[])]
    for path in paths:
        pts=np.rint([[(p['x']-origin['x'])*ppg/4,(p['y']-origin['y'])*ppg/4] for p in path]).astype(np.int32)
        if len(pts)>1: cv2.polylines(graph,[pts],False,1,1)
    # Raster endpoint tolerance joins nearly coincident hand-drawn anchors.
    n,_,stats,_=cv2.connectedComponentsWithStats(cv2.dilate(graph,np.ones((3,3),np.uint8)))
    boxes=[[int(x),int(y),int(x+w),int(y+h)] for x,y,w,h,a in stats[1:]]
    def overlap(a,b): return a[0]<=b[2] and b[0]<=a[2] and a[1]<=b[3] and b[1]<=a[3]
    changed=True
    while changed:
        changed=False
        for i in range(len(boxes)):
            for j in range(i+1,len(boxes)):
                if overlap(boxes[i],boxes[j]):
                    a,b=boxes[i],boxes.pop(j);boxes[i]=[min(a[0],b[0]),min(a[1],b[1]),max(a[2],b[2]),max(a[3],b[3])];changed=True;break
            if changed:break
    boxes.sort(key=lambda b:((b[0]+b[2])/2,(b[1]+b[3])/2))
    train=np.zeros(shape,np.uint8);held=train.copy()
    groups=[]
    for i,b in enumerate(boxes):
        x0,y0,x1,y1=b;x0=max(0,x0-6);y0=max(0,y0-6);x1=min(shape[1],x1+6);y1=min(shape[0],y1+6)
        target=held if i%2 else train;target[y0:y1,x0:x1]=1
        groups.append({'id':i,'bbox_xyxy_lowres':b,'partition':'heldout' if i%2 else 'train'})
    # All held-out building boxes remain intact; remove nearby train pixels so
    # even the widest train and validation receptive windows cannot overlap.
    train[cv2.dilate(held,np.ones((4*GUARD+1,4*GUARD+1),np.uint8))>0]=0
    assert not np.any(cv2.dilate(train,np.ones((2*GUARD+1,2*GUARD+1),np.uint8)) & cv2.dilate(held,np.ones((2*GUARD+1,2*GUARD+1),np.uint8)))
    terrain=(cv2.dilate(train|held,np.ones((4*GUARD+1,4*GUARD+1),np.uint8))==0)
    split={'method':'connected raster graphs including doors; merge intersecting/nested bboxes to fixed point; alternate ascending bbox-center x','groups':groups,'scale':4,'guard_source_pixels':GUARD*4,'train_exclusion_source_pixels':GUARD*8,'seed':42,'image_sha256':sha(IMAGE),'reference_sha256':sha(REF),'warning':'Spatial development validation, not independent-map generalization; raster endpoint tolerance 4 source pixels; masks measure bands, not UVTT geometry.'}
    (OUT/'split.json').write_text(json.dumps(split,indent=2))
    for name,m in [('train-mask',train),('heldout-mask',held),('unannotated-terrain-mask',terrain)]:cv2.imwrite(str(OUT/f'{name}.png'),m.astype(np.uint8)*255)
    return train>0,held>0,terrain

def scores(pred,y,region):
    result={}
    for c in (1,2):
        eligible=region&(y!=255); truth=(y==c)&eligible; guess=(pred==c)&eligible;tp=int((truth&guess).sum());fp=int((guess&~truth).sum());fn=int((truth&~guess).sum())
        result[str(c)]={'target_pixels':int(truth.sum()),'tp':tp,'fp':fp,'fn':fn,'recall':tp/max(1,tp+fn),'precision':tp/max(1,tp+fp)}
    result['background_pixels']=int((region&(y==0)).sum());result['background_predicted_wall_or_portal']=int((region&(y==0)&(pred>0)).sum())
    return result

def run():
    OUT.mkdir(exist_ok=True); image=cv2.imread(IMAGE); assert image is not None
    y=labels(REF,features(image).shape[:2]);train,held,terrain=freeze(y.shape)
    assert np.any(train&(y==1)) and np.any(held&(y==1))
    prior=json.loads(Path('/private/tmp/auto-wall-building-model/train.json').read_text());reports={}
    for name,fn in [('baseline',features),('context',context)]:
        folder=OUT/name;folder.mkdir(exist_ok=True);rng=np.random.default_rng(42);xs=[];ys=[];sources=[]
        for source in prior+[{'image':IMAGE,'reference':REF}]:
            im=cv2.imread(source['image']);f=fn(im);target=labels(source['reference'],f.shape[:2]);mask=train if source['image']==IMAGE else np.ones(target.shape,bool);counts={}
            for c in range(3):
                ids=np.flatnonzero(mask&(target==c));ids=rng.choice(ids,min(16000,len(ids)),False);assert len(ids);xs.append(f.reshape(-1,f.shape[2])[ids]);ys.append(target.ravel()[ids].astype(np.int32));counts[str(c)]=len(ids)
            sources.append(dict(source,image_sha256=sha(source['image']),reference_sha256=sha(source['reference']),samples=counts))
        cv2.setRNGSeed(42);rf=cv2.ml.RTrees_create();rf.setMaxDepth(18);rf.setMinSampleCount(12);rf.setActiveVarCount(6);rf.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER,65,0));assert rf.train(np.concatenate(xs),cv2.ml.ROW_SAMPLE,np.concatenate(ys));rf.save(str(folder/'model.xml'))
        f=fn(image);flat=f.reshape(-1,f.shape[2]);probs=[]
        for start in range(0,len(flat),100000):
            v=rf.getVotes(flat[start:start+100000],0);assert np.array_equal(v[0],[0,1,2]);v=v[1:].astype(np.float32);probs.append(v/v.sum(1,keepdims=True))
        p=np.concatenate(probs).reshape(*y.shape,3);pred=p.argmax(2).astype(np.uint8);pred[p.max(2)<.55]=0
        cv2.imwrite(str(folder/'classes.png'),pred)
        for c in (1,2):cv2.imwrite(str(folder/f'probability-{c}.png'),np.rint(p[:,:,c]*255).astype(np.uint8))
        overlay=render_prediction(image,pred);small=cv2.resize(overlay,(y.shape[1],y.shape[0]),interpolation=cv2.INTER_AREA)
        for m,color in [(train,(255,255,0)),(held,(255,0,255))]:
            contours,_=cv2.findContours(m.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(small,contours,-1,color,2)
        cv2.putText(small,'CYAN train / MAGENTA heldout; GREEN wall / ORANGE door',(8,18),cv2.FONT_HERSHEY_SIMPLEX,.42,(255,255,255),1)
        cv2.imwrite(str(folder/'overlay.jpg'),small)
        report={'features':f.shape[2],'sources':sources,'model_sha256':sha(folder/'model.xml'),'split_sha256':sha(OUT/'split.json'),'threshold':.55,'heldout':scores(pred,y,held),'training':scores(pred,y,train),'unannotated_terrain':{'pixels':int(terrain.sum()),'predicted_wall_pixels':int(((pred==1)&terrain).sum()),'predicted_portal_pixels':int(((pred==2)&terrain).sum()),'interpretation':'Unannotated background proxy; fences/roads not semantically labeled. Predictions are not verified false positives.'},'inference_inputs':['image pixels','trained model'],'limitations':['Reference bands are training objective; appearance boundaries can be offset from accepted LOS.','No geometric wall/door accuracy is implied.','Conyberry training and validation share image/art style.']}
        (folder/'provenance.json').write_text(json.dumps(report,indent=2));reports[name]=report
        print(name,json.dumps(report['heldout']),flush=True)
    (OUT/'scores.json').write_text(json.dumps(reports,indent=2))

def model_predict(image, model):
    """Global image/model-only inference; reference and region masks are not inputs."""
    f=features(image);flat=f.reshape(-1,f.shape[2]);rf=cv2.ml.RTrees_load(str(model));assert rf.getVarCount()==31
    probs=[]
    for start in range(0,len(flat),100000):
        v=rf.getVotes(flat[start:start+100000],0);assert np.array_equal(v[0],[0,1,2]);v=v[1:].astype(np.float32);probs.append(v/v.sum(1,keepdims=True))
    p=np.concatenate(probs).reshape(*f.shape[:2],3);pred=p.argmax(2).astype(np.uint8);pred[p.max(2)<.55]=0
    return pred,p

def hard_negative(balanced=False):
    folder=OUT/('hard-negative-balanced' if balanced else 'hard-negative');folder.mkdir(exist_ok=True)
    split_sha=sha(OUT/'split.json');image=cv2.imread(IMAGE);assert image is not None
    train=cv2.imread(str(OUT/'train-mask.png'),0)>0;held=cv2.imread(str(OUT/'heldout-mask.png'),0)>0;terrain=cv2.imread(str(OUT/'unannotated-terrain-mask.png'),0)>0
    y=labels(REF,train.shape)
    allowed=cv2.dilate(held.astype(np.uint8),np.ones((4*GUARD+1,4*GUARD+1),np.uint8))==0
    background=allowed&(y==0)
    assert not np.any(cv2.dilate(background.astype(np.uint8),np.ones((2*GUARD+1,2*GUARD+1),np.uint8)) & cv2.dilate(held.astype(np.uint8),np.ones((2*GUARD+1,2*GUARD+1),np.uint8)))
    baseline,p=model_predict(image,OUT/'baseline/model.xml');eligible=np.flatnonzero(background)
    confidence=p[:,:,1:].max(2).ravel()[eligible]
    # Fixed hypothesis: half uniform, half greatest false-positive confidence;
    # ties use raster index, never held-out measurements or manual coordinates.
    hard=eligible[np.lexsort((eligible,-confidence))[:8000]]
    rng=np.random.default_rng(42);xs=[];ys=[];sources=[]
    prior=json.loads(Path('/private/tmp/auto-wall-building-model/train.json').read_text())
    for source in prior+[{'image':IMAGE,'reference':REF}]:
        is_cony=source['image']==IMAGE;im=image if is_cony else cv2.imread(source['image']);f=features(im);target=y if is_cony else labels(source['reference'],f.shape[:2]);mask=train if is_cony else np.ones(target.shape,bool);counts={}
        for c in range(3):
            if is_cony and c==0:
                uniform=rng.choice(np.setdiff1d(eligible,hard),8000,False);ids=np.concatenate([uniform,hard]);assert len(np.unique(ids))==16000
            else:
                ids=np.flatnonzero(mask&(target==c));ids=rng.choice(ids,min(16000,len(ids)),False)
            assert len(ids);xs.append(f.reshape(-1,31)[ids]);ys.append(target.ravel()[ids].astype(np.int32));counts[str(c)]=len(ids)
        sources.append(dict(source,image_sha256=sha(source['image']),reference_sha256=sha(source['reference']),samples=counts))
    train_x=np.concatenate(xs);train_y=np.concatenate(ys);class_counts=np.bincount(train_y,minlength=3)
    if balanced:
        # Repeat minority examples deterministically; held-out pixels never enter.
        balanced_ids=[]
        for c in range(3):
            ids=np.flatnonzero(train_y==c);extra=rng.choice(ids,int(class_counts.max()-len(ids)),replace=True);balanced_ids.append(np.concatenate([ids,extra]))
        ids=np.concatenate(balanced_ids);train_x=train_x[ids];train_y=train_y[ids]
        assert len(set(np.bincount(train_y,minlength=3)))==1
    cv2.setRNGSeed(42);rf=cv2.ml.RTrees_create();rf.setMaxDepth(18);rf.setMinSampleCount(12);rf.setActiveVarCount(6);rf.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER,65,0));assert rf.train(train_x,cv2.ml.ROW_SAMPLE,train_y);rf.save(str(folder/'model.xml'))
    pred,p=model_predict(image,folder/'model.xml');assert set(np.unique(pred))<={0,1,2}
    cv2.imwrite(str(folder/'classes.png'),pred)
    for c in (1,2):cv2.imwrite(str(folder/f'probability-{c}.png'),np.rint(p[:,:,c]*255).astype(np.uint8))
    overlay=cv2.resize(render_prediction(image,pred),(y.shape[1],y.shape[0]),interpolation=cv2.INTER_AREA)
    for mask,color in [(allowed,(255,255,0)),(held,(255,0,255))]:
        contours,_=cv2.findContours(mask.astype(np.uint8),cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE);cv2.drawContours(overlay,contours,-1,color,1)
    cv2.putText(overlay,'CYAN allowed training / MAGENTA heldout',(8,18),cv2.FONT_HERSHEY_SIMPLEX,.45,(255,255,255),1);cv2.imwrite(str(folder/'overlay.jpg'),overlay)
    cv2.imwrite(str(folder/'permitted-background-mask.png'),background.astype(np.uint8)*255)
    mined=np.zeros(y.shape,np.uint8);mined.ravel()[hard]=255;cv2.imwrite(str(folder/'mined-negatives-mask.png'),mined)
    report={'hypothesis':'One fixed mining pass: 8000 highest nonbackground-vote permitted negatives plus 8000 uniform, no heldout tuning','class_balance':{'oversampled':balanced,'before':class_counts.tolist(),'after':np.bincount(train_y,minlength=3).tolist()},'sources':sources,'features':31,'trees':65,'max_depth':18,'active_vars':6,'min_sample_count':12,'seed':42,'threshold':.55,'split_sha256':split_sha,'model_sha256':sha(folder/'model.xml'),'baseline_model_sha256':sha(OUT/'baseline/model.xml'),'permitted_background_pixels':int(background.sum()),'mined_confidence_range':[float(confidence[np.isin(eligible,hard)].min()),float(confidence.max())],'baseline_permitted_background_fp':int((background&(baseline>0)).sum()),'refined_permitted_background_fp':int((background&(pred>0)).sum()),'heldout':scores(pred,y,held),'training_buildings':scores(pred,y,train),'terrain':{'pixels':int(terrain.sum()),'baseline_wall':int((terrain&(baseline==1)).sum()),'baseline_portal':int((terrain&(baseline==2)).sum()),'refined_wall':int((terrain&(pred==1)).sum()),'refined_portal':int((terrain&(pred==2)).sum()),'warning':'Terrain now overlaps permitted training background; training diagnostic, not independent validation. No semantic fence/road labels.'},'global':{'baseline_wall':int((baseline==1).sum()),'baseline_portal':int((baseline==2).sum()),'refined_wall':int((pred==1).sum()),'refined_portal':int((pred==2).sum())},'inference_inputs':['image pixels','trained model'],'warning':'Heldout Conyberry band validation only; not geometry accuracy or independent-map generalization.'}
    assert sha(OUT/'split.json')==split_sha
    (folder/'provenance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

if __name__=='__main__':
    import sys
    if sys.argv[1:]==['hard-negative']:hard_negative()
    elif sys.argv[1:]==['hard-negative-balanced']:hard_negative(True)
    else:run()
