//+------------------------------------------------------------------+
//| RecoveryArcsStackHardened.mqh — T16.1 event-order/SL hardening   |
//| Prevents: broker SL effect -> premature Gnext -> late DEAL_ADD   |
//| being misclassified as manual/external mutation.                 |
//+------------------------------------------------------------------+
#ifndef BD_RECOVERY_ARCS_STACK_HARDENED_MQH
#define BD_RECOVERY_ARCS_STACK_HARDENED_MQH

#include "RecoveryT1714InterleavePolicy.mqh"

#define private protected
#define CRecoveryArcsStack CRecoveryArcsStackBase
#include "RecoveryArcsStack.mqh"
#undef CRecoveryArcsStack
#undef private

#define BD_ARCS_PROTECTIVE_WAIT_TIMEOUT_SEC 10

struct SArcsHardeningCloseDeal
{
   ulong  deal;
   ulong  positionId;
   long   type;
   long   reason;
   double programmedSl;
   double dealPrice;
   double volume;
};

class CRecoveryArcsStack : public CRecoveryArcsStackBase
{
private:
   bool RecoveryPositionIdentity(const ulong positionId,
                                 int &generation,
                                 ulong &positionTicket,
                                 long &openingType,
                                 long &openingMsc) const
   {
      generation = -1;
      positionTicket = 0;openingType=-1;openingMsc=0;
      string openingComment="";
      if(positionId == 0 || !HistorySelectByPosition(positionId)) return false;

      ulong oldestDeal = 0;
      long oldestMsc = 0;
      long owner = 0;
      int g = -1;
      ulong openingOrder = 0;
      for(int i = 0; i < HistoryDealsTotal(); i++)
      {
         ulong deal = HistoryDealGetTicket(i);
         if(deal == 0 || HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) continue;
         long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
         if(entry != DEAL_ENTRY_IN && entry != DEAL_ENTRY_INOUT) continue;
         long tmsc = HistoryDealGetInteger(deal, DEAL_TIME_MSC);
         if(oldestDeal == 0 || tmsc < oldestMsc ||
            (tmsc == oldestMsc && deal < oldestDeal))
         {
            oldestDeal = deal;
            oldestMsc = tmsc;
            owner = HistoryDealGetInteger(deal, DEAL_MAGIC);
            openingOrder = (ulong)HistoryDealGetInteger(deal, DEAL_ORDER);
            openingType=HistoryDealGetInteger(deal,DEAL_TYPE);
            openingComment=HistoryDealGetString(deal,DEAL_COMMENT);
            g = Recovery_ArcsGenerationFromComment(openingComment);
         }
      }
      if(owner != (long)RecoveryMagic_ || g < 1 || oldestMsc<=0) return false;
      eRecoveryCoreDirection openingDir;
      if(openingType==DEAL_TYPE_SELL)openingDir=recovery_CORE_BUY;
      else if(openingType==DEAL_TYPE_BUY)openingDir=recovery_CORE_SELL;
      else return false;
      if(!OC_RhMatchesCycle(openingComment,Recovery_CycleKey(openingDir)))return false;
      openingMsc=oldestMsc;
      generation = g;
      positionTicket = openingOrder;
      return true;
   }

   bool DealDirection(const long dealType,
                      eRecoveryCoreDirection &dir) const
   {
      // Closing a SELL Recovery Hedge is a BUY deal => BUY Core cycle.
      if(dealType == DEAL_TYPE_BUY)
      {
         dir = recovery_CORE_BUY;
         return true;
      }
      // Closing a BUY Recovery Hedge is a SELL deal => SELL Core cycle.
      if(dealType == DEAL_TYPE_SELL)
      {
         dir = recovery_CORE_SELL;
         return true;
      }
      return false;
   }

