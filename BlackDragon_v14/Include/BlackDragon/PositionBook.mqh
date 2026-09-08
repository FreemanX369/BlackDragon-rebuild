#ifndef BD_POSITION_BOOK_MQH
#define BD_POSITION_BOOK_MQH
#include <BlackDragon/Diagnostics/LocalMetrics.mqh>
#include "Recovery/RecoveryMath.mqh"
#include "OrderCommentCodec.mqh"
// Immutable observation within Begin/End. A mutation must reselect live ID,
// volume and broker constraints. A failed capture is never published.
struct SBDPositionRecord
{
   ulong ticket,id;
   long owner,units;
   datetime openTime;
   int dir,role,generation; // actual direction; role 0=Seed/DCA, 1=PY, 2=RH
   double lots,openPrice,sl,tp,profit,swap;
};
struct SBDPositionAggregate
{
   long key,units;
   int count;
   double lots,weightedNumerator,floatingCash;
};
class CObservationPositionBook
{
private:
   bool m_enabled,m_indexValid;
   string m_symbol;
   long m_coreMagic,m_hedgeMagic;
   double m_step;
   long m_coreUnits[2],m_hedgeUnits[2];
   int m_triggerCount[2],m_count;
   SBDPositionRecord m_rows[];
   SBDPositionAggregate m_aggregates[];
   int m_ids[],m_order[],m_work[];
   ulong m_scans,m_visits,m_hits,m_revision,m_sequence;
   long ScopeKey(const int role,const int dir,const int generation)const
   {return ((long)role*2+dir)*4294967296+(long)MathMax(generation,0);}
   int ScopeAt(const long key)const
   {int lo=0,hi=ArraySize(m_aggregates);while(lo<hi){int m=lo+(hi-lo)/2;if(m_aggregates[m].key<key)lo=m+1;else hi=m;}return lo;}
   bool Accumulate(const SBDPositionRecord &r)
   {
      long key=ScopeKey(r.role,r.dir,r.generation);int at=ScopeAt(key),n=ArraySize(m_aggregates);
      if(at==n||m_aggregates[at].key!=key)
      {
         if(ArrayResize(m_aggregates,n+1,16)!=n+1)return false;
         for(int i=n;i>at;i--)m_aggregates[i]=m_aggregates[i-1];
         ZeroMemory(m_aggregates[at]);m_aggregates[at].key=key;
      }
      m_aggregates[at].count++;m_aggregates[at].units+=r.units;m_aggregates[at].lots+=r.lots;
      m_aggregates[at].weightedNumerator+=r.openPrice*r.lots;m_aggregates[at].floatingCash+=r.profit+r.swap;return true;
   }
   bool Less(const int a,const int b,const bool byId)const
   {
      if(byId)return m_rows[a].id<m_rows[b].id;
      return m_rows[a].openTime<m_rows[b].openTime||(m_rows[a].openTime==m_rows[b].openTime&&m_rows[a].ticket<m_rows[b].ticket);
   }
   bool Index(int &index[],const bool byId)
   {
      if(ArrayResize(index,m_count,64)!=m_count||ArrayResize(m_work,m_count,64)!=m_count)return false;
      g_bdMetrics.Add(BD_M_SORT_ITEMS,(ulong)m_count);
      for(int i=0;i<m_count;i++)index[i]=i;
      for(int w=1;w<m_count;w*=2)
      {
         for(int left=0;left<m_count;left+=2*w)
         {
            int mid=(int)MathMin(left+w,m_count),end=(int)MathMin(left+2*w,m_count),a=left,b=mid;
            for(int k=left;k<end;k++)m_work[k]=a<mid&&(b>=end||Less(index[a],index[b],byId))?index[a++]:index[b++];
         }
         for(int i=0;i<m_count;i++)index[i]=m_work[i];
      }
      return true;
   }
public:
   CObservationPositionBook():m_enabled(false),m_indexValid(false),m_symbol(""),m_coreMagic(0),m_hedgeMagic(0),m_step(0),m_count(0),m_scans(0),m_visits(0),m_hits(0),m_revision(0),m_sequence(0){}
   void End(){m_enabled=false;}
   void Invalidate(){m_enabled=false;m_revision++;}
   bool Begin(const string symbol,const long coreMagic,const long hedgeMagic,const double step)
   {
      m_enabled=false;m_symbol=symbol;m_coreMagic=coreMagic;m_hedgeMagic=hedgeMagic;m_step=step;m_sequence++;
      if(!MathIsValidNumber(step)||step<=0||coreMagic<=0)return false;
      for(int d=0;d<2;d++){m_coreUnits[d]=0;m_hedgeUnits[d]=0;m_triggerCount[d]=0;}
      int total=PositionsTotal(),n=0;m_scans++;bool changed=!m_indexValid||m_count==0;m_indexValid=false;ArrayResize(m_aggregates,0);
      // One enumeration detects missed callbacks and unchanged-count volume
      // changes. Storage is reused; ordering rebuilds only when its key changes.
      if(ArraySize(m_rows)<total&&ArrayResize(m_rows,total,64)!=total)return false;
      for(int i=total-1;i>=0;i--)
      {
         ulong ticket=PositionGetTicket(i);m_visits++;if(ticket==0)return false;
         if(PositionGetString(POSITION_SYMBOL)!=symbol)continue;
         long owner=PositionGetInteger(POSITION_MAGIC);if(owner!=coreMagic&&owner!=hedgeMagic)continue;
         long type=PositionGetInteger(POSITION_TYPE);if(type!=POSITION_TYPE_BUY&&type!=POSITION_TYPE_SELL)return false;
         SBDPositionRecord r;ZeroMemory(r);r.ticket=ticket;r.id=(ulong)PositionGetInteger(POSITION_IDENTIFIER);r.owner=owner;
         r.openTime=(datetime)PositionGetInteger(POSITION_TIME);r.dir=type==POSITION_TYPE_BUY?0:1;
         string comment=PositionGetString(POSITION_COMMENT);r.role=owner==hedgeMagic?2:(OC_IsPyramid(comment)?1:0);r.generation=r.role==2?OC_RhGeneration(comment):0;
         r.lots=PositionGetDouble(POSITION_VOLUME);r.openPrice=PositionGetDouble(POSITION_PRICE_OPEN);r.sl=PositionGetDouble(POSITION_SL);r.tp=PositionGetDouble(POSITION_TP);r.profit=PositionGetDouble(POSITION_PROFIT);r.swap=PositionGetDouble(POSITION_SWAP);
         if(r.id==0||!MathIsValidNumber(r.lots)||r.lots<=0||!MathIsValidNumber(r.openPrice)||r.openPrice<=0||!MathIsValidNumber(r.sl)||!MathIsValidNumber(r.tp)||!MathIsValidNumber(r.profit)||!MathIsValidNumber(r.swap))return false;
         r.units=Recovery_VolumeToUnitsFloor(r.lots,step);
         if(n>=m_count||m_rows[n].id!=r.id||m_rows[n].ticket!=r.ticket||m_rows[n].openTime!=r.openTime)changed=true;
         m_rows[n++]=r;if(!Accumulate(r))return false;
         if(r.role!=2){m_coreUnits[r.dir]+=r.units;if(r.role==0&&r.units>0)m_triggerCount[r.dir]++;}else m_hedgeUnits[1-r.dir]+=r.units;
      }
      if(PositionsTotal()!=total)return false;changed=changed||m_count!=n;m_count=n;
      if(changed&&(!Index(m_ids,true)||!Index(m_order,false)))return false;
      for(int i=1;i<n;i++)if(m_rows[m_ids[i-1]].id==m_rows[m_ids[i]].id)return false;
      m_enabled=true;m_indexValid=true;return true;
   }
   bool Matches(const string symbol,const long coreMagic,const long hedgeMagic,const double step)const
   {return m_enabled&&symbol==m_symbol&&coreMagic==m_coreMagic&&hedgeMagic==m_hedgeMagic&&MathAbs(step-m_step)<1e-12;}
   bool ById(const ulong id,SBDPositionRecord &r)
   {if(!m_enabled)return false;int lo=0,hi=m_count;while(lo<hi){int m=lo+(hi-lo)/2;if(m_rows[m_ids[m]].id<id)lo=m+1;else hi=m;}if(lo>=m_count||m_rows[m_ids[lo]].id!=id)return false;r=m_rows[m_ids[lo]];m_hits++;return true;}
   bool OrderedAt(const int i,SBDPositionRecord &r)
   {if(!m_enabled||i<0||i>=m_count)return false;r=m_rows[m_order[i]];m_hits++;return true;}
   bool HasUnknownGeneration()const
   {for(int i=0;i<m_count;i++)if(m_rows[i].role==2&&m_rows[i].generation<1)return true;return false;}
   bool Aggregate(const int role,const int dir,const int generation,SBDPositionAggregate &out)
   {ZeroMemory(out);if(!m_enabled||role<0||role>2||dir<0||dir>1)return false;long key=ScopeKey(role,dir,generation);int i=ScopeAt(key);if(i<ArraySize(m_aggregates)&&m_aggregates[i].key==key)out=m_aggregates[i];m_hits++;return true;}
   long LayerUnits(const int coreDir,const int generation)
   {SBDPositionAggregate out;return Aggregate(2,1-coreDir,generation,out)?out.units:0;}
   int Count()const{return m_enabled?m_count:0;}
   long CoreUnits(const int d){m_hits++;return d>=0&&d<2?m_coreUnits[d]:0;}
   long HedgeUnits(const int d){m_hits++;return d>=0&&d<2?m_hedgeUnits[d]:0;}
   int CoreCount(const int d){m_hits++;return d>=0&&d<2?m_triggerCount[d]:0;}
   ulong Scans()const{return m_scans;}ulong Visits()const{return m_visits;}ulong Hits()const{return m_hits;}
   ulong Revision()const{return m_revision;}ulong Sequence()const{return m_sequence;}
};
CObservationPositionBook g_bdObservationBook;
#endif
