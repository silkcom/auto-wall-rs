#!/usr/bin/env python3
"""Throwaway local-only evaluation. Run: python3 prototype/run.py [output-directory]."""
import base64, hashlib, json, math, pathlib, platform, random, re, statistics, subprocess, sys, time
ROOT=pathlib.Path(__file__).resolve().parent
OUT=pathlib.Path(sys.argv[1] if len(sys.argv)>1 else '/private/tmp/auto-wall-detection-review');OUT.mkdir(parents=True,exist_ok=True)
BIN=ROOT/'target/release/auto-wall-detection-prototype'
SOURCES=[('Building','ExportingVtt.dd2vtt'),('Tavern','The Pig and Whistle tavern.uvtt'),('Caverns','CarlosProMaps - Lost Caves of Tsojcanth LC/LCOT - Lesser Caverns 36x45.dd2vtt')]

def distance(p,a,b):
 dx=b[0]-a[0];dy=b[1]-a[1];den=dx*dx+dy*dy
 t=max(0,min(1,((p[0]-a[0])*dx+(p[1]-a[1])*dy)/den)) if den else 0
 return math.hypot(p[0]-a[0]-t*dx,p[1]-a[1]-t*dy)
def agreement(source,target,tol):
 # Spatial buckets reduce distance checks without altering the tolerance.
 cell=tol*2; buckets={}
 for a,b in target:
  for x in range(math.floor((min(a[0],b[0])-tol)/cell),math.floor((max(a[0],b[0])+tol)/cell)+1):
   for y in range(math.floor((min(a[1],b[1])-tol)/cell),math.floor((max(a[1],b[1])+tol)/cell)+1):buckets.setdefault((x,y),[]).append((a,b))
 total=matched=0.
 for a,b in source:
  length=math.dist(a,b);n=max(1,math.ceil(length/10));weight=length/n
  for i in range(n):
   f=(i+.5)/n;p=[a[k]+(b[k]-a[k])*f for k in (0,1)];total+=weight
   if any(distance(p,c,d)<=tol for c,d in buckets.get((math.floor(p[0]/cell),math.floor(p[1]/cell)),[])):matched+=weight
 return round(matched/total,4) if total else None

def crosses(a,b,c,d):
 def cross(p,q,r):return (q[0]-p[0])*(r[1]-p[1])-(q[1]-p[1])*(r[0]-p[0])
 return cross(a,b,c)*cross(a,b,d)<0 and cross(c,d,a)*cross(c,d,b)<0

def execute(image,mode,cap=1600):
 samples=[];rss=[];result=None
 for _ in range(3):
  p=subprocess.run(['/usr/bin/time','-l',str(BIN),str(image),mode,str(cap)],capture_output=True,text=True,check=True)
  result=json.loads(p.stdout);samples.append(result['detect_ms']);m=re.search(r'(\d+)\s+maximum resident set size',p.stderr)
  if m:rss.append(int(m.group(1))/1024**2)
 result['detect_samples_ms']=samples;result['detect_median_ms']=statistics.median(samples);result['peak_rss_mib']=max(rss) if rss else None
 return result

