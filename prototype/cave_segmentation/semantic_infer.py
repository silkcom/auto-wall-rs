"""Image-only semantic samples -> CPU material model -> deterministic pixel tracing."""
import argparse,json,time,hashlib
from pathlib import Path
import cv2,numpy as np
from candidate import features,SCALE
p=argparse.ArgumentParser();p.add_argument('samples');p.add_argument('labels');p.add_argument('out');p.add_argument('--balanced',action='store_true');a=p.parse_args();t=time.perf_counter();samples=json.load(open(a.samples));labels=json.load(open(a.labels))['labels'];im=cv2.imread(samples['image']);f=features(im);h,w=f.shape[:2];X=[];Y=[];seeds=np.full((h,w),255,np.uint8)
for r in samples['samples']:
 label=labels.get(r['id'],'unknown')
 if label not in ('floor','solid'):continue
 target=int(label=='floor');x=min(w-1,r['x']//SCALE);y=min(h-1,r['y']//SCALE)
 for yy in range(max(0,y-1),min(h,y+2)):
  for xx in range(max(0,x-1),min(w,x+2)):X.append(f[yy,xx]);Y.append(target);seeds[yy,xx]=target
assert set(Y)=={0,1},'Need confident examples of floor and solid'
if a.balanced:
 # Sample frequency reflects audit policy, not the true image class prior.
 groups=[np.flatnonzero(np.asarray(Y)==k)for k in(0,1)];n=max(map(len,groups));rng=np.random.default_rng(42);indices=np.concatenate([rng.choice(g,n,replace=len(g)<n)for g in groups]);X=np.asarray(X)[indices];Y=np.asarray(Y)[indices];assert np.count_nonzero(Y==0)==np.count_nonzero(Y==1)
cv2.setRNGSeed(42);rf=cv2.ml.RTrees_create();rf.setMaxDepth(12);rf.setMinSampleCount(3);rf.setActiveVarCount(5);rf.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER,65,0));rf.train(np.asarray(X,np.float32),cv2.ml.ROW_SAMPLE,np.asarray(Y,np.int32));votes=rf.getVotes(f.reshape(-1,f.shape[2]),0);classes=votes[0];counts=votes[1:].astype(np.float32);prob=(counts[:,np.flatnonzero(classes==1)[0]]/counts.sum(axis=1)).reshape(h,w);raw=(prob>.5).astype(np.uint8)
# Four fixed image-guided solver passes; only explicit semantic seeds are hard constraints.
small=cv2.resize(im,(w,h),interpolation=cv2.INTER_AREA);mask=np.where(prob>.5,cv2.GC_PR_FGD,cv2.GC_PR_BGD).astype(np.uint8);mask[seeds==1]=cv2.GC_FGD;mask[seeds==0]=cv2.GC_BGD
bg=np.zeros((1,65),np.float64);fg=np.zeros((1,65),np.float64);cv2.grabCut(small,mask,None,bg,fg,4,cv2.GC_INIT_WITH_MASK);floor=np.isin(mask,[cv2.GC_FGD,cv2.GC_PR_FGD]).astype(np.uint8)
# Keep meaningful small solid obstacles; suppress only sub-8px raster speckles.
floor=cv2.morphologyEx(floor,cv2.MORPH_CLOSE,np.ones((3,3),np.uint8))
contours,_=cv2.findContours(floor,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE);walls=[]
for c in contours:
 if cv2.contourArea(c)<4:continue
 q=cv2.approxPolyDP(c,1.0,True).reshape(-1,2)*SCALE
 for u,v in zip(q,np.roll(q,-1,axis=0)):
  if np.array_equal(u,v):continue
  if any(u[j]==v[j]and u[j]in(0,(f.shape[1-j]-1)*SCALE)for j in(0,1)):continue
  walls.append([int(u[0]),int(u[1]),int(v[0]),int(v[1])])
seconds=time.perf_counter()-t;out=Path(a.out);out.mkdir(parents=True,exist_ok=True);rf.save(str(out/'material-model.xml'));np.save(out/'probability.npy',prob);cv2.imwrite(str(out/'raw-mask.png'),raw*255);cv2.imwrite(str(out/'mask.png'),floor*255);(out/'walls.json').write_text(json.dumps({'walls':walls}));overlay=im.copy()
for x,y,u,v in walls:cv2.line(overlay,(x,y),(u,v),(0,0,255),3)
cv2.imwrite(str(out/'overlay.jpg'),cv2.resize(overlay,None,fx=.25,fy=.25));report={'seconds':seconds,'segments':len(walls),'semantic_labels':{k:list(labels.values()).count(k)for k in ['floor','solid','unknown']},'image':samples['image'],'inputs':['raster','automatically selected sample coordinates','AI semantic class labels'],'reference_read':False,'balanced_training':a.balanced,'solver_passes':4,'floor_fraction':float(floor.mean()),'limitations':'AI labels are sparse semantic guesses; no independent-map groundtruth validation.'};(out/'inference.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))
