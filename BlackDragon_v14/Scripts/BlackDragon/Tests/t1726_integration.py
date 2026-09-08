#!/usr/bin/env python3
"""T17.26 actual production methods + atomic ledger; host API seams, not MT5."""
from pathlib import Path
import ast
T=Path(__file__).resolve().parent
pre=(T/'t1725_integration.py').read_text().split("exec((T/'t1725_cases.py').read_text())")[0]
pre=pre.replace("'-g','-Wall'","'-g','-fsanitize=undefined,bounds','-fno-sanitize-recover=all','-Wall'")
exec(pre)
case=ast.parse((T/'t1725_cases.py').read_text())
history=next(ast.literal_eval(n.value) for n in case.body if isinstance(n,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='history' for t in n.targets))
history=history.replace('DEAL_REASON_SL};','DEAL_REASON_SL,DEAL_REASON_EXPERT,DEAL_ORDER};')
history=history.replace('double lots=.1;','double lots=.1;double sl=0;long reason=DEAL_REASON_EXPERT;ulong order=0;string symbol="fixture";')
history=history.replace('if(k==DEAL_TYPE)return d.type;','if(k==DEAL_TYPE)return d.type;if(k==DEAL_REASON)return d.reason;if(k==DEAL_ORDER)return d.order;')
history=history.replace('k==DEAL_SYMBOL?"fixture"','k==DEAL_SYMBOL?Get(id).symbol')
history=history.replace('k==DEAL_PRICE?d.price:', 'k==DEAL_SL?d.sl:k==DEAL_PRICE?d.price:')
history=history.replace('k==DEAL_VOLUME?d.lots:0;', 'k==DEAL_VOLUME?d.lots:k==DEAL_COMMISSION?-0.25:k==DEAL_SWAP?-0.5:k==DEAL_FEE?-0.125:0;')
stack=source('Recovery/RecoveryArcsStack.mqh');hard=source('Recovery/RecoveryArcsStackHardened.mqh');identity=source('Recovery/RecoveryExecutionIdentity.mqh')
methods='\n'.join(extract(stack,x) for x in ['int Idx(', 'void GetLayer(', 'void PutLayer(', 'int FindLayerByGeneration(', 'bool CursorAfter(', 'void TrackCursor(', 'long ResolveClosedOwnerMagic(', 'eRecoveryCoreDirection DirectionForClose(', 'int ReadReceipt(', 'bool ApplyReceiptEffect(', 'bool ReconcileReceipt(', 'void RecordDealCursor(', 'bool Save('])
methods+='\n'+'\n'.join(extract(hard,x) for x in ['bool RecoveryPositionIdentity(', 'bool DealDirection(', 'bool IsExpectedPersistedProtectiveClose(', 'bool RepairProtectiveLayerDecreases(', 'void RefreshVirtualGenerationFromDeal(', 'bool RememberProtectiveSl(', 'void RefreshClosedGenerationFromDeal(', 'bool ExpectedBrokerSlDeal('])
methods=adapt(methods).replace('g_pyramidProtection.ExpectedRhTrim','g_pyramidProtection->ExpectedRhTrim')
reset=extract(arcs,'void Recovery_ArcsLayerReset(');credit=extract(arcs,'void Recovery_ArcsRecomputeCredit(');math=extract(source('Recovery/RecoveryMath.mqh'),'long Recovery_VolumeToUnitsFloor(')
policy=adapt(source('Recovery/RecoveryT1714InterleavePolicy.mqh'))
proof=extract(identity,'bool Recovery_ProtectiveSlIdentityPure(')
body=bridge+enums+atomic+types+legacy+'\n#define private public\n'+ledger+'\n#undef private\n'+history+r'''
enum eRecoveryCoreDirection{recovery_CORE_BUY,recovery_CORE_SELL};
enum{SL_BROKER,SL_VIRTUAL,recovery_ACTIVE=2};int HedgeSLMode_=SL_BROKER,RecoveryMode_=recovery_ACTIVE;
double _Point=.001;bool modifyProof=false;long liveUnits[2]={0,0},liveUnitsG2[2]={0,0};
struct Protect{bool ExpectedRhTrim(ulong){return false;}}protect;Protect *g_pyramidProtection=&protect;
int Recovery_CycleKey(eRecoveryCoreDirection d){return 100+(int)d;}
int Recovery_ArcsGenerationFromComment(const string &s){return s=="RH100G1"||s=="RH101G1"?1:(s=="RH100G2"||s=="RH101G2"?2:-1);}
bool OC_RhMatchesCycle(const string &s,int key){return s=="RH"+std::to_string(key)+"G1"||s=="RH"+std::to_string(key)+"G2";}
int Recovery_ArcsGenerationFromPositionHistory(ulong pid){for(auto d:db)if(d.pid==pid&&d.entry==DEAL_ENTRY_IN)return Recovery_ArcsGenerationFromComment(d.comment);return -1;}
long Recovery_ArcsLayerUnits(eRecoveryCoreDirection d,int g,double){return g==2?liveUnitsG2[d]:liveUnits[d];}
bool Exec_T14ModifyProofMatches(ulong,long,int,double,double){return modifyProof;}
double Recovery_DealCashPure(double p,double s,double c,double f){return p+s+c+f;}
void Log_Error(const string&,const string&){}
'''+proof+policy+reset+credit+math+extract(hard,'struct SArcsHardeningCloseDeal')+';\n'+r'''
class Fixture{public:
 CArcsLedgerPersistence m_persistence;SArcsDirection m_dir[2];SArcsExternalPending m_pending[2];std::vector<SArcsLayer> m_buyLayers,m_sellLayers;
 bool m_dirty=false,m_persistenceBlocked=false,m_ready=true;long m_saveSequence=0;double m_volumeStep=.01,m_tickSize=.001;
 Fixture():m_buyLayers(4),m_sellLayers(4){ZeroMemory(m_dir);ZeroMemory(m_pending);m_persistence.Init("fixture",123,100,200);}
 void LatchReconcile(eRecoveryCoreDirection d,const string&){m_dir[d].reconcileRequired=true;m_ready=false;}
'''+methods+r'''
 void Init(int side=0){string why;nowMsc=100000;HedgeSLMode_=SL_BROKER;modifyProof=false;historyFail=false;liveUnitsG2[0]=liveUnitsG2[1]=0;
 m_persistence.Init("fixture",123,100,200);m_dir[side].phase=ARCS_BUILDING;m_dir[side].generationCount=1;m_dir[side].activeLayer=0;m_dir[1-side].activeLayer=-1;
 SArcsLayer l{};l.used=true;l.generation=1;l.state=ARCS_LAYER_BUILDING;l.remainingUnits=205;l.openedUnits=205;l.targetUnits=205;l.lockTargetPrice=4593.789;
 PutLayer(side==0?recovery_CORE_BUY:recovery_CORE_SELL,0,l);Check("initial epoch",Save(why));
 nowMsc=180000;m_dir[side].phase=ARCS_LOCKED;l.state=ARCS_LAYER_LOCKED;PutLayer(side==0?recovery_CORE_BUY:recovery_CORE_SELL,0,l);Check("locked epoch",Save(why));nowMsc=210000;
 long openType=side==0?DEAL_TYPE_SELL:DEAL_TYPE_BUY,closeType=side==0?DEAL_TYPE_BUY:DEAL_TYPE_SELL;string comment=side==0?"RH100G1":"RH101G1";
 db={{1300,1300,110000,200,DEAL_ENTRY_IN,comment,4597.429,0,openType,.34,0,DEAL_REASON_EXPERT,1300},
 {1301,1301,120000,200,DEAL_ENTRY_IN,comment,4595.463,0,openType,1.71,0,DEAL_REASON_EXPERT,1301},
 {1415,1300,200000,0,DEAL_ENTRY_OUT,"SL",4594.770,30,closeType,.34,4593.789,DEAL_REASON_SL,1415},
 {1416,1301,200000,0,DEAL_ENTRY_OUT,"SL",4594.770,170,closeType,1.71,4593.789,DEAL_REASON_SL,1416}};liveUnits[0]=0;liveUnits[1]=0;
 }
 bool Reload(){SArcsPersistIdentity id;string why;return m_persistence.Load(id,m_dir[0],m_dir[1],m_pending[0],m_pending[1],m_buyLayers,m_sellLayers,why)==ARCS_PERSIST_OK;}
};
void V1Checkpoint(Fixture &f){
 SBDAtomicHeader h;BD_AtomicIdentity(h,17250002,1,Recovery_T16SemanticFingerprint());h.sequence=8;h.records=1;h.epochs=ArraySize(f.m_persistence.m_epochs);
 int fd=BD_AtomicBegin(f.m_persistence.FileName(),h);bool ok=true;
 ok=FileWriteStruct(fd,f.m_persistence.m_meta)==sizeof(SBDArcsLedgerMeta)&&ok;
 for(int i=0;i<2;i++)ok=FileWriteStruct(fd,f.m_dir[i])==sizeof(SArcsDirection)&&ok;
 for(int i=0;i<2;i++)ok=FileWriteStruct(fd,f.m_pending[i])==sizeof(SArcsExternalPending)&&ok;
 for(int i=0;i<4;i++){ok=FileWriteStruct(fd,f.m_buyLayers[i])==sizeof(SArcsLayer)&&ok;ok=FileWriteStruct(fd,f.m_sellLayers[i])==sizeof(SArcsLayer)&&ok;}
 SBDArcsReceiptV1 r{};r.deal=1415;r.positionId=1300;r.stamp=200000;r.owner=200;r.cycle=1;r.units=34;r.dir=0;r.generation=1;r.phase=ARCS_LOCKED;r.cash=29.125;
 ok=FileWriteStruct(fd,r)==sizeof(SBDArcsReceiptV1)&&ok;
 for(auto ep:f.m_persistence.m_epochs)ok=FileWriteStruct(fd,ep)==sizeof(SBDArcsEpoch)&&ok;
 Check("create real v1 layout/checksum",BD_AtomicCommit(f.m_persistence.FileName(),fd,h,ok));
}
int main(){
 Fixture f;f.Init();string why;
 Check("incident leg1 large gap accepted",f.ExpectedBrokerSlDeal(1415));Check("incident leg2 large gap accepted",f.ExpectedBrokerSlDeal(1416));
 SArcsHardeningCloseDeal d{};d.deal=1415;d.type=DEAL_TYPE_BUY;d.reason=DEAL_REASON_SL;d.programmedSl=4593.789;d.dealPrice=4594.770;
 Check("repair callback share decision",f.IsExpectedPersistedProtectiveClose(recovery_CORE_BUY,f.m_buyLayers[0],d));
 db[2].price=9000;Check("extreme gap ownership unchanged",f.ExpectedBrokerSlDeal(1415));db[2].price=4593.789;
 db[2].reason=DEAL_REASON_EXPERT;Check("manual/expert close rejected at exact fill",!f.ExpectedBrokerSlDeal(1415));db[2].reason=DEAL_REASON_SL;
 db[0].owner=999;Check("wrong opening owner rejected",!f.ExpectedBrokerSlDeal(1415));db[0].owner=200;
 db[0].comment="RH101G1";Check("wrong opening cycle rejected",!f.ExpectedBrokerSlDeal(1415));db[0].comment="RH100G1";
 db[0].type=DEAL_TYPE_BUY;Check("wrong opening direction rejected",!f.ExpectedBrokerSlDeal(1415));db[0].type=DEAL_TYPE_SELL;
 db[2].symbol="other";Check("wrong symbol rejected",!f.ExpectedBrokerSlDeal(1415));db[2].symbol="fixture";
 db[2].entry=DEAL_ENTRY_IN;Check("entry deal rejected",!f.ExpectedBrokerSlDeal(1415));db[2].entry=DEAL_ENTRY_OUT;
 db[2].pid=999;Check("unknown position rejected",!f.ExpectedBrokerSlDeal(1415));db[2].pid=1300;
 db[2].sl=4590;Check("unknown SL rejected",!f.ExpectedBrokerSlDeal(1415));db[2].sl=4593.789;
 db[2].price=0;Check("invalid fill rejected",!f.ExpectedBrokerSlDeal(1415));db[2].price=4594.770;
 historyFail=true;Check("missing history fails closed",!f.ExpectedBrokerSlDeal(1415));historyFail=false;
 double target=f.m_buyLayers[0].lockTargetPrice;f.m_buyLayers[0].lockTargetPrice=0;
 Check("missing intent rejected",!f.ExpectedBrokerSlDeal(1415));modifyProof=true;Check("exact modify recovers moved target",f.ExpectedBrokerSlDeal(1415));modifyProof=false;f.m_buyLayers[0].lockTargetPrice=target;
 long cycle=0;nowMsc=110000;f.m_dir[0].phase=ARCS_ACTIVE;f.m_persistence.RecordPhase(0,f.m_dir[0]);f.m_dir[0].phase=ARCS_LOCKED;f.m_persistence.RecordPhase(0,f.m_dir[0]);nowMsc=210000;
 Check("same-ms phase changes do not erase campaign",f.m_persistence.CycleAt(0,110000,cycle)&&cycle==1&&f.ExpectedBrokerSlDeal(1415));
 f.m_persistence.NewCycle(0);Check("prior campaign without receipt rejected",!f.ExpectedBrokerSlDeal(1415));f.m_persistence.m_meta.cycle[0]--;
 // Both broker effects visible before Overlap finalizer: commit both actual receipts before topology.
 Check("two legs refresh succeeds",f.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why));
 SBDArcsReceipt r1,r2;Check("both receipts protective",f.m_persistence.Get(1415,r1)&&f.m_persistence.Get(1416,r2)&&r1.protectiveSl&&r2.protectiveSl);
 Check("actual profit and all costs once",f.m_buyLayers[0].realizedOtherCash==198.25&&f.m_buyLayers[0].remainingUnits==0);
 Check("no theoretical funding credit",f.m_dir[0].hedgeFundingCash==0&&f.m_dir[0].availableCredit==0);
 Check("atomic save before retirement",f.Save(why)&&f.m_persistence.ReceiptsDurable());
 f.m_buyLayers[0].lockTargetPrice=0;f.m_buyLayers[0].used=false;f.m_persistence.NewCycle(0);
 Check("late callback proven across retirement",f.ExpectedBrokerSlDeal(1415)&&f.ExpectedBrokerSlDeal(1416));
 Check("duplicate cash unchanged",f.ReconcileReceipt(1415,false,true,why)&&f.m_buyLayers[0].realizedOtherCash==198.25);
 Check("save retired state",f.Save(why));Fixture restart;Check("reload version2",restart.Reload());Check("restart retains exact proof",restart.ExpectedBrokerSlDeal(1415));
 db[2].sl=4592;Check("changed historical SL cannot reuse receipt",!restart.ExpectedBrokerSlDeal(1415));db[2].sl=4593.789;
 // Current-cycle UPDATE/DELETE are inverse/delta accounting; do not mint credit.
 Fixture c;c.Init();Check("correction seed",c.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why));db[2].cash=-20;
 Check("negative fill economics remain own SL",c.ExpectedBrokerSlDeal(1415)&&c.ReconcileReceipt(1415,false,true,why)&&c.m_buyLayers[0].realizedOtherCash==148.25);
 Check("delete reverses contribution once",c.ReconcileReceipt(1415,true,true,why)&&c.m_buyLayers[0].realizedOtherCash==169.125&&c.ReconcileReceipt(1415,true,true,why));
 // Accounting callback first advances cursor: refresh must still consume known, unapplied proof.
 Fixture early;early.Init();Check("callback receipt first",early.ReconcileReceipt(1415,false,true,why));MqlTradeTransaction tx{};tx.deal=1415;
 early.RefreshClosedGenerationFromDeal(tx);Check("callback-first consumes both legs",early.m_ready&&early.m_buyLayers[0].remainingUnits==0&&early.m_buyLayers[0].realizedOtherCash==198.25);
 tx.deal=1416;early.RefreshClosedGenerationFromDeal(tx);Check("late second callback no double cash",early.m_buyLayers[0].realizedOtherCash==198.25);
 // Partial close then second fill, preserve first receipt and prove only remaining delta.
 Fixture partial;partial.Init();db.pop_back();liveUnits[0]=171;
 Check("partial first geometry",partial.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why)&&partial.m_buyLayers[0].remainingUnits==171);
 db.push_back({1416,1301,205000,0,DEAL_ENTRY_OUT,"SL",4594.770,170,DEAL_TYPE_BUY,1.71,4593.789,DEAL_REASON_SL,1416});liveUnits[0]=0;
 Check("partial second geometry exact once",partial.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why)&&partial.m_buyLayers[0].remainingUnits==0&&partial.m_buyLayers[0].realizedOtherCash==198.25);
 Fixture sell;sell.Init(1);db[2].price=4592.808;db[3].price=4592.808;Check("BUY hedge symmetric gap",sell.ExpectedBrokerSlDeal(1415)&&sell.RepairProtectiveLayerDecreases(recovery_CORE_SELL,why)&&sell.m_sellLayers[0].remainingUnits==0);
 Fixture bad;bad.Init();db[3].reason=DEAL_REASON_EXPERT;Check("mixed manual decrease rejected",!bad.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why)&&bad.m_buyLayers[0].remainingUnits==205);
 Fixture disk;disk.Init();Check("durable baseline",disk.Save(why));Check("RAM repair before write failure",disk.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why));failMove=true;
 Check("failed commit blocks readiness",!disk.Save(why)&&!disk.m_ready&&!disk.m_persistence.ReceiptsDurable());failMove=false;Fixture crash;Check("restart previous atomic image",crash.Reload()&&crash.m_buyLayers[0].remainingUnits==205);Check("restart replays effects once",crash.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why)&&crash.m_buyLayers[0].realizedOtherCash==198.25);
 Fixture migrated;migrated.Init();V1Checkpoint(migrated);Fixture v1;Check("v1 migration readable",v1.Reload());Check("migration never invents SL proof",v1.m_persistence.Get(1415,r1)&&!r1.protectiveSl&&r1.cash==29.125&&r1.programmedSl==0);Check("migration upgrades atomically",v1.Save(why));
 Fixture incomplete;incomplete.Init();db[2].stamp=199000;nowMsc=200000;
 incomplete.m_persistence.RecordPhase(0,incomplete.m_dir[0]);incomplete.m_dir[0].phase=ARCS_TP_PENDING;incomplete.m_persistence.RecordPhase(0,incomplete.m_dir[0]);incomplete.m_dir[0].phase=ARCS_LOCKED;incomplete.m_persistence.RecordPhase(0,incomplete.m_dir[0]);nowMsc=210000;
 Check("ambiguous second receipt rejects batch",!incomplete.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why));
 Check("partial receipt failure cannot persist",incomplete.m_persistenceBlocked&&!incomplete.m_ready&&!incomplete.Save(why));


 // Retained G1, active G2, partial TP already journaled and two asynchronous closes.
 int sequence[3]={0,1,2};
 do {
  Fixture multi;multi.Init(1);auto &g1=multi.m_sellLayers[0];g1.remainingUnits=36;g1.openedUnits=37;
  SArcsLayer g2{};g2.used=true;g2.generation=2;g2.state=ARCS_LAYER_BUILDING;g2.remainingUnits=1;g2.openedUnits=1;
  multi.m_sellLayers[1]=g2;multi.m_dir[1].activeLayer=1;multi.m_dir[1].generationCount=2;
  db={{1197,1197,110000,200,DEAL_ENTRY_IN,"RH101G1",4618.670,0,DEAL_TYPE_BUY,.37,0,DEAL_REASON_EXPERT,1197},
      {1198,1197,185000,0,DEAL_ENTRY_OUT,"partial",4624.375,5.705,DEAL_TYPE_SELL,.01,0,DEAL_REASON_EXPERT,1198},
      {1199,1199,196000,200,DEAL_ENTRY_IN,"RH101G2",4625.814,0,DEAL_TYPE_BUY,.01,0,DEAL_REASON_EXPERT,1199},
      {1200,1200,196000,100,DEAL_ENTRY_IN,"core",4625.613,0,DEAL_TYPE_SELL,.11,0,DEAL_REASON_EXPERT,1200},
      {1201,1200,200100,0,DEAL_ENTRY_OUT,"overlap",4621.491,45.342,DEAL_TYPE_BUY,.11,0,DEAL_REASON_EXPERT,1201},
      {1202,1197,200250,0,DEAL_ENTRY_OUT,"SL",4620.651,71.316,DEAL_TYPE_SELL,.36,4620.670,DEAL_REASON_SL,1202}};
  g1.lockTargetPrice=4620.670;liveUnits[1]=0;liveUnitsG2[1]=1;
  nowMsc=181000;multi.m_dir[1].generationCount=1;multi.m_dir[1].phase=ARCS_TP_PENDING;multi.m_persistence.RecordPhase(1,multi.m_dir[1]);
  nowMsc=186000;multi.m_dir[1].phase=ARCS_LOCKED;multi.m_persistence.RecordPhase(1,multi.m_dir[1]);
  nowMsc=195000;multi.m_dir[1].generationCount=2;multi.m_dir[1].phase=ARCS_BUILDING;multi.m_persistence.RecordPhase(1,multi.m_dir[1]);nowMsc=200500;
  Check("partial TP receipt precedes SL",multi.ReconcileReceipt(1198,false,true,why));
  Check("partial TP funding preserved",std::abs(multi.m_dir[1].hedgeFundingCash-(5.705-.875))<1e-9);
  double prior=g1.realizedOtherCash;
  for(int action:sequence){
   if(action==2)Check("G1/G2 Overlap repair and atomic save",multi.RepairProtectiveLayerDecreases(recovery_CORE_SELL,why)&&multi.Save(why));
   else{ulong ticket=action==0?1201:1202;Check("G1/G2 callback cash",multi.ReconcileReceipt(ticket,false,true,why));MqlTradeTransaction t{};t.deal=ticket;multi.RefreshClosedGenerationFromDeal(t);}
  }
  Check("G1 closed while G2 retained",multi.m_ready&&g1.remainingUnits==0&&multi.m_sellLayers[1].remainingUnits==1);
  Check("G1 actual SL cash exactly once",std::abs(g1.realizedOtherCash-prior-(71.316-.875))<1e-9);
  Check("G1 duplicate receipt remains idempotent",multi.ReconcileReceipt(1202,false,true,why)&&std::abs(g1.realizedOtherCash-prior-(71.316-.875))<1e-9);
  Check("G1/G2 atomic checkpoint",multi.Save(why));Fixture after;Check("G1/G2 reload",after.Reload()&&after.m_sellLayers[0].remainingUnits==0&&after.m_sellLayers[1].remainingUnits==1);
 } while(std::next_permutation(sequence,sequence+3));
 // Native history ranges use whole-second endpoints, while deals retain milliseconds.
 // Exact incident shape: G1 retained 0.36 closes by SL, live G2 is independent.
 for(long ms: {1L,250L,999L}){
  Fixture boundary;boundary.Init(1);nowMsc=200000+ms;
  db.resize(3);db[0].lots=.37;db[2].lots=.36;db[2].stamp=nowMsc;
  boundary.m_sellLayers[0].remainingUnits=36;boundary.m_sellLayers[0].openedUnits=37;
  Check("current-second SL recognized directly",boundary.ExpectedBrokerSlDeal(1415));
  bool ok=boundary.RepairProtectiveLayerDecreases(recovery_CORE_SELL,why);
  if(!ok)std::cout<<"BOUNDARY ms="<<ms<<" "<<why<<"\n";
  Check("current-second protective history visible",ok&&boundary.m_sellLayers[0].remainingUnits==0);
 }
 Fixture virt;virt.Init();HedgeSLMode_=SL_VIRTUAL;virt.m_buyLayers[0].virtualSlArmed=true;db[2].reason=DEAL_REASON_EXPERT;tx.deal=1415;virt.RefreshClosedGenerationFromDeal(tx);Check("virtual callback path preserved",virt.m_buyLayers[0].remainingUnits==0&&virt.m_buyLayers[0].state==ARCS_LAYER_CLOSED);
 return Finish("T1726 protective integration");}
'''

