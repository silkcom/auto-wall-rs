#!/usr/bin/env python3
"""Compare candidate JSON against the pinned automatic-path oracle."""
import json,sys

def normalized(uvtt):
 uvtt=json.loads(json.dumps(uvtt));uvtt.pop('image',None);uvtt.pop('_preview_pixels',None)
 uvtt['line_of_sight']=sorted([sorted([[p['x'],p['y']]for p in line]) for line in uvtt['line_of_sight']])
 uvtt['lights']=sorted(uvtt.get('lights',[]),key=lambda x:json.dumps(x,sort_keys=True))
 return uvtt

def compare(expected,actual):
 differences=[]
 for k in ['working_dimensions','scale_factor','working_bgr_sha256']:
  if expected.get(k)!=actual.get(k):differences.append(k)
 for name,stage in expected['stages'].items():
  other=actual.get('stages',{}).get(name,{})
  for key in ['contours','lights']:
   if key in stage and stage[key]!=other.get(key):differences.append('stages.'+name+'.'+key)
 if normalized(expected['uvtt'])!=normalized(actual['uvtt']):differences.append('uvtt')
 return differences
if __name__=='__main__':
 a,b=[json.load(open(p))for p in sys.argv[1:3]];diff=compare(a,b)
 print(json.dumps({'parity':not diff,'differing_stages':diff},indent=2));sys.exit(bool(diff))
