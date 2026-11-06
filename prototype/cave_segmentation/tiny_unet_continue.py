"""Throwaway tiny CNN experiment; reference geometry is training-only."""
import argparse,hashlib,json,time
from pathlib import Path
import cv2,numpy as np,torch
from torch import nn
from torch.nn import functional as F
import candidate as labels
SCALE=4
HALO=48

def block(a,b):return nn.Sequential(nn.Conv2d(a,b,3,padding=1),nn.ReLU(),nn.Conv2d(b,b,3,padding=1),nn.ReLU())
class Net(nn.Module):
 def __init__(self):
  super().__init__();self.enc=nn.ModuleList([block(3,8),block(8,16),block(16,32)]);self.mid=block(32,64);self.dec=nn.ModuleList([block(96,32),block(48,16),block(24,8)]);self.out=nn.Conv2d(8,1,1)
 def forward(self,x):
  skips=[]
  for layer in self.enc:x=layer(x);skips.append(x);x=F.max_pool2d(x,2)
  x=self.mid(x)
  for layer,skip in zip(self.dec,reversed(skips)):x=layer(torch.cat([F.interpolate(x,size=skip.shape[-2:],mode='bilinear',align_corners=False),skip],1))
  return self.out(x)

def image_tensor(path):
 im=cv2.imread(path);small=cv2.resize(im,None,fx=1/SCALE,fy=1/SCALE,interpolation=cv2.INTER_AREA)
 return im,small[:,:,::-1].copy().astype(np.float32)/255

