"""Throwaway shared material RF: one frozen model and identical four-pass ICM."""
import argparse,hashlib,json,time
from pathlib import Path
import cv2,numpy as np
import candidate
from structured_refine import probability,icm,save

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def train(config,model,out):
 start=time.perf_counter();rng=np.random.default_rng(42);xs=[];ys=[];sources=[]
 for source in json.loads(Path(config).read_text())['sources']:
  im=cv2.imread(source['image']);f=candidate.features(im);shape=f.shape[:2]
  if source.get('reference'):
   y=candidate.reference_labels(source['reference'],shape);uncertain=candidate.open_reference_band(source['reference'],shape);role='authoritative development reference';labelpath=source['reference']
  else:
   raw=cv2.imread(source['pseudo_mask'],cv2.IMREAD_GRAYSCALE);assert raw.shape==shape,(raw.shape,shape);y=(raw>127).astype(np.uint8);uncertain=np.zeros(shape,bool);role='accepted semantic round mask: PSEUDOLABEL, not authoritative';labelpath=source['pseudo_mask']
  boundary=cv2.morphologyEx(y,cv2.MORPH_GRADIENT,np.ones((7,7),np.uint8))>0
  eligible=~uncertain&~boundary;counts={}
  for cls in (0,1):
   available=np.flatnonzero(eligible&(y==cls));assert len(available)>0
   indices=rng.choice(available,min(10000,len(available)),False);xs.append(f.reshape(-1,f.shape[2])[indices]);ys.append(np.full(len(indices),cls,np.int32));counts[str(cls)]=len(indices)
  sources.append({'image':source['image'],'image_sha256':sha(source['image']),'labels':labelpath,'label_sha256':sha(labelpath),'role':role,'samples_by_class':counts,'working_shape':shape})
 cv2.setRNGSeed(42);forest=cv2.ml.RTrees_create();forest.setMaxDepth(18);forest.setMinSampleCount(12);forest.setActiveVarCount(5);forest.setTermCriteria((cv2.TERM_CRITERIA_MAX_ITER,65,0));forest.train(np.concatenate(xs),cv2.ml.ROW_SAMPLE,np.concatenate(ys));forest.save(model)
 report={'seconds':time.perf_counter()-start,'model_sha256':sha(model),'sources':sources,'samples':sum(map(len,ys)),'features':23,'trees':65,'max_depth':18,'boundary_ignore_original_pixels':12,'open_object_ignore_original_pixels':36,'validation':'None: every supplied map is development/training; outputs measure reproduction only.','inference':'One model, original appearance features, identical four ICM passes; no map identity or coordinates.'}
 Path(out).mkdir(parents=True,exist_ok=True);Path(out+'/training.json').write_text(json.dumps(report,indent=2));print(json.dumps(report),flush=True)

def infer(image,model,out):
 start=time.perf_counter();im=cv2.imread(image);f=candidate.features(im);forest=cv2.ml.RTrees_load(model);p=probability(forest,f);small=cv2.resize(im,(p.shape[1],p.shape[0]),interpolation=cv2.INTER_AREA);mask,detail=icm(p,small)
 report={'seconds':time.perf_counter()-start,'variant':'shared-model-four-pass-icm','model_sha256':sha(model),'inference_inputs':['image pixels','one shared random forest model'],'reference_read':False,'pseudo_labels_read':False,'scale':candidate.SCALE,'validation':'Image-only inference; training/test role must be recorded by the experiment.',**detail};save(im,mask,p,out,report)
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('mode',choices=['train','infer']);p.add_argument('input');p.add_argument('model');p.add_argument('out');a=p.parse_args()
 if a.mode=='train':train(a.input,a.model,a.out)
 else:infer(a.input,a.model,a.out)
