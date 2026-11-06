"""Reuse image-only semantic RF confidence in a fixed four-pass local solver."""
import argparse,json,time
from pathlib import Path
import cv2,numpy as np
from structured_refine import icm,save
p=argparse.ArgumentParser();p.add_argument('samples');p.add_argument('labels');p.add_argument('probability');p.add_argument('out');a=p.parse_args();t=time.perf_counter()
s=json.loads(Path(a.samples).read_text());labels=json.loads(Path(a.labels).read_text())['labels'];im=cv2.imread(s['image']);prob=np.load(a.probability).copy();h,w=prob.shape
assert im is not None and np.isfinite(prob).all() and prob.min()>=0 and prob.max()<=1
fixed=np.full((h,w),-1,np.int8)
for r in s['samples']:
 label=labels.get(r['id'])
 if label not in ('floor','solid'):continue
 x=min(w-1,int(r['x']*w/im.shape[1]));y=min(h-1,int(r['y']*h/im.shape[0]));value=int(label=='floor');fixed[max(0,y-1):min(h,y+2),max(0,x-1):min(w,x+2)]=value
prob[fixed>=0]=fixed[fixed>=0];small=cv2.resize(im,(w,h),interpolation=cv2.INTER_AREA);mask,detail=icm(prob,small)
assert np.all(mask[fixed>=0]==fixed[fixed>=0])
save(im,mask,prob,a.out,{'seconds':time.perf_counter()-t,'reference_read':False,'inputs':['raster','frozen semantic RF probability','sparse semantic labels'],'solver':'four-pass fixed RF unary ICM','hard_seed_pixels':int((fixed>=0).sum()),**detail})
