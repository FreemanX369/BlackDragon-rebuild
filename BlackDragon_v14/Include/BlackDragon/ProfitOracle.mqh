#ifndef BD_PROFIT_ORACLE_MQH
#define BD_PROFIT_ORACLE_MQH
// D-205 validation utility. Trading formulas keep their approved semantics.
struct SBDOracleLeg { ENUM_ORDER_TYPE type;double lots,openPrice,signedCosts; };
bool BD_OracleCash(const string symbol,const SBDOracleLeg &legs[],const double price,const double feeReserve,double &cash,string &why)
{
   cash=0;why="";double tick=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE),step=SymbolInfoDouble(symbol,SYMBOL_VOLUME_STEP);
   if(ArraySize(legs)==0||!MathIsValidNumber(price)||price<=0||tick<=0||step<=0||!MathIsValidNumber(feeReserve)||feeReserve<0){why="invalid oracle domain";return false;}
   if(MathAbs(price/tick-MathRound(price/tick))>1e-6){why="price off tick grid";return false;}
   double sum=0;
   for(int i=0;i<ArraySize(legs);i++)
   {
      SBDOracleLeg r=legs[i];double profit=0;
      if((r.type!=ORDER_TYPE_BUY&&r.type!=ORDER_TYPE_SELL)||!MathIsValidNumber(r.lots)||r.lots<=0||!MathIsValidNumber(r.openPrice)||r.openPrice<=0||!MathIsValidNumber(r.signedCosts)||MathAbs(r.lots/step-MathRound(r.lots/step))>1e-6){why="invalid oracle leg";return false;}
      if(!OrderCalcProfit(r.type,symbol,r.lots,r.openPrice,price,profit)||!MathIsValidNumber(profit)){why="OrderCalcProfit unavailable";return false;}
      sum+=profit+r.signedCosts;
   }
   cash=sum-feeReserve;if(!MathIsValidNumber(cash)){cash=0;why="oracle overflow";return false;}return true;
}
bool BD_OracleSolveTicks(const string symbol,const SBDOracleLeg &legs[],const long lowerTick,const long upperTick,const double target,const double feeReserve,long &answer,string &why)
{
   answer=0;why="";double tick=SymbolInfoDouble(symbol,SYMBOL_TRADE_TICK_SIZE);
   if(lowerTick<1||upperTick<lowerTick||upperTick>9007199254740991||!MathIsValidNumber(target)||tick<=0){why="invalid integer bracket";return false;}
   double lowCash=0,highCash=0;
   if(!BD_OracleCash(symbol,legs,lowerTick*tick,feeReserve,lowCash,why)||!BD_OracleCash(symbol,legs,upperTick*tick,feeReserve,highCash,why))return false;
   if(MathAbs(highCash-lowCash)<1e-12){why="flat/unproven monotonic oracle";return false;}
   bool up=highCash>lowCash;
   if(target<MathMin(lowCash,highCash)||target>MathMax(lowCash,highCash)){why="target outside bracket";return false;}
   long lo=lowerTick,hi=upperTick;
   for(int iter=0;lo<hi&&iter<54;iter++)
   {
      long mid=up?lo+(hi-lo)/2:lo+(hi-lo+1)/2;double value=0;
      if(!BD_OracleCash(symbol,legs,mid*tick,feeReserve,value,why))return false;
      if(value<MathMin(lowCash,highCash)-1e-8||value>MathMax(lowCash,highCash)+1e-8){why="non-monotonic oracle bracket";return false;}
      if(up){if(value>=target){hi=mid;highCash=value;}else{lo=mid+1;lowCash=value;}}
      else{if(value>=target){lo=mid;lowCash=value;}else{hi=mid-1;highCash=value;}}
   }
   if(lo!=hi){why="oracle iteration budget";return false;}
   double result=0;if(!BD_OracleCash(symbol,legs,lo*tick,feeReserve,result,why)||result<target-1e-8){why="oracle target verification";return false;}
   answer=lo;return true;
}
#endif
