# Executed by t1725_integration.py; API seams are explicit in generated C++.
run('outcome_store',bridge+enums+atomic+outcome+r'''
SBDStoredOutcome Intent(long nonce=1){SBDStoredOutcome r{};r.id=101;r.ticket=10;r.nonce=nonce;r.groupSerial=7;r.actualDirection=0;r.owner=100;r.cycle=172200;r.command=EXEC_CMD_PY_PROTECT_MODIFY;r.beforeVolume=1;r.sl=3000;r.state=BD_OUT_INTENT;return r;}
int main(){
 COperationResultStore a;Check("empty init",a.Init(true));auto r=Intent();Check("durable intent",a.Prepare(r));Check("duplicate nonce cannot send",!a.Prepare(r));
 COperationResultStore b;SBDStoredOutcome got;Check("restart intent",b.Init(true)&&b.At(0,got)&&got.state==BD_OUT_INTENT&&got.groupSerial==7);
 Check("intent cannot ACK",!b.Acknowledge(101,1));r.state=BD_OUT_UNKNOWN;Check("unknown persists",b.Update(r));Check("unknown cannot ACK",!b.Acknowledge(101,1));
 r.state=BD_OUT_NO_EFFECT;r.retcode=10016;Check("reject persists",b.Update(r));COperationResultStore c;Check("restart before ACK",c.Init(true)&&c.At(0,got)&&got.state==BD_OUT_NO_EFFECT);
 auto wrong=r;wrong.id=202;Check("wrong identifier cannot overwrite",!c.Update(wrong));wrong=r;wrong.groupSerial++;Check("wrong campaign cannot overwrite",!c.Update(wrong));
 Check("consumer ACK",c.Acknowledge(101,1));Check("duplicate ACK",c.Acknowledge(101,1));auto next=Intent(2);next.id=102;Check("next intent",c.Prepare(next));
 failMove=true;next.state=BD_OUT_PENDING;Check("failed replace reported",!c.Update(next));Check("failed store cannot ACK RAM",!c.Acknowledge(101,1));failMove=false;
 COperationResultStore d;Check("replace failure retains complete old snapshot",d.Init(true)&&d.At(1,got)&&got.state==BD_OUT_INTENT);
 next.state=BD_OUT_PARTIAL;next.observedVolume=.2;Check("partial effect durable",d.Update(next));Check("partial consumed",d.Acknowledge(102,2));
 for(long n=3;n<=600;n++){auto x=Intent(n);if(!d.Prepare(x)){failed++;break;}x.state=BD_OUT_APPLIED;if(!d.Update(x)||!d.Acknowledge(101,n)){failed++;break;}}
 Check("bounded settled prefix",d.Count()<=34);Check("retired nonce cannot resend",!d.Prepare(Intent(1)));COperationResultStore e;Check("watermark restart",e.Init(true)&&!e.Prepare(Intent(1)));
 auto path=files.begin()->first;files[path].back()^=1;COperationResultStore corrupt;Check("corrupt snapshot refused",!corrupt.Init(true));return Finish("outcome store");}
''')
run('arcs_checkpoint',bridge+enums+atomic+types+legacy+ledger+r'''
int main(){
 CArcsLedgerPersistence l;l.Init("fixture",123,100,200);SArcsDirection buy{},sell{};buy.phase=ARCS_CORE_FUNDING;sell.phase=ARCS_TP_PENDING;sell.generationCount=1;
 SArcsExternalPending bp{},sp{};std::vector<SArcsLayer> bl(4),sl(4);string why;SArcsPersistIdentity identity{};
 Check("phase persisted",l.Save(1,buy,sell,bp,sp,bl,sl,why));SBDArcsEpoch e;Check("phase lookup",l.PhaseAt(0,100010,e)&&e.phase==ARCS_CORE_FUNDING);
 SBDArcsReceipt r{};r.deal=10;r.positionId=101;r.stamp=100010;r.owner=100;r.cycle=l.Cycle(0);r.dir=0;r.phase=ARCS_CORE_FUNDING;r.coreFunding=true;r.cash=-50;r.units=10;
 Check("loss oracle fifty",BD_ReceiptCoreLoss(r)==50);Check("receipt put",l.Put(r));buy.coreLossSpent=50;Check("atomic cash and receipt",l.Save(2,buy,sell,bp,sp,bl,sl,why));
 CArcsLedgerPersistence restart;restart.Init("fixture",123,100,200);SBDArcsReceipt old;
 Check("paired restart",restart.Load(identity,buy,sell,bp,sp,bl,sl,why)==ARCS_PERSIST_OK&&restart.Get(10,old)&&buy.coreLossSpent==50&&identity.saveSequence==2);
 auto corrected=old;corrected.cash=-5;double delta=BD_ReceiptCoreLoss(corrected)-BD_ReceiptCoreLoss(old);Check("delta minus fortyfive",delta==-45);
 buy.coreLossSpent+=delta;Check("replace receipt",restart.Put(corrected));Check("corrected checkpoint",restart.Save(3,buy,sell,bp,sp,bl,sl,why));Check("idempotent fingerprint",restart.Get(10,old)&&BD_ReceiptEqual(old,corrected));
 corrected.deleted=true;Check("deleted zero contribution",BD_ReceiptCoreLoss(corrected)==0);corrected.deleted=false;corrected.suppressed=true;Check("suppressed zero contribution",BD_ReceiptCoreLoss(corrected)==0);
 nowMsc=200000;buy.phase=ARCS_LOCKED;Check("phase transition",restart.Save(4,buy,sell,bp,sp,bl,sl,why));Check("historic funding phase",restart.PhaseAt(0,150000,e)&&e.phase==ARCS_CORE_FUNDING);Check("new funding phase",restart.PhaseAt(0,210000,e)&&e.phase==ARCS_LOCKED);Check("missing phase not guessed",!restart.PhaseAt(0,99999,e));
 failMove=true;buy.coreLossSpent=999;Check("failed ledger replace",!restart.Save(5,buy,sell,bp,sp,bl,sl,why));failMove=false;
 CArcsLedgerPersistence after;after.Init("fixture",123,100,200);Check("old complete pair preserved",after.Load(identity,buy,sell,bp,sp,bl,sl,why)==ARCS_PERSIST_OK&&buy.coreLossSpent==5&&after.Get(10,old)&&old.cash==-5);
 buy.coreLossSpent=std::nan("");Check("writer rejects invalid economics",!after.Save(6,buy,sell,bp,sp,bl,sl,why));buy.coreLossSpent=5;
 after.NewCycle(0);Check("cycle separates historic economics",after.Cycle(0)!=old.cycle);
 files["arcs.bin.t1725"].pop_back();Check("truncation rejected",after.Load(identity,buy,sell,bp,sp,bl,sl,why)==ARCS_PERSIST_CORRUPT);
 CArcsLedgerPersistence cap;cap.Init("fixture",123,100,200);r.deleted=false;r.suppressed=false;
 for(int i=1;i<=65535;i++){r.deal=i;if(!cap.Put(r)){failed++;break;}}Check("65535 receipt boundary",cap.Get(65535,old));r.deal=65536;Check("65536 receipt boundary",cap.Put(r));r.deal=65537;Check("65537 append refused",!cap.Put(r));
 cap.NewCycle(0);cap.NewCycle(0);cap.Compact();Check("settled old cycles compact",cap.Put(r));Check("retired proof floor refuses unknown historical correction",!cap.PhaseAt(0,100010,e));
 return Finish("ARCS checkpoint");}
''')
core=source('Pyramid/CorePyramid.mqh');stat=core[core.index('struct SPyramidCampaignStats'):core.index('void Pyramid_BookReset')]
helpers='\n'.join(extract(core,x) for x in ['void Pyramid_CampaignReset(', 'bool Pyramid_LaterDeal(', 'void Pyramid_RecordMutation('])
history=r'''
enum{DEAL_ENTRY_IN=10,DEAL_ENTRY_OUT,DEAL_ENTRY_INOUT,DEAL_ENTRY_OUT_BY,DEAL_SYMBOL,DEAL_POSITION_ID,DEAL_TIME_MSC,DEAL_TIME,DEAL_MAGIC,DEAL_ENTRY,DEAL_COMMENT,DEAL_PRICE,DEAL_PROFIT,DEAL_SWAP,DEAL_COMMISSION,DEAL_FEE,DEAL_TYPE,DEAL_VOLUME,DEAL_SL,DEAL_REASON,DEAL_REASON_SL};
enum{DEAL_TYPE_BUY=100,DEAL_TYPE_SELL=101};enum{TRADE_TRANSACTION_DEAL_ADD,TRADE_TRANSACTION_DEAL_UPDATE,TRADE_TRANSACTION_DEAL_DELETE};
struct MqlTradeTransaction{int type=0;ulong deal=0;};ulong g_pyramidDealRevision=0;
struct Deal{ulong id,pid;long stamp,owner,entry;string comment;double price,cash;long type=DEAL_TYPE_BUY;double lots=.1;};
std::vector<Deal> db;std::vector<ulong> selected;int selections=0;bool historyFail=false;
bool HistorySelect(long a,long b){selections++;if(historyFail)return false;selected.clear();for(auto d:db)if(d.stamp>=a*1000&&d.stamp<=b*1000)selected.push_back(d.id);return true;}
bool HistoryDealSelect(ulong id){if(historyFail)return false;for(auto d:db)if(d.id==id){selected={id};return true;}return false;}
bool HistorySelectByPosition(ulong id){if(historyFail)return false;selected.clear();for(auto d:db)if(d.pid==id)selected.push_back(d.id);return !selected.empty();}
int HistoryDealsTotal(){return selected.size();}ulong HistoryDealGetTicket(int i){return selected.at(i);}
Deal Get(ulong id){for(auto d:db)if(d.id==id)return d;return {};}
long HistoryDealGetInteger(ulong id,int k){auto d=Get(id);if(k==DEAL_POSITION_ID)return d.pid;if(k==DEAL_TIME_MSC)return d.stamp;if(k==DEAL_TIME)return d.stamp/1000;if(k==DEAL_MAGIC)return d.owner;if(k==DEAL_ENTRY)return d.entry;if(k==DEAL_TYPE)return d.type;return 0;}
string HistoryDealGetString(ulong id,int k){return k==DEAL_SYMBOL?"fixture":Get(id).comment;}
double HistoryDealGetDouble(ulong id,int k){auto d=Get(id);return k==DEAL_PRICE?d.price:k==DEAL_PROFIT?d.cash:k==DEAL_VOLUME?d.lots:0;}
bool Pyramid_IsComment(const string&c){return c.rfind("PY",0)==0;}int Pyramid_CommentFieldInt(const string&c,const string&){return c=="PYSELL"?1:0;}int Pyramid_LevelFromComment(const string&c){return c=="PY2"?2:1;}
'''
campaign=adapt(source('Pyramid/CampaignLedger.mqh'))
run('campaign_incremental',bridge+stat+helpers+history+campaign+r'''
int main(){
 db={{1,101,100010,100,DEAL_ENTRY_IN,"PY",100,-1},{2,101,110000,0,DEAL_ENTRY_OUT,"manual",102,10},{3,202,100010,999,DEAL_ENTRY_IN,"PY",100,-99}};
 CCampaignLedger c;SPyramidCampaignStats st;Check("cash by opening identity",c.Read(0,100000,120,0,st)&&st.realizedCash==9&&st.addCount==1&&st.exitDeals==1);Check("quiet second no history rebuild",c.Read(0,100000,121,0,st)&&selections==1);
 db.push_back({4,101,122000,0,DEAL_ENTRY_OUT_BY,"manual",103,5});MqlTradeTransaction tx;tx.deal=4;c.Observe(tx,1);Check("per-deal delta",c.Read(0,100000,123,1,st)&&st.realizedCash==14&&st.exitDeals==2&&selections==1);
 c.Observe(tx,2);Check("duplicate exact once",c.Read(0,100000,124,2,st)&&st.realizedCash==14&&st.exitDeals==2&&selections==1);
 db[3].cash=-2;tx.type=TRADE_TRANSACTION_DEAL_UPDATE;c.Observe(tx,3);Check("correction replaces cash",c.Read(0,100000,125,3,st)&&st.realizedCash==7&&selections==1);
 tx.type=TRADE_TRANSACTION_DEAL_DELETE;c.Observe(tx,4);Check("delete removes contribution",c.Read(0,100000,126,4,st)&&st.realizedCash==9&&st.exitDeals==1);
 tx.deal=1;c.Observe(tx,5);Check("opening delete removes dependent cash",c.Read(0,100000,127,5,st)&&st.realizedCash==0&&st.addCount==0);
 tx.type=TRADE_TRANSACTION_DEAL_ADD;tx.deal=1;c.Observe(tx,6);Check("opening re-add restores cash",c.Read(0,100000,128,6,st)&&st.realizedCash==9);
 db.push_back({5,303,130000,100,DEAL_ENTRY_IN,"PY2",110,-1});db.push_back({6,303,131000,0,DEAL_ENTRY_OUT,"manual",111,3});tx.deal=6;c.Observe(tx,7);
 Check("exit-before-entry hydrates owner",c.Read(0,100000,132,7,st)&&st.realizedCash==11&&st.addCount==2&&st.highestLevel==2&&selections==1);
 tx.deal=5;c.Observe(tx,8);Check("late opening dedup",c.Read(0,100000,133,8,st)&&st.realizedCash==11&&st.addCount==2);
 historyFail=true;tx.deal=99;c.Observe(tx,9);Check("missing deal invalidates ready",!c.Read(0,100000,134,9,st)&&!st.ready);int before=selections;Check("bounded retry",!c.Read(0,100000,134,9,st)&&selections==before);
 historyFail=false;db.erase(db.begin()+3);Check("reasoned rebuild repairs",c.Read(0,100000,135,9,st)&&st.realizedCash==11&&selections==before+1);Check("revision gap rebuilds",c.Read(0,100000,136,11,st)&&selections==before+2);
 CCampaignLedger sell;Check("SELL isolated",sell.Read(1,100000,136,11,st)&&st.addCount==0&&st.realizedCash==0);c.Reset();Check("new campaign excludes old cash",c.Read(0,130000,136,11,st)&&st.addCount==1&&st.realizedCash==2);return Finish("campaign");}
''')
oracle=adapt(source('ProfitOracle.mqh'))
run('profit_oracle',bridge+r'''
enum ENUM_ORDER_TYPE{ORDER_TYPE_BUY,ORDER_TYPE_SELL,ORDER_TYPE_OTHER};bool calcFail=false;int calls=0;
bool OrderCalcProfit(ENUM_ORDER_TYPE type,const string&,double lots,double open,double close,double &cash){calls++;if(calcFail)return false;cash=(type==ORDER_TYPE_BUY?1:-1)*(close-open)*lots*100;return true;}
'''+oracle+r'''
int main(){std::vector<SBDOracleLeg> legs={{ORDER_TYPE_BUY,1,100,-1}};string why;double cash;long tick;
 Check("cash costs/reserve separate",BD_OracleCash("fixture",legs,101,2,cash,why)&&cash==97);Check("BUY tick target",BD_OracleSolveTicks("fixture",legs,9900,10200,50,2,tick,why)&&tick==10053);Check("logarithmic calls",calls<20);legs[0].type=ORDER_TYPE_SELL;
 Check("SELL reversed ordering",BD_OracleSolveTicks("fixture",legs,9800,10100,50,2,tick,why)&&tick==9947);Check("target outside bracket",!BD_OracleSolveTicks("fixture",legs,9990,10010,100,0,tick,why));Check("off tick rejected",!BD_OracleCash("fixture",legs,100.001,0,cash,why));calcFail=true;Check("broker failure not zero success",!BD_OracleCash("fixture",legs,100,0,cash,why));calcFail=false;
 legs[0].lots=.001;Check("off step rejected",!BD_OracleCash("fixture",legs,100,0,cash,why));legs[0].lots=1;legs.push_back({ORDER_TYPE_BUY,1,100,0});Check("flat bracket refused",!BD_OracleSolveTicks("fixture",legs,9900,10100,0,0,tick,why));Check("negative reserve rejected",!BD_OracleCash("fixture",legs,100,-1,cash,why));return Finish("oracle");}
''')
stack=source('Recovery/RecoveryArcsStack.mqh')
methods='\n'.join(extract(stack,x) for x in ['int Idx(', 'void GetLayer(', 'void PutLayer(', 'int FindLayerByGeneration(', 'bool CursorAfter(', 'void TrackCursor(', 'long ResolveClosedOwnerMagic(', 'eRecoveryCoreDirection DirectionForClose(', 'int ReadReceipt(', 'bool ApplyReceiptEffect(', 'bool ReconcileReceipt(', 'bool ReplayAfterCursor(', 'void RecordDealCursor('])
methods=adapt(methods).replace('g_pyramidProtection.ExpectedRhTrim','g_pyramidProtection->ExpectedRhTrim')
reset=extract(arcs,'void Recovery_ArcsLayerReset(');credit=extract(arcs,'void Recovery_ArcsRecomputeCredit(');math=extract(source('Recovery/RecoveryMath.mqh'),'long Recovery_VolumeToUnitsFloor(')
run('arcs_replay',bridge+enums+atomic+types+legacy+ledger+history+r'''
enum eRecoveryCoreDirection{recovery_CORE_BUY,recovery_CORE_SELL};struct Protect{bool ExpectedRhTrim(ulong d){return d==20;}}protect;Protect *g_pyramidProtection=&protect;
int Recovery_ArcsGenerationFromPositionHistory(ulong){return 1;}long Recovery_ArcsLayerUnits(eRecoveryCoreDirection,int,double){return 10;}
double Recovery_DealCashPure(double p,double s,double c,double f){return p+s+c+f;}
'''+reset+credit+math+r'''
class Fixture{public:
 CArcsLedgerPersistence m_persistence;SArcsDirection m_dir[2];SArcsExternalPending pending[2];std::vector<SArcsLayer> m_buyLayers,m_sellLayers;bool m_dirty=false,m_persistenceBlocked=false;double m_volumeStep=.01;
 Fixture():m_buyLayers(4),m_sellLayers(4){ZeroMemory(m_dir);ZeroMemory(pending);m_persistence.Init("fixture",123,100,200);m_dir[0].phase=ARCS_TP_PENDING;m_dir[1].phase=ARCS_CORE_FUNDING;m_dir[0].generationCount=1;m_dir[0].activeLayer=0;m_dir[1].activeLayer=-1;m_buyLayers[0].used=true;m_buyLayers[0].generation=1;m_buyLayers[0].state=ARCS_LAYER_TP_PENDING;}
 bool Save(){string why;return m_persistence.Save(1,m_dir[0],m_dir[1],pending[0],pending[1],m_buyLayers,m_sellLayers,why);}
 void LatchReconcile(eRecoveryCoreDirection d,string){m_dir[d].reconcileRequired=true;}
'''+methods+r'''
};
int main(){nowMsc=100000;Fixture f;Check("phase checkpoint",f.Save());
 db={{1,101,100000,100,DEAL_ENTRY_IN,"Seed",100,0,DEAL_TYPE_SELL},{2,101,150000,0,DEAL_ENTRY_OUT,"manual",99,-50},{3,101,250000,0,DEAL_ENTRY_OUT,"manual",99,-5}};
 nowMsc=300000;f.m_dir[0].lastDealTimeMsc=200000;f.m_dir[0].lastDealTicket=1;f.m_dir[1].lastDealTimeMsc=100000;f.m_dir[1].lastDealTicket=1;string why;
 Check("Q11 different cursors preserve cash55",f.ReplayAfterCursor(recovery_CORE_BUY,why)&&f.ReplayAfterCursor(recovery_CORE_SELL,why)&&f.m_dir[1].coreLossSpent==55&&f.m_dir[0].coreLossSpent==0);
 Check("Q12 overlap exact once",f.ReplayAfterCursor(recovery_CORE_SELL,why)&&f.m_dir[1].coreLossSpent==55);
 db[2].cash=-7;Check("UPDATE exact delta",f.ReconcileReceipt(3,false,true,why)&&f.m_dir[1].coreLossSpent==57);Check("DELETE reverses receipt",f.ReconcileReceipt(2,true,true,why)&&f.m_dir[1].coreLossSpent==7);Check("duplicate DELETE",f.ReconcileReceipt(2,true,true,why)&&f.m_dir[1].coreLossSpent==7);
 db.erase(db.begin()+1);Check("deleted history remains correct",f.ReplayAfterCursor(recovery_CORE_SELL,why)&&f.m_dir[1].coreLossSpent==7);
 db.push_back({4,101,120000,0,DEAL_ENTRY_OUT,"manual",99,-2});Check("late old deal not hidden by cursor",f.ReconcileReceipt(4,false,true,why)&&f.m_dir[1].coreLossSpent==9);f.m_dir[1].phase=ARCS_LOCKED;Check("new phase",f.Save());
 db.push_back({5,101,180000,0,DEAL_ENTRY_OUT,"manual",99,-3});Check("historic phase retained",f.ReconcileReceipt(5,false,true,why)&&f.m_dir[1].coreLossSpent==12);db.push_back({6,101,310000,0,DEAL_ENTRY_OUT,"manual",99,-8});Check("locked phase no old funding",f.ReconcileReceipt(6,false,true,why)&&f.m_dir[1].coreLossSpent==12);
 db.push_back({7,101,170000,0,DEAL_ENTRY_OUT,"manual",99,-4});f.RecordDealCursor(7);Check("coordinator suppression survives replay",f.ReplayAfterCursor(recovery_CORE_SELL,why)&&f.m_dir[1].coreLossSpent==12);db.back().cash=-9;Check("suppressed correction excluded",f.ReconcileReceipt(7,false,true,why)&&f.m_dir[1].coreLossSpent==12);
 db.push_back({10,202,100000,200,DEAL_ENTRY_IN,"RH",100,0,DEAL_TYPE_SELL});db.push_back({11,202,160000,0,DEAL_ENTRY_OUT,"manual",101,20});Check("RH funding generation",f.ReconcileReceipt(11,false,true,why)&&f.m_dir[0].hedgeFundingCash==20&&f.m_buyLayers[0].fundingClosedUnits==10);db.back().cash=8;Check("RH cash correction",f.ReconcileReceipt(11,false,true,why)&&f.m_dir[0].hedgeFundingCash==8&&f.m_buyLayers[0].fundingClosedUnits==10);Check("RH delete units and cash",f.ReconcileReceipt(11,true,true,why)&&f.m_dir[0].hedgeFundingCash==0&&f.m_buyLayers[0].fundingClosedUnits==0);
 db.push_back({20,202,190000,200,DEAL_ENTRY_OUT,"trim",101,-2});Check("PY trim cannot fund Core",f.ReconcileReceipt(20,false,true,why)&&f.m_dir[0].hedgeFundingCash==0&&f.m_buyLayers[0].realizedOtherCash==-2);Check("unknown delete reconcile",!f.ReconcileReceipt(999,true,true,why));db.push_back({30,999,320000,100,DEAL_ENTRY_OUT,"unknown",100,-1});Check("opening owner required",!f.ReconcileReceipt(30,false,true,why));Check("paired checkpoint",f.Save());Fixture restored;SArcsPersistIdentity identity;Check("restart receipt and cash",restored.m_persistence.Load(identity,restored.m_dir[0],restored.m_dir[1],restored.pending[0],restored.pending[1],restored.m_buyLayers,restored.m_sellLayers,why)==ARCS_PERSIST_OK&&restored.m_dir[1].coreLossSpent==12);return Finish("replay");}
'''.replace('return Finish("replay");}',r'''
 files.clear();db.clear();nowMsc=500000;Fixture phase;phase.m_dir[0].phase=ARCS_CORE_FUNDING;phase.m_buyLayers[0].tpBaselineUnits=100;
 Check("trim baseline phase checkpoint",phase.Save());
 db={{10,202,500000,200,DEAL_ENTRY_IN,"RH",100,0,DEAL_TYPE_SELL},{20,202,600000,200,DEAL_ENTRY_OUT,"trim",101,-2}};
 Check("funding-phase trim reduces baseline",phase.ReconcileReceipt(20,false,true,why)&&phase.m_buyLayers[0].tpBaselineUnits==90&&phase.m_buyLayers[0].realizedOtherCash==-2);
 phase.m_buyLayers[0].state=ARCS_LAYER_CLOSED;phase.m_dir[0].phase=ARCS_LOCKED;db.back().cash=-4;
 Check("closed-layer correction preserves original trim classification",phase.ReconcileReceipt(20,false,true,why)&&phase.m_buyLayers[0].tpBaselineUnits==90&&phase.m_buyLayers[0].realizedOtherCash==-4);
 Check("closed-layer delete restores original baseline",phase.ReconcileReceipt(20,true,true,why)&&phase.m_buyLayers[0].tpBaselineUnits==100&&phase.m_buyLayers[0].realizedOtherCash==0);
 return Finish("replay");}'''))
