"""One fixed spatial-development CNN. Inference receives image and weights only."""
import json,time
from pathlib import Path
import cv2,numpy as np,torch
from torch import nn
from torch.nn import functional as F
from building_model import labels,sha,render_prediction
from building_holdout import IMAGE,REF,OUT as SPLIT,scores
OUT=Path('/private/tmp/auto-wall-building-cnn')
STEPS=1000; PATCH=96; GUARD=52

def block(a,b):return nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.ReLU(),nn.Conv2d(b,b,3,padding=1),nn.ReLU())
class Net(nn.Module):
 def __init__(self):
  super().__init__();self.a=block(3,8);self.b=block(8,16);self.c=block(16,32);self.d=block(48,16);self.e=block(24,8);self.out=nn.Conv2d(8,3,1)
 def forward(self,x):
  a=self.a(x);b=self.b(F.max_pool2d(a,2));c=self.c(F.max_pool2d(b,2));d=self.d(torch.cat([F.interpolate(c,size=b.shape[-2:],mode='nearest'),b],1));return self.out(self.e(torch.cat([F.interpolate(d,size=a.shape[-2:],mode='nearest'),a],1)))

def pixels(path):
 im=cv2.imread(str(path));assert im is not None
 return im,cv2.resize(im,(round(im.shape[1]/4),round(im.shape[0]/4)),interpolation=cv2.INTER_AREA)[:,:,::-1].copy().astype(np.float32)/255

def predict(image,model):
 # Reference geometry and partition masks are deliberately absent from this API.
 _,rgb=pixels(image);net=Net();net.load_state_dict(torch.load(model,map_location='cpu',weights_only=True)['state']);net.eval();h,w=rgb.shape[:2];p=np.zeros((h,w,3),np.float32)
 # Tile with a conservative 24-pixel halo to preserve local receptive fields.
 for z in range(0,h,192):
  for x in range(0,w,192):
   z0=max(0,z-24);x0=max(0,x-24);z1=min(h,z+216);x1=min(w,x+216)
   # Keep pooling alignment identical across tiles.
   z0=z0//4*4;x0=x0//4*4
   a=rgb[z0:z1,x0:x1];a=np.pad(a,((0,(-len(a))%4),(0,(-a.shape[1])%4),(0,0)),mode='edge')
   with torch.no_grad():q=net(torch.from_numpy(a.transpose(2,0,1)[None])).softmax(1)[0].permute(1,2,0).numpy()
   dz=min(192,h-z);dx=min(192,w-x);p[z:z+dz,x:x+dx]=q[z-z0:z-z0+dz,x-x0:x-x0+dx]
 return p