   bool IsExpectedPersistedProtectiveClose(const eRecoveryCoreDirection dir,
                                           const SArcsLayer &layer,
                                           const SArcsHardeningCloseDeal &d)
   {
      if(HedgeSLMode_ == SL_BROKER)
      {
         eRecoveryCoreDirection closeDir;
         return DealDirection(d.type,closeDir)&&closeDir==dir&&ExpectedBrokerSlDeal(d.deal);
      }
      double target=m_dir[Idx(dir)].globalSlArmed&&m_dir[Idx(dir)].globalSlPrice>0
                    ?m_dir[Idx(dir)].globalSlPrice
                    :(layer.virtualSlArmed&&layer.virtualSlPrice>0?layer.virtualSlPrice:layer.lockTargetPrice);
      if(target<=0)return false;
      return HedgeSLMode_ == SL_VIRTUAL && layer.virtualSlArmed &&
             d.reason == DEAL_REASON_EXPERT;
   }

   bool RepairProtectiveLayerDecreases(const eRecoveryCoreDirection dir,
                                       string &why)
   {
      why = "";
      int di = Idx(dir);
      // Deal times have millisecond precision; datetime truncates to seconds.
      // Include the full current second so a directly visible SL is not omitted
      // from the protective proof batch. Exact identity and unit checks remain.
      if(!HistorySelect(0, TimeCurrent()+1))
      {
         why = "không đọc được history để reconcile protective ARCS layer";
         return false;
      }

      ulong deals[];
      ArrayResize(deals, 0);
      for(int i = 0; i < HistoryDealsTotal(); i++)
      {
         ulong deal = HistoryDealGetTicket(i);
         if(deal == 0 || HistoryDealGetString(deal, DEAL_SYMBOL) != _Symbol) continue;
         // Callback order is not ticket order. A newer deal can advance the
         // cash cursor before an older SL is delivered. Only a consumed receipt
         // may exclude protective proof; the high-water cursor cannot do so.
         SBDArcsReceipt receipt;bool known=m_persistence.Get(deal,receipt);
         if(known&&!receipt.deleted&&(receipt.protectiveSl||receipt.pyTrim))continue;
         if(HedgeSLMode_!=SL_BROKER &&
            !CursorAfter(HistoryDealGetInteger(deal,DEAL_TIME_MSC),deal,
                         m_dir[di].lastDealTimeMsc,m_dir[di].lastDealTicket))continue;
         long entry = HistoryDealGetInteger(deal, DEAL_ENTRY);
         if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) continue;
         int n = ArraySize(deals);
         if(ArrayResize(deals,n+1,128)!=n+1){why="protective history allocation";return false;}
         deals[n] = deal;
      }

