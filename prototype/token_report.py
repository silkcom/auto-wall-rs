"""Read only this experiment's known local token counters, without copying conversation text."""
import argparse,datetime,json,pathlib
ROOT=pathlib.Path('/private/tmp/auto-wall-ai-v2')
MANIFEST=json.loads((ROOT/'session-manifest.json').read_text())
FILES=MANIFEST['maps']
SESSION_DIR=pathlib.Path(MANIFEST['session_dir'])
PARENT=MANIFEST['parent_file']
def read(path):
 latest=None;meta={};stamp=None;completed=False;model=None;events=0
 for line in path.open():
  try:d=json.loads(line)
  except json.JSONDecodeError:continue
  p=d.get('payload',{})
  if d.get('type')=='session_meta':meta={k:p[k]for k in ['id','agent_path','parent_thread_id','timestamp']if k in p}
  if d.get('type')=='turn_context':model=p.get('model',model)
  if d.get('type')=='event_msg' and p.get('type')=='token_count' and p.get('info'):
   latest=p['info']['total_token_usage'];stamp=d.get('timestamp');events+=1
  if d.get('type')=='event_msg' and p.get('type')=='task_started':completed=False
  if d.get('type')=='event_msg' and p.get('type')=='task_complete':completed=True
 return latest,{'session':meta,'model':model,'last_usage_timestamp':stamp,'completed_event_seen':completed,'usage_events_seen':events}
def row(raw):
 return {**raw,'uncached_input_tokens':raw['input_tokens']-raw.get('cached_input_tokens',0),'uncached_input_plus_output_tokens':raw['input_tokens']-raw.get('cached_input_tokens',0)+raw['output_tokens']}
def main():
 parser=argparse.ArgumentParser();parser.add_argument('--final',action='store_true');a=parser.parse_args();maps={};details={}
 for name,filename in FILES.items():
  raw,detail=read(SESSION_DIR/filename)
  if raw is None:raise ValueError('No usage counter for '+name)
  assert detail['session'].get('agent_path')=='/root/ai_v2_'+name.lower(),'Wrong map thread'
  maps[name]=row(raw);details[name]=detail
  if a.final and not detail['completed_event_seen']:raise ValueError('Thread not complete: '+name)
 parent,_=read(SESSION_DIR/PARENT);base=json.loads((ROOT/'parent-token-baseline.json').read_text())['baseline']
 coordinator=row({k:parent.get(k,0)-base.get(k,0)for k in parent})if base else None
 totals={k:sum(r.get(k,0)for r in maps.values())for k in next(iter(maps.values()))}
 report={'snapshot_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),'final_map_threads':a.final,'maps':maps,'map_totals':totals,'grand_total_through_snapshot':{k:totals.get(k,0)+(coordinator or {}).get(k,0)for k in totals},'coordinator_through_snapshot':coordinator,'details':details,'notes':['Latest cumulative token_count.info.total_token_usage per fresh map thread; do not sum cumulative events.','Total tokens are reported input plus output; cached input is a subset of input. Reasoning output is shown separately as a subset, not added again.','Map totals include prompts, instructions, image/tool interactions, repeated context and final agent responses. No inherited parent conversation was supplied.','Coordinator is a separate cumulative delta from immediately before the feedback request through this snapshot, excluding subsequent integration/final response.','These are measured interactive Codex workflow tokens, not a one-shot production image inference estimate. No pricing or plan-quota conversion is inferred.'],'sources':['https://learn.chatgpt.com/docs/app-server#turn-events']}
 ROOT.mkdir(exist_ok=True);(ROOT/'token-usage.json').write_text(json.dumps(report,indent=2))
 lines=['# AI map revision token usage','',f"Snapshot: {report['snapshot_utc']}",'','| Map | Input (including cache) | Cached input | Uncached input | Output | Total | Uncached input + output |','| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
 for name,r in [*maps.items(),('Map subtotal',totals)]:lines.append('| '+name+' | '+' | '.join(f"{r[k]:,}"for k in ['input_tokens','cached_input_tokens','uncached_input_tokens','output_tokens','total_tokens','uncached_input_plus_output_tokens'])+' |')
 lines+=['','\n'.join('- '+n for n in report['notes'])]
 if coordinator:lines+=['',f"Combined map + coordinator through snapshot: {report['grand_total_through_snapshot']['total_tokens']:,} total tokens; {report['grand_total_through_snapshot']['uncached_input_plus_output_tokens']:,} uncached input + output.",'',f"Coordinator through snapshot: {coordinator['total_tokens']:,} total tokens; {coordinator['cached_input_tokens']:,} cached input; {coordinator['uncached_input_plus_output_tokens']:,} uncached input + output."]
 (ROOT/'token-usage.md').write_text('\n'.join(lines)+'\n')
 print(json.dumps({'maps':maps,'map_totals':totals,'grand_total_through_snapshot':{k:totals.get(k,0)+(coordinator or {}).get(k,0)for k in totals},'coordinator_through_snapshot':coordinator,'final':a.final}))
if __name__=='__main__':main()
