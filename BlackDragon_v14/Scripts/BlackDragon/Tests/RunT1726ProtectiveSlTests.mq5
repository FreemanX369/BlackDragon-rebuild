#property strict
// No trading. Uses a unique scratch filename; does not load EA checkpoint files.
#include <BlackDragon/Config.mqh>
#include <BlackDragon/Recovery/RecoveryEngine.mqh>
int passed=0,failed=0;
void Check(const string name,const bool ok){if(ok)passed++;else{failed++;Print("FAIL: ",name);}}
void OnStart()
{
   Check("logged SELL SL gap",Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,4593.789,4593.789,4594.770,.002,.682,true));
   Check("BUY SL gap",Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,4593.789,4593.789,4592.808,.002,.682,true));
   Check("zero legacy fill tolerance",Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,4593.789,4593.789,4594.770,.002,0,false));
   Check("wide legacy fill tolerance",Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,4593.789,4593.789,4594.770,.002,100,false));
   Check("wrong owner",!Recovery_ProtectiveSlIdentityPure(false,true,DEAL_REASON_SL,4593.789,4593.789,4593.789,.002,100,true));
   Check("unknown position",!Recovery_ProtectiveSlIdentityPure(true,false,DEAL_REASON_SL,4593.789,4593.789,4593.789,.002,100,true));
   Check("manual close",!Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_CLIENT,4593.789,4593.789,4593.789,.002,100,true));
   Check("mismatched programmed SL",!Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,4500,4593.789,4593.789,.002,100,true));
   Check("missing programmed SL",!Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,0,4593.789,4593.789,.002,100,true));
   Check("invalid actual fill",!Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,4593.789,4593.789,0,.002,100,true));
   SBDArcsReceipt r;ZeroMemory(r);r.deal=1415;r.positionId=1300;r.stamp=200000;r.cycle=1;r.owner=(long)RecoveryMagic_;r.dir=0;r.generation=1;r.phase=ARCS_LOCKED;r.units=34;r.cash=29.125;r.programmedSl=4593.789;r.protectiveSl=true;
   Check("valid protective receipt",BD_ReceiptValid(r));
   string path="BD_T1726_TEST_"+(string)GetTickCount64()+".bin";SBDAtomicHeader h;BD_AtomicIdentity(h,17269999,2,1);h.records=1;
   int f=BD_AtomicBegin(path,h);bool saved=false;
   if(f!=INVALID_HANDLE)saved=BD_AtomicCommit(path,f,h,FileWriteStruct(f,r)==sizeof(SBDArcsReceipt));
   Check("native v2 POD write",saved);SBDAtomicHeader loaded;SBDArcsReceipt result;ZeroMemory(result);int reader=BD_AtomicOpen(path,h,loaded);bool read=reader!=INVALID_HANDLE;
   if(read){read=FileReadStruct(reader,result)==sizeof(SBDArcsReceipt)&&BD_ReceiptEqual(result,r);FileClose(reader);}
   Check("native v2 receipt reload",read);FileDelete(path);FileDelete(path+".tmp");
   result=r;result.protectiveSl=false;Check("proof part of equality",!BD_ReceiptEqual(result,r));
   result=r;result.programmedSl=0;Check("proof requires SL",!BD_ReceiptValid(result));
   Print("T17.26 protective SL tests: ",passed," passed, ",failed," failed");if(failed==0)Print("ALL GREEN");
}
