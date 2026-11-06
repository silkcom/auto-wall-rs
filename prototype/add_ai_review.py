"""Attach private, AI-authored wall annotations to the local comparison page."""
import base64,json,pathlib
OUT=pathlib.Path('/private/tmp/auto-wall-detection-review')
ANNOTATIONS=pathlib.Path('/private/tmp/auto-wall-ai/round4.json')
a=json.loads(ANNOTATIONS.read_text());d=json.loads((OUT/'results.json').read_text())
for c in d['cases']:
 c['results']=[r for r in c['results']if r['mode']!='ai-guess']
 ow,oh=c['results'][0]['original'];vw,vh=a['coordinates'][c['name']]
 def point(p):return[p[0]*ow/vw,p[1]*oh/vh]
 walls=[[point(p),point(q)]for p,q in a['maps'][c['name']]]
 assert all(0<=p[0]<=ow and 0<=p[1]<=oh for line in walls for p in line)
 assert all(p!=q for p,q in walls)
 canonical=[tuple(sorted((tuple(p),tuple(q))))for p,q in walls]
 assert len(set(canonical))==len(walls),'Duplicate walls'
 qa=[{**q,'a':point(q['a']),'b':point(q['b'])}for q in a['review_checks'][c['name']]]
 r={'mode':'ai-guess','original':[ow,oh],'working':[vw,vh],'walls':walls,'lights':[],'portals':[],'probes':[],'review_checks':qa,'iterations':4,'annotation_only':True,'method':'AI visual interpretation and coordinate editing; initial cavern mask-assisted tracing, followed by hand-edited structural boundaries and simplification. No original UVTT geometry read during construction. Not a blind benchmark: earlier conversation included some reference overlays. No autonomous model API, latency, price, lights, or movable-door performance evaluated.'}
 c['results'].append(r)
 g=c['grid'];uvtt={'format':.3,'resolution':{'map_origin':{'x':0,'y':0},'map_size':{'x':ow/g,'y':oh/g},'pixels_per_grid':g},'line_of_sight':[[{'x':p[0]/g,'y':p[1]/g}for p in line]for line in walls],'objects_line_of_sight':[],'portals':[],'lights':[]}
 (ANNOTATIONS.parent/(c['name'].lower()+'-ai-walls.uvtt')).write_text(json.dumps(uvtt,indent=2))
(OUT/'results.json').write_text(json.dumps(d,indent=2))
for c in d['cases']:c['thumbnail']='data:image/jpeg;base64,'+base64.b64encode((OUT/(c['name'].lower()+'.jpg')).read_bytes()).decode()
s=(pathlib.Path(__file__).parent/'review.html').read_text()
(OUT/'review.html').write_text(s.replace('/*PAYLOAD*/',json.dumps(d).replace('</','<\\/')))
print('Added AI visual annotations:',{c['name']:len(c['results'][-1]['walls'])for c in d['cases']})
