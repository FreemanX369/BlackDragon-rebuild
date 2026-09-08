#!/usr/bin/env python3
"""Additional production-body host gates. Memory filesystem is an explicit seam;
C++ struct layout is NOT native MQL5 binary-layout proof. No terminal is run.
"""
from pathlib import Path
import argparse,ast,hashlib,json,re,subprocess
R=Path(__file__).resolve().parents[4];I=R/'BlackDragon_v14/Include/BlackDragon';T=Path(__file__).parent
ap=argparse.ArgumentParser();ap.add_argument('--out',type=Path,default=Path('/tmp/bd-t1724-extra'));a=ap.parse_args();O=a.out.resolve();O.mkdir(parents=True,exist_ok=True)
module=ast.parse((T/'t1724_integration.py').read_text())
bridge=next(ast.literal_eval(n.value) for n in module.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='bridge' for t in n.targets))
manifest=[];results=[]
def extract(path,sig):
 s=path.read_text();start=s.index(sig);i=s.index('{',start)+1;depth=1
 while depth:depth+=(s[i]=='{')-(s[i]=='}');i+=1
 body=s[start:i];manifest.append({'path':str(path.relative_to(R)),'signature':sig,'sha256':hashlib.sha256(body.encode()).hexdigest()});return body

def run(name,s):
 cpp=O/(name+'.cpp');cpp.write_text(s);exe=O/name
 commands=[['g++','-std=c++17','-O1','-g','-Wall','-Wextra','-Wno-unused-parameter',str(cpp),'-I',str(O/'include'),'-o',str(exe)],[str(exe)]]
 c=subprocess.run(commands[0],capture_output=True,text=True);(O/(name+'.compile.log')).write_text(c.stdout+c.stderr)
 if c.returncode:print(c.stderr);raise SystemExit(c.returncode)
 p=subprocess.run(commands[1],capture_output=True,text=True);log=p.stdout+p.stderr;(O/(name+'.log')).write_text(log);print(log,end='')
 counts=re.search(r': (\d+) passed, (\d+) failed',log)
 result={'name':name,'exit_code':p.returncode,'status':'PASS' if p.returncode==0 and counts and counts[2]=='0' else 'FAIL','assertions_passed':int(counts[1]) if counts else 0,'assertions_failed':int(counts[2]) if counts else 0,'commands':commands,'native':False};results.append(result)
 return result

