#!/usr/bin/env python3
"""T17.25 wiring invariants, supplementary to executable production fixtures."""
from pathlib import Path
import re,sys
R=Path(__file__).resolve().parents[4];I=R/'BlackDragon_v14/Include/BlackDragon';checks=[]
def rd(x):return (I/x).read_text()
def ck(ok,name):checks.append((bool(ok),name))
e=rd('ExecutionLayer.mqh');p=rd('Pyramid/PyramidProtection.mqh');s=rd('OperationResultStore.mqh');a=rd('Recovery/RecoveryArcsStack.mqh');l=rd('Recovery/RecoveryArcsLedger.mqh');b=rd('PositionBook.mqh');c=rd('Pyramid/CampaignLedger.mqh');m=rd('Diagnostics/LocalMetrics.mqh');o=rd('ProfitOracle.mqh');ea=(R/'BlackDragon_v14/Experts/BlackDragon/BlackDragon.mq5').read_text()
ck(all(x in s for x in ['groupSerial','actualDirection','r.owner>0','r.id>0','r.nonce>0']),'operation scope includes stable ID, nonce, serial and actual direction')
segment=e[e.index('if(IsProtectedCommand(meta.commandType))'):e.index('// Async path: fire and journal')]
ck(segment.index('PersistOutcome(j,BD_OUT_INTENT)')<segment.index('OrderSendAsync(req,res)'),'intent persisted before transport')
ck('m_records[drop].state==BD_OUT_SETTLED' in s and 'r.nonce<=m_retired' in s and 'n>=512' in s,'bounded settled-only retention and replay watermark')
ck('if(!m_ok)return false;' in s and '!m_outcomes.Healthy()' in e,'failed snapshot cannot ACK RAM or admit risk')
ck('OutcomeConsumed' in p and 'if(m_fault' in p and 'if(!Save())' in p,'consumer durability/fault boundary retained')
ck('LoadFlatCheckpoint' in p and 'm_nonce==0' in p,'flat OFF permits saved consumption watermark')
ck('CompactRetiredRhOperations' in p and 'ReceiptsDurable()' in p and 'coreStartDeal!=m_group' in p,'RH proof retires only outside campaign after durable receipts')
ck('if(known&&!ApplyReceiptEffect(old,-1,why))return false;' in a and 'if(!ApplyReceiptEffect(next,1,why))return false;' in a,'correction is undo then apply with error propagation')
ck('BD_ReceiptEqual(old,next)' in a and 'r.suppressed=old.suppressed' in a,'duplicate and coordinator-suppressed receipts preserved')
ck('r.adjustBaseline=old.adjustBaseline' in a and 'if(r.adjustBaseline)' in a,'original RH baseline classification survives corrections')
ck('m_persistenceBlocked=true' in a and 'funding phase proof unavailable/ambiguous' in a,'unknown funding proof cannot silently guess')
ck('ScannedThrough' in a and '-300' in l and 'm_overlapAt=ctx.now+30' in a,'reasoned periodic overlap uses scan watermark')
ck(all(x in l for x in ['BD_ArcsPayloadValid','BD_AtomicCommit','m_meta.migrated=true','m_meta.floorMsc','n>=65536']),'atomic ledger, migration and bounded coverage')
ck('bool ById' in b and 'ScopeAt' in b and 'weightedNumerator' in b and 'm_indexValid' in b,'position identity/scope/order indexes and aggregates')
ck(ea.index('g_bdObservationBook.End()')<ea.index('g_strategy.OnTick(ctx)'),'snapshot ends before strategy mutations')
ck('Pyramid_ObserveCampaignTransaction(trans)' in ea and 'g_bdCampaignLedger[dir].Read' in rd('Pyramid/CorePyramid.mqh'),'OFF/ON campaign event integration')
ck('revision!=m_revision+1' in c and 'now<m_retry' in c and 'if(fast)AddCash(r)' in c,'incremental campaign, gap invalidation and bounded retry')
ck('HistorySelectByPosition(r.id)' in c and c.index('ids[i]=HistoryDealGetTicket(i)')<c.index('ReadDeal(ids[i]'),'history IDs frozen before nested selection')
ck('#define BD_DIAGNOSTICS' not in ea and '#ifdef BD_DIAGNOSTICS' in m and 'WebRequest' not in m,'local diagnostics default OFF and no network')
ck(all(x in m for x in ['#define PositionsTotal BD_DiagPositionsTotal','#define FileWriteLong BD_DiagWriteLong','#define FileFlush BD_DiagFlush','#define FileMove BD_DiagMove','BD_M_PERSIST_IO_US']),'whole-EA pool and persistence I/O wrappers enrolled')
ck(all(x in ea for x in ['BD_M_TICK','BD_M_TIMER','BD_M_TRANSACTION','BD_M_PROTECTION','BD_M_RECOVERY','BD_M_EXECUTOR']),'handler and subsystem timing wired')
ck('OrderCalcProfit' in o and 'feeReserve<0' in o and 'iter<54' in o and 'non-monotonic oracle' in o,'validation-only cash oracle and integer bounded solver')
ck('BD_OracleSolveTicks' not in a and 'BD_OracleSolveTicks' not in p,'D205 does not silently alter trading formulas')
wf=(R/'.github/workflows/verify-current.yml').read_text();ck('RunT1725Modules' in wf and 't1725_source_contract.py' in wf,'new native and source gates enrolled')
for name in ['OperationResultStore.mqh','Recovery/RecoveryArcsLedger.mqh','PositionBook.mqh','Pyramid/CampaignLedger.mqh','ProfitOracle.mqh','Diagnostics/LocalMetrics.mqh']:
 ck(not re.search(r'^#if\s',rd(name),re.M),'MQL preprocessor uses supported conditionals: '+name)
fails=[n for ok,n in checks if not ok];print(f'T17.25 source contract: {len(checks)-len(fails)} passed, {len(fails)} failed')
for name in fails:print('FAIL:',name)
if fails:sys.exit(1)
print('SOURCE CONTRACT GREEN')