def train(image,reference,model,out,steps=1500):
 t=time.perf_counter();torch.manual_seed(42);rng=np.random.default_rng(42);torch.set_num_threads(4)
 im,rgb=image_tensor(image);h,w=rgb.shape[:2];y=labels.reference_labels(reference,(h,w));ignore=labels.open_reference_band(reference,(h,w));edge=cv2.morphologyEx(y,cv2.MORPH_GRADIENT,np.ones((7,7),np.uint8))
 weights=(1+3*edge).astype(np.float32);weights[ignore]=0
 splitx=1800//SCALE;splity=2250//SCALE;held=np.zeros((h,w),np.uint8);held[splity+HALO:,splitx+HALO:]=255;held[ignore]=0
 net=Net();checkpoint=torch.load(RESUME,map_location='cpu',weights_only=True);net.load_state_dict(checkpoint['state']);start=checkpoint['steps'];best=float('inf');selected_step=start
 full=torch.from_numpy(rgb.transpose(2,0,1)[None]);held_tensor=torch.from_numpy((held>0)[None,None]);truth=torch.from_numpy(y[None,None].astype(np.float32));valweight=torch.from_numpy(weights[None,None])*held_tensor
 def validate():
  net.eval()
  with torch.no_grad():
   logits=net(full);p=logits.sigmoid();bce=(F.binary_cross_entropy_with_logits(logits,truth,reduction='none')*valweight).sum()/valweight.sum().clamp_min(1);dice=1-(2*(p*truth*valweight).sum()+1)/((p*valweight).sum()+(truth*valweight).sum()+1)
  net.train();return float(bce+dice)
 best=validate();torch.save({'state':net.state_dict(),'scale':SCALE,'architecture':'3level-base8','steps':start},model)
 validations=[{'step':start,'validation_loss':best}]
 opt=torch.optim.Adam(net.parameters(),lr=.001);losses=[];sample_origins=[]
 for step in range(start,steps):
  xs=[];ys=[];ws=[]
  for _ in range(4):
   while True:
    x=int(rng.integers(0,w-128+1));z=int(rng.integers(0,h-128+1))
    if x+128<=splitx-HALO or z+128<=splity-HALO:break
   sample_origins.append((x,z));a=rgb[z:z+128,x:x+128].copy();b=y[z:z+128,x:x+128].copy();c=weights[z:z+128,x:x+128].copy();k=int(rng.integers(4));a=np.rot90(a,k);b=np.rot90(b,k);c=np.rot90(c,k)
   if rng.random()<.5:a=a[:,::-1];b=b[:,::-1];c=c[:,::-1]
   a=np.clip((a-.5)*rng.uniform(.7,1.3)+.5+rng.uniform(-.12,.12),0,1);a=np.clip(a*rng.uniform(.85,1.15,(1,1,3)),0,1)
   xs.append(a.transpose(2,0,1));ys.append(b[None]);ws.append(c[None])
  x=torch.tensor(np.array(xs),dtype=torch.float32);target=torch.tensor(np.array(ys),dtype=torch.float32);weight=torch.tensor(np.array(ws),dtype=torch.float32);logit=net(x);prob=logit.sigmoid()
  bce=(F.binary_cross_entropy_with_logits(logit,target,reduction='none')*weight).sum()/weight.sum().clamp_min(1)
  dice=1-(2*(prob*target*weight).sum()+1)/((prob*weight).sum()+(target*weight).sum()+1);loss=bce+dice;opt.zero_grad();loss.backward();opt.step();losses.append(float(loss.detach()))
  if (step+1)%250==0:
   value=validate();validations.append({'step':step+1,'validation_loss':value,'training_loss_mean_last250':float(np.mean(losses[-250:]))})
   if value<best:
    best=value;selected_step=step+1;torch.save({'state':net.state_dict(),'scale':SCALE,'architecture':'3level-base8','steps':selected_step},model)
   print(json.dumps(validations[-1]|{'selected_step':selected_step,'seconds':time.perf_counter()-t}),flush=True)
  if time.perf_counter()-t>170:break
 # Assertions check every sampled patch plus halo lies outside the heldout quadrant.
 assert all(x+128<=splitx-HALO or z+128<=splity-HALO for x,z in sample_origins)
 net.load_state_dict(torch.load(model,map_location='cpu',weights_only=True)['state'])
 Path(out).mkdir(parents=True,exist_ok=True);cv2.imwrite(out+'/heldout-mask.png',held);cv2.imwrite(out+'/labels.png',y*255)
 with torch.no_grad():pred=net(torch.from_numpy(rgb.transpose(2,0,1)[None])).sigmoid()[0,0].numpy()>.5
 a=pred[held>0];b=y[held>0]>0
 report={'steps_total':start+len(losses),'selected_step':selected_step,'validation_loss':best,'validation_history':validations,'optimizer_note':'Adam restarted because original checkpoint omitted optimizer state; same learning rate and loss.','seconds':time.perf_counter()-t,'parameters':sum(p.numel() for p in net.parameters()),'last_loss':losses[-1],'heldout_accuracy':float((a==b).mean()),'heldout_floor_iou':float((a&b).sum()/(a|b).sum()),'heldout_pixels':int(a.size),'heldout_definition_original':'SE x>=1800,y>=2250 reserved; training patch ends exclude additional192px halo; evaluation begins192px into reserved quadrant','patches':len(sample_origins),'no_overlap_assertion':True,'selection':'Minimum boundary-weighted BCE+Dice on SE spatial validation, checkpoint every250steps','warning':'Single-map development; spatial validation only. Different heldout region from RF.'};Path(out+'/training.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

def infer(image,model,out):
 t=time.perf_counter();torch.set_num_threads(4);im,rgb=image_tensor(image);checkpoint=torch.load(model,map_location='cpu',weights_only=True);net=Net();net.load_state_dict(checkpoint['state']);net.eval()
 with torch.no_grad():prob=net(torch.from_numpy(rgb.transpose(2,0,1)[None])).sigmoid()[0,0].numpy()
 pred=(prob>.5).astype(np.uint8);mask=cv2.morphologyEx(pred,cv2.MORPH_CLOSE,np.ones((5,5),np.uint8));mask=cv2.morphologyEx(mask,cv2.MORPH_OPEN,np.ones((3,3),np.uint8));n,ids,stats,_=cv2.connectedComponentsWithStats(mask);mask=np.isin(ids,np.flatnonzero((stats[:,cv2.CC_STAT_AREA]>=120)&(np.arange(n)>0))).astype(np.uint8)
 contours,_=cv2.findContours(mask,cv2.RETR_LIST,cv2.CHAIN_APPROX_SIMPLE);walls=[];overlay=im.copy()
 for c in contours:
  if cv2.contourArea(c)<80:continue
  p=cv2.approxPolyDP(c,1.5,True).reshape(-1,2)*SCALE
  for a,b in zip(p,np.roll(p,-1,axis=0)):
   if any(a[j]==b[j] and a[j] in (0,(mask.shape[1-j]-1)*SCALE) for j in (0,1)):continue
   walls.append([int(a[0]),int(a[1]),int(b[0]),int(b[1])]);cv2.line(overlay,tuple(a),tuple(b),(0,0,255),3)
 Path(out).mkdir(parents=True,exist_ok=True);cv2.imwrite(out+'/raw-mask.png',pred*255);cv2.imwrite(out+'/mask.png',mask*255);cv2.imwrite(out+'/probability.png',(prob*255).astype(np.uint8));cv2.imwrite(out+'/overlay.jpg',cv2.resize(overlay,None,fx=.25,fy=.25));Path(out+'/walls.json').write_text(json.dumps({'walls':walls}));report={'seconds':time.perf_counter()-t,'device':'cpu','segments':len(walls),'model_sha256':hashlib.sha256(Path(model).read_bytes()).hexdigest(),'inference_inputs':['image','frozen weights'],'reference_read':False,'floor_fraction':float(mask.mean())};Path(out+'/inference.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['train','infer']);p.add_argument('image');p.add_argument('model');p.add_argument('out');p.add_argument('--reference');p.add_argument('--resume');a=p.parse_args();RESUME=a.resume
 if a.mode=='train':train(a.image,a.reference,a.model,a.out)
 else:infer(a.image,a.model,a.out)
