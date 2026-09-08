#ifndef BD_OPERATION_RESULT_STORE_MQH
#define BD_OPERATION_RESULT_STORE_MQH
#include "Diagnostics/AtomicSnapshot.mqh"
enum eBDOutcome { BD_OUT_INTENT=0,BD_OUT_PENDING,BD_OUT_APPLIED,BD_OUT_PARTIAL,BD_OUT_NO_EFFECT,BD_OUT_UNKNOWN,BD_OUT_SETTLED };
struct SBDStoredOutcome
{
   ulong id,ticket,serverOrder,serverDeal,lastDeal;
   long nonce,owner,sentAt,groupSerial;
   uint requestId,retcode;
   int cycle,command,action,state,actualDirection;
   double volume,beforeVolume,observedVolume,sl,tp;
   bool serverFinal,orderDeleted;
};
bool BD_OutcomeValid(const SBDStoredOutcome &r)
{ return r.id>0 && r.ticket>0 && r.nonce>0 && r.groupSerial>0 && r.actualDirection>=0 && r.actualDirection<2 && r.owner>0 && r.cycle>=172200 && r.cycle<=172201 &&
         r.state>=BD_OUT_INTENT && r.state<=BD_OUT_SETTLED &&
         (r.command==EXEC_CMD_PY_RH_TRIM || r.command==EXEC_CMD_PY_PROTECT_CLOSE || r.command==EXEC_CMD_PY_PROTECT_MODIFY) &&
         MathIsValidNumber(r.volume) && r.volume>=0 && MathIsValidNumber(r.beforeVolume) && r.beforeVolume>0 &&
         MathIsValidNumber(r.observedVolume) && r.observedVolume>=0 && MathIsValidNumber(r.sl) && MathIsValidNumber(r.tp); }
class COperationResultStore
{
private:
   SBDStoredOutcome m_records[];
   string m_file;
   bool m_persist,m_ok;
   long m_sequence,m_retired;
   bool Save()
   {
      if(!m_persist)return true;
      SBDAtomicHeader h;BD_AtomicIdentity(h,17250001,1,1);h.sequence=m_sequence+1;h.records=ArraySize(m_records);
      if(h.records>512){m_ok=false;return false;}
      for(int i=0;i<h.records;i++)if(!BD_OutcomeValid(m_records[i])){m_ok=false;return false;}
      int f=BD_AtomicBegin(m_file,h);if(f==INVALID_HANDLE){m_ok=false;return false;}
      bool ok=FileWriteLong(f,m_retired)==sizeof(long);
      for(int i=0;i<h.records;i++)ok=FileWriteStruct(f,m_records[i])==sizeof(SBDStoredOutcome) && ok;
      ok=BD_AtomicCommit(m_file,f,h,ok);if(ok)m_sequence=h.sequence;else m_ok=false;return ok;
   }
public:
   COperationResultStore():m_file(""),m_persist(false),m_ok(true),m_sequence(0),m_retired(0){}
   int Find(const ulong id,const long nonce) const
   { int lo=0,hi=ArraySize(m_records);while(lo<hi){int m=lo+(hi-lo)/2;if(m_records[m].nonce<nonce)lo=m+1;else hi=m;}return lo<ArraySize(m_records)&&m_records[lo].nonce==nonce&&m_records[lo].id==id?lo:-1; }
   int Count() const{return ArraySize(m_records);}
   bool Healthy() const{return m_ok;}
   bool At(const int i,SBDStoredOutcome &out) const
   { if(i<0||i>=ArraySize(m_records))return false;out=m_records[i];return true; }
   bool Init(const bool persist)
   {
      m_persist=persist;m_ok=true;m_sequence=0;m_retired=0;ArrayResize(m_records,0);
      m_file="BD_T1725_OUT_"+(string)AccountInfoInteger(ACCOUNT_LOGIN)+"_"+(string)BD_HashText(_Symbol)+"_"+(string)Magic+"_"+(string)RecoveryMagic_+".bin";
      if(!persist || !FileIsExist(m_file))return true;
      SBDAtomicHeader h,want;BD_AtomicIdentity(want,17250001,1,1);int f=BD_AtomicOpen(m_file,want,h);
      if(f==INVALID_HANDLE){m_ok=false;return false;}
      bool ok=h.records<=512 && h.payload==(long)sizeof(long)+(long)h.records*sizeof(SBDStoredOutcome) && ArrayResize(m_records,h.records)==h.records;
      if(ok)m_retired=FileReadLong(f);
      for(int i=0;ok&&i<h.records;i++)ok=FileReadStruct(f,m_records[i])==sizeof(SBDStoredOutcome) && BD_OutcomeValid(m_records[i]) && m_records[i].nonce>m_retired && (i==0 || m_records[i-1].nonce<m_records[i].nonce);
      FileClose(f);m_sequence=h.sequence;m_ok=ok&&m_retired>=0;return m_ok;
   }
   bool Prepare(const SBDStoredOutcome &r)
   {
      if(!m_ok || !BD_OutcomeValid(r) || r.nonce<=m_retired || Find(r.id,r.nonce)>=0)return false;
      int n=ArraySize(m_records),drop=0;
      // Retire only a SETTLED prefix. Unknown/pending and unconsumed results pin retention.
      while(drop<n-32 && m_records[drop].state==BD_OUT_SETTLED)drop++;
      if(drop>0){m_retired=m_records[drop-1].nonce;for(int i=drop;i<n;i++)m_records[i-drop]=m_records[i];n-=drop;ArrayResize(m_records,n);}
      if(n>=512 || (n>0 && r.nonce<=m_records[n-1].nonce) || ArrayResize(m_records,n+1,32)!=n+1)return false;
      m_records[n]=r;return Save();
   }
   bool Update(const SBDStoredOutcome &r)
   {
      int i=Find(r.id,r.nonce);if(!m_ok||i<0||!BD_OutcomeValid(r))return false;
      if(m_records[i].state==BD_OUT_SETTLED)return true;
      if(r.ticket!=m_records[i].ticket || r.owner!=m_records[i].owner || r.command!=m_records[i].command || r.cycle!=m_records[i].cycle || r.groupSerial!=m_records[i].groupSerial || r.actualDirection!=m_records[i].actualDirection)return false;
      m_records[i]=r;return Save();
   }
   bool Acknowledge(const ulong id,const long nonce)
   {
      if(!m_ok)return false;
      int i=Find(id,nonce);if(i<0)return nonce>0&&nonce<=m_retired;
      if(m_records[i].state==BD_OUT_SETTLED)return true;
      if(m_records[i].state!=BD_OUT_APPLIED && m_records[i].state!=BD_OUT_PARTIAL && m_records[i].state!=BD_OUT_NO_EFFECT)return false;
      m_records[i].state=BD_OUT_SETTLED;return Save();
   }
};
#endif
