#!/usr/bin/env python3
"""Production module adapters. Host PASS never promotes native/MT5 gates."""
from pathlib import Path
import argparse,hashlib,json,re,subprocess
R=Path(__file__).resolve().parents[4];I=R/'BlackDragon_v14/Include/BlackDragon';T=Path(__file__).parent
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,required=True);a=ap.parse_args();O=a.out.resolve();O.mkdir(parents=True,exist_ok=True)
manifest=[];results=[]
def source(name):
 p=I/name;manifest.append({'path':str(p.relative_to(R)),'sha256':hashlib.sha256(p.read_bytes()).hexdigest()});return p.read_text()
def adapt(s):
 s=re.sub(r'^#include .+$','',s,flags=re.M)
 s=re.sub(r'const (\w+) &(\w+)\[\]',r'const std::vector<\1> &\2',s)
 s=re.sub(r'(\w+) &(\w+)\[\]',r'std::vector<\1> &\2',s)
 s=re.sub(r'\b(\w+) (\w+)\[\];',r'std::vector<\1> \2;',s)
 s=re.sub(r'\(string\)(AccountInfoInteger\(ACCOUNT_LOGIN\)|BD_HashText\(_Symbol\)|RecoveryMagic_|Magic)',r'std::to_string(\1)',s)
 return s

def extract(s,sig):
 a=s.index(sig);i=s.index('{',a)+1;d=1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]

def run(name,body):
 cpp=O/(name+'.cpp');cpp.write_text(body);exe=O/name
 cmd=['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Wno-unused-parameter',str(cpp),'-o',str(exe)]
 c=subprocess.run(cmd,capture_output=True,text=True);(O/(name+'.compile.log')).write_text(c.stdout+c.stderr)
 if c.returncode:print(c.stderr[-6000:]);results.append({'name':name,'status':'FAIL','phase':'compile'});return
 p=subprocess.run([str(exe)],capture_output=True,text=True);log=p.stdout+p.stderr;(O/(name+'.log')).write_text(log);print(log,end='')
 counts=re.search(r'(\d+) passed, (\d+) failed',log)
 results.append({'name':name,'status':'PASS' if p.returncode==0 and counts and counts[2]=='0' else 'FAIL','assertions_passed':int(counts[1]) if counts else 0,'assertions_failed':int(counts[2]) if counts else 0,'commands':[cmd,[str(exe)]],'exit_code':p.returncode,'native':False})
bridge=(T/'t1725_platform.hpp').read_text()
types_source=source('Types.mqh');enums=extract(types_source,'enum eExecCommandType')+';\n'+extract(types_source,'enum eIntent')+';\n'+extract(types_source,'enum eExecReconcilePolicy')+';\n'
atomic=adapt(source('Diagnostics/AtomicSnapshot.mqh'));outcome=adapt(source('OperationResultStore.mqh'))
arcs=source('Recovery/RecoveryArcsTypes.mqh');types=arcs[arcs.index('enum eArcsLayerState'):arcs.index('void Recovery_ArcsLayerReset')]
legacy=r'''
const int BD_ARCS_MAX_LAYERS=4;
enum eArcsPersistStatus{ARCS_PERSIST_OK,ARCS_PERSIST_NOT_FOUND,ARCS_PERSIST_CORRUPT,ARCS_PERSIST_MISMATCH,ARCS_PERSIST_IO_ERROR};
struct SArcsPersistIdentity{long accountLogin,coreMagic,recoveryMagic,saveSequence;uint symbolHash,semanticHash;double volumeStep,tickSize;};
uint Recovery_ArcsSymbolHash(const string&s){return BD_HashText(s);}uint Recovery_T16SemanticFingerprint(){return 17;}
class CRecoveryArcsPersistence{public:void Init(const string&,long,long,long){}string FileName()const{return "arcs.bin";}eArcsPersistStatus Load(SArcsPersistIdentity&,SArcsDirection&,SArcsDirection&,SArcsExternalPending&,SArcsExternalPending&,std::vector<SArcsLayer>&,std::vector<SArcsLayer>&,string&){return ARCS_PERSIST_NOT_FOUND;}};
'''
ledger=adapt(source('Recovery/RecoveryArcsLedger.mqh'))
exec((T/'t1725_cases.py').read_text())
(O/'extraction.json').write_text(json.dumps(manifest,indent=2));(O/'results.json').write_text(json.dumps(results,indent=2));raise SystemExit(any(x['status']!='PASS' for x in results))