def run(stratified=False):
 global OUT
 if stratified:OUT=Path('/private/tmp/auto-wall-building-cnn-sampled')
 start=time.perf_counter();torch.set_num_threads(4);torch.manual_seed(42);rng=np.random.default_rng(42);OUT.mkdir(exist_ok=True)
 split_sha=sha(SPLIT/'split.json');held=cv2.imread(str(SPLIT/'heldout-mask.png'),0)>0;train=cv2.imread(str(SPLIT/'train-mask.png'),0)>0
 forbidden=cv2.dilate(held.astype(np.uint8),np.ones((2*GUARD+1,2*GUARD+1),np.uint8))>0
 sources=json.loads(Path('/private/tmp/auto-wall-building-model/train.json').read_text())+[dict(image=IMAGE,reference=REF)];data=[];counts=np.zeros(3,np.int64)
 for s in sources:
  _,rgb=pixels(s['image']);y=labels(s['reference'],rgb.shape[:2]);cony=s['image']==IMAGE
  if cony:
   assert y.shape==held.shape
   y[(y>0)&(y<3)&~train]=255
   y[forbidden]=255
  h,w=y.shape;valid=np.ones((h-PATCH+1,w-PATCH+1),bool)
  if cony:
   sums=cv2.integral(forbidden.astype(np.uint8));valid=(sums[PATCH:,PATCH:]-sums[:-PATCH,PATCH:]-sums[PATCH:,:-PATCH]+sums[:-PATCH,:-PATCH])==0
  origins=np.argwhere(valid);assert len(origins)
  if cony:
   zz,xx=np.where(valid);diff=np.zeros((h+1,w+1),np.int32)
   for az,ax,sign in [(zz,xx,1),(zz+PATCH,xx,-1),(zz,xx+PATCH,-1),(zz+PATCH,xx+PATCH,1)]:np.add.at(diff,(az,ax),sign)
   covered=diff.cumsum(0).cumsum(1)[:-1,:-1]>0
   coverage=dict(admissible_crop_origins=len(origins),wall_pixels=int(((y==1)&covered).sum()),portal_pixels=int(((y==2)&covered).sum()))
   assert coverage['wall_pixels'] and coverage['portal_pixels']
  counts+=np.array([(y==c).sum() for c in range(3)])
  pools={}
  for cls in (1,2):
   area=cv2.integral((y==cls).astype(np.uint8));total=area[PATCH:,PATCH:]-area[:-PATCH,PATCH:]-area[PATCH:,:-PATCH]+area[:-PATCH,:-PATCH]
   pools[cls]=np.argwhere(valid&(total>0));assert len(pools[cls])
  data.append((rgb,y,origins,cony,pools))
 weights=np.sqrt(counts.max()/counts).clip(1,20);weights=torch.tensor(weights,dtype=torch.float32);net=Net();opt=torch.optim.Adam(net.parameters(),lr=.001);losses=[];sample_counts=[0]*len(data);exposures=np.zeros(3,np.int64);patch_coverage=np.zeros(3,np.int64);sampling_modes=np.zeros(3,np.int64)
 for step in range(STEPS):
  xs=[];ys=[]
  for _ in range(4):
   sid=int(rng.integers(len(data)));rgb,y,origins,cony,pools=data[sid]
   mode=(step*4+_)%3 if stratified else 0;sampling_modes[mode]+=1
   candidates=origins if mode==0 else pools[mode]
   z,x=candidates[int(rng.integers(len(candidates)))];sample_counts[sid]+=1
   target_patch=y[z:z+PATCH,x:x+PATCH]
   if mode:assert (target_patch==mode).any()
   for cls in range(3):
    n=int((target_patch==cls).sum());exposures[cls]+=n;patch_coverage[cls]+=n>0
   if cony:assert not forbidden[z:z+PATCH,x:x+PATCH].any()
   a=rgb[z:z+PATCH,x:x+PATCH].copy();b=y[z:z+PATCH,x:x+PATCH].copy();k=int(rng.integers(4));a=np.rot90(a,k);b=np.rot90(b,k)
   if rng.random()<.5:a=a[:,::-1];b=b[:,::-1]
   a=np.clip((a-.5)*rng.uniform(.8,1.2)+.5+rng.uniform(-.08,.08),0,1);xs.append(a.transpose(2,0,1));ys.append(b)
  xt=torch.tensor(np.array(xs),dtype=torch.float32);target=torch.tensor(np.array(ys),dtype=torch.long);logit=net(xt);prob=logit.softmax(1);mask=(target!=255);one=F.one_hot(target.clamp_max(2),3).permute(0,3,1,2)*mask[:,None];m=mask[:,None];inter=(prob*one).sum((0,2,3));den=(prob*m+one).sum((0,2,3));dice=(1-(2*inter+1)/(den+1))[1:].mean();loss=F.cross_entropy(logit,target,weight=weights,ignore_index=255)+dice;opt.zero_grad();loss.backward();opt.step();losses.append(float(loss.detach()))
  if step%100==0:print(json.dumps(dict(step=step,loss=losses[-1],seconds=time.perf_counter()-start)),flush=True)
 torch.save(dict(state=net.state_dict(),scale=4,steps=STEPS,classes=['background','wall','portal']),OUT/'model.pt')
 p=predict(IMAGE,OUT/'model.pt');assert np.isfinite(p).all() and np.allclose(p.sum(2),1,atol=1e-5);pred=p.argmax(2).astype(np.uint8);im,_=pixels(IMAGE);y=labels(REF,pred.shape)
 cv2.imwrite(str(OUT/'classes.png'),pred);cv2.imwrite(str(OUT/'overlay.jpg'),cv2.resize(render_prediction(im,pred),(pred.shape[1],pred.shape[0])))
 for c in range(3):cv2.imwrite(str(OUT/f'probability-{c}.png'),np.rint(p[:,:,c]*255).astype(np.uint8))
 assert split_sha==sha(SPLIT/'split.json')
 report=dict(config=dict(steps=STEPS,batch=4,patch_lowres=PATCH,scale=4,receptive_field_lowres=44,conservative_rf_radius_source=96,guard_source=GUARD*4,seed=42,loss='sqrt-inverse-frequency weighted CE + foreground Dice',weights=weights.tolist(),threshold='argmax; no confidence tuning'),sources=[dict(s,image_sha256=sha(s['image']),reference_sha256=sha(s['reference'])) for s in sources],sampling=dict(policy='cycle uniform/wall-containing/portal-containing admissible crops' if stratified else 'uniform',modes=sampling_modes.tolist(),supervised_class_pixel_exposures=exposures.tolist(),patches_containing_class=patch_coverage.tolist(),admissible_pool_sizes=[{str(k):len(v) for k,v in d[4].items()} for d in data]),sample_counts=sample_counts,conyberry_training_coverage=coverage,model_sha256=sha(OUT/'model.pt'),split_sha256=split_sha,heldout=scores(pred,y,held),training=scores(pred,y,train),seconds=time.perf_counter()-start,last_loss=losses[-1],parameters=sum(p.numel() for p in net.parameters()),inference_inputs=['image pixels','fixed trained weights'],no_overlap_assertion=True,warning='Spatial development validation on shared map/art style, not new-map generalization. Band accuracy is not geometric accuracy. No heldout checkpoint selection.')
 (OUT/'provenance.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':
 import sys
 run('--stratified' in sys.argv)
