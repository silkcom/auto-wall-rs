"""Frozen boundary-feature forest + existing four-pass contrast-sensitive ICM."""
import argparse,hashlib,time
from pathlib import Path
import cv2
from boundary_candidate import features,SCALE
from structured_refine import probability,icm,save

if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('image');p.add_argument('model');p.add_argument('out');a=p.parse_args()
 t=time.perf_counter();im=cv2.imread(a.image);assert im is not None
 f=features(im);forest=cv2.ml.RTrees_load(a.model);assert forest.getVarCount()==f.shape[2]
 prob=probability(forest,f);shared=time.perf_counter()-t
 small=cv2.resize(im,(prob.shape[1],prob.shape[0]),interpolation=cv2.INTER_AREA)
 t=time.perf_counter();mask,detail=icm(prob,small);seconds=time.perf_counter()-t
 save(im,mask,prob,a.out,{'variant':'boundary RF + unchanged structured ICM','image':str(Path(a.image).resolve()),'model_sha256':hashlib.sha256(Path(a.model).read_bytes()).hexdigest(),'reference_read':False,'inference_inputs':['image pixels','boundary-feature random forest model'],'feature_and_votes_seconds':shared,'solver_seconds':seconds,'scale':SCALE,**detail})