      for(int li = 0; li < BD_ARCS_MAX_LAYERS; li++)
      {
         SArcsLayer layer;
         GetLayer(dir, li, layer);
         if(!layer.used || layer.remainingUnits <= 0) continue;
         if(layer.state != ARCS_LAYER_LOCK_PENDING &&
            layer.state != ARCS_LAYER_LOCKED &&
            layer.state != ARCS_LAYER_GLOBAL_PROTECTED &&
            layer.state != ARCS_LAYER_PROTECTIVE_CLOSE_PENDING)
            continue;

         long live = Recovery_ArcsLayerUnits(dir, layer.generation, m_volumeStep);
         if(live == layer.remainingUnits) continue;
         long provenClose = 0;
         string proofTrace="";int proofRejected=0,identityRejected=0;
         ulong protectiveDeals[];
         for(int k = 0; k < ArraySize(deals); k++)
         {
            ulong deal = deals[k];
            if(!HistoryDealSelect(deal)) continue;
            ulong positionId = (ulong)HistoryDealGetInteger(deal, DEAL_POSITION_ID);
            int generation = -1;
            ulong positionTicket = 0;
            long openingType=-1,openingMsc=0;
            if(!RecoveryPositionIdentity(positionId, generation, positionTicket,openingType,openingMsc) ||
               generation != layer.generation ||
               (dir==recovery_CORE_BUY?openingType!=DEAL_TYPE_SELL:openingType!=DEAL_TYPE_BUY))
            {identityRejected++;continue;}
            if(!HistoryDealSelect(deal)) continue;

            SArcsHardeningCloseDeal d;
            d.deal = deal;
            d.positionId = positionId;
            d.type = HistoryDealGetInteger(deal, DEAL_TYPE);
            d.reason = HistoryDealGetInteger(deal, DEAL_REASON);
            d.programmedSl = HistoryDealGetDouble(deal, DEAL_SL);
            d.dealPrice = HistoryDealGetDouble(deal, DEAL_PRICE);
            d.volume = HistoryDealGetDouble(deal, DEAL_VOLUME);
            bool pyTrim=g_pyramidProtection!=NULL && g_pyramidProtection.ExpectedRhTrim(deal);
            bool candidateExpected=pyTrim || IsExpectedPersistedProtectiveClose(dir, layer, d);
            if(StringLen(proofTrace)<2048)
               proofTrace+=StringFormat(" deal=%I64u,pos=%I64u,vol=%.8f,reason=%I64d,sl=%.8f,expected=%d;",
                                      deal,positionId,d.volume,d.reason,d.programmedSl,(int)candidateExpected);
            if(!candidateExpected){proofRejected++;continue;}
            provenClose += Recovery_VolumeToUnitsFloor(d.volume, m_volumeStep);
            if(!pyTrim&&HedgeSLMode_==SL_BROKER)
            {
               int n=ArraySize(protectiveDeals);
               if(ArrayResize(protectiveDeals,n+1)!=n+1){why="protective receipt allocation";return false;}
               protectiveDeals[n]=deal;
            }
         }

         eRecoveryT1714LayerRefresh disposition =
            Recovery_T1714LayerRefreshPure(layer.remainingUnits, live, provenClose);
         if(disposition == recovery_T1714_REFRESH_RECONCILE)
         {
            why = live > layer.remainingUnits
                  ? "protective layer broker volume tăng so với persisted ownership"
                  : "persisted protective layer giảm volume nhưng không có exact protective-close proof";
            why+=StringFormat(" [PROTECTIVE_MISMATCH dir=%d layer=%d gen=%d state=%d persisted=%I64d live=%I64d proven=%I64d candidates=%d identity_rejected=%d proof_rejected=%d now=%I64d]%s",
                              (int)dir,li,layer.generation,(int)layer.state,layer.remainingUnits,live,provenClose,
                              ArraySize(deals),identityRejected,proofRejected,(long)TimeCurrent(),proofTrace);
            return false;
         }
         if(disposition == recovery_T1714_REFRESH_UNCHANGED) continue;

         // Cash and proof are journaled before topology is committed. A late
         // DEAL_ADD reuses this receipt even after coordinator/layer retirement.
         for(int k=0;k<ArraySize(protectiveDeals);k++)
            if(!RememberProtectiveSl(protectiveDeals[k],why))return false;
         GetLayer(dir,li,layer); // ReconcileReceipt may have updated actual cash.
         layer.remainingUnits = live;
         if(live == 0)
         {
            layer.state = ARCS_LAYER_CLOSED;
            layer.virtualSlArmed = false;
            if(m_dir[di].activeLayer == li &&
               m_dir[di].phase == ARCS_PROTECTIVE_CLOSE_WAIT)
               m_dir[di].phase = ARCS_LOCKED;
         }
         PutLayer(dir, li, layer);
      }
      return true;
   }

   void RefreshVirtualGenerationFromDeal(const MqlTradeTransaction &trans)
   {
      if(g_pyramidProtection!=NULL && g_pyramidProtection.ExpectedRhTrim(trans.deal)) return;
      if(trans.deal == 0 || !HistoryDealSelect(trans.deal)) return;
      long entry = HistoryDealGetInteger(trans.deal, DEAL_ENTRY);
      if(entry != DEAL_ENTRY_OUT && entry != DEAL_ENTRY_OUT_BY) return;
      ulong positionId = (ulong)HistoryDealGetInteger(trans.deal, DEAL_POSITION_ID);
      long type = HistoryDealGetInteger(trans.deal, DEAL_TYPE);
      long reason = HistoryDealGetInteger(trans.deal, DEAL_REASON);
      if(positionId == 0) return;

      int generation = -1;
      ulong positionTicket = 0;
      long openingType=-1,openingMsc=0;
      if(!RecoveryPositionIdentity(positionId, generation, positionTicket,openingType,openingMsc)) return;
      if(!HistoryDealSelect(trans.deal)) return;

      eRecoveryCoreDirection dir;
      if(!DealDirection(type, dir)) return;
      int li = FindLayerByGeneration(dir, generation);
      if(li < 0) return;
      SArcsLayer layer;
      GetLayer(dir, li, layer);

      if(layer.state != ARCS_LAYER_LOCK_PENDING &&
         layer.state != ARCS_LAYER_PROTECTIVE_CLOSE_PENDING &&
         layer.state != ARCS_LAYER_LOCKED &&
         layer.state != ARCS_LAYER_GLOBAL_PROTECTED)
         return;

      bool expected = false;
      if(HedgeSLMode_ == SL_BROKER && reason == DEAL_REASON_SL)
         expected = ExpectedBrokerSlDeal(trans.deal);
      else if(HedgeSLMode_ == SL_VIRTUAL && reason == DEAL_REASON_EXPERT &&
              layer.virtualSlArmed)
         expected = true;
      if(!expected) return;

      long live = Recovery_ArcsLayerUnits(dir, generation, m_volumeStep);
      if(live < 0 || live > layer.remainingUnits)
      {
         LatchReconcile(dir, "post-deal protective layer volume violates persisted ownership");
         return;
      }

      layer.remainingUnits = live;
      if(live == 0)
      {
         layer.state = ARCS_LAYER_CLOSED;
         layer.virtualSlArmed = false;
         if(m_dir[Idx(dir)].activeLayer == li &&
            (m_dir[Idx(dir)].phase == ARCS_PROTECTIVE_CLOSE_WAIT ||
             m_dir[Idx(dir)].phase == ARCS_LOCK_PENDING))
            m_dir[Idx(dir)].phase = ARCS_LOCKED;
      }
      PutLayer(dir, li, layer);
   }

   bool RememberProtectiveSl(const ulong deal,string &why)
   {
      if(!ReconcileReceipt(deal,false,true,why))
      {m_persistenceBlocked=true;m_ready=false;return false;}
      SBDArcsReceipt receipt;
      if(!m_persistence.Get(deal,receipt)||receipt.deleted||receipt.suppressed||
         receipt.owner!=(long)RecoveryMagic_||receipt.programmedSl<=0)
      {why="protective settlement receipt missing/invalid";m_persistenceBlocked=true;m_ready=false;return false;}
      receipt.protectiveSl=true;
      if(!m_persistence.Put(receipt)){why="protective receipt capacity";m_persistenceBlocked=true;m_ready=false;return false;}
      m_dirty=true;return true;
   }

   void RefreshClosedGenerationFromDeal(const MqlTradeTransaction &trans)
   {
      if(HedgeSLMode_==SL_VIRTUAL){RefreshVirtualGenerationFromDeal(trans);return;}
      if(m_persistenceBlocked||!ExpectedBrokerSlDeal(trans.deal))return;
      if(!HistoryDealSelect(trans.deal))return;
      eRecoveryCoreDirection dir;
      if(!DealDirection(HistoryDealGetInteger(trans.deal,DEAL_TYPE),dir))return;
      string why="";
      if(!RepairProtectiveLayerDecreases(dir,why))
      {m_persistenceBlocked=true;LatchReconcile(dir,"protective callback refresh: "+why);}
   }

   void NormalizeStableLockedHold(const eRecoveryCoreDirection dir)
   {
      int di = Idx(dir);
      if(m_dir[di].phase != ARCS_LOCKED || m_dir[di].activeLayer < 0) return;
      long core = Recovery_ArcsCoreUnits(dir, m_volumeStep);
      bool terminalByMax = m_dir[di].generationCount >= MaxHedgeGenerations_;
      bool noCoreForNext = core <= 0;
      if(!terminalByMax && !noCoreForNext) return;
      m_dir[di].activeLayer = -1;
      m_dirty = true;
   }

   bool EnterProtectiveCloseWait(const eRecoveryCoreDirection dir,
                                 const EAContext &ctx,
                                 string &why)
   {
      int di = Idx(dir);
      if(m_dir[di].phase != ARCS_LOCK_PENDING || m_dir[di].activeLayer < 0)
         return false;
      int li = m_dir[di].activeLayer;
      SArcsLayer layer;
      GetLayer(dir, li, layer);
      if(!layer.used || layer.state != ARCS_LAYER_LOCK_PENDING ||
         layer.remainingUnits <= 0)
         return false;

      long live = Recovery_ArcsLayerUnits(dir, layer.generation, m_volumeStep);
      if(live > 0) return false;

      // A retained layer vanished while the FSM was still confirming its
      // broker lock. Do NOT mark it CLOSED or start Gnext from position state
      // alone. The corresponding DEAL_ADD must classify first.
      if(layer.lockTargetPrice <= 0.0)
      {
         why = "retained Hedge biến mất trước khi có durable lock target";
         LatchReconcile(dir, why);
         Save(why);
         return true;
      }

      layer.state = ARCS_LAYER_PROTECTIVE_CLOSE_PENDING;
      layer.protectiveCloseObservedAt = ctx.now;
      PutLayer(dir, li, layer);
      m_dir[di].phase = ARCS_PROTECTIVE_CLOSE_WAIT;
      m_dirty = true;
      if(!Save(why)) return true;
      Log_Info("Recovery", "T16.1 " + Recovery_DirectionName(dir) +
               " protective broker effect observed; waiting exact DEAL_ADD before next generation");
      return true;
   }

   bool HoldProtectiveCloseWait(const eRecoveryCoreDirection dir,
                                const EAContext &ctx,
                                string &why)
   {
      int di = Idx(dir);
      if(m_dir[di].phase != ARCS_PROTECTIVE_CLOSE_WAIT) return false;
      int li = m_dir[di].activeLayer;
      if(li < 0)
      {
         why = "PROTECTIVE_CLOSE_WAIT mất active layer identity";
         LatchReconcile(dir, why);
         Save(why);
         return true;
      }
      SArcsLayer layer;
      GetLayer(dir, li, layer);
      if(!layer.used || layer.state != ARCS_LAYER_PROTECTIVE_CLOSE_PENDING)
      {
         why = "PROTECTIVE_CLOSE_WAIT layer state mismatch";
         LatchReconcile(dir, why);
         Save(why);
         return true;
      }

      long live = Recovery_ArcsLayerUnits(dir, layer.generation, m_volumeStep);
      if(live > 0)
      {
         why = "protective-close wait broker exposure reappeared";
         LatchReconcile(dir, why);
         Save(why);
         return true;
      }
      if(layer.protectiveCloseObservedAt > 0 &&
         ctx.now > layer.protectiveCloseObservedAt + BD_ARCS_PROTECTIVE_WAIT_TIMEOUT_SEC)
      {
         why = "timeout waiting exact DEAL_ADD for observed protective close";
         LatchReconcile(dir, why);
         Save(why);
         return true;
      }
      // Intentional terminal hold for this tick: no Core DCA, no Gnext.
      return true;
   }

   bool ResumeAfterConsumedProtectiveClose(const eRecoveryCoreDirection dir,
                                           const EAContext &ctx,
                                           string &why)
   {
      int di = Idx(dir);
      if(m_dir[di].phase != ARCS_LOCKED || m_dir[di].activeLayer < 0)
         return false;
      int li = m_dir[di].activeLayer;
      SArcsLayer layer;
      GetLayer(dir, li, layer);
      if(!layer.used || layer.state != ARCS_LAYER_CLOSED ||
         layer.protectiveCloseObservedAt <= 0)
         return false;

      // DEAL proof has now been consumed and persisted. Only now may ARCS
      // advance to the next generation.
      layer.protectiveCloseObservedAt = 0;
      PutLayer(dir, li, layer);
      return AfterLayerLocked(dir, ctx.now, why);
   }