execution=source('ExecutionLayer.mqh')
execmethods='\n'.join(extract(execution,x) for x in ['bool IsProtectedCommand(', 'bool PersistOutcome(', 'void RestoreOutcomes(', 'void ConsumeStoredOutcomes(', 'void Journal_CompleteAt(', 'bool Journal_ServerOrderLive(', 'bool Journal_StateResolved(', 'void Journal_TryCompleteAt(', 'void Journal_ApplyResult('])
execmethods=adapt(execmethods).replace('g_pyramidProtection.','g_pyramidProtection->')
pending='\n'.join(extract(types_source,x)+';' for x in ['enum ePendingPhase','enum ePendingEvidence','struct PendingRequest'])
run('execution_outcomes',bridge+enums+pending+'\n'+atomic+outcome+r'''
enum{TRADE_RETCODE_DONE=10009,TRADE_RETCODE_DONE_PARTIAL=10010,TRADE_RETCODE_PLACED=10008,SYMBOL_POINT=200,POSITION_IDENTIFIER,POSITION_VOLUME,POSITION_SL,POSITION_TP};
struct MqlTradeResult{uint request_id=0,retcode=0;ulong order=0,deal=0;double volume=0;};
bool live=true,orderLive=false,consume=false;ulong positionId=101,ticket=10;double volume=1,sl=0,tp=0;
bool PositionSelectByTicket(ulong t){return live&&t==ticket;}int PositionsTotal(){return live?1:0;}ulong PositionGetTicket(int){return ticket;}long PositionGetInteger(int){return positionId;}double PositionGetDouble(int k){return k==POSITION_VOLUME?volume:k==POSITION_SL?sl:tp;}bool OrderSelect(ulong){return orderLive;}
void Log_Error(const string&,const string&){}
struct Protect{bool OperationScope(ulong,long,long &serial,int &direction){serial=7;direction=0;return true;}bool OutcomeConsumed(ulong,long){return consume;}bool OnDefinitiveReject(int,int,ulong,ulong,long,uint){return consume;}}protect;Protect *g_pyramidProtection=&protect;
bool Exec_CloseVolumeResolved(double before,double after,double target,double step){return after<=before-target+step*1e-7;}bool Exec_PendingReady(ePendingEvidence){return false;}void Exec_T14RecordProof(const PendingRequest&){}
class ExecFixture{public:std::vector<PendingRequest> m_journal;COperationResultStore m_outcomes;bool m_busyOpenBuy=false,m_busyOpenSell=false;
 bool RetcodeOk(uint code)const{return code==TRADE_RETCODE_DONE||code==TRADE_RETCODE_DONE_PARTIAL||code==TRADE_RETCODE_PLACED;}
 bool Journal_OpenIdentityResolved(const PendingRequest&)const{return false;}int CountOpenPositions(eIntent,const string&,long)const{return 0;}bool AnyLiveOrder(long,const string&)const{return false;}
'''+execmethods+r'''
 void Seed(){m_outcomes.Init(true);PendingRequest p{};p.active=true;p.protectedPositionId=101;p.protectedNonce=1;p.ticket=10;p.symbol="fixture";p.ownerMagic=100;p.cycleKey=172200;p.commandType=EXEC_CMD_PY_PROTECT_CLOSE;p.action=INTENT_CLOSE_TICKET;p.volume=.5;p.targetVolume=.5;p.positionVolumeBefore=1;p.reconcilePolicy=EXEC_RECONCILE_FAIL_CLOSED;m_journal.push_back(p);}
};
int main(){ExecFixture f;f.Seed();Check("executor persists intent",f.PersistOutcome(0,BD_OUT_INTENT));MqlTradeResult res;res.retcode=TRADE_RETCODE_PLACED;res.order=500;f.Journal_ApplyResult(0,res);f.Journal_TryCompleteAt(0);Check("REQUEST alone cannot settle",f.m_journal[0].active);
 volume=.8;f.m_journal[0].observedVolume=.2;f.Journal_TryCompleteAt(0);Check("one partial callback cannot settle pending order",f.m_journal[0].active);
 res.retcode=TRADE_RETCODE_DONE_PARTIAL;res.deal=77;res.volume=.2;f.Journal_ApplyResult(0,res);orderLive=true;f.Journal_TryCompleteAt(0);Check("live server order remains pending",f.m_journal[0].active);orderLive=false;f.Journal_TryCompleteAt(0);SBDStoredOutcome got;
 Check("actual partial effect committed",!f.m_journal[0].active&&f.m_outcomes.At(0,got)&&got.state==BD_OUT_PARTIAL);ExecFixture restart;restart.RestoreOutcomes();Check("restart preserves unconsumed terminal",restart.m_outcomes.At(0,got)&&got.state==BD_OUT_PARTIAL);restart.ConsumeStoredOutcomes();Check("no early ACK",restart.m_outcomes.At(0,got)&&got.state==BD_OUT_PARTIAL);consume=true;restart.ConsumeStoredOutcomes();Check("durable consumer permits ACK",restart.m_outcomes.At(0,got)&&got.state==BD_OUT_SETTLED);
 files.clear();consume=false;volume=1;ExecFixture unknown;unknown.Seed();unknown.PersistOutcome(0,BD_OUT_INTENT);res={};res.retcode=10012;unknown.Journal_ApplyResult(0,res);Check("ambiguous result persists UNKNOWN",unknown.m_outcomes.At(0,got)&&got.state==BD_OUT_UNKNOWN);ExecFixture loaded;loaded.RestoreOutcomes();Check("restart unknown retains reconciliation",loaded.m_journal.size()==1&&loaded.m_journal[0].active&&loaded.m_journal[0].reconcileRequired);loaded.Journal_TryCompleteAt(0);Check("unknown unchanged state stays pending",loaded.m_journal[0].active);
 ticket=11;loaded.Journal_TryCompleteAt(0);Check("ticket rollover not false close success",loaded.m_journal[0].active&&loaded.m_journal[0].reconcileRequired);ticket=10;
 Check("no-effect result commit",loaded.PersistOutcome(0,BD_OUT_NO_EFFECT));loaded.Journal_TryCompleteAt(0);Check("no-effect awaits consumer",loaded.m_journal[0].active);consume=true;loaded.ConsumeStoredOutcomes();Check("no-effect consumed and settled",!loaded.m_journal[0].active&&loaded.m_outcomes.At(0,got)&&got.state==BD_OUT_SETTLED);return Finish("execution outcomes");}
''')
