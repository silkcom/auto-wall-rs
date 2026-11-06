"""Freeze development-only reference-labeled appearance examples for a semantic prompt."""
import argparse,json
from pathlib import Path
import cv2,numpy as np
from candidate import reference_labels
p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('directory');a=p.parse_args();d=Path(a.directory);s=json.load(open(d/'samples-combined.json'));old=json.load(open(d/'labels-combined.json'))['labels'];im=cv2.imread(s['image']);mask=reference_labels(a.reference,(im.shape[0]//4,im.shape[1]//4));edge=cv2.morphologyEx(mask,cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8));dist=cv2.distanceTransform(1-edge,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)*4
positives=[];negatives=[]
for r in s['samples']:
 x,y=r['x']//4,r['y']//4
 if dist[y,x]<20:continue
 if mask[y,x]and old.get(r['id'])=='solid':positives.append(r)
 elif not mask[y,x]and old.get(r['id'])=='solid':negatives.append(r)
records=[];sheet=np.full((3*200,4*200,3),235,np.uint8)
for i,(r,cls)in enumerate([(r,'VISIBLE')for r in positives[:6]]+[(r,'SOLID CORE')for r in negatives[:6]]):
 x,y=r['x'],r['y'];rad=128;crop=im[max(0,y-rad):min(im.shape[0],y+rad),max(0,x-rad):min(im.shape[1],x+rad)];tile=np.zeros((256,256,3),np.uint8);sx=max(0,rad-x);sy=max(0,rad-y);tile[sy:sy+crop.shape[0],sx:sx+crop.shape[1]]=crop;tile=cv2.resize(tile,(176,176));cv2.drawMarker(tile,(88,88),(255,255,255),cv2.MARKER_CROSS,9,1);bx=(i%4)*200;by=(i//4)*200;sheet[by+24:by+200,bx+12:bx+188]=tile;cv2.putText(sheet,'E'+str(i+1)+': '+cls,(bx+5,by+18),0,.45,(0,0,0),1);records.append({'example':i+1,'label':cls,'development_sample':r['id']})
cv2.imwrite(str(d/'convention-examples.jpg'),sheet);(d/'convention-examples.json').write_text(json.dumps({'source':'Development reference closed-region side labels only','warning':'Examples teach visible-side vs solid-core convention; not held-out evidence. Freezebeforetestingnewmaps. No referencegeometryusedatinference.','examples':records},indent=2))