public:
   // T17.14 synchronous trade effects may be broker-visible before MT5 delivers
   // DEAL_ADD callbacks. Refresh only exact-proven protective decreases so an
   // unrelated Overlap finalizer validates fresh ownership without weakening
   // manual/ambiguous mutation fail-closed behavior.
   bool RefreshExpectedProtectiveCloseOwnership(
      const eRecoveryCoreDirection dir,
      string &why)
   {
      return RepairProtectiveLayerDecreases(dir, why);
   }

   // T16.1 classifier: prefer durable layer target, but if event ordering has
   // already moved mutable state, exact ExecutionLayer MODIFY identity can
   // independently prove that this broker SL was Recovery-owned.
   bool ExpectedBrokerSlDeal(const ulong deal)
   {
      if(HedgeSLMode_!=SL_BROKER||deal==0||!HistoryDealSelect(deal))return false;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol||
         HistoryDealGetInteger(deal,DEAL_REASON)!=DEAL_REASON_SL)return false;
      long entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      if(entry!=DEAL_ENTRY_OUT&&entry!=DEAL_ENTRY_OUT_BY)return false;
      ulong positionId=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);
      long type=HistoryDealGetInteger(deal,DEAL_TYPE),stamp=HistoryDealGetInteger(deal,DEAL_TIME_MSC);
      double programmedSl=HistoryDealGetDouble(deal,DEAL_SL),price=HistoryDealGetDouble(deal,DEAL_PRICE);
      if(!MathIsValidNumber(programmedSl)||!MathIsValidNumber(price)||programmedSl<=0||price<=0)return false;
      int generation=-1;ulong ticket=0;long openingType=-1,openingMsc=0;
      if(!RecoveryPositionIdentity(positionId,generation,ticket,openingType,openingMsc))return false;
      if(!HistoryDealSelect(deal))return false;
      eRecoveryCoreDirection dir;
      if(!DealDirection(type,dir)||stamp<openingMsc||
         (dir==recovery_CORE_BUY?openingType!=DEAL_TYPE_SELL:openingType!=DEAL_TYPE_BUY))return false;
      double tolerance=MathMax(2.0*m_tickSize,_Point);
      SBDArcsReceipt receipt;
      if(m_persistence.Get(deal,receipt)&&receipt.protectiveSl&&!receipt.deleted&&!receipt.suppressed&&
         receipt.positionId==positionId&&receipt.owner==(long)RecoveryMagic_&&
         receipt.dir==Idx(dir)&&receipt.generation==generation&&receipt.stamp==stamp)
         return Recovery_ProtectiveSlIdentityPure(true,true,DEAL_REASON_SL,
                  programmedSl,receipt.programmedSl,price,tolerance,0.0,false);

      long openingCycle=0;
      if(!m_persistence.CycleAt(Idx(dir),openingMsc,openingCycle)||
         openingCycle!=m_persistence.Cycle(Idx(dir)))return false;
      int li=FindLayerByGeneration(dir,generation);double target=0.0;
      if(li>=0)
      {
         SArcsLayer layer;GetLayer(dir,li,layer);
         target=m_dir[Idx(dir)].globalSlArmed&&m_dir[Idx(dir)].globalSlPrice>0
                ?m_dir[Idx(dir)].globalSlPrice:layer.lockTargetPrice;
      }
      bool modifyProof=ticket!=0&&Exec_T14ModifyProofMatches(ticket,(long)RecoveryMagic_,
                            Recovery_CycleKey(dir),programmedSl,tolerance);
      if(!modifyProof)modifyProof=Exec_T14ModifyProofMatches(positionId,(long)RecoveryMagic_,
                            Recovery_CycleKey(dir),programmedSl,tolerance);
      if(target<=0||MathAbs(target-programmedSl)>tolerance)
      {if(!modifyProof)return false;target=programmedSl;}
      return Recovery_ProtectiveSlIdentityPure(true,generation>=1,DEAL_REASON_SL,
                  programmedSl,target,price,tolerance,0.0,modifyProof);
   }

   bool StartupReconcile(CExecutionLayer &exec, string &why)
   {
      why = "";
      if(RecoveryMode_ == recovery_ACTIVE && m_initialized &&
         m_persistLoaded && !m_persistenceBlocked)
      {
         string repairWhy = "";
         if(!RepairProtectiveLayerDecreases(recovery_CORE_BUY, repairWhy) ||
            !RepairProtectiveLayerDecreases(recovery_CORE_SELL, repairWhy))
         {
            why = repairWhy;
            m_ready = false;
            return false;
         }
      }
      return CRecoveryArcsStackBase::StartupReconcile(exec, why);
   }

   void OnTradeTransaction(const MqlTradeTransaction &trans)
   {
      CRecoveryArcsStackBase::OnTradeTransaction(trans);
      if(!m_initialized || RecoveryMode_ != recovery_ACTIVE ||
         trans.type != TRADE_TRANSACTION_DEAL_ADD || trans.deal == 0 ||
         trans.symbol != _Symbol)
         return;
      RefreshClosedGenerationFromDeal(trans);
      string why = "";
      if(m_dirty && !Save(why))
         Log_Error("Recovery", "T16.1 protective-layer persistence failed: " + why);
   }

   void OnTick(const EAContext &ctx)
   {
      if(!m_initialized || RecoveryMode_ == recovery_OFF) return;
      for(int d = 0; d < 2; d++)
      {
         eRecoveryCoreDirection dir = d == 0 ? recovery_CORE_BUY : recovery_CORE_SELL;
         long core = Recovery_ArcsCoreUnits(dir, m_volumeStep);
         long hedge = Recovery_ArcsTotalHedgeUnits(dir, m_volumeStep);
         m_dir[d].lastObservedCoreUnits = core;
         m_dir[d].lastObservedHedgeUnits = hedge;
         if(core <= 0 && hedge <= 0 && m_dir[d].phase == ARCS_REVERSAL_HOLD)
            ResetDirection(dir);
         if(m_dir[d].phase == ARCS_IDLE) ArmFromCore(dir, ctx.now);
         if(RecoveryMode_ == recovery_SHADOW && m_dir[d].phase == ARCS_ARMED && InitialGapHit(dir, ctx))
         {
            long target = Recovery_T16NewGenerationUnitsPure(RecoverySizingPolicy_, core, hedge,
                                                             HedgeVolumePercent_);
            Log_Info("Recovery", "T16 SHADOW " + Recovery_DirectionName(dir) +
                     " would open G1=" + DoubleToString(Recovery_UnitsToVolume(target, m_volumeStep), 2) +
                     " lot at HedgeVolume=" + DoubleToString(HedgeVolumePercent_, 2) + "%");
            m_dir[d].phase = ARCS_ACTIVE;
         }
      }
   }

   bool Drive(CExecutionLayer &exec, const EAContext &ctx, string &why)
   {
      why = "";
      NormalizeStableLockedHold(recovery_CORE_BUY);
      NormalizeStableLockedHold(recovery_CORE_SELL);

      if(EnterProtectiveCloseWait(recovery_CORE_BUY, ctx, why) ||
         HoldProtectiveCloseWait(recovery_CORE_BUY, ctx, why) ||
         ResumeAfterConsumedProtectiveClose(recovery_CORE_BUY, ctx, why))
         return true;
      if(EnterProtectiveCloseWait(recovery_CORE_SELL, ctx, why) ||
         HoldProtectiveCloseWait(recovery_CORE_SELL, ctx, why) ||
         ResumeAfterConsumedProtectiveClose(recovery_CORE_SELL, ctx, why))
         return true;

      bool terminal = CRecoveryArcsStackBase::Drive(exec, ctx, why);
      if(!terminal && why == "TP Hedge ảo chưa đạt") why = "";
      return terminal;
   }
};

#endif // BD_RECOVERY_ARCS_STACK_HARDENED_MQH
