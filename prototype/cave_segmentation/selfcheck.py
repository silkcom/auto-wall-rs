"""Small boundary/provenance check. Uses an already-trained model, no reference."""
import builtins,json,sys,tempfile
from pathlib import Path
import cv2,numpy as np
import candidate
model=sys.argv[1]
accesses=[]
def audit(event,args):
    if event=="open":
        name=str(args[0]);accesses.append(name)
        assert not name.lower().endswith((".dd2vtt",".uvtt",".ddvtt")),name
sys.addaudithook(audit)
def forbidden(*a,**kw):raise AssertionError('Reference labeling reached during infer')
candidate.reference_labels=forbidden;candidate.open_reference_band=forbidden
with tempfile.TemporaryDirectory() as folder:
    image=folder+'/blank.png';cv2.imwrite(image,np.full((512,640,3),255,np.uint8))
    candidate.infer(image,model,folder+'/result')
    result=json.load(open(folder+'/result/walls.json'));assert result['walls']==[]
print(json.dumps({'blank_control':'pass','reference_helpers_forbidden':'pass','python_file_accesses':accesses,'caveat':'OpenCV native model/image reads do not use Python open; infer explicitly receives those two paths only.'}))
