"""Development-only vector and visibility scoring. Never imported by inference."""
import argparse,json,math,time
from pathlib import Path
import cv2,numpy as np

def segments(paths,grid):
 return np.asarray([[a['x']*grid,a['y']*grid,b['x']*grid,b['y']*grid]for line in paths for a,b in zip(line,line[1:])],np.float64).reshape(-1,4)
def normalize(items):
 a=np.asarray(items,np.float64)
 return a.reshape(-1,4)if a.size else np.empty((0,4))
def distances(lines,target,w,h):
 mask=np.full((h,w),255,np.uint8)
 for x,y,u,v in target:cv2.line(mask,(round(x),round(y)),(round(u),round(v)),0,1)
 field=cv2.distanceTransform(mask,cv2.DIST_L2,cv2.DIST_MASK_PRECISE)if len(target)else np.full((h,w),np.inf,np.float32)
 ds=[];weights=[];midpoints=[]
 for x,y,u,v in lines:
  length=math.hypot(u-x,v-y)
  if not length:continue
  n=max(1,math.ceil(length/2));t=(np.arange(n)+.5)/n;xx=x+(u-x)*t;yy=y+(v-y)*t
  inside=(xx>=0)&(xx<w)&(yy>=0)&(yy<h);z=np.full(n,np.inf);z[inside]=field[np.minimum(h-1,np.rint(yy[inside]).astype(int)),np.minimum(w-1,np.rint(xx[inside]).astype(int))]
  ds.append(z);weights.append(np.full(n,length/n));midpoints.append(np.column_stack((xx,yy)))
 if not ds:return np.array([]),np.array([]),np.empty((0,2))
 return np.concatenate(ds),np.concatenate(weights),np.concatenate(midpoints)
def blocked(a,b,lines):
 if not len(lines):return False
 c=lines[:,:2];d=lines[:,2:];ab=b-a;cd=d-c
 ca=c-a;da=d-a;ac=a-c;bc=b-c
 cross1=ab[0]*ca[:,1]-ab[1]*ca[:,0];cross2=ab[0]*da[:,1]-ab[1]*da[:,0]
 cross3=cd[:,0]*ac[:,1]-cd[:,1]*ac[:,0];cross4=cd[:,0]*bc[:,1]-cd[:,1]*bc[:,0]
 return bool(np.any((cross1*cross2<0)&(cross3*cross4<0)))
def score(candidate,ref,w,h,grid,heldout=None):
 dp,wp,pp=distances(candidate,ref,w,h);dr,wr,pr=distances(ref,candidate,w,h)
 def measure(maskp,maskr):
  result={}
  for tol in [grid*.1,grid*.2,grid*.3]:
   precision=float(wp[maskp&(dp<=tol)].sum()/wp[maskp].sum())if wp[maskp].sum()else None
   recall=float(wr[maskr&(dr<=tol)].sum()/wr[maskr].sum())if wr[maskr].sum()else None
   result[str(tol)]={'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall)if precision is not None and recall is not None and precision+recall else 0}
  return result
 allp=np.ones(len(dp),bool);allr=np.ones(len(dr),bool);result={'full_image':measure(allp,allr)}
 if heldout is not None:
  def select(points):
   x=np.minimum(heldout.shape[1]-1,np.maximum(0,(points[:,0]/w*heldout.shape[1]).astype(int)));y=np.minimum(heldout.shape[0]-1,np.maximum(0,(points[:,1]/h*heldout.shape[0]).astype(int)));return heldout[y,x]>0
  result['spatial_heldout']=measure(select(pp),select(pr))
 rng=np.random.default_rng(2026);lengths=np.linalg.norm(ref[:,2:]-ref[:,:2],axis=1);weights=lengths/lengths.sum();probes=[]
 for i in rng.choice(len(ref),500,p=weights):
  p=ref[i,:2];q=ref[i,2:];v=q-p;length=np.linalg.norm(v)
  if length<1:continue
  center=p+rng.uniform(.2,.8)*v;normal=np.array([-v[1],v[0]])/length; a=center-normal*.4*grid;b=center+normal*.4*grid
  if np.all(a>=0)and np.all(b>=0)and a[0]<w and a[1]<h and b[0]<w and b[1]<h:probes.append((a,b))
 for _ in range(1500):
  a=rng.uniform([0,0],[w,h]);b=np.clip(a+rng.uniform(-2*grid,2*grid,2),[0,0],[w-1,h-1]);probes.append((a,b))
 counts={'reference_blocked':0,'reference_open':0,'false_open':0,'false_blocked':0};held_counts=dict(counts)if heldout is not None else None
 failures=[]
 for a,b in probes:
  expected=blocked(a,b,ref);actual=blocked(a,b,candidate);counts['reference_blocked'if expected else 'reference_open']+=1
  if held_counts is not None and np.all(select(np.asarray([a,b]))):
   held_counts['reference_blocked'if expected else 'reference_open']+=1
   if expected!=actual:held_counts['false_open'if expected else 'false_blocked']+=1
  if expected!=actual:
   counts['false_open'if expected else 'false_blocked']+=1
   if len(failures)<100:failures.append({'a':a.tolist(),'b':b.tolist(),'reference_blocked':expected,'candidate_blocked':actual})
 if held_counts is not None:result['spatial_heldout_visibility']=held_counts
 result['visibility']=counts;result['example_visibility_failures']=failures
 return result
if __name__=='__main__':
 a=argparse.ArgumentParser();a.add_argument('reference');a.add_argument('candidate');a.add_argument('output');a.add_argument('--heldout');args=a.parse_args();t=time.perf_counter()
 refdoc=json.load(open(args.reference));g=refdoc['resolution']['pixels_per_grid'];w=round(refdoc['resolution']['map_size']['x']*g);h=round(refdoc['resolution']['map_size']['y']*g);raw=json.load(open(args.candidate));candidate=normalize(raw['walls']);ref=segments(refdoc['line_of_sight'],g);objects=segments(refdoc.get('objects_line_of_sight',[]),g)
 held=cv2.imread(args.heldout,cv2.IMREAD_GRAYSCALE)if args.heldout else None
 r={'candidate':str(Path(args.candidate).resolve()),'reference_role':'Development/evaluation only; not inference input','segments':len(candidate),'reference_structural_segments':len(ref),'reference_object_segments':len(objects),'method':'Length-weighted2px boundary samples to1px raster distance; proper-intersection visibility probes. Spatial holdout same map, not independent-map test.','structural':score(candidate,ref,w,h,g,held)}
 if len(objects):r['combined']=score(candidate,np.concatenate((ref,objects)),w,h,g)
 r['seconds']=time.perf_counter()-t;Path(args.output).write_text(json.dumps(r,indent=2));print(json.dumps({k:v for k,v in r.items()if k not in ['structural','combined']}|{'boundary':r['structural']['full_image'],'heldout':r['structural'].get('spatial_heldout'),'visibility':r['structural']['visibility']}))
