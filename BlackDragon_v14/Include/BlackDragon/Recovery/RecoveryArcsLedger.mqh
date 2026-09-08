#ifndef BD_ARCS_LEDGER_MQH
#define BD_ARCS_LEDGER_MQH
#include "RecoveryArcsPersistence.mqh"
#include <BlackDragon/Diagnostics/AtomicSnapshot.mqh>
struct SBDArcsReceiptV1
{
   ulong deal,positionId;
   long stamp,owner,cycle,units;
   int dir,generation,phase;
   bool funding,coreFunding,pyTrim,deleted,suppressed,adjustBaseline;
   double cash;
};
struct SBDArcsReceipt
{
   ulong deal,positionId;
   long stamp,owner,cycle,units;
   int dir,generation,phase;
   bool funding,coreFunding,pyTrim,deleted,suppressed,adjustBaseline;
   double cash;
   bool protectiveSl;
   double programmedSl;
};
struct SBDArcsEpoch { long stamp,cycle;int dir,phase,generation; };
struct SBDArcsLedgerMeta
{
   long cycle[2],legacyMsc[2],floorMsc[2],scanMsc[2];
   ulong legacyDeal[2];
   double step,tick;
   long freshStartMsc;
   bool migrated;
};
long BD_ServerMsc()
{ MqlTick t;return SymbolInfoTick(_Symbol,t)&&t.time_msc>0?t.time_msc:(long)TimeCurrent()*1000; }
bool BD_ReceiptEqual(const SBDArcsReceipt &a,const SBDArcsReceipt &b)
{ return a.deal==b.deal&&a.positionId==b.positionId&&a.stamp==b.stamp&&a.owner==b.owner&&a.cycle==b.cycle&&a.units==b.units&&a.dir==b.dir&&a.generation==b.generation&&a.phase==b.phase&&a.funding==b.funding&&a.coreFunding==b.coreFunding&&a.pyTrim==b.pyTrim&&a.deleted==b.deleted&&a.suppressed==b.suppressed&&a.adjustBaseline==b.adjustBaseline&&a.cash==b.cash&&a.protectiveSl==b.protectiveSl&&a.programmedSl==b.programmedSl; }
bool BD_ReceiptValid(const SBDArcsReceipt &r)
{ return r.deal>0&&r.positionId>0&&r.stamp>0&&r.cycle>0&&r.dir>=0&&r.dir<2&&r.units>=0&&MathIsValidNumber(r.cash)&&r.phase>=ARCS_IDLE&&r.phase<=ARCS_RECONCILE&&MathIsValidNumber(r.programmedSl)&&r.programmedSl>=0&&(!r.protectiveSl||(r.owner==(long)RecoveryMagic_&&r.generation>0&&r.programmedSl>0)); }
double BD_ReceiptCoreLoss(const SBDArcsReceipt &r)
{ return !r.deleted&&!r.suppressed&&r.coreFunding&&r.cash<0?-r.cash:0; }
bool BD_ArcsPayloadValid(const SArcsDirection &d,const SArcsExternalPending &p,const SArcsLayer &layers[])
{
   if(d.phase<ARCS_IDLE||d.phase>ARCS_RECONCILE||d.generationCount<0||d.generationCount>65536||d.activeLayer< -1||d.activeLayer>=BD_ARCS_MAX_LAYERS||d.lastObservedCoreUnits<0||d.lastObservedHedgeUnits<0||d.lastDealTimeMsc<0)return false;
   if(!MathIsValidNumber(d.anchorPrice)||d.anchorPrice<0||!MathIsValidNumber(d.hedgeFundingCash)||!MathIsValidNumber(d.coreLossSpent)||d.coreLossSpent<0||!MathIsValidNumber(d.availableCredit)||d.availableCredit<0||!MathIsValidNumber(d.globalSlPrice)||d.globalSlPrice<0||!MathIsValidNumber(d.transitionReferencePrice)||d.transitionReferencePrice<0)return false;
   if(p.targetUnits<0||p.observedUnitsBefore<0||!MathIsValidNumber(p.targetPrice)||p.targetPrice<0||p.startedAt<0||(p.active&&p.ownerMagic!=(long)Magic&&p.ownerMagic!=(long)RecoveryMagic_))return false;
   if(ArraySize(layers)!=BD_ARCS_MAX_LAYERS)return false;
   for(int i=0;i<ArraySize(layers);i++)
   {
      SArcsLayer l=layers[i];if(l.state<ARCS_LAYER_EMPTY||l.state>ARCS_LAYER_CLOSED||(l.used&&l.generation<1))return false;
      if(l.targetUnits<0||l.openedUnits<0||l.remainingUnits<0||l.tpBaselineUnits<0||l.tpTargetCloseUnits<0||l.tpObservedCloseUnits<0||l.fundingClosedUnits<0)return false;
      if(!MathIsValidNumber(l.weightedEntry)||l.weightedEntry<0||!MathIsValidNumber(l.netBE)||l.netBE<0||!MathIsValidNumber(l.tpTriggerPrice)||l.tpTriggerPrice<0||!MathIsValidNumber(l.lockTargetPrice)||l.lockTargetPrice<0||!MathIsValidNumber(l.virtualSlPrice)||l.virtualSlPrice<0||!MathIsValidNumber(l.realizedFundingCash)||!MathIsValidNumber(l.realizedOtherCash))return false;
   }
   return true;
}
// Composition owns the legacy reader and new atomic checkpoint. Ledger receipts,
// funding-phase epochs, directions, pending commands and layers commit together.
class CArcsLedgerPersistence
{
private:
   CRecoveryArcsPersistence m_legacy;
   string m_file;
   SBDArcsReceipt m_receipts[];
   SBDArcsEpoch m_epochs[];
   SBDArcsLedgerMeta m_meta;
   bool m_changed;
   void Reset()
   {
      ArrayResize(m_receipts,0);ArrayResize(m_epochs,0);ZeroMemory(m_meta);
      m_meta.cycle[0]=1;m_meta.cycle[1]=1;m_meta.freshStartMsc=BD_ServerMsc();
      m_meta.step=SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP);m_meta.tick=SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE);m_changed=false;
   }