protect=I/'Pyramid/PyramidProtection.mqh';s=protect.read_text()
structs=s[s.index('enum ePyProtectPhase'):s.index('// Extends existing basket')]
methods='\n'.join(extract(protect,sig) for sig in ['uint HashBytes(','bool Save()','bool HeaderMatches(','long PayloadSize(','bool ReadPayload(','bool LoadedStateValid(','bool LoadFlatCheckpoint(','bool Load()','int Pending()','void EraseOperationAt(','void CompactTerminalNonRhOperations()'])
methods=methods.replace('const uchar &bytes[]','const std::vector<uchar> &bytes').replace('uchar bytes[];','std::vector<uchar> bytes;')
fs=bridge+r'''
#include <map>
#include <cstring>
using uchar=unsigned char;
template<class T>void ZeroMemory(T&v){v=T{};}
enum {INVALID_HANDLE=-1,FILE_BIN=1,FILE_WRITE=2,FILE_READ=4,FILE_REWRITE=8,ACCOUNT_LOGIN=9};
enum {EXEC_CMD_PY_RH_TRIM=1,EXEC_CMD_PY_PROTECT_MODIFY=2,EXEC_CMD_PY_PROTECT_CLOSE=3};
string _Symbol="fixture";long Magic=100,RecoveryMagic_=200;
long AccountInfoInteger(int){return 123;}
uint Recovery_StringHash(const string&s){uint h=2166136261;for(unsigned char c:s){h^=c;h*=16777619;}return h;}
struct Handle{string path;size_t at=0;};
std::map<string,std::vector<uchar>> files;
std::map<int,Handle> handles;int nextHandle=1,writeCall=0,failWrite=0,readCall=0,failRead=0;
bool failOpen=false,failMove=false,failSeek=false;
bool FileIsExist(const string&p){return files.count(p);}
bool FileDelete(const string&p){return files.erase(p)>0;}
int FileOpen(const string&p,int flags){if(failOpen)return INVALID_HANDLE;if(flags== (FILE_BIN|FILE_WRITE))files[p].clear();if(!files.count(p))return INVALID_HANDLE;int h=nextHandle++;handles[h]={p,0};return h;}
void FileClose(int h){handles.erase(h);}void FileFlush(int){}
ulong FileSize(int h){return files.at(handles.at(h).path).size();}
ulong FileTell(int h){return handles.at(h).at;}
bool FileSeek(int h,long pos,int origin){if(failSeek||origin!=SEEK_SET||pos<0)return false;handles.at(h).at=pos;return true;}
template<class V>uint FileWriteStruct(int h,const V&v){writeCall++;auto &f=handles.at(h);auto &bytes=files[f.path];uint n=sizeof(V);if(writeCall==failWrite)n--;if(bytes.size()<f.at+n)bytes.resize(f.at+n);std::memcpy(bytes.data()+f.at,&v,n);f.at+=n;return n;}
template<class V>uint FileReadStruct(int h,V&v){auto &f=handles.at(h);auto &bytes=files[f.path];size_t available=f.at<bytes.size()?bytes.size()-f.at:0;uint n=std::min(available,sizeof(V));if(n)std::memcpy(&v,bytes.data()+f.at,n);f.at+=n;return n;}
uint FileReadArray(int h,std::vector<uchar>&v,int from,int count){readCall++;if(readCall==failRead)return 0;auto &f=handles.at(h);auto &bytes=files[f.path];if(from<0||count<0||from+count>(int)v.size())return 0;size_t available=f.at<bytes.size()?bytes.size()-f.at:0;uint n=std::min(available,(size_t)count);if(n)std::memcpy(v.data()+from,bytes.data()+f.at,n);f.at+=n;return n;}
bool FileMove(const string&from,int,const string&to,int){if(failMove||!files.count(from))return false;files[to]=files[from];files.erase(from);return true;}
void ResetFaults(){failOpen=failMove=failSeek=false;writeCall=readCall=failWrite=failRead=0;}
'''+ '\n#include "'+str(I/'Pyramid/PyramidProtectionPolicy.mqh')+'"\n'+structs+r'''
class DiskFixture {public:
 SPyProtectGroup m_group[2]{};SPyProtectRetry m_retry[2]{};
 std::vector<SPyProtectMember> m_members;std::vector<SPyProtectOperation> m_ops;
 long m_nonce=42;string m_file="state.bin";bool m_fault=false,persist=true;
 bool Persisted()const{return persist;}uint Semantics()const{return 17;}
 void Fault(const string&){m_fault=true;}
'''+methods+r'''
};
void Seed(DiskFixture &f){f.m_group[0].phase=PY_PREPARE;f.m_group[0].serial=1;f.m_group[0].mode=2;f.m_group[0].stop=3000;
 f.m_members.resize(1);f.m_members[0].dir=0;f.m_members[0].id=101;f.m_members[0].ticket=10;f.m_members[0].serial=1;
 f.m_ops.resize(1);f.m_ops[0].dir=0;f.m_ops[0].kind=EXEC_CMD_PY_PROTECT_MODIFY;f.m_ops[0].serial=1;f.m_ops[0].ticket=10;f.m_ops[0].id=101;f.m_ops[0].nonce=42;f.m_ops[0].beforeLots=1;f.m_ops[0].targetSl=3001;
 f.m_retry[0].id=101;f.m_retry[0].kind=EXEC_CMD_PY_PROTECT_MODIFY;f.m_retry[0].serial=1;f.m_retry[0].rejects=3;f.m_retry[0].nextEligible=900;}
int main(){
 DiskFixture f;Seed(f);
 T1724Check("disk v2 actual Save succeeds",f.Save());auto original=files["state.bin"];
 DiskFixture loaded;T1724Check("disk v2 actual Load roundtrip",loaded.Load());
 T1724Check("disk retry and pending identity survive host roundtrip",loaded.m_retry[0].nextEligible==900&&loaded.m_retry[0].rejects==3&&loaded.m_ops.size()==1&&loaded.m_ops[0].nonce==42);
 SPyProtectDisk h;std::memcpy(&h,original.data(),sizeof(h));
 T1724Check("disk v2 size exact",original.size()==sizeof(h)+f.PayloadSize(h));
 std::vector<uchar> legacy(original.begin(),original.end()-2*sizeof(SPyProtectRetry));h.version=1;
 std::vector<uchar> payload(legacy.begin()+sizeof(h),legacy.end());h.checksum=f.HashBytes(payload);std::memcpy(legacy.data(),&h,sizeof(h));files["state.bin"]=legacy;
 DiskFixture v1;T1724Check("disk v1 migration reader",v1.Load());
 T1724Check("disk v1 keeps pending and initializes retry",v1.m_ops.size()==1&&v1.m_ops[0].nonce==42&&v1.m_retry[0].rejects==0&&v1.m_retry[0].nextEligible==0);
 T1724Check("disk migrated writer emits v2",v1.Save());std::memcpy(&h,files["state.bin"].data(),sizeof(h));T1724Check("disk migrated header v2",h.version==2);
 files["state.bin"]=original;files["state.bin"].pop_back();DiskFixture truncated;T1724Check("disk truncated payload refused",!truncated.Load());
 files["state.bin"]=original;files["state.bin"][sizeof(h)+3]^=0x40;DiskFixture badcrc;T1724Check("disk corrupt checksum refused",!badcrc.Load());
 files["state.bin"]=original;std::memcpy(&h,original.data(),sizeof(h));h.account=999;std::memcpy(files["state.bin"].data(),&h,sizeof(h));DiskFixture wrong;T1724Check("disk wrong account refused",!wrong.Load());
 files["state.bin"]=original;f.m_group[0].stop=3010;ResetFaults();failWrite=3;
 T1724Check("disk short temp write refuses save",!f.Save());T1724Check("disk short write preserves previous snapshot",files["state.bin"]==original);
 ResetFaults();failRead=1;T1724Check("disk checksum-read failure refuses save",!f.Save());T1724Check("disk checksum-read failure preserves snapshot",files["state.bin"]==original);
 ResetFaults();failMove=true;T1724Check("disk atomic-replace failure refuses save",!f.Save());T1724Check("disk failed replace preserves old snapshot",files["state.bin"]==original);
 ResetFaults();T1724Check("disk successful replace commits complete new snapshot",f.Save());DiskFixture latest;T1724Check("disk new snapshot readable after replace",latest.Load()&&latest.m_group[0].stop==3010);
 // Writer/reader share boundary: a valid pending record is repeated only for
 // this allocation/count stress seam, not a simulated broker portfolio.
 DiskFixture cap;Seed(cap);cap.m_members.resize(65536);for(auto &m:cap.m_members){m.dir=0;m.id=101;m.ticket=10;}
 cap.m_members.resize(65535);T1724Check("disk 65535-member boundary accepted",cap.Save());
 cap.m_members.resize(65536);cap.m_members.back().dir=0;cap.m_members.back().id=101;cap.m_members.back().ticket=10;
 T1724Check("disk 65536-member boundary accepted",cap.Save());DiskFixture capRead;T1724Check("disk boundary snapshot reloads",capRead.Load()&&capRead.m_members.size()==65536);
 auto boundary=files["state.bin"];cap.m_members.resize(65537);
 T1724Check("disk 65537-member append refused",!cap.Save());T1724Check("disk over-cap writer preserves prior snapshot",files["state.bin"]==boundary);
 DiskFixture broken;Seed(broken);broken.m_ops[0].dir=9;SPyProtectDisk bh{};bh.members=1;bh.operations=1;
 T1724Check("disk loaded operation direction must be valid",!broken.LoadedStateValid(bh));
 T1724Check("disk writer refuses invalid operation fields",!broken.Save()&&files["state.bin"]==boundary);
 broken.m_ops[0].dir=0;broken.m_retry[0].rejects=8;broken.m_retry[0].reconcile=false;
 T1724Check("disk exhausted retry cannot load as retryable",!broken.LoadedStateValid(bh));
 DiskFixture flat;flat.m_group[0].phase=PY_EMPTY;flat.m_group[1].phase=PY_EMPTY;flat.m_nonce=99;
 T1724Check("T1725 flat nonce checkpoint saved",flat.Save());DiskFixture off;
 T1724Check("T1725 OFF can load flat nonce receipt",off.LoadFlatCheckpoint()&&off.m_nonce==99);
 DiskFixture active;Seed(active);active.Save();DiskFixture blocked;
 T1724Check("T1725 OFF refuses active obligation",!blocked.LoadFlatCheckpoint());
 std::cout<<"T17.24 production persistence host: "<<passed<<" passed, "<<failed<<" failed\n";
 return failed?1:0;
}
'''
run('persistence_host',fs)

