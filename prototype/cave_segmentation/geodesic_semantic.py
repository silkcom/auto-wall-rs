"""Throwaway local-feature geodesic propagation of image-only semantic seeds.

Run SAMPLES LABELS OUTPUT. No reference geometry, global RF, or GrabCut.
"""
import argparse, heapq, json, time
from pathlib import Path
import cv2
import numpy as np
from candidate import features,SCALE


def propagate(f,seeds):
    h,w=seeds.shape
    # Scale every feature by its own map-wide variation; feature distance is local.
    spread=np.std(f,axis=(0,1));z=f/np.maximum(spread,.03)
    horizontal=.002+np.mean(np.diff(z,axis=1)**2,axis=2)
    vertical=.002+np.mean(np.diff(z,axis=0)**2,axis=2)
    costs=np.full(h*w,np.inf,np.float64);owners=np.full(h*w,255,np.uint8)
    horizontal=horizontal.ravel();vertical=vertical.ravel();queue=[]
    for i in np.flatnonzero(seeds.ravel()!=255):
        costs[i]=0;owners[i]=seeds.ravel()[i];queue.append((0.,int(i)))
    heapq.heapify(queue)
    while queue:
        distance,i=heapq.heappop(queue)
        if distance!=costs[i]:continue
        y,x=divmod(i,w)
        neighbors=[]
        if x:neighbors.append((i-1,horizontal[y*(w-1)+x-1]))
        if x<w-1:neighbors.append((i+1,horizontal[y*(w-1)+x]))
        if y:neighbors.append((i-w,vertical[i-w]))
        if y<h-1:neighbors.append((i+w,vertical[i]))
        for j,weight in neighbors:
            proposal=distance+float(weight)
            if proposal<costs[j]:
                costs[j]=proposal;owners[j]=owners[i];heapq.heappush(queue,(proposal,j))
    assert np.all(owners!=255)
    return owners.reshape(h,w),costs.reshape(h,w)


def run(a):
    start=time.perf_counter();samples=json.loads(Path(a.samples).read_text());labels=json.loads(Path(a.labels).read_text())['labels'];im=cv2.imread(samples['image']);assert im is not None
    f=features(im);h,w=f.shape[:2];seeds=np.full((h,w),255,np.uint8)
    for point in samples['samples']:
        label=labels.get(point['id'],'unknown')
        if label not in ('floor','solid'):continue
        x=min(w-1,point['x']//SCALE);y=min(h-1,point['y']//SCALE)
        # Single pixel: seed patches must not silently cross a narrow boundary.
        seeds[y,x]=int(label=='floor')
    assert set(np.unique(seeds))>={0,1}
    floor,distance=propagate(f,seeds);assert np.all(floor[seeds!=255]==seeds[seeds!=255])
    seconds=time.perf_counter()-start;out=Path(a.out);out.mkdir(parents=True,exist_ok=True)
    contours,_=cv2.findContours(floor,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE);walls=[];overlay=im.copy()
    for c in contours:
        q=cv2.approxPolyDP(c,1.,True).reshape(-1,2)*SCALE
        if len(q)<3:continue
        for u,v in zip(q,np.roll(q,-1,axis=0)):
            if any(u[j]==v[j]and u[j]in(0,(f.shape[1-j]-1)*SCALE)for j in(0,1)):continue
            walls.append([int(u[0]),int(u[1]),int(v[0]),int(v[1])]);cv2.line(overlay,tuple(u),tuple(v),(0,0,255),3)
    cv2.imwrite(str(out/'mask.png'),floor*255);cv2.imwrite(str(out/'overlay.jpg'),cv2.resize(overlay,None,fx=.25,fy=.25));cv2.imwrite(str(out/'distance.png'),np.uint8(np.clip(distance/max(1e-6,float(np.percentile(distance,99))),0,1)*255));(out/'walls.json').write_text(json.dumps({'walls':walls}))
    report={'image':samples['image'],'reference_read':False,'inputs':['image features','automatic sample coordinates','AI semantic labels'],'method':'4-neighbor additive geodesic shortest path; edge .002 + standardized multiscale feature squared difference','scale':SCALE,'seconds_features_and_solver':seconds,'segments':len(walls),'floor_fraction':float(floor.mean()),'seeds':int(np.count_nonzero(seeds!=255)),'seed_agreement':1.,'limitations':'Forced seed agreement is not accuracy. Missing region seeds or weak boundaries can cause global leaks; no open-line class.'};(out/'inference.json').write_text(json.dumps(report,indent=2));print(json.dumps(report))

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('samples');p.add_argument('labels');p.add_argument('out');run(p.parse_args())