public:
   CArcsLedgerPersistence(){Reset();}
   void Init(const string symbol,const long account,const long core,const long hedge)
   {m_legacy.Init(symbol,account,core,hedge);m_file=m_legacy.FileName()+".t1725";Reset();}
   string FileName() const{return m_file;}
   long Cycle(const int d) const{return d>=0&&d<2?m_meta.cycle[d]:0;}
   void NewCycle(const int d){if(d>=0&&d<2){m_meta.cycle[d]++;m_changed=true;}}
   int Find(const ulong deal) const
   {int lo=0,hi=ArraySize(m_receipts);while(lo<hi){int m=lo+(hi-lo)/2;if(m_receipts[m].deal<deal)lo=m+1;else hi=m;}return lo<ArraySize(m_receipts)&&m_receipts[lo].deal==deal?lo:-1;}
   bool Get(const ulong deal,SBDArcsReceipt &r) const
   {int i=Find(deal);if(i<0)return false;r=m_receipts[i];return true;}
   bool LegacyCovered(const int d,const long stamp,const ulong deal) const
   {return stamp<m_meta.legacyMsc[d]||(stamp==m_meta.legacyMsc[d]&&deal<=m_meta.legacyDeal[d]);}
   bool ReceiptsDurable()const{return !m_changed;}
   long FirstEpoch(const int d) const
   {for(int i=0;i<ArraySize(m_epochs);i++)if(m_epochs[i].dir==d)return m_epochs[i].stamp;return 0;}
   bool BeforeFreshStart(const int d,const long stamp) const
   {return !m_meta.migrated&&stamp<m_meta.freshStartMsc;}
   datetime ReplayFrom(const int d,const long cursor)const
   {long base=m_meta.scanMsc[d]>0?m_meta.scanMsc[d]:(cursor>0?cursor:FirstEpoch(d));return (datetime)MathMax(0,base/1000-300);}
   void ScannedThrough(const int d,const long stamp){m_meta.scanMsc[d]=stamp;m_changed=true;}
   bool CycleAt(const int d,const long stamp,long &cycle) const
   {
      cycle=0;if(d<0||d>1||stamp<=m_meta.floorMsc[d])return false;
      for(int i=ArraySize(m_epochs)-1;i>=0;i--)
         if(m_epochs[i].dir==d&&m_epochs[i].stamp<=stamp)
         {
            cycle=m_epochs[i].cycle;
            // Phase/generation can change in the opening millisecond. Only a
            // campaign change makes campaign ownership ambiguous here.
            for(int j=i-1;j>=0&&m_epochs[j].stamp==stamp;j--)
               if(m_epochs[j].dir==d&&m_epochs[j].cycle!=cycle)return false;
            return true;
         }
      return false;
   }
   bool PhaseAt(const int d,const long stamp,SBDArcsEpoch &e) const
   {
      if(d<0||d>1||stamp<=m_meta.floorMsc[d])return false;
      for(int i=ArraySize(m_epochs)-1;i>=0;i--)
         if(m_epochs[i].dir==d && m_epochs[i].stamp<=stamp)
         {
            e=m_epochs[i];
            // Two transitions within the same millisecond cannot be ordered by
            // the broker timestamp. Require direct receipt proof, never guess.
            for(int j=i-1;j>=0&&m_epochs[j].stamp==stamp;j--)
               if(m_epochs[j].dir==d&&(m_epochs[j].phase!=e.phase||m_epochs[j].generation!=e.generation||m_epochs[j].cycle!=e.cycle))return false;
            return true;
         }
      return false;
   }
   bool Put(const SBDArcsReceipt &r)
   {
      if(!BD_ReceiptValid(r))return false;int at=Find(r.deal);
      if(at>=0){m_receipts[at]=r;m_changed=true;return true;}
      int n=ArraySize(m_receipts);if(n>=65536||ArrayResize(m_receipts,n+1,128)!=n+1)return false;
      at=n;while(at>0&&m_receipts[at-1].deal>r.deal){m_receipts[at]=m_receipts[at-1];at--;}
      m_receipts[at]=r;m_changed=true;return true;
   }
   bool RecordPhase(const int d,const SArcsDirection &state)
   {
      int generation=state.generationCount;
      for(int i=ArraySize(m_epochs)-1;i>=0;i--)if(m_epochs[i].dir==d)
      {if(m_epochs[i].phase==(int)state.phase&&m_epochs[i].generation==generation&&m_epochs[i].cycle==Cycle(d))return true;break;}
      int n=ArraySize(m_epochs);if(n>=65536||ArrayResize(m_epochs,n+1,64)!=n+1)return false;
      m_epochs[n].dir=d;m_epochs[n].stamp=BD_ServerMsc();
      if(n>0&&m_epochs[n].stamp<m_epochs[n-1].stamp)m_epochs[n].stamp=m_epochs[n-1].stamp;
      m_epochs[n].cycle=Cycle(d);m_epochs[n].phase=(int)state.phase;m_epochs[n].generation=generation;m_changed=true;return true;
   }
   void Compact()
   {
      if(ArraySize(m_receipts)<4096 && ArraySize(m_epochs)<4096)return;
      int keep=0;
      // Only old cycles can be retired: their cash no longer funds a current
      // obligation. The floor rejects future corrections beyond retained proof.
      for(int i=0;i<ArraySize(m_receipts);i++)
      {
         int d=m_receipts[i].dir;
         if(m_receipts[i].cycle+1<Cycle(d))
         {m_meta.floorMsc[d]=(long)MathMax(m_meta.floorMsc[d],m_receipts[i].stamp);continue;}
         m_receipts[keep++]=m_receipts[i];
      }
      ArrayResize(m_receipts,keep);keep=0;
      for(int i=0;i<ArraySize(m_epochs);i++)if(m_epochs[i].cycle+1>=Cycle(m_epochs[i].dir))m_epochs[keep++]=m_epochs[i];
      ArrayResize(m_epochs,keep);
   }
   bool Save(const long sequence,const SArcsDirection &buy,const SArcsDirection &sell,
             const SArcsExternalPending &bp,const SArcsExternalPending &sp,
             SArcsLayer &bl[],SArcsLayer &sl[],string &why)
   {
      why="";Compact();if(!RecordPhase(0,buy)||!RecordPhase(1,sell)){why="phase journal capacity";return false;}
      if(ArraySize(bl)!=BD_ARCS_MAX_LAYERS||ArraySize(sl)!=BD_ARCS_MAX_LAYERS){why="layer capacity";return false;}
      if(!BD_ArcsPayloadValid(buy,bp,bl)||!BD_ArcsPayloadValid(sell,sp,sl)){why="invalid state payload";return false;}
      if(MQLInfoInteger(MQL_TESTER)&&!RecoveryTesterResumeState_){m_changed=false;return true;}
      SBDAtomicHeader h;BD_AtomicIdentity(h,17250002,2,Recovery_T16SemanticFingerprint());
      h.sequence=sequence;h.records=ArraySize(m_receipts);h.epochs=ArraySize(m_epochs);
      for(int i=0;i<h.records;i++)if(!BD_ReceiptValid(m_receipts[i])){why="invalid receipt";return false;}
      int f=BD_AtomicBegin(m_file,h);if(f==INVALID_HANDLE){why="checkpoint temp open";return false;}
      bool ok=FileWriteStruct(f,m_meta)==sizeof(SBDArcsLedgerMeta) && FileWriteStruct(f,buy)==sizeof(SArcsDirection) && FileWriteStruct(f,sell)==sizeof(SArcsDirection) && FileWriteStruct(f,bp)==sizeof(SArcsExternalPending) && FileWriteStruct(f,sp)==sizeof(SArcsExternalPending);
      for(int i=0;i<BD_ARCS_MAX_LAYERS;i++)ok=FileWriteStruct(f,bl[i])==sizeof(SArcsLayer) && FileWriteStruct(f,sl[i])==sizeof(SArcsLayer) && ok;
      for(int i=0;i<h.records;i++)ok=FileWriteStruct(f,m_receipts[i])==sizeof(SBDArcsReceipt) && ok;
      for(int i=0;i<h.epochs;i++)ok=FileWriteStruct(f,m_epochs[i])==sizeof(SBDArcsEpoch) && ok;
      if(!BD_AtomicCommit(m_file,f,h,ok)){why="checkpoint atomic replace";return false;}
      m_changed=false;return true;
   }
   eArcsPersistStatus Load(SArcsPersistIdentity &identity,SArcsDirection &buy,SArcsDirection &sell,
                          SArcsExternalPending &bp,SArcsExternalPending &sp,SArcsLayer &bl[],SArcsLayer &sl[],string &why)
   {
      why="";Reset();
      if(MQLInfoInteger(MQL_TESTER)&&!RecoveryTesterResumeState_)return ARCS_PERSIST_NOT_FOUND;
      if(!FileIsExist(m_file))
      {
         eArcsPersistStatus st=m_legacy.Load(identity,buy,sell,bp,sp,bl,sl,why);
         if(st==ARCS_PERSIST_OK)
         {
            m_meta.migrated=true;
            m_meta.legacyMsc[0]=buy.lastDealTimeMsc;m_meta.legacyMsc[1]=sell.lastDealTimeMsc;
            m_meta.legacyDeal[0]=buy.lastDealTicket;m_meta.legacyDeal[1]=sell.lastDealTicket;
            if(!RecordPhase(0,buy)||!RecordPhase(1,sell)){why="migration phase capacity";return ARCS_PERSIST_IO_ERROR;}
         }
         return st;
      }
      SBDAtomicHeader h,want;BD_AtomicIdentity(want,17250002,2,Recovery_T16SemanticFingerprint());int f=BD_AtomicOpen(m_file,want,h);
      bool v1=false;
      if(f==INVALID_HANDLE)
      {
         want.version=1;f=BD_AtomicOpen(m_file,want,h);v1=f!=INVALID_HANDLE;
      }
      if(f==INVALID_HANDLE){why="ledger checksum/identity/size";return ARCS_PERSIST_CORRUPT;}
      long expected=(long)sizeof(SBDArcsLedgerMeta)+2*(long)sizeof(SArcsDirection)+2*(long)sizeof(SArcsExternalPending)+2*BD_ARCS_MAX_LAYERS*(long)sizeof(SArcsLayer)+(long)h.records*(v1?sizeof(SBDArcsReceiptV1):sizeof(SBDArcsReceipt))+(long)h.epochs*sizeof(SBDArcsEpoch);
      bool ok=h.payload==expected && ArrayResize(bl,BD_ARCS_MAX_LAYERS)==BD_ARCS_MAX_LAYERS && ArrayResize(sl,BD_ARCS_MAX_LAYERS)==BD_ARCS_MAX_LAYERS && ArrayResize(m_receipts,h.records)==h.records && ArrayResize(m_epochs,h.epochs)==h.epochs;
      if(ok)ok=FileReadStruct(f,m_meta)==sizeof(SBDArcsLedgerMeta) && FileReadStruct(f,buy)==sizeof(SArcsDirection) && FileReadStruct(f,sell)==sizeof(SArcsDirection) && FileReadStruct(f,bp)==sizeof(SArcsExternalPending) && FileReadStruct(f,sp)==sizeof(SArcsExternalPending);
      for(int i=0;ok&&i<BD_ARCS_MAX_LAYERS;i++)ok=FileReadStruct(f,bl[i])==sizeof(SArcsLayer) && FileReadStruct(f,sl[i])==sizeof(SArcsLayer);
      for(int i=0;ok&&i<h.records;i++)
      {
         if(v1)
         {
            SBDArcsReceiptV1 old;ZeroMemory(old);
            ok=FileReadStruct(f,old)==sizeof(SBDArcsReceiptV1);
            ZeroMemory(m_receipts[i]);
            m_receipts[i].deal=old.deal;m_receipts[i].positionId=old.positionId;
            m_receipts[i].stamp=old.stamp;m_receipts[i].owner=old.owner;m_receipts[i].cycle=old.cycle;
            m_receipts[i].units=old.units;m_receipts[i].dir=old.dir;m_receipts[i].generation=old.generation;
            m_receipts[i].phase=old.phase;m_receipts[i].funding=old.funding;m_receipts[i].coreFunding=old.coreFunding;
            m_receipts[i].pyTrim=old.pyTrim;m_receipts[i].deleted=old.deleted;m_receipts[i].suppressed=old.suppressed;
            m_receipts[i].adjustBaseline=old.adjustBaseline;m_receipts[i].cash=old.cash;
            // Migration preserves cash, but cannot invent a protective-SL proof.
         }
         else ok=FileReadStruct(f,m_receipts[i])==sizeof(SBDArcsReceipt);
         ok=ok&&BD_ReceiptValid(m_receipts[i])&&(i==0||m_receipts[i-1].deal<m_receipts[i].deal);
      }
      for(int i=0;ok&&i<h.epochs;i++)ok=FileReadStruct(f,m_epochs[i])==sizeof(SBDArcsEpoch) && m_epochs[i].dir>=0&&m_epochs[i].dir<2&&m_epochs[i].cycle>0&&m_epochs[i].generation>=0&&m_epochs[i].stamp>0&&m_epochs[i].phase>=ARCS_IDLE&&m_epochs[i].phase<=ARCS_RECONCILE && (i==0||m_epochs[i].stamp>=m_epochs[i-1].stamp);
      FileClose(f);
      ok=ok&&m_meta.cycle[0]>0&&m_meta.cycle[1]>0&&MathAbs(m_meta.step-SymbolInfoDouble(_Symbol,SYMBOL_VOLUME_STEP))<1e-12&&MathAbs(m_meta.tick-SymbolInfoDouble(_Symbol,SYMBOL_TRADE_TICK_SIZE))<1e-12;
      ok=ok&&BD_ArcsPayloadValid(buy,bp,bl)&&BD_ArcsPayloadValid(sell,sp,sl);
      if(!ok){why="ledger payload validation";return ARCS_PERSIST_CORRUPT;}
      ZeroMemory(identity);identity.saveSequence=h.sequence;identity.accountLogin=h.account;identity.coreMagic=h.core;identity.recoveryMagic=h.hedge;identity.symbolHash=Recovery_ArcsSymbolHash(_Symbol);identity.semanticHash=h.semantics;identity.volumeStep=m_meta.step;identity.tickSize=m_meta.tick;
      return ARCS_PERSIST_OK;
   }
};
CArcsLedgerPersistence *g_bdArcsReceiptStore=NULL;
#endif