# Exercise the actual coordinator routing method and startup gate on the same
# fixture, with only MT5 transport/coordinator base behavior supplied as seams.
coordinator=source('Recovery/RecoveryExitCoordinatorT177Base.mqh')
basecoordinator=source('Recovery/RecoveryExitCoordinatorT13Base.mqh')
stop=source('Recovery/RecoveryDca.mqh')
slpolicy=adapt(source('Recovery/RecoveryT1717StopLivenessPolicy.mqh'))
router=extract(coordinator,'bool OnTradeTransaction(').replace('m_recovery.','m_recovery->')
router=re.sub(r'\(string\)(trans.deal|HistoryDealGetInteger\(trans.deal,DEAL_POSITION_ID\)|reason|ownerMagic|apiError)',r'std::to_string(\1)',router)
gate=extract(stop,'class CRecoveryStartupFilter').replace('m_recovery.ActiveReady()','m_recovery->ActiveReady()').replace('(string)dir','std::to_string(dir)')+';\n'
extra=slpolicy+extract(basecoordinator,'bool Recovery_ExitExternalDealReason(')+r"""
int _Digits=3;void ResetLastError(){}int GetLastError(){return 0;}
string DoubleToString(double v,int){return std::to_string(v);}
void Log_Info(const string&,const string&,const string&){}void Log_Warn(const string&,const string&,const string&){}
struct CRecoveryExitCoordinatorT13Base{bool OnTradeTransaction(const MqlTradeTransaction&){return false;}};
struct CRecoveryEngine{Fixture *f;bool ActiveReady(){return f->m_ready;}bool T16ExpectedBrokerSlDeal(ulong d){return f->ExpectedBrokerSlDeal(d);}void T16LatchExternalMutation(eRecoveryCoreDirection d,const string&w){f->LatchReconcile(d,w);}};
class Router:public CRecoveryExitCoordinatorT13Base{public:
 CRecoveryEngine *m_recovery;bool m_accountWidePending=false;struct Cycle{bool active=false;};Cycle m_cycle[2];
 Router(CRecoveryEngine*e):m_recovery(e){}
 bool IsT16Arcs(){return true;}bool IsRecoveryCloseTransaction(const MqlTradeTransaction&t){return HistoryDealSelect(t.deal);}
 long ResolveClosedOwnerMagic(ulong d){return m_recovery->f->ResolveClosedOwnerMagic(d);}
 int Index(eRecoveryCoreDirection d){return (int)d;}
 bool ExpectedT1722PySl(bool,long,ulong){return false;}bool IsExpectedRecoveryLockSlT14(eRecoveryCoreDirection,ulong){return false;}
"""+extract(coordinator,'bool MapClosingDeal(')+router+r"""
};
bool g_recoveryTesterStopRequested=false;int stopCalls=0;void TesterStop(){stopCalls++;}struct EAContext{};struct IEntryFilter{};
"""+extract(stop,'void Recovery_StopTesterOnStartupBlock(')+gate
extra=extra.replace('(string)Recovery_CycleKey(dir)','std::to_string(Recovery_CycleKey(dir))')
extra='string Recovery_DirectionName(eRecoveryCoreDirection d){return d==0?"BUY":"SELL";}\n'+extra
# Original bridge explicitly simulates tester mode; no native execution claim.
body=body.replace('int MQLInfoInteger(int){return 0;}','int MQLInfoInteger(int){return 1;}')
body=body.replace('void Log_Error(const string&,const string&){}','string lastError;void Log_Error(const string&,const string&msg){lastError=msg;}')
body=body.replace('int main(){',extra+'\nint main(){',1)
more=r"""
 HedgeSLMode_=SL_BROKER;
 int order[3]={0,1,2};
 do{
    Fixture ordered;ordered.Init();CRecoveryEngine engine{&ordered};Router route(&engine);route.m_cycle[0].active=true;
    CRecoveryStartupFilter gate(&engine);EAContext ctx;Check("ready runtime gate",gate.Allow(ctx,0));int stops=stopCalls;
    for(int action:order){
       if(action==2){bool ok=ordered.RepairProtectiveLayerDecreases(recovery_CORE_BUY,why)&&ordered.Save(why);if(!ok)std::cout<<"WHY order="<<order[0]<<order[1]<<order[2]<<" reason="<<why<<" units="<<ordered.m_buyLayers[0].remainingUnits<<" cash="<<ordered.m_buyLayers[0].realizedOtherCash<<"\n";Check("Overlap refresh before retire",ok);route.m_cycle[0].active=false;}
       else{MqlTradeTransaction event{};event.deal=action==0?1415:1416;
          Check("production router own SL bypass",!route.OnTradeTransaction(event));
          Check("callback actual receipt",ordered.ReconcileReceipt(event.deal,false,true,why));ordered.RefreshClosedGenerationFromDeal(event);
       }
    }
    Check("permutation ready/cash/no stop",ordered.m_ready&&ordered.m_buyLayers[0].realizedOtherCash==198.25&&gate.Allow(ctx,0)&&stopCalls==stops);
 }while(std::next_permutation(order,order+3));
 Fixture external;external.Init();CRecoveryEngine engine{&external};Router route(&engine);CRecoveryStartupFilter gate(&engine);EAContext ctx;gate.Allow(ctx,0);
 db[2].reason=999;MqlTradeTransaction event{};event.deal=1415;int stopped=stopCalls;
 Check("production router unknown mutation latches",route.OnTradeTransaction(event)&&!external.m_ready);
 Check("runtime stop preserved",!gate.Allow(ctx,0)&&stopCalls==stopped+1&&lastError.find("phase=RUNTIME")!=string::npos);
 g_recoveryTesterStopRequested=false; // Simulate a fresh EA instance.
 CRecoveryStartupFilter init(&engine);Check("initial failure phase accurate",!init.Allow(ctx,0)&&lastError.find("phase=INIT")!=string::npos);
 int once=stopCalls;string first=lastError;
 Recovery_StopTesterOnStartupBlock("duplicate different gate",true);
 Check("fatal stop once and first cause preserved",stopCalls==once&&lastError==first);
 double nan=std::numeric_limits<double>::quiet_NaN();
 Check("NaN identity rejected",!Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,nan,4593.789,4594.770,.002,100,true));
 Check("wrong SL proof cannot bypass target",!Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,4500,4593.789,4594.770,.002,100,true));
"""
body=body.replace('return Finish("T1726 protective integration");',more+'\nreturn Finish("T1726 protective integration");')
dca_source=source('Recovery/RecoveryDcaT1713.mqh')
dca_allow=extract(dca_source,'bool Allow(').split('      eRecoveryCoreDirection recoveryDir =')[0]+'      return true;\n   }'
dca_allow=dca_allow.replace('m_recovery.ActiveReady()','m_recovery->ActiveReady()').replace('(string)dir','std::to_string(dir)')
dca_fixture=r"""
struct CBasketManager{};
class DcaGuardFixture {public:
 CRecoveryEngine *m_recovery;CBasketManager *m_basket;bool m_seenReady=false;
 DcaGuardFixture(CRecoveryEngine *r,CBasketManager *b):m_recovery(r),m_basket(b){}
"""+dca_allow+'};\n'
body=body.replace('int main(){',dca_fixture+'\nint main(){',1)
dca_test=r"""
 Fixture df;df.Init();CRecoveryEngine de{&df};CBasketManager basket;EAContext dc;
 DcaGuardFixture dg(&de,&basket);g_recoveryTesterStopRequested=false;
 Check("actual DCA override records readiness",dg.Allow(dc,0)&&dg.m_seenReady);
 df.m_ready=false;Check("actual DCA override runtime phase",!dg.Allow(dc,0)&&lastError.find("phase=RUNTIME")!=string::npos);
 g_recoveryTesterStopRequested=false;DcaGuardFixture dginit(&de,&basket);
 Check("actual DCA override initial phase",!dginit.Allow(dc,0)&&lastError.find("phase=INIT")!=string::npos);
"""
body=body.replace('return Finish("T1726 protective integration");',dca_test+'\nreturn Finish("T1726 protective integration");')
body='#include <limits>\n#include <cstdio>\n'+body
fmt=r"""
const char* FmtArg(const string &s){return s.c_str();}
template<class A> A FmtArg(A a){return a;}
template<class... A> string StringFormat(string fmt,A... args){
 for(auto pair:{std::make_pair(string("%I64d"),string("%ld")),std::make_pair(string("%I64u"),string("%lu"))}){
  size_t pos=0;while((pos=fmt.find(pair.first,pos))!=string::npos){fmt.replace(pos,pair.first.size(),pair.second);pos+=pair.second.size();}}
 int n=snprintf(nullptr,0,fmt.c_str(),FmtArg(args)...);std::vector<char> buf(n+1);snprintf(buf.data(),buf.size(),fmt.c_str(),FmtArg(args)...);return string(buf.data());
}
"""
body=body.replace('class Fixture{public:',fmt+'\nclass Fixture{public:')
run('t1726_protective',body)

(O/'extraction.json').write_text(json.dumps(manifest,indent=2));(O/'results.json').write_text(json.dumps(results,indent=2));raise SystemExit(any(x['status']!='PASS' for x in results))
