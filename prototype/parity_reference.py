#!/usr/bin/env python3
"""Full automatic-path oracle using unmodified upstream methods; UI-only shell is stubbed."""
import argparse,contextlib,hashlib,json,os,pathlib,subprocess,sys,time
from collections import deque
from types import SimpleNamespace as NS
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
parser=argparse.ArgumentParser();parser.add_argument('image');parser.add_argument('output');parser.add_argument('--profile',choices=['startup','default','black'],default='default');parser.add_argument('--lights',action='store_true');args=parser.parse_args()
upstream=pathlib.Path(os.environ.get('AUTO_WALL_UPSTREAM','/private/tmp/auto-wall-upstream-scout'))
PIN='c11b8fa7ad5923d742722a063b3d4385f68527d8'
assert subprocess.check_output(['git','-C',str(upstream),'rev-parse','HEAD'],text=True).strip()==PIN,'Wrong upstream revision'
assert not subprocess.check_output(['git','-C',str(upstream),'diff','--name-only'],text=True).strip(),'Upstream tracked source modified'
sys.path.insert(0,str(upstream))
import cv2,numpy as np
from PyQt6.QtCore import QCoreApplication
from PyQt6.QtGui import QColor
from src.core.image_processor import ImageProcessor
from src.core.contour_processor import ContourProcessor
from src.gui.export_panel import ExportPanel
import src.core.image_processor as processing
cv2.setNumThreads(1);qt=QCoreApplication([])
out=pathlib.Path(args.output);out.parent.mkdir(parents=True,exist_ok=True)
log=out.with_suffix('.log').open('w')
class Control:
 def __init__(self,value):self.v=value
 def value(self):return self.v
 def isChecked(self):return bool(self.v)
 def count(self):return 0
 def setEnabled(self,v):pass
 def setVisible(self,v):pass

stages={}
def contours_value(contours):return [c.tolist() for c in contours]
def capture(module,name):
 original=getattr(module,name)
 def wrapper(*a,**kw):
  t=time.perf_counter();result=original(*a,**kw)
  stages[name]={'elapsed_ms':(time.perf_counter()-t)*1000,'contours':contours_value(result)}
  return result
 setattr(module,name,wrapper)
for name in ['detect_walls','merge_contours','split_edge_contours']:capture(processing,name)
image=cv2.imdecode(np.fromfile(args.image,np.uint8),cv2.IMREAD_COLOR)
assert image is not None,'Cannot decode image'
settings={'Smoothing':5,'Edge Sensitivity':255,'Edge Threshold':106,'Edge Margin':0,'Min Merge Distance':5,'Min Area':100}
if args.profile in ['default','black']:settings.update({'Smoothing':3,'Edge Sensitivity':50,'Edge Threshold':150,'Edge Margin':2,'Min Merge Distance':10,'Min Area':124 if args.profile=='default' else 500})
app=NS(original_image=image,max_working_dimension=1500,high_res_checkbox=Control(False),edit_mask_mode_enabled=False,using_pixels_mode=False,sliders={k:{'slider':Control(v)}for k,v in settings.items()},bg_removed_image=None,bg_removal_checkbox=Control(False),remove_hatching_checkbox=Control(False),color_detection_radio=Control(args.profile=='black'),wall_colors_list=Control(0),merge_contours=Control(args.profile!='startup'),enable_light_detection=Control(args.lights),light_brightness_slider=Control(80),light_min_size_slider=Control(5),light_max_size_slider=Control(500),light_merge_distance_slider=Control(20),light_colors_list=Control(0),current_contours=[],current_lights=[],selection_manager=NS(clear_selection=lambda:None),refresh_display=lambda:None,history=deque(),setStatusTip=lambda _:None,mask_layer=None)
if args.profile=='black':
 app.wall_colors_list=NS(count=lambda:1,item=lambda _:NS(data=lambda _:{'color':QColor(0,0,0),'threshold':0.0}))
app.image_processor=ImageProcessor(app);app.contour_processor=ContourProcessor(app)
# UI rendering/history adapters are no-ops. Processing and export methods remain upstream code.
app.export_panel=ExportPanel(app);app.export_panel.display_uvtt_preview=lambda:None;app.export_panel.setup_wall_editing_controls=lambda:None
with contextlib.redirect_stdout(log):
 t=time.perf_counter();app.current_image,app.scale_factor=app.image_processor.create_working_image(image)
 app.image_processor._update_image_internal();detection_ms=(time.perf_counter()-t)*1000
 stages['postprocess']={'contours':contours_value(app.current_contours),'lights':json.loads(json.dumps(app.current_lights))}
 export={'simplify_tolerance':.0005,'max_wall_length':50,'max_walls':5000,'merge_distance':25.,'angle_tolerance':1.,'max_gap':10.,'grid_size':0,'allow_half_grid':True,'grid_offset_x':0.,'grid_offset_y':0.,'overlay_grid_size':70}
 app.uvtt_export_params={'walls_to_export':app.current_contours,'image_shape':image.shape,**export}
 t=time.perf_counter();app.export_panel.preview_uvtt_walls();export_ms=(time.perf_counter()-t)*1000
 uvtt=app.uvtt_walls_preview
 embedded=uvtt.pop('image',None);uvtt.pop('_preview_pixels',None)
# Exclude only timings and embedded-image bytes from equality; public geometry stays intact.
canonical=json.dumps(uvtt,sort_keys=True,separators=(',',':'))
result={'upstream_commit':PIN,'profile':args.profile,'lights_enabled':args.lights,'opencv':cv2.__version__,'numpy':np.__version__,'python':sys.version.split()[0],'opencv_threads':cv2.getNumThreads(),'input_bgr_sha256':hashlib.sha256(image.tobytes()).hexdigest(),'original_dimensions':[image.shape[1],image.shape[0]],'working_dimensions':[app.current_image.shape[1],app.current_image.shape[0]],'scale_factor':app.scale_factor,'working_bgr_sha256':hashlib.sha256(app.current_image.tobytes()).hexdigest(),'detection_settings':settings,'export_settings':export,'stages':stages,'uvtt':uvtt,'uvtt_sha256':hashlib.sha256(canonical.encode()).hexdigest(),'embedded_image_sha256':hashlib.sha256(embedded.encode()).hexdigest()if embedded else None,'detection_and_display_ms':detection_ms,'export_with_encoding_ms':export_ms}
out.write_text(json.dumps(result,indent=2));log.close()
print(json.dumps({'profile':args.profile,'walls':len(uvtt['line_of_sight']),'lights':len(uvtt['lights']),'working':result['working_dimensions'],'uvtt_sha256':result['uvtt_sha256'],'output':str(out),'detection_ms':detection_ms,'export_ms':export_ms}))
