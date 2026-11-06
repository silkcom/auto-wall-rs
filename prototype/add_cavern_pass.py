"""Capture one private cavern correction pass, its isolated token usage and supplied-rate cost."""
import base64,json,math,pathlib,datetime
from decimal import Decimal
ROOT=pathlib.Path('/private/tmp/auto-wall-ai-v3');REVIEW=pathlib.Path('/private/tmp/auto-wall-detection-review')
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
report={'snapshot_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'scope':'Single isolated Caverns correction task only; parent coordination/integration excluded. Includes instructions, image/tool interactions, repeated context and final agent response. One construction/quality-check pass, not one inference call.','usage':usage,'rates_per_million':manifest['rates_per_million'],'costs_usd':{k:str(v)for k,v in costs.items()},'total_cost_usd':str(total)}
(ROOT/'token-cost.json').write_text(json.dumps(report,indent=2))
md=['# Caverns: one correction pass','',report['scope'],'','| Category | Tokens | Rate per million | Cost |','| --- | ---: | ---: | ---: |']
for key,n in counts.items():md.append(f'| {key.replace("_"," ")} | {n:,} | ${rates[key]:.2f} | ${costs[key]:.6f} |')
md+=['',f'**Total: ${total:.6f}** ({usage["total_tokens"]:,} reported total tokens).','',f'Snapshot: {report["snapshot_utc"]}']
(ROOT/'token-cost.md').write_text('\n'.join(md)+'\n')
result=json.loads((ROOT/'caverns/result.json').read_text());assert len(result['iterations'])==1,'User requested exactly one quality pass'
w,h=result['width'],result['height'];assert[w,h]==[3600,4500]
def valid(p):return len(p)==2 and all(math.isfinite(x)for x in p)and 0<=p[0]<=w and 0<=p[1]<=h
assert all(valid(a)and valid(b)and a!=b for a,b in result['walls'])
keys=[tuple(sorted((tuple(a),tuple(b))))for a,b in result['walls']];assert len(keys)==len(set(keys))
data=json.loads((REVIEW/'results.json').read_text());case=next(c for c in data['cases']if c['name']=='Caverns')
r={'mode':'ai-v3','original':[w,h],'working':[w,h],'walls':result['walls'],'portals':result['doors'],'lights':[[l['position']['x'],l['position']['y']]for l in result['lights']],'light_records':result['lights'],'probes':[],'review_checks':[],'iterations':1,'iteration_notes':result['iterations'],'notes':result['notes'],'checks':result['checks'],'annotation_only':True,'token_usage':usage,'cost_total_usd':str(total)}
case['results']=[old for old in case['results']if old['mode']!='ai-v3']+[r];data['cavern_single_pass_accounting']=report
(REVIEW/'results.json').write_text(json.dumps(data,indent=2))
for c in data['cases']:c['thumbnail']='data:image/jpeg;base64,'+base64.b64encode((REVIEW/(c['name'].lower()+'.jpg')).read_bytes()).decode()
template=(pathlib.Path(__file__).parent/'review.html').read_text();(REVIEW/'review.html').write_text(template.replace('/*PAYLOAD*/',json.dumps(data).replace('</','<\\/')))
print(json.dumps({'walls':len(result['walls']),'doors':len(result['doors']),'lights':len(result['lights']),'usage':usage,'costs_usd':report['costs_usd'],'total_cost_usd':str(total)}))
