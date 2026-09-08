#property strict
#property version "1.00"
int actions=0;
int OnInit(){if(!MQLInfoInteger(MQL_TESTER))return INIT_FAILED;return INIT_SUCCEEDED;}
void OnTick(){
 if(actions>=8)return;
 MqlTradeRequest r={};MqlTradeResult x={};r.action=TRADE_ACTION_DEAL;r.symbol=_Symbol;r.magic=817260908;r.volume=0.01;r.deviation=100;r.type_filling=ORDER_FILLING_IOC;
 if(PositionSelect(_Symbol)){r.position=PositionGetInteger(POSITION_TICKET);r.type=ORDER_TYPE_SELL;r.price=SymbolInfoDouble(_Symbol,SYMBOL_BID);}else{r.type=ORDER_TYPE_BUY;r.price=SymbolInfoDouble(_Symbol,SYMBOL_ASK);}
 bool ok=OrderSend(r,x);PrintFormat("PROBE_ORDER ok=%d ret=%u",(int)ok,x.retcode);actions++;
}
bool Selected(ulong target){for(int i=0;i<HistoryDealsTotal();i++)if(HistoryDealGetTicket(i)==target)return true;return false;}
void OnTradeTransaction(const MqlTradeTransaction &t,const MqlTradeRequest &r,const MqlTradeResult &x){
 if(t.type!=TRADE_TRANSACTION_DEAL_ADD||t.deal==0||!HistoryDealSelect(t.deal))return;
 long ms=HistoryDealGetInteger(t.deal,DEAL_TIME_MSC);datetime now=TimeCurrent();
 bool a=HistorySelect(0,now);bool foundA=Selected(t.deal);int n=HistoryDealsTotal();
 bool b=HistorySelect(0,now+1);bool foundB=Selected(t.deal);
 PrintFormat("NATIVE_HISTORY_BOUNDARY deal=%I64u ms=%I64d now=%I64d offset=%I64d old_ok=%d old_found=%d old_n=%d plus1_ok=%d plus1_found=%d",t.deal,ms,(long)now,ms-(long)now*1000,(int)a,(int)foundA,n,(int)b,(int)foundB);
}