# ADX production class; only platform API/base interface supplied by fixture.
adx=(I/'Filters/AdxFilter.mqh').read_text();manifest.append({'path':'BlackDragon_v14/Include/BlackDragon/Filters/AdxFilter.mqh','sha256':hashlib.sha256(adx.encode()).hexdigest()})
adx=re.sub(r'^#include .*$','',adx,flags=re.M)
adx_cpp=bridge+r'''
struct EAContext{};class IEntryFilter{public:virtual bool Allow(const EAContext&,int)=0;};
#include <limits>
const double EMPTY_VALUE=std::numeric_limits<double>::max();
enum {INVALID_HANDLE=-1,PERIOD_CURRENT=0};int AdxPeriod=14;double MinAdx=20;
string _Symbol="fixture";int handle=1,copyCount=1,releases=0;double adxValue=25;
int iADX(const string&,int,int){return handle;}void IndicatorRelease(int){releases++;}
int CopyBuffer(int,int,int start,int,double *out){if(start!=1)return 0;out[0]=adxValue;return copyCount;}
'''+adx+r'''
int main(){EAContext ctx;{
 CAdxFilter f;T1724Check("ADX uninitialized blocks",!f.Allow(ctx,0));
 handle=-1;T1724Check("ADX init failure returned",!f.Init());T1724Check("ADX invalid handle blocks",!f.Allow(ctx,1));
 handle=1;T1724Check("ADX valid handle initializes",f.Init());
 copyCount=0;T1724Check("ADX missing buffer blocks",!f.Allow(ctx,0));
 copyCount=1;adxValue=19.99;T1724Check("ADX low trend blocks",!f.Allow(ctx,0));
 adxValue=20;T1724Check("ADX threshold equality allows",f.Allow(ctx,1));
 adxValue=30;T1724Check("ADX above threshold allows both directions",f.Allow(ctx,0)&&f.Allow(ctx,1));
 adxValue=std::numeric_limits<double>::quiet_NaN();T1724Check("ADX NaN is invalid",!f.Allow(ctx,0));
 adxValue=std::numeric_limits<double>::infinity();T1724Check("ADX infinite data is invalid",!f.Allow(ctx,0));
 adxValue=EMPTY_VALUE;T1724Check("ADX EMPTY_VALUE is invalid",!f.Allow(ctx,0));
 }T1724Check("ADX initialized handle released",releases==1);
 std::cout<<"T17.24 production ADX host: "<<passed<<" passed, "<<failed<<" failed\n";return failed?1:0;}
'''
run('adx_host',adx_cpp)

