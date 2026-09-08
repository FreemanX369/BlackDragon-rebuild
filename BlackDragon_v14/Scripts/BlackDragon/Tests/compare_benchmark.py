#!/usr/bin/env python3
"""Validate paired native exports; never generates a benchmark from host models.
CSV timing quantiles are conservative log2 bucket intervals, not exact values.
"""
import argparse,csv,hashlib,json,math,statistics
from pathlib import Path

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def metrics(path,build):
 counters={};hist={};maximum={}
 for row in csv.DictReader(path.open(encoding='utf-8-sig')):
  if row['build']!=build:raise ValueError('metric build identity mismatch')
  k=int(row['key']);v=int(row['value']);b=int(row['bucket'])
  if v<0:raise ValueError('negative metric')
  if row['kind']=='counter':counters[k]=v
  if row['kind']=='max_us':maximum[k]=v
  if row['kind']=='hist_us_log2':
   if b<0 or b>63:raise ValueError('invalid histogram bucket')
   hist.setdefault(k,{})[b]=v
 summary={}
 for k in range(9):
  bins=hist.get(k,{})
  if len(bins)!=64 or sum(bins.values())!=counters.get(k,0):raise ValueError('incomplete histogram')
  n=sum(bins.values());item={'count':n,'max_us':maximum.get(k)}
  for label,q in [('p50',.50),('p95',.95),('p99',.99)]:
   cumulative=0;interval=None
   for b in range(64):
    cumulative+=bins[b]
    if n and cumulative>=math.ceil(n*q):interval=[0 if b==0 else 2**b,2**(b+1)-1];break
   item[label+'_us_interval']=interval
  summary[str(k)]=item
 return counters,summary

def compare(config,root):
 runs=config['runs'];pairs={};artifacts=[];problems=[]
 fields=['environment','set_sha256','data_sha256','profile_sha256','model','warmup','start','end']
 for r in runs:
  if r['variant'] not in ('B1','C') or r['build']=='unbound':raise ValueError('unbound variant/build')
  if not r['completed'] or r['actual_end']!=r['end']:raise ValueError('scenario did not complete end date')
  for key in ['wall_seconds','memory_peak_bytes']:
   if not math.isfinite(r[key]) or r[key]<=0:raise ValueError('invalid run metric')
  for key in ['metrics','trace']:
   p=(root/r[key+'_path']).resolve()
   if not p.is_relative_to(root.resolve()) or not p.is_file():raise ValueError('missing/unsafe artifact path')
   if sha(p)!=r[key+'_sha256']:raise ValueError('artifact hash mismatch')
   artifacts.append({'path':str(p),'sha256':sha(p),'size':p.stat().st_size})
  counts,hist=metrics(root/r['metrics_path'],r['build']);r=dict(r,counters=counts,latency=hist)
  pair=pairs.setdefault(str(r['pair']),{})
  if r['variant'] in pair:raise ValueError('duplicate pair variant')
  pair[r['variant']]=r
 if len(pairs)<5:raise ValueError('at least five paired runs required')
 changes=[];walls={'B1':[],'C':[]};memory={'B1':[],'C':[]}
 for pair,r in pairs.items():
  if set(r)!= {'B1','C'}:raise ValueError('unpaired run')
  b,c=r['B1'],r['C']
  if any(b[k]!=c[k] for k in fields):raise ValueError('paired run configuration mismatch')
  if b['trace_sha256']!=c['trace_sha256']:raise ValueError('behavior trace differs')
  if b['counters'].get(0,0)<=0 or c['counters'].get(0,0)<=0:raise ValueError('empty tick workload')
  before=b['counters'].get(9,0);after=c['counters'].get(9,0)
  reduction=1-after/before if before else None
  item={'pair':pair,'position_visit_reduction':reduction,'latency':{}}
  for handler in ('0','1','2'):
   item['latency'][handler]={'B1':b['latency'][handler],'C':c['latency'][handler]}
  changes.append(item)
  for v in walls:walls[v].append(r[v]['wall_seconds']);memory[v].append(r[v]['memory_peak_bytes'])
 def summary(xs):return {'median':statistics.median(xs),'min':min(xs),'max':max(xs),'spread':max(xs)-min(xs)}
 for variant,xs in walls.items():
  if (max(xs)-min(xs))/statistics.median(xs)>.10:problems.append(variant+' wall-time spread exceeds 10%')
 # Proposal budgets are not owner-approved and log2 intervals cannot establish
 # a 5% latency claim in the usual case. Preserve that distinction explicitly.
 return {'schema':'bd-paired-benchmark/1','status':'INCONCLUSIVE' if problems else 'MEASURED_NOT_QUALIFIED',
         'release_eligible':False,'pairs':changes,'wall_seconds':{v:summary(x) for v,x in walls.items()},
         'memory_peak_bytes':{v:summary(x) for v,x in memory.items()},'problems':problems,
         'limitations':['Position visit counts are not unique whole-account enumeration counts.','Percentiles are bucket intervals.','B1 native correctness qualification and approved budgets remain separate gates.'], 'artifacts':artifacts}

def main():
 p=argparse.ArgumentParser(description=__doc__);p.add_argument('input',type=Path);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
 try:result=compare(json.loads(a.input.read_text()),a.input.parent);code=0
 except (KeyError,TypeError,ValueError,OSError) as error:result={'schema':'bd-paired-benchmark/1','status':'INVALID','reason':str(error),'release_eligible':False};code=1
 a.out.parent.mkdir(parents=True,exist_ok=True);a.out.write_text(json.dumps(result,indent=2)+'\n');print(result['status']);return code
if __name__=='__main__':raise SystemExit(main())
