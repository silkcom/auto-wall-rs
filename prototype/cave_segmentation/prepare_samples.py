"""Choose semantic material samples using image features only; no reference geometry."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from candidate import features,SCALE
p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('out');a=p.parse_args();out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
im=cv2.imread(a.image);f=features(im);h,w=f.shape[:2];rng=np.random.default_rng(123);flat=f.reshape(-1,f.shape[2]);idx=rng.choice(len(flat),min(40000,len(flat)),False);sample=flat[idx];cv2.setRNGSeed(123)
_,labels,centers=cv2.kmeans(sample,24,None,(cv2.TERM_CRITERIA_MAX_ITER|cv2.TERM_CRITERIA_EPS,50,.001),1,cv2.KMEANS_PP_CENTERS);records=[]
for k,center in enumerate(centers):
 candidates=idx[labels[:,0]==k]
 if not len(candidates):continue
 dist=np.linalg.norm(flat[candidates]-center,axis=1);top=candidates[np.argsort(dist)[:min(150,len(candidates))]]
 first=top[0];yy,xx=divmod(int(first),w);spatial=np.array([divmod(int(i),w)for i in top]);second=top[np.argmax(((spatial-[yy,xx])**2).sum(axis=1))]
 for index in [first,second]:
  y,x=divmod(int(index),w);records.append({'id':f'P{len(records)+1:02}','x':int((x+.5)*SCALE),'y':int((y+.5)*SCALE),'cluster':k})
for page in range(2):
 chosen=records[page*24:(page+1)*24];sheet=np.full((6*160,4*160,3),235,np.uint8)
 for j,r in enumerate(chosen):
  x,y=r['x'],r['y'];radius=128;crop=im[max(0,y-radius):min(im.shape[0],y+radius),max(0,x-radius):min(im.shape[1],x+radius)]
  # Border patches are padded, keeping the cross at the actual selected image pixel.
  tile=np.zeros((radius*2,radius*2,3),np.uint8);sx=max(0,radius-x);sy=max(0,radius-y);tile[sy:sy+crop.shape[0],sx:sx+crop.shape[1]]=crop
  tile=cv2.resize(tile,(144,144),interpolation=cv2.INTER_AREA);cv2.drawMarker(tile,(72,72),(255,255,255),cv2.MARKER_CROSS,9,1)
  bx=(j%4)*160;by=(j//4)*160;sheet[by+16:by+160,bx+8:bx+152]=tile;cv2.putText(sheet,r['id'],(bx+8,by+13),0,.42,(0,0,0),1)
 cv2.imwrite(str(out/f'contacts-{page+1}.jpg'),sheet)
preview=cv2.resize(im,(int(im.shape[1]*min(1,1000/max(im.shape[:2]))),int(im.shape[0]*min(1,1000/max(im.shape[:2])))),interpolation=cv2.INTER_AREA);cv2.imwrite(str(out/'overview.jpg'),preview)
(out/'samples.json').write_text(json.dumps({'image':a.image,'dimensions':[im.shape[1],im.shape[0]],'samples':records,'method':'24 image-feature clusters, two image-selected representatives each; no coordinates/labels from reference.'},indent=2));print(len(records),'samples')