cases=[]
for name,filename in SOURCES:
 path=pathlib.Path.home()/'Downloads'/filename;raw=path.read_bytes();d=json.loads(raw);g=d['resolution']['pixels_per_grid'];image=base64.b64decode(d['image'].split(',')[-1]);imagepath=OUT/(name.lower()+'.input');imagepath.write_bytes(image)
 thumb=OUT/(name.lower()+'.jpg');subprocess.run(['sips','-s','format','jpeg','-Z','1100',str(imagepath),'--out',str(thumb)],check=True,capture_output=True)
 def segments(key):
  return [[[a['x']*g,a['y']*g],[b['x']*g,b['y']*g]] for line in d.get(key,[]) for a,b in zip(line,line[1:])]
 structural=segments('line_of_sight');objects=segments('objects_line_of_sight');reference=structural or objects
 case={'name':name,'source_sha256':hashlib.sha256(raw).hexdigest(),'grid':g,'thumbnail':'data:image/jpeg;base64,'+base64.b64encode(thumb.read_bytes()).decode(),'reference':reference,'objects':objects if structural else [],'reference_kind':'structural' if structural else 'object geometry (unreviewed)','reference_lights':[[l['position']['x']*g,l['position']['y']*g] for l in d.get('lights',[])],'portals':[[[p['x']*g,p['y']*g] for p in door['bounds']] for door in d.get('portals',[])],'results':[]}
 for mode in ['dark40','dark70','edges','void']:
  result=execute(imagepath,mode);walls=result['walls'];tol=.2*g
  result['reference_agreement_precision']=agreement(walls,reference,tol);result['reference_agreement_recall']=agreement(reference,walls,tol)
  rng=random.Random(2026);w,h=result['original'];probes=[]
  for i in range(100):
   a=[rng.uniform(0,w),rng.uniform(0,h)];b=[a[0]+rng.uniform(-2*g,2*g),a[1]+rng.uniform(-2*g,2*g)];b=[min(w,max(0,b[0])),min(h,max(0,b[1]))]
   expected=any(crosses(a,b,c,e) for c,e in reference);actual=any(crosses(a,b,c,e) for c,e in walls)
   probes.append({'a':a,'b':b,'reference_blocked':expected,'detected_blocked':actual})
  result['probes']=probes;result['probe_disagreements']=sum(p['reference_blocked']!=p['detected_blocked'] for p in probes)
  # Greedy nearest one-to-one matches: reference annotation is not verified image truth.
  pairs=sorted((math.dist(a,b),i,j) for i,a in enumerate(result['lights']) for j,b in enumerate(case['reference_lights']))
  useda=set();usedb=set()
  for dist,i,j in pairs:
   if dist<=.5*g and i not in useda and j not in usedb:useda.add(i);usedb.add(j)
  result['light_reference_matches']=len(useda);result['light_unmatched_candidates']=len(result['lights'])-len(useda);result['light_unmatched_reference']=len(case['reference_lights'])-len(usedb)
  case['results'].append(result)
  print(name,mode,'walls',len(walls),'lights',len(result['lights']),'detect ms',round(result['detect_median_ms'],1),'RSS MiB',result['peak_rss_mib'],flush=True)
 cases.append(case)
# Controlled exact fixtures: closed room, blank negative, and warm light with white clutter.
for name in ['blank','room','warm-light']:
 w=h=512;data=bytearray([220,220,220])*(w*h)
 if name=='room':
  for y in range(90,422):
   for x in range(90,422):
    if x<100 or x>=412 or y<100 or y>=412:data[(y*w+x)*3:(y*w+x)*3+3]=bytes([20,20,20])
 if name=='warm-light':
  for y in range(512):
   for x in range(512):
    if (x-256)**2+(y-256)**2<36:data[(y*w+x)*3:(y*w+x)*3+3]=bytes([255,200,80])
    elif 40<x<80 and 40<y<80:data[(y*w+x)*3:(y*w+x)*3+3]=bytes([255,255,255])
 ppm=OUT/(name+'.ppm');ppm.write_bytes(b'P6\n512 512\n255\n'+data);png=OUT/(name+'.png');subprocess.run(['sips','-s','format','png',str(ppm),'--out',str(png)],check=True,capture_output=True)
 results=[execute(png,m) for m in ['dark40','dark70','edges','void']]
 (OUT/(name+'-results.json')).write_text(json.dumps(results,indent=2))
 print('controlled',name,[(r['mode'],len(r['walls']),len(r['lights'])) for r in results],flush=True)
metadata={'platform':platform.platform(),'machine':platform.machine(),'cpu':subprocess.check_output(['sysctl','-n','machdep.cpu.brand_string'],text=True).strip(),'rustc':subprocess.check_output(['rustc','--version'],text=True).strip(),'working_cap':1600,'samples_per_candidate':3,'notes':'Fresh processes, warm filesystem cache. No p95 or concurrency claim. RSS includes decoding and detection. Agreement is with unreviewed reference geometry, not ground-truth accuracy.'}
(OUT/'results.json').write_text(json.dumps({'metadata':metadata,'cases':[{k:v for k,v in c.items() if k!='thumbnail'} for c in cases]},indent=2))
page=(ROOT/'review.html').read_text().replace('/*PAYLOAD*/',json.dumps({'metadata':metadata,'cases':cases}).replace('</','<\\/'))
(OUT/'review.html').write_text(page)
print('Review:',OUT/'review.html')
