"""Run one frozen building model with raw and fixed straightening; evaluation only."""
import argparse,hashlib,json,time
from pathlib import Path
import cv2,numpy as np
from building_holdout import model_predict
from building_centerlines import extract
from building_portal_support import anchored


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()

def run(image_path,model,out,grid):
    assert grid>0 and np.isfinite(grid)
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    manifest={'image_sha256':sha(image_path),'model_sha256':sha(model),'geometry_code_sha256':sha(Path(__file__).with_name('building_centerlines.py')),'grid_hint':grid,'simplification_grid_fraction':.12,'frozen_before_inference':True,'reference_input':False,'training_performed':False}
    (out/'run-manifest.json').write_text(json.dumps(manifest,indent=2))
    start=time.perf_counter();im=cv2.imread(str(image_path));assert im is not None;classes,probability=model_predict(im,model);model_seconds=time.perf_counter()-start
    cv2.imwrite(str(out/'classes.png'),classes);np.save(out/'probability.npy',probability)
    for name,straight in [('raw',None),('straight',grid)]:
        start=time.perf_counter();geometry,_=extract(classes,im.shape,straight);regions=len(geometry['portals']);geometry['portals']=anchored(geometry['walls'],geometry['portals'],grid);seconds=model_seconds+time.perf_counter()-start
        folder=out/name;folder.mkdir(exist_ok=True);(folder/'walls.json').write_text(json.dumps(geometry));overlay=im.copy()
        for key,color in [('walls',(50,245,60)),('portals',(66,174,255))]:
            for x,y,u,v in geometry[key]:cv2.line(overlay,(round(x),round(y)),(round(u),round(v)),color,2)
        cv2.imwrite(str(folder/'overlay.jpg'),overlay)
        report={'seconds':seconds,'model_seconds':model_seconds,'reference_read':False,'model_sha256':manifest['model_sha256'],'input_image_sha256':manifest['image_sha256'],'dimensions':[im.shape[1],im.shape[0]],'straightening_grid_fraction':.12 if straight else None,'grid_hint':grid,'class_fraction':[float(np.mean(classes==c))for c in range(3)],'wall_segments':len(geometry['walls']),'portal_regions':regions,'supported_portal_proposals':len(geometry['portals']),'inputs':['image','frozen model','unchanged grid hint'],'paid_vision_calls':0,'validation':'Qualitative different-map evaluation; no reference or training used.'}
        (folder/'inference.json').write_text(json.dumps(report,indent=2));print(name,json.dumps(report),flush=True)


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('image');p.add_argument('model');p.add_argument('out');p.add_argument('--grid',required=True,type=float);a=p.parse_args();run(a.image,a.model,a.out,a.grid)
