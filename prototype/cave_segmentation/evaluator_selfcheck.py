"""Development evaluator sanity checks; never imported by inference."""
import argparse,json
from pathlib import Path
import numpy as np
from evaluate import segments,score
p=argparse.ArgumentParser();p.add_argument('reference');p.add_argument('output');a=p.parse_args()
d=json.load(open(a.reference));g=d['resolution']['pixels_per_grid'];w=round(d['resolution']['map_size']['x']*g);h=round(d['resolution']['map_size']['y']*g);r=segments(d['line_of_sight'],g)
cases={'oracle':r,'empty':np.empty((0,4)),'shifted':r+np.array([4*g,4*g,4*g,4*g])};results={k:score(v,r,w,h,g)for k,v in cases.items()}
for metric in results['oracle']['full_image'].values():assert metric['precision']>.999 and metric['recall']>.999,metric
assert results['oracle']['visibility']['false_open']==0 and results['oracle']['visibility']['false_blocked']==0
assert results['empty']['full_image'][str(g*.2)]['recall']==0
assert results['empty']['visibility']['false_open']==results['empty']['visibility']['reference_blocked']>0
assert results['shifted']['full_image'][str(g*.2)]['f1']<.5
assert results['shifted']['visibility']['false_open']>0
summary={k:{'boundary':v['full_image'],'visibility':v['visibility']}for k,v in results.items()}
Path(a.output).write_text(json.dumps({'passed':True,'grid':g,'dimensions':[w,h],'shift_original_pixels':4*g,'results':summary},indent=2));print(json.dumps(summary))
