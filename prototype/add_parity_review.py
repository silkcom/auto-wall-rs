"""Attach full-path oracle results to the local visual comparison without rerunning old candidates."""
import base64,json,pathlib
from run import agreement,crosses
out=pathlib.Path('/private/tmp/auto-wall-detection-review');oracle=pathlib.Path('/private/tmp/auto-wall-parity')
d=json.loads((out/'results.json').read_text())
for c in d['cases']:
 c['results']=[r for r in c['results'] if not r['mode'].startswith('full-')]
 for profile in ['startup','default']:
  p=json.loads((oracle/f"{c['name'].lower()}-{profile}.json").read_text());uvtt=p['uvtt'];g=uvtt['resolution']['pixels_per_grid']
  walls=[[[pt['x']*g,pt['y']*g]for pt in line]for line in uvtt['line_of_sight']];lights=[[l['position']['x']*g,l['position']['y']*g]for l in uvtt['lights']]
  probes=[]
  for probe in c['results'][0]['probes']:
   actual=any(crosses(probe['a'],probe['b'],a,b)for a,b in walls);probes.append({**probe,'detected_blocked':actual})
  r={'mode':'full-'+profile,'original':p['original_dimensions'],'working':p['working_dimensions'],'decode_ms':0,'detect_median_ms':p['detection_and_display_ms'],'detect_samples_ms':[p['detection_and_display_ms']],'processing_label':'Automatic processing including preview','peak_rss_mib':None,'export_ms':p['export_with_encoding_ms'],'walls':walls,'lights':lights,'probes':probes,'probe_disagreements':sum(q['reference_blocked']!=q['detected_blocked']for q in probes),'reference_agreement_precision':agreement(walls,c['reference'],.2*c['grid']),'reference_agreement_recall':agreement(c['reference'],walls,.2*c['grid']),'light_reference_matches':0,'light_unmatched_candidates':0,'light_unmatched_reference':0,'light_scores_unavailable':True}
  c['results'].append(r)
(out/'results.json').write_text(json.dumps(d,indent=2))
for c in d['cases']:c['thumbnail']='data:image/jpeg;base64,'+base64.b64encode((out/(c['name'].lower()+'.jpg')).read_bytes()).decode()
s=(pathlib.Path(__file__).parent/'review.html').read_text();s=s.replace('/*PAYLOAD*/',json.dumps(d).replace('</','<\\/'));(out/'review.html').write_text(s)