# Shared actual cash reducer plus actual Basket daily/commission methods.
header=(I/'CashLedger.mqh').read_text();inc=O/'include/BlackDragon';inc.mkdir(parents=True,exist_ok=True)
header=re.sub(r'\b(ulong|long|SBDCashDeal)\s+(\w+)\[\];',r'std::vector<\1> \2;',header)
(inc/'CashLedger.mqh').write_text(header)
account=bridge+'\n#include "'+str(I/'Pyramid/PyramidProtectionPolicy.mqh')+'"\n#include "'+str(T/'t1724_cash_fixture.mqh')+'"\n'+r"""
string _Symbol="fixture";long Magic=1000;bool flag_Hand_Ord=false;
enum {ACCOUNT_BALANCE=400};double balance=1007.6;
double AccountInfoDouble(int){return balance;}
struct PositionInfo{ulong ticket=0,positionId=0;};
struct BasketSide{int count=0;std::vector<PositionInfo> pos;};
#define HistorySelectByPosition T1724HistorySelectByPosition
#define HistoryDealsTotal T1724HistoryDealsTotal
#define HistoryDealGetTicket T1724HistoryDealGetTicket
#define HistoryDealGetDouble T1724HistoryDealGetDouble
class AccountingFixture {public:
 CScopedDayCashLedger m_dayCash;bool m_dayCashAnchored=false;
 datetime m_dayStart=0;double m_dayProfit=0,m_dayStartBalance=0;
"""+extract(I/'BasketManager.mqh','void RefreshDayCash(')+extract(I/'BasketManager.mqh','bool TrySumCommission(')+r"""
};
int main(){
 datetime day=100*86400,now=day+100;T1724ResetHistory();
 T1724Add(10,101,1000,DEAL_ENTRY_IN,day+1,0,-1,-.2);
 T1724Add(11,101,0,DEAL_ENTRY_OUT,day+2,10,-1,-.2);
 AccountingFixture a;a.RefreshDayCash(now);
 T1724Check("Q20 initial scope-derived denominator",std::abs(a.m_dayStartBalance-1000)<1e-8&&std::abs(a.m_dayProfit-7.6)<1e-8);
 balance+=200;a.RefreshDayCash(now+1);
 T1724Check("Q20 external deposit does not change session anchor",std::abs(a.m_dayStartBalance-1000)<1e-8);
 AccountingFixture restart;restart.RefreshDayCash(now+1);
 T1724Check("Q20 restart reconstructs approved scoped denominator, not midnight balance",std::abs(restart.m_dayStartBalance-1200)<1e-8);
 balance=1234;a.RefreshDayCash(day+86400+10);
 T1724Check("Q20 day rollover rebases once",std::abs(a.m_dayStartBalance-1234)<1e-8&&a.m_dayProfit==0);
 t1724_historyOk=false;AccountingFixture missing;missing.RefreshDayCash(now);
 T1724Check("Q19 history failure does not publish a valid day anchor",!missing.m_dayCash.Valid()&&!missing.m_dayCashAnchored);
 t1724_historyOk=true;BasketSide side;side.count=1;side.pos.resize(1);side.pos[0].ticket=999;side.pos[0].positionId=101;
 double cost=0;
 T1724Check("Q21 commission resolves immutable ID instead of live ticket",a.TrySumCommission(side,cost)&&cost==-2);
 side.pos[0].ticket=1001;
 T1724Check("Q21 ticket replacement preserves commission",a.TrySumCommission(side,cost)&&cost==-2);
 t1724_historyOk=false;
 T1724Check("Q22 commission history outage invalid",!a.TrySumCommission(side,cost));
 t1724_historyOk=true;
 T1724Check("Q22 commission history can recover",a.TrySumCommission(side,cost)&&cost==-2);
 side.pos[0].positionId=404;
 T1724Check("Q22 empty immutable history invalid, not zero proof",!a.TrySumCommission(side,cost));
 side.pos[0].positionId=0;
 T1724Check("Q21 zero position identity invalid",!a.TrySumCommission(side,cost));
 std::cout<<"T17.24 production accounting host: "<<passed<<" passed, "<<failed<<" failed\n";return failed?1:0;
}
"""
run('accounting_host',account)
(O/'extraction.json').write_text(json.dumps(manifest,indent=2));(O/'results.json').write_text(json.dumps(results,indent=2))
raise SystemExit(any(x['status']!='PASS' for x in results))
