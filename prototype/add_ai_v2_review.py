"""Integrate fresh-context map annotations and measured usage; private data stays local."""
import base64,json,math,pathlib
ROOT=pathlib.Path('/private/tmp/auto-wall-ai-v2');OUT=pathlib.Path('/private/tmp/auto-wall-detection-review')
data=json.loads((OUT/'results.json').read_text());usage=json.loads((ROOT/'token-usage.json').read_text())
for case in data['cases']:
 result=json.loads((ROOT/case['name'].lower()/'result.json').read_text())
 w,h=result['width'],result['height'];assert[w,h]==case['results'][0]['original']
 def valid(p):return len(p)==2 and all(math.isfinite(v)for v in p)and 0<=p[0]<=w and 0<=p[1]<=h
 walls=result['walls'];assert all(valid(a)and valid(b)and a!=b for a,b in walls)
 keys=[tuple(sorted((tuple(a),tuple(b))))for a,b in walls];assert len(keys)==len(set(keys))
 doors=result['doors']
 for door in doors:
  assert len(door['bounds'])==2 and all(valid([p['x'],p['y']])for p in door['bounds'])
  assert valid([door['position']['x'],door['position']['y']])and math.isfinite(door['rotation'])
  assert isinstance(door['closed'],bool)
 lights=result['lights']
 for light in lights:
  assert valid([light['position']['x'],light['position']['y']])
  assert math.isfinite(light['range_grid'])and light['range_grid']>0
  assert math.isfinite(light['intensity'])and light['intensity']>=0
  assert len(light['color'])==8 and all(c in '0123456789abcdefABCDEF'for c in light['color'])
 r={'mode':'ai-v2','original':[w,h],'working':[w,h],'walls':walls,'portals':doors,'lights':[[l['position']['x'],l['position']['y']]for l in lights],'light_records':lights,'probes':[],'review_checks':[],'iterations':len(result['iterations']),'iteration_notes':result['iterations'],'notes':result['notes'],'checks':result['checks'],'annotation_only':True,'token_usage':usage['maps'][case['name']]}
 case['results']=[old for old in case['results']if old['mode']!='ai-v2']+[r]
 g=case['grid']
 def point(p):return{'x':p['x']/g,'y':p['y']/g}
 uvtt={'format':.3,'resolution':{'map_origin':{'x':0,'y':0},'map_size':{'x':w/g,'y':h/g},'pixels_per_grid':g},'line_of_sight':[[{'x':p[0]/g,'y':p[1]/g}for p in wall]for wall in walls],'objects_line_of_sight':[],'portals':[{k:door[k]for k in ['rotation','closed','freestanding']}|{'position':point(door['position']),'bounds':[point(p)for p in door['bounds']]}for door in doors],'lights':[{k:light[k]for k in ['intensity','color','shadows']}|{'position':point(light['position']),'range':light['range_grid']}for light in lights]}
 # No embedded image in these private data artifacts; original images remain in review.
 (ROOT/case['name'].lower()/'ai-v2.uvtt').write_text(json.dumps(uvtt,indent=2))
data['ai_v2_usage']=usage
(OUT/'results.json').write_text(json.dumps(data,indent=2))
for case in data['cases']:case['thumbnail']='data:image/jpeg;base64,'+base64.b64encode((OUT/(case['name'].lower()+'.jpg')).read_bytes()).decode()
template=(pathlib.Path(__file__).parent/'review.html').read_text()
(OUT/'review.html').write_text(template.replace('/*PAYLOAD*/',json.dumps(data).replace('</','<\\/')))
print(json.dumps({c['name']:{'walls':len(c['results'][-1]['walls']),'doors':len(c['results'][-1]['portals']),'lights':len(c['results'][-1]['lights'])}for c in data['cases']}))
