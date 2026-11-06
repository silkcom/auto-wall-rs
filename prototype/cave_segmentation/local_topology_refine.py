"""Throwaway topology-preserving local refinement of a frozen semantic mask.

Run BASELINE SAMPLES LABELS OUT. No geometry reference or new semantic labels.
"""
import argparse,json,time,hashlib
from pathlib import Path
import cv2,numpy as np
from structured_refine import save


def simple(mask,y,x):
    patch=mask[y-1:y+2,x-1:x+2].copy()
    # The center is excluded; both surrounding classes must remain one component.
    a=patch.copy();a[1,1]=0
    b=1-patch;b[1,1]=0
    solid_adjacent=bool(b[0,1] or b[1,0] or b[1,2] or b[2,1])
    return solid_adjacent and cv2.connectedComponents(a,connectivity=8)[0]==2 and cv2.connectedComponents(b,connectivity=4)[0]==2


def run(a):
    start=time.perf_counter();base=Path(a.baseline);samples=json.loads(Path(a.samples).read_text());labels=json.loads(Path(a.labels).read_text())['labels'];im=cv2.imread(samples['image']);mask=(cv2.imread(str(base/'mask.png'),0)>0).astype(np.uint8);original=mask.copy();h,w=mask.shape
    small=cv2.resize(im,(w,h),interpolation=cv2.INTER_AREA);lab=cv2.cvtColor(small,cv2.COLOR_BGR2LAB).astype(np.float32)/255
    probability=np.load(base/'probability.npy');assert probability.shape==mask.shape
    fixed=np.zeros(mask.shape,bool)
    for r in samples['samples']:
        if labels.get(r['id']) in ('floor','solid'):fixed[min(h-1,r['y']//4),min(w-1,r['x']//4)]=True
    boundary=cv2.morphologyEx(mask,cv2.MORPH_GRADIENT,np.ones((3,3),np.uint8));band=cv2.dilate(boundary,np.ones((5,5),np.uint8))>0
    band[[0,-1],:]=False;band[:,[0,-1]]=False;band&=~fixed
    unary=[]
    for cls in (0,1):
        weight=(original==cls).astype(np.float32);den=cv2.boxFilter(weight,-1,(19,19),normalize=False)
        mean=cv2.boxFilter(lab*weight[:,:,None],-1,(19,19),normalize=False)/np.maximum(den[:,:,None],1)
        # Shortcut: local squared color fit; no second global material classifier.
        unary.append(np.mean((lab-mean)**2,axis=2)/.005+.4*(original!=cls))
    yy,xx=np.indices(mask.shape);changes=[];rejected=[]
    for _ in range(4):
        changed=0;denied=0
        for parity in (0,1):
            costs=[u.copy() for u in unary]
            for dy,dx in ((-1,0),(1,0),(0,-1),(0,1)):
                neighbor=np.roll(mask,(dy,dx),(0,1));neighborcolor=np.roll(lab,(dy,dx),(0,1));edge=.3*np.exp(-np.sum((lab-neighborcolor)**2,axis=2)/.003)
                costs[0]+=edge*neighbor;costs[1]+=edge*(1-neighbor)
            proposed=(costs[1]<costs[0]).astype(np.uint8)
            locations=np.argwhere(band&((yy+xx)%2==parity)&(proposed!=mask))
            for y,x in locations:
                if simple(mask,y,x):mask[y,x]=proposed[y,x];changed+=1
                else:denied+=1
        changes.append(changed);rejected.append(denied)
    def topology(m):
        return {'floor_components':int(cv2.connectedComponents(m,connectivity=8)[0]-1),'solid_components':int(cv2.connectedComponents(1-m,connectivity=4)[0]-1)}
    before=topology(original);after=topology(mask);assert before==after,(before,after)
    assert np.all(mask[fixed]==original[fixed])
    report={'variant':'frozen semantic + topology-preserving local edge refinement','image':samples['image'],'reference_read':False,'inference_inputs':['image','frozen baseline mask/probability','existing semantic seeds'],'baseline_sha256':hashlib.sha256((base/'mask.png').read_bytes()).hexdigest(),'seconds_local_refinement':time.perf_counter()-start,'passes':4,'changes_per_pass':changes,'topology_rejected_per_pass':rejected,'topology_before':before,'topology_after':after,'pixels_changed_from_baseline':int(np.count_nonzero(mask!=original)),'method':'fixed 3-small-pixel boundary band;19x19 local class color means;original-label inertia.4;neighbor contrast weight.3;8-floor/4-solid simple-point flips','limitations':'Cannot add missing barriers/islands or remove existing false islands; topology preservation can preserve baseline errors.'}
    save(im,mask,probability,a.out,report)
    # Match baseline vectorization so visual changes come from mask refinement.
    out=Path(a.out);walls=[];overlay=im.copy()
    for c in cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE)[0]:
        if cv2.contourArea(c)<4:continue
        q=cv2.approxPolyDP(c,1.,True).reshape(-1,2)*4
        for u,v in zip(q,np.roll(q,-1,axis=0)):
            if np.array_equal(u,v):continue
            if any(u[j]==v[j] and u[j] in (0,(mask.shape[1-j]-1)*4) for j in (0,1)):continue
            walls.append([int(u[0]),int(u[1]),int(v[0]),int(v[1])]);cv2.line(overlay,tuple(u),tuple(v),(0,0,255),3)
    (out/'walls.json').write_text(json.dumps({'walls':walls}));cv2.imwrite(str(out/'overlay.jpg'),cv2.resize(overlay,None,fx=.25,fy=.25))
    report['segments']=len(walls);report['vectorization']='Same as baseline: epsilon1, area>=4 quarter-resolution pixels'
    report['visual_inspection']='Small edge alignment changes only. Bridge and island connectivity retained. No new barriers recovered; false furniture blockers remain. No demonstrated overall improvement.'
    (out/'inference.json').write_text(json.dumps(report,indent=2))

if __name__=='__main__':
 p=argparse.ArgumentParser()
 for name in ('baseline','samples','labels','out'):p.add_argument(name)
 run(p.parse_args())
