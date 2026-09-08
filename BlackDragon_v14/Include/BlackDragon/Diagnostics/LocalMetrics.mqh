#ifndef BD_LOCAL_METRICS_MQH
#define BD_LOCAL_METRICS_MQH
// Opt in with #define BD_DIAGNOSTICS before the EA includes. No input changes,
// per-tick logging, network telemetry, account IDs or raw trades are recorded.
#ifndef BD_BUILD_ID
#define BD_BUILD_ID "unbound"
#endif
enum eBDMetric {BD_M_TICK,BD_M_TIMER,BD_M_TRANSACTION,BD_M_SIGNAL,BD_M_BASKET,BD_M_PROTECTION,BD_M_RECOVERY,BD_M_STRATEGY,BD_M_EXECUTOR,BD_M_POSITION_VISIT,BD_M_HISTORY_VISIT,BD_M_HISTORY_SELECT,BD_M_HISTORY_POSITION,BD_M_SORT_ITEMS,BD_M_ALLOC_BYTES,BD_M_ALLOC_REQUESTS,BD_M_POSITION_REFRESH,BD_M_PERSIST_BYTES,BD_M_SEND,BD_M_REJECT,BD_M_RECONCILE,BD_M_POSITION_TOTAL_CALL,BD_M_PERSIST_IO_US,BD_M_COUNT};
class CBDLocalMetrics
{
private:
   ulong m_count[BD_M_COUNT],m_hist[9][64],m_total[9],m_max[9];
public:
   CBDLocalMetrics(){ZeroMemory(m_count);ZeroMemory(m_hist);ZeroMemory(m_total);ZeroMemory(m_max);}
   void Add(const int key,const ulong n=1)
   {
#ifdef BD_DIAGNOSTICS
      if(key>=0&&key<BD_M_COUNT)m_count[key]+=n;
#endif
   }
   void Finish(const int key,const ulong micros)
   {
#ifdef BD_DIAGNOSTICS
      if(key<0||key>8)return;Add(key);int b=0;ulong v=micros;
      while(v>1&&b<63){v>>=1;b++;}m_hist[key][b]++;m_total[key]+=micros;if(micros>m_max[key])m_max[key]=micros;
#endif
   }
   void Flush()
   {
#ifdef BD_DIAGNOSTICS
      string path="BD_METRICS_"+BD_BUILD_ID+"_"+(string)GetTickCount64()+".csv";
      int f=FileOpen(path,FILE_WRITE|FILE_CSV|FILE_ANSI,',');if(f==INVALID_HANDLE)return;
      FileWrite(f,"build","kind","key","bucket","value");
      for(int k=0;k<BD_M_COUNT;k++)FileWrite(f,BD_BUILD_ID,"counter",k,0,m_count[k]);
      for(int k=0;k<9;k++)
      {
         FileWrite(f,BD_BUILD_ID,"total_us",k,0,m_total[k]);FileWrite(f,BD_BUILD_ID,"max_us",k,0,m_max[k]);
         for(int b=0;b<64;b++)FileWrite(f,BD_BUILD_ID,"hist_us_log2",k,b,m_hist[k][b]);
      }
      FileFlush(f);FileClose(f);
#endif
   }
};
CBDLocalMetrics g_bdMetrics;
class CBDMetricScope
{
private:int m_key;ulong m_start;
public:
   CBDMetricScope(const int key):m_key(key),m_start(0)
   {
#ifdef BD_DIAGNOSTICS
      m_start=GetMicrosecondCount();
#endif
   }
   ~CBDMetricScope()
   {
#ifdef BD_DIAGNOSTICS
      g_bdMetrics.Finish(m_key,GetMicrosecondCount()-m_start);
#endif
   }
};
#ifdef BD_DIAGNOSTICS
int BD_DiagPositionsTotal(){g_bdMetrics.Add(BD_M_POSITION_TOTAL_CALL);return PositionsTotal();}
ulong BD_DiagPositionTicket(const int i){g_bdMetrics.Add(BD_M_POSITION_VISIT);return PositionGetTicket(i);}
ulong BD_DiagHistoryTicket(const int i){g_bdMetrics.Add(BD_M_HISTORY_VISIT);return HistoryDealGetTicket(i);}
bool BD_DiagHistorySelect(const datetime a,const datetime b){g_bdMetrics.Add(BD_M_HISTORY_SELECT);return HistorySelect(a,b);}
bool BD_DiagHistoryPosition(const ulong id){g_bdMetrics.Add(BD_M_HISTORY_POSITION);return HistorySelectByPosition(id);}
bool BD_DiagPositionSelect(const ulong ticket){g_bdMetrics.Add(BD_M_POSITION_REFRESH);return PositionSelectByTicket(ticket);}
bool BD_DiagSend(MqlTradeRequest &r,MqlTradeResult &s){g_bdMetrics.Add(BD_M_SEND);bool ok=OrderSend(r,s);if(!ok||(s.retcode!=TRADE_RETCODE_DONE&&s.retcode!=TRADE_RETCODE_DONE_PARTIAL&&s.retcode!=TRADE_RETCODE_PLACED))g_bdMetrics.Add(BD_M_REJECT);return ok;}
bool BD_DiagSendAsync(MqlTradeRequest &r,MqlTradeResult &s){g_bdMetrics.Add(BD_M_SEND);bool ok=OrderSendAsync(r,s);if(!ok||s.retcode!=TRADE_RETCODE_PLACED)g_bdMetrics.Add(BD_M_REJECT);return ok;}
template<typename T>
int BD_DiagArrayResize(T &values[],const int size,const int reserve=0)
{g_bdMetrics.Add(BD_M_ALLOC_REQUESTS);if(size>0)g_bdMetrics.Add(BD_M_ALLOC_BYTES,(ulong)size*sizeof(T));return ArrayResize(values,size,reserve);}
template<typename T>
uint BD_DiagWriteStruct(const int file,const T &value,const int size=-1)
{ulong start=GetMicrosecondCount();uint bytes=FileWriteStruct(file,value,size);g_bdMetrics.Add(BD_M_PERSIST_IO_US,GetMicrosecondCount()-start);g_bdMetrics.Add(BD_M_PERSIST_BYTES,bytes);return bytes;}
uint BD_DiagWriteLong(const int file,const long value)
{ulong start=GetMicrosecondCount();uint bytes=FileWriteLong(file,value);g_bdMetrics.Add(BD_M_PERSIST_IO_US,GetMicrosecondCount()-start);g_bdMetrics.Add(BD_M_PERSIST_BYTES,bytes);return bytes;}
void BD_DiagFlush(const int file)
{ulong start=GetMicrosecondCount();FileFlush(file);g_bdMetrics.Add(BD_M_PERSIST_IO_US,GetMicrosecondCount()-start);}
bool BD_DiagMove(const string source,const int common,const string target,const int flags)
{ulong start=GetMicrosecondCount();bool ok=FileMove(source,common,target,flags);g_bdMetrics.Add(BD_M_PERSIST_IO_US,GetMicrosecondCount()-start);return ok;}
template<typename T>
bool BD_DiagArraySort(T &values[])
{g_bdMetrics.Add(BD_M_SORT_ITEMS,(ulong)ArraySize(values));return ArraySort(values);}
// Logical requested bytes do not claim physical heap allocation size.
#define PositionsTotal BD_DiagPositionsTotal
#define ArrayResize BD_DiagArrayResize
#define ArraySort BD_DiagArraySort
#define FileWriteStruct BD_DiagWriteStruct
#define FileWriteLong BD_DiagWriteLong
#define FileFlush BD_DiagFlush
#define FileMove BD_DiagMove
#define PositionSelectByTicket BD_DiagPositionSelect
#define PositionGetTicket BD_DiagPositionTicket
#define HistoryDealGetTicket BD_DiagHistoryTicket
#define HistorySelect BD_DiagHistorySelect
#define HistorySelectByPosition BD_DiagHistoryPosition
#define OrderSend BD_DiagSend
#define OrderSendAsync BD_DiagSendAsync
#endif
#endif
