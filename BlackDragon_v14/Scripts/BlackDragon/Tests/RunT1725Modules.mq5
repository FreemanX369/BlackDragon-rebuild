#property strict
// Diagnostic compile also instantiates the optional platform wrappers.
#define BD_DIAGNOSTICS
#define BD_BUILD_ID "T1725_NATIVE_TEST"
#include <BlackDragon/Diagnostics/LocalMetrics.mqh>
#include <BlackDragon/Config.mqh>
#include <BlackDragon/Recovery/RecoveryEngine.mqh>
#include <BlackDragon/ProfitOracle.mqh>
int passed=0,failed=0;
void Check(const string name,const bool ok){if(ok)passed++;else{failed++;Print("FAIL: ",name);}}
void OnStart()
{
   // Volatile operation store avoids touching the EA's real recovery state.
   COperationResultStore store;Check("volatile store",store.Init(false));
   SBDStoredOutcome r;ZeroMemory(r);r.id=101;r.ticket=10;r.nonce=1;r.groupSerial=7;r.actualDirection=0;r.owner=(long)Magic;
   r.cycle=172200;r.command=EXEC_CMD_PY_PROTECT_MODIFY;r.beforeVolume=1;r.sl=3000;r.state=BD_OUT_INTENT;
   Check("intent",store.Prepare(r));Check("duplicate denied",!store.Prepare(r));
   r.state=BD_OUT_UNKNOWN;Check("unknown retained",store.Update(r));Check("unknown no ACK",!store.Acknowledge(r.id,r.nonce));
   r.state=BD_OUT_NO_EFFECT;Check("reject retained",store.Update(r));Check("ACK",store.Acknowledge(r.id,r.nonce));Check("duplicate ACK",store.Acknowledge(r.id,r.nonce));
   bool bounded=true;for(int i=2;i<=600;i++){r.nonce=i;r.state=BD_OUT_INTENT;if(!store.Prepare(r)){bounded=false;break;}r.state=BD_OUT_APPLIED;if(!store.Update(r)||!store.Acknowledge(r.id,r.nonce)){bounded=false;break;}}
   Check("settled compaction",bounded&&store.Count()<=34);
   string path="BD_T1725_TEST_"+(string)GetTickCount64()+".bin";SBDAtomicHeader h;BD_AtomicIdentity(h,17259999,1,1);h.records=1;
   int f=BD_AtomicBegin(path,h);bool saved=false;
   if(f!=INVALID_HANDLE)saved=BD_AtomicCommit(path,f,h,FileWriteStruct(f,r)==sizeof(SBDStoredOutcome));
   Check("native atomic POD snapshot",saved);SBDAtomicHeader loaded;SBDStoredOutcome result;ZeroMemory(result);
   int reader=BD_AtomicOpen(path,h,loaded);bool read=reader!=INVALID_HANDLE;
   if(read){read=FileReadStruct(reader,result)==sizeof(SBDStoredOutcome)&&result.nonce==r.nonce;FileClose(reader);}
   Check("native POD checksum/identity reload",read);FileDelete(path);FileDelete(path+".tmp");
   SBDOracleLeg legs[];ArrayResize(legs,1);legs[0].type=ORDER_TYPE_BUY;legs[0].lots=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_MIN);
   double tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);MqlTick quote;bool quoteOk=SymbolInfoTick(_Symbol,quote)&&tick>0;
   legs[0].openPrice=quoteOk?MathRound(quote.ask/tick)*tick:0;legs[0].signedCosts=-1;
   double cash=0;string why;Check("native account currency oracle",quoteOk&&BD_OracleCash(_Symbol,legs,legs[0].openPrice,2,cash,why)&&MathAbs(cash+3)<1e-8);
   Check("invalid fee reserve refused",!BD_OracleCash(_Symbol,legs,legs[0].openPrice,-1,cash,why));
   Print("T17.25 native modules: ",passed," passed, ",failed," failed");if(failed==0)Print("ALL GREEN");
}
