"""Second semantic-label round: uncertainty and confidence audits, image/model only."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from candidate import SCALE
p=argparse.ArgumentParser();p.add_argument('directory');p.add_argument('--prior');p.add_argument('--probability');p.add_argument('--start-id',type=int,default=49);a=p.parse_args();out=Path(a.directory);out.mkdir(parents=True,exist_ok=True);d=json.load(open(a.prior or out/'samples.json'));im=cv2.imread(d['image']);prob=np.load(a.probability or out/'result/probability.npy');h,w=prob.shape;rng=np.random.default_rng(321);chosen=[];old=np.array([[s['x']/SCALE,s['y']/SCALE]for s in d['samples']]);
# A 4x4 coverage grid avoids spending every query on the same uncertain boundary.
for ty in range(4):
 for tx in range(4):
  x0,x1=tx*w//4,(tx+1)*w//4;y0,y1=ty*h//4,(ty+1)*h//4
  yy,xx=np.mgrid[y0:y1,x0:x1];points=np.column_stack((xx.ravel(),yy.ravel()));v=prob[y0:y1,x0:x1].ravel();entropy=1-np.abs(v-.5)*2
  # Three generic query policies: uncertain material; tile center; confident counterexample audit.
  order=np.argsort(-entropy)
  candidates=[points[i]for i in order[:min(1500,len(order))]]
  confident=points[(v<=.1)|(v>=.9)];confident=confident if len(confident)else points
  policies=[candidates,[np.array([(x0+x1)//2,(y0+y1)//2])],list(confident[rng.choice(len(confident),min(1000,len(confident)),False)])]
  for policy,items in enumerate(policies):
   for q in items:
    used=np.concatenate((old,np.array(chosen).reshape(-1,2)))if chosen else old
    if np.min(np.linalg.norm(used-q,axis=1))>=8:
     chosen.append(q.tolist());break
records=[{'id':f'P{a.start_id+i:02}','x':int((x+.5)*SCALE),'y':int((y+.5)*SCALE),'policy':'uncertainty/coverage/confidence audit'}for i,(x,y)in enumerate(chosen)]
assert len({(r['x'],r['y']) for r in records})==len(records)
for page in range(2):
 sheet=np.full((960,640,3),235,np.uint8)
 for j,r in enumerate(records[page*24:(page+1)*24]):
  x,y=r['x'],r['y'];rad=128;crop=im[max(0,y-rad):min(im.shape[0],y+rad),max(0,x-rad):min(im.shape[1],x+rad)];tile=np.zeros((256,256,3),np.uint8);sx=max(0,rad-x);sy=max(0,rad-y);tile[sy:sy+crop.shape[0],sx:sx+crop.shape[1]]=crop;tile=cv2.resize(tile,(144,144));cv2.drawMarker(tile,(72,72),(255,255,255),cv2.MARKER_CROSS,9,1);bx=(j%4)*160;by=(j//4)*160;sheet[by+16:by+160,bx+8:bx+152]=tile;cv2.putText(sheet,r['id'],(bx+8,by+13),0,.42,(0,0,0),1)
 cv2.imwrite(str(out/f'active-contacts-{page+1}.jpg'),sheet)
(out/'samples-active.json').write_text(json.dumps({**d,'samples':records},indent=2));print(len(records),'new samples')
