"""Import pinned upstream detectors for comparison; upstream checkout is external."""
import contextlib,json,pathlib,sys,time
import cv2,numpy as np
sys.path.insert(0,str(pathlib.Path('/private/tmp/auto-wall-upstream-scout')))
from src.wall_detection.detector import detect_walls
from src.wall_detection.light_detector import detect_lights
cv2.setNumThreads(1)
t=time.perf_counter();original=cv2.imdecode(np.fromfile(sys.argv[1],np.uint8),cv2.IMREAD_COLOR);decode=(time.perf_counter()-t)*1000
t=time.perf_counter();oh,ow=original.shape[:2];cap=int(sys.argv[3]);scale=min(1,cap/max(ow,oh));w,h=round(ow*scale),round(oh*scale);im=cv2.resize(original,(w,h),interpolation=cv2.INTER_AREA);sx,sy=ow/w,oh/h
mode=sys.argv[2]
with contextlib.redirect_stdout(sys.stderr):
 if mode=='upstream-gui':contours=detect_walls(im,min_contour_area=w*h*.001,blur_kernel_size=5,canny_threshold1=255,canny_threshold2=106)
 else:contours=detect_walls(im)
 lights=detect_lights(im)
walls=[]
for c in contours:
 # Same fixed-pixel simplification as Rust baseline, isolates detector differences.
 points=cv2.approxPolyDP(c,3,True).reshape(-1,2).tolist()
 if len(points)<3:continue
 for a,b in zip(points,points[1:]+points[:1]):
  if a!=b:walls.append([[a[0]*sx,a[1]*sy],[b[0]*sx,b[1]*sy]])
print(json.dumps({'mode':mode,'original':[ow,oh],'working':[w,h],'decode_ms':decode,'detect_ms':(time.perf_counter()-t)*1000,'wall_components':len(contours),'walls':walls,'lights':[[l['position']['x']*sx,l['position']['y']*sy] for l in lights],'portals':[],'simplify_working_pixels':3}))
