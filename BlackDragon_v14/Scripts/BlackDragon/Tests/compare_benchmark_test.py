#!/usr/bin/env python3
"""Synthetic input validation test, not a native benchmark."""
import copy,csv,tempfile
from pathlib import Path
from compare_benchmark import compare,sha
passed=0;failed=0
def check(name,ok):
 global passed,failed
 if ok:passed+=1
 else:failed+=1;print('FAIL:',name)
with tempfile.TemporaryDirectory() as temp:
 root=Path(temp);(root/'trace.txt').write_text('SYNTHETIC TRACE FOR VALIDATOR TEST ONLY')
 config={'runs':[]}
 for pair in range(5):
  for variant in ('B1','C'):
   build='synthetic_'+variant;file=root/(variant+'.csv')
   with file.open('w') as f:
    w=csv.writer(f);w.writerow(['build','kind','key','bucket','value'])
    for k in range(9):
     w.writerow([build,'counter',k,0,10]);w.writerow([build,'max_us',k,0,4])
     for b in range(64):w.writerow([build,'hist_us_log2',k,b,10 if b==2 else 0])
    w.writerow([build,'counter',9,0,100 if variant=='B1' else 40])
   config['runs'].append(dict(pair=pair,variant=variant,build=build,environment='synthetic',set_sha256='1'*64,data_sha256='2'*64,profile_sha256='3'*64,model='synthetic',warmup='warm',start='2026-01-01',end='2026-01-02',actual_end='2026-01-02',completed=True,wall_seconds=10+pair*.01,memory_peak_bytes=1024,trace_path='trace.txt',trace_sha256=sha(root/'trace.txt'),metrics_path=file.name,metrics_sha256=sha(file)))
 result=compare(config,root);check('measured input cannot qualify release',result['status']=='MEASURED_NOT_QUALIFIED' and not result['release_eligible'])
 def refuses(cfg):
  try:compare(cfg,root);return False
  except ValueError:return True
 c=copy.deepcopy(config);c['runs']=c['runs'][:8];check('insufficient pairs',refuses(c))
 c=copy.deepcopy(config);c['runs'][0]['completed']=False;check('incomplete end',refuses(c))
 c=copy.deepcopy(config);c['runs'][0]['metrics_sha256']='0'*64;check('wrong artifact hash',refuses(c))
 c=copy.deepcopy(config);c['runs'][0]['profile_sha256']='x';check('different broker profile',refuses(c))
 c=copy.deepcopy(config);c['runs'][0]['build']='unbound';check('unbound build',refuses(c))
 c=copy.deepcopy(config);c['runs'][0]['wall_seconds']=50;check('noise remains inconclusive',compare(c,root)['status']=='INCONCLUSIVE')
print(f'Benchmark input validator: {passed} passed, {failed} failed');raise SystemExit(bool(failed))
