#ifndef BD_CAMPAIGN_LEDGER_MQH
#define BD_CAMPAIGN_LEDGER_MQH
// History bootstrap is restricted to restart/new campaign or a reasoned
// invalidation. Normal deal callbacks update this exact-ID cache in memory.
struct SBDCampaignDeal
{
   ulong deal,id;
   long stamp,owner,entry;
   datetime time;
   int dir,level;
   bool pyramid,deleted;
   double price,cash;
};
class CCampaignLedger
{
private:
   SBDCampaignDeal m_deals[];
   ulong m_owners[];
   SPyramidCampaignStats m_stats;
   int m_dir;
   long m_start,m_levelStamp;
   ulong m_revision,m_levelDeal,m_bootstraps,m_deltas,m_reductions;
   datetime m_retry;
   string m_reason;
   int Find(const ulong deal)const
   {int lo=0,hi=ArraySize(m_deals);while(lo<hi){int m=lo+(hi-lo)/2;if(m_deals[m].deal<deal)lo=m+1;else hi=m;}return lo<ArraySize(m_deals)&&m_deals[lo].deal==deal?lo:-1;}
   int OwnerAt(const ulong id)const
   {int lo=0,hi=ArraySize(m_owners);while(lo<hi){int m=lo+(hi-lo)/2;if(m_owners[m]<id)lo=m+1;else hi=m;}return lo;}
   bool Owned(const ulong id)const
   {int i=OwnerAt(id);return i<ArraySize(m_owners)&&m_owners[i]==id;}
   bool Opening(const SBDCampaignDeal &r)const
   {return !r.deleted&&r.owner==(long)Magic&&r.pyramid&&r.dir==m_dir&&r.stamp>=m_start&&(r.entry==DEAL_ENTRY_IN||r.entry==DEAL_ENTRY_INOUT);}
   bool ReadDeal(const ulong deal,SBDCampaignDeal &r)
   {
      ZeroMemory(r);r.deal=deal;
      if(!HistoryDealSelect(deal))return false;
      if(HistoryDealGetString(deal,DEAL_SYMBOL)!=_Symbol){r.deleted=true;return true;}
      r.id=(ulong)HistoryDealGetInteger(deal,DEAL_POSITION_ID);r.stamp=HistoryDealGetInteger(deal,DEAL_TIME_MSC);
      r.time=(datetime)HistoryDealGetInteger(deal,DEAL_TIME);if(r.stamp<=0)r.stamp=(long)r.time*1000;
      r.owner=HistoryDealGetInteger(deal,DEAL_MAGIC);r.entry=HistoryDealGetInteger(deal,DEAL_ENTRY);
      string c=HistoryDealGetString(deal,DEAL_COMMENT);r.pyramid=Pyramid_IsComment(c);r.dir=Pyramid_CommentFieldInt(c,"D=");r.level=Pyramid_LevelFromComment(c);
      r.price=HistoryDealGetDouble(deal,DEAL_PRICE);
      r.cash=HistoryDealGetDouble(deal,DEAL_PROFIT)+HistoryDealGetDouble(deal,DEAL_SWAP)+HistoryDealGetDouble(deal,DEAL_COMMISSION)+HistoryDealGetDouble(deal,DEAL_FEE);
      if(r.stamp<m_start||r.id==0)r.deleted=true;
      return MathIsValidNumber(r.price)&&MathIsValidNumber(r.cash)&&(!Opening(r)||r.level>0);
   }
   bool Put(const SBDCampaignDeal &r)
   {
      int at=Find(r.deal);if(at>=0){m_deals[at]=r;return true;}if(r.deleted)return true;
      int n=ArraySize(m_deals);if(n>=65536||ArrayResize(m_deals,n+1,128)!=n+1)return false;
      at=n;while(at>0&&m_deals[at-1].deal>r.deal){m_deals[at]=m_deals[at-1];at--;}m_deals[at]=r;return true;
   }
   void AddCash(const SBDCampaignDeal &r)
   {
      if(r.deleted||!Owned(r.id))return;m_stats.realizedCash+=r.cash;
      if(r.entry==DEAL_ENTRY_OUT||r.entry==DEAL_ENTRY_OUT_BY||r.entry==DEAL_ENTRY_INOUT)
      {
         m_stats.exitDeals++;
         if(Pyramid_LaterDeal(r.stamp,r.deal,m_stats.lastExitTimeMsc,m_stats.lastExitDeal))
         {m_stats.lastExitTimeMsc=r.stamp;m_stats.lastExitTime=r.time;m_stats.lastExitDeal=r.deal;m_stats.lastExitPrice=r.price;}
         Pyramid_RecordMutation(m_stats,r.stamp,r.time,r.deal,true);
      }
   }
   bool Reduce()
   {
      m_reductions++;Pyramid_CampaignReset(m_stats);ArrayResize(m_owners,0);m_levelStamp=0;m_levelDeal=0;
      for(int i=0;i<ArraySize(m_deals);i++)
      {
         SBDCampaignDeal r=m_deals[i];if(!Opening(r))continue;if(r.level<=0)return false;
         int at=OwnerAt(r.id),n=ArraySize(m_owners);
         if(at==n||m_owners[at]!=r.id)
         {if(ArrayResize(m_owners,n+1,64)!=n+1)return false;for(int j=n;j>at;j--)m_owners[j]=m_owners[j-1];m_owners[at]=r.id;m_stats.addCount++;}
         if(Pyramid_LaterDeal(r.stamp,r.deal,m_stats.lastAddTimeMsc,m_stats.lastAddDeal))
         {m_stats.lastAddTimeMsc=r.stamp;m_stats.lastAddTime=r.time;m_stats.lastAddDeal=r.deal;}
         Pyramid_RecordMutation(m_stats,r.stamp,r.time,r.deal,false);
         if(r.level>m_stats.highestLevel||(r.level==m_stats.highestLevel&&Pyramid_LaterDeal(r.stamp,r.deal,m_levelStamp,m_levelDeal)))
         {m_stats.highestLevel=r.level;m_stats.lastSerialEntryPrice=r.price;m_levelStamp=r.stamp;m_levelDeal=r.deal;}
      }
      for(int i=0;i<ArraySize(m_deals);i++)AddCash(m_deals[i]);m_stats.ready=true;return true;
   }
   bool Bootstrap(const datetime now)
   {
      m_bootstraps++;ArrayResize(m_deals,0);ArrayResize(m_owners,0);
      if(!HistorySelect((datetime)(m_start/1000),now+1))return false;
      int n=HistoryDealsTotal();ulong ids[];if(ArrayResize(ids,n)!=n)return false;
      for(int i=0;i<n;i++){ids[i]=HistoryDealGetTicket(i);if(ids[i]==0)return false;}
      for(int i=0;i<n;i++){SBDCampaignDeal r;if(!ReadDeal(ids[i],r)||!Put(r))return false;}
      return Reduce();
   }
public:
   CCampaignLedger():m_dir(-1),m_start(0),m_levelStamp(0),m_revision(0),m_levelDeal(0),m_bootstraps(0),m_deltas(0),m_reductions(0),m_retry(0),m_reason(""){Pyramid_CampaignReset(m_stats);}
   void Reset(){m_start=0;m_dir=-1;m_retry=0;ArrayResize(m_deals,0);ArrayResize(m_owners,0);Pyramid_CampaignReset(m_stats);}
   bool Read(const int dir,const long start,const datetime now,const ulong revision,SPyramidCampaignStats &out)
   {
      if(dir<0||dir>1||start<=0||now<=0){Pyramid_CampaignReset(out);return false;}
      if(m_dir!=dir||m_start!=start){Reset();m_dir=dir;m_start=start;m_reason="new campaign/restart";}
      if(m_stats.ready&&revision==m_revision){out=m_stats;return true;}
      if(now<m_retry){Pyramid_CampaignReset(out);return false;}
      if(m_stats.ready&&revision!=m_revision)m_reason="missing event revision";
      m_retry=now+1;bool ok=Bootstrap(now);m_revision=revision;
      if(!ok){m_stats.ready=false;m_reason="history unavailable/capacity";}else m_retry=0;
      out=m_stats;return ok;
   }
   void Observe(const MqlTradeTransaction &tx,const ulong revision)
   {
      if(m_start<=0)return;
      if(!m_stats.ready||revision!=m_revision+1){m_stats.ready=false;m_reason="event gap";return;}
      m_revision=revision;int at=Find(tx.deal);SBDCampaignDeal r;
      if(tx.type==TRADE_TRANSACTION_DEAL_DELETE){if(at<0)return;r=m_deals[at];r.deleted=true;}
      else if(!ReadDeal(tx.deal,r)){m_stats.ready=false;m_reason="deal unavailable";return;}
      bool fast=at<0&&!Opening(r)&&!r.deleted&&Owned(r.id);
      if(!Put(r)){m_stats.ready=false;m_reason="campaign capacity";return;}
      // Close can arrive before its opening callback: hydrate that exact ID.
      if(at<0&&!r.deleted&&!Owned(r.id)&&!Opening(r)&&(r.entry==DEAL_ENTRY_OUT||r.entry==DEAL_ENTRY_OUT_BY))
      {
         if(!HistorySelectByPosition(r.id)){m_stats.ready=false;m_reason="opening owner unavailable";return;}
         int n=HistoryDealsTotal();ulong ids[];if(ArrayResize(ids,n)!=n){m_stats.ready=false;return;}
         for(int i=0;i<n;i++)ids[i]=HistoryDealGetTicket(i);
         for(int i=0;i<n;i++){SBDCampaignDeal related;if(ids[i]==0||!ReadDeal(ids[i],related)||!Put(related)){m_stats.ready=false;return;}}
      }
      m_deltas++;if(fast)AddCash(r);else if(!Reduce()){m_stats.ready=false;m_reason="invalid reduction";}
   }
   ulong Bootstraps()const{return m_bootstraps;}ulong Deltas()const{return m_deltas;}
   ulong Reductions()const{return m_reductions;}string Reason()const{return m_reason;}
};
CCampaignLedger g_bdCampaignLedger[2];
void Pyramid_ObserveCampaignTransaction(const MqlTradeTransaction &tx)
{for(int d=0;d<2;d++)g_bdCampaignLedger[d].Observe(tx,g_pyramidDealRevision);}
#endif
