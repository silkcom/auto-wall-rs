"""Capture one private cavern correction pass, its isolated token usage and supplied-rate cost."""
import argparse,base64,json,math,pathlib,datetime
from decimal import Decimal
parser=argparse.ArgumentParser();parser.add_argument('--revision',type=int,choices=[3,4],default=3);args=parser.parse_args();mode=f'ai-v{args.revision}'
ROOT=pathlib.Path(f'/private/tmp/auto-wall-ai-v{args.revision}');REVIEW=pathlib.Path('/private/tmp/auto-wall-detection-review')
manifest=json.loads((ROOT/'session-manifest.json').read_text());usage=None;completed=False;meta={}
for line in pathlib.Path(manifest['session_file']).open():
 try:d=json.loads(line)
 except json.JSONDecodeError:continue
 p=d.get('payload',{})
 if d.get('type')=='session_meta':meta=p
 if d.get('type')=='event_msg' and p.get('type')=='task_started':completed=False
 if d.get('type')=='event_msg' and p.get('type')=='task_complete':completed=True
 if d.get('type')=='event_msg' and p.get('type')=='token_count' and p.get('info'):usage=p['info']['total_token_usage']
assert meta.get('agent_path')==manifest['agent_path'] and completed and usage,'Isolated task must be complete'
usage={**usage,'uncached_input_tokens':usage['input_tokens']-usage['cached_input_tokens']}
rates={k:Decimal(str(v))for k,v in manifest['rates_per_million'].items()}
# This experiment's telemetry reports zero cache-write tokens, as did the prior passes.
writes=usage.get('cache_write_input_tokens',0)
assert writes==0,'Resolve cache-write/input accounting semantics before calculating a nonzero cache-write case'
counts={'cached_input':usage['cached_input_tokens'],'uncached_input':usage['uncached_input_tokens'],'cache_writes':writes,'output':usage['output_tokens']}
costs={k:Decimal(n)*rates[k]/Decimal(1000000)for k,n in counts.items()};total=sum(costs.values())
report={'snapshot_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Isolated Caverns correction task only; parent coordination/integration excluded. Includes instructions, image/tool interactions, repeated context and final agent response. '+('One construction/quality-check pass, not one inference call.' if args.revision==3 else 'Native-coordinate alignment revision with iterative inspection; not one inference call.'),'usage':usage,'rates_per_million':manifest['rates_per_million'],'costs_usd':{k:str(v)for k,v in costs.items()},'total_cost_usd':str(total)}
(ROOT/'token-cost.json').write_text(json.dumps(report,indent=2))
md=[f'# Caverns: revision {args.revision}','',report['scope'],'','| Category | Tokens | Rate per million | Cost |','| --- | ---: | ---: | ---: |']
for key,n in counts.items():md.append(f'| {key.replace("_"," ")} | {n:,} | ${rates[key]:.2f} | ${costs[key]:.6f} |')
md+=['',f'**Total: ${total:.6f}** ({usage["total_tokens"]:,} reported total tokens).','',f'Snapshot: {report["snapshot_utc"]}']
(ROOT/'token-cost.md').write_text('\n'.join(md)+'\n')
result=json.loads((ROOT/'caverns/result.json').read_text())
if args.revision==3:assert len(result['iterations'])==1,'User requested exactly one quality pass'
w,h=result['width'],result['height'];assert[w,h]==[3600,4500]
def valid(p):return len(p)==2 and all(math.isfinite(x)for x in p)and 0<=p[0]<=w and 0<=p[1]<=h
assert all(valid(a)and valid(b)and a!=b for a,b in result['walls'])
keys=[tuple(sorted((tuple(a),tuple(b))))for a,b in result['walls']];assert len(keys)==len(set(keys))
data=json.loads((REVIEW/'results.json').read_text());case=next(c for c in data['cases']if c['name']=='Caverns')
r={'mode':mode,'original':[w,h],'working':[w,h],'walls':result['walls'],'portals':result['doors'],'lights':[[l['position']['x'],l['position']['y']]for l in result['lights']],'light_records':result['lights'],'probes':[],'review_checks':[],'iterations':len(result['iterations']),'iteration_notes':result['iterations'],'notes':result['notes'],'checks':result['checks'],'annotation_only':True,'token_usage':usage,'cost_total_usd':str(total)}
if args.revision==4:
 snapshots=[]
 for path in sorted((ROOT/'caverns').glob('pass-*-paths.json')):
  paths=json.loads(path.read_text());seen=set();segments=[]
  for trace in paths:
   for a,b in zip(trace['points'],trace['points'][1:]):
    a=[round(x,2)for x in a];b=[round(x,2)for x in b];key=tuple(sorted((tuple(a),tuple(b))))
    if a!=b and key not in seen:seen.add(key);segments.append([a,b])
  snapshots.append({'label':path.stem.replace('-paths',''),'walls':segments})
 if snapshots:
  final_keys={tuple(sorted((tuple(a),tuple(b))))for a,b in r['walls']}
  snapshot_keys={tuple(sorted((tuple(a),tuple(b))))for a,b in snapshots[-1]['walls']}
  if final_keys!=snapshot_keys:snapshots.append({'label':'Final validated geometry','walls':r['walls']})
  r['passes']=snapshots
case['results']=[old for old in case['results']if old['mode']!=mode]+[r];data['cavern_revision_'+str(args.revision)+'_accounting']=report
(REVIEW/'results.json').write_text(json.dumps(data,indent=2))
for c in data['cases']:c['thumbnail']='data:image/jpeg;base64,'+base64.b64encode((REVIEW/(c['name'].lower()+'.jpg')).read_bytes()).decode()
template=(pathlib.Path(__file__).parent/'review.html').read_text();(REVIEW/'review.html').write_text(template.replace('/*PAYLOAD*/',json.dumps(data).replace('</','<\\/')))
print(json.dumps({'walls':len(result['walls']),'doors':len(result['doors']),'lights':len(result['lights']),'usage':usage,'costs_usd':report['costs_usd'],'total_cost_usd':str(total)}))
