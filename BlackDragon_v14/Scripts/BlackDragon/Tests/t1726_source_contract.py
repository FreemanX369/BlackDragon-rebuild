#!/usr/bin/env python3
"""Supplementary T17.26 wiring/input contract; actual behavior is tested separately."""
from pathlib import Path
import json,re
R=Path(__file__).resolve().parents[4];I=R/'BlackDragon_v14/Include/BlackDragon';D=R/'BlackDragon_v14/docs/vibecode/T17_26_protective_sl';checks=[]
def ck(ok,name):checks.append((bool(ok),name))
def rd(x):return (I/x).read_text()
def body(s,sig):
 a=s.index(sig);i=s.index('{',a)+1;d=1
 while d:d+=(s[i]=='{')-(s[i]=='}');i+=1
 return s[a:i]
baseline=json.loads((D/'BASELINE_INPUTS.json').read_text())
for f in baseline['files']:
 ck(re.findall(r'^\s*input\s+(?!group\b)[^;]+;',(R/f['path']).read_text(),re.M)==f['inputs'],'unchanged inputs: '+f['path'])
contract=json.loads((D/'AI-BUILD-CONTRACT.json').read_text())
ck('User approved implementation' in contract['authorization'] and not contract['release_eligible'],'implementation authority without release promotion')
hard=rd('Recovery/RecoveryArcsStackHardened.mqh');identity=rd('Recovery/RecoveryExecutionIdentity.mqh');ledger=rd('Recovery/RecoveryArcsLedger.mqh');stack=rd('Recovery/RecoveryArcsStack.mqh');dca=rd('Recovery/RecoveryDca.mqh')
classifier=body(hard,'bool ExpectedBrokerSlDeal(');pure=body(identity,'bool Recovery_ProtectiveSlIdentityPure(');repair=body(hard,'bool RepairProtectiveLayerDecreases(');remember=body(hard,'bool RememberProtectiveSl(')
ck('SYMBOL_SPREAD' not in classifier and 'dealPrice - durableTargetSl' not in pure,'ownership independent of spread and fill-distance')
ck('return programmedMatch;' in pure and 'MathIsValidNumber' in pure,'exact valid SL identity cannot be overridden by generic proof boolean')
ck('ExpectedBrokerSlDeal(d.deal)' in body(hard,'bool IsExpectedPersistedProtectiveClose('),'repair uses shared classifier')
ck('ExpectedBrokerSlDeal(deal)' in rd('Recovery/RecoveryArcsStackT1719Reentry.mqh'),'terminal broker reentry uses same classifier')
ck(all(x in classifier for x in ['DEAL_SYMBOL','DEAL_ENTRY','DEAL_REASON_SL','openingType','openingMsc','receipt.positionId==positionId','receipt.dir==Idx(dir)','CycleAt']),'exact close/opening/receipt/campaign scope')
ck('OC_RhMatchesCycle' in body(hard,'bool RecoveryPositionIdentity('),'opening comment cycle validated')
ck('HedgeSLMode_!=SL_BROKER &&' in repair and 'receipt.protectiveSl||receipt.pyTrim' in repair,'broker repair uses receipts rather than high-water exclusion; virtual policy retained')
ck(repair.index('RememberProtectiveSl(protectiveDeals[k],why)')<repair.index('layer.remainingUnits = live;'),'receipt and actual cash precede topology')
ck('ReconcileReceipt(deal,false,true,why)' in remember and 'm_persistenceBlocked=true' in remember,'partial receipt failure blocks checkpoint commit')
ck('GetLayer(dir,li,layer); // ReconcileReceipt' in repair,'topology write preserves freshly settled cash')
ck('r.programmedSl=HistoryDealGetDouble(deal,DEAL_SL)' in stack and 'closeReason==DEAL_REASON_SL' in stack,'correction retains proof only for same programmed SL/reason')
ck('BD_ReceiptEqual(old,next)' in stack and 'ApplyReceiptEffect(old,-1,why)' in stack,'duplicates and inverse corrections retained')
ck('struct SBDArcsReceiptV1' in ledger and '17250002,2' in ledger and 'want.version=1' in ledger,'v2 writer and validated v1 reader')
ck('ZeroMemory(m_receipts[i])' in ledger and 'cannot invent a protective-SL proof' in ledger,'migration does not promote old receipts')
ck('BD_AtomicCommit' in ledger and 'BD_AtomicOpen' in ledger,'proof and cash/state share atomic checkpoint')
ck('HistoryDealGetDouble(deal,DEAL_PROFIT),HistoryDealGetDouble(deal,DEAL_SWAP),HistoryDealGetDouble(deal,DEAL_COMMISSION),HistoryDealGetDouble(deal,DEAL_FEE)' in stack,'actual cash includes all deal costs')
ck('RefreshVirtualGenerationFromDeal(trans)' in hard and 'if(target<=0)return false;' in body(hard,'bool IsExpectedPersistedProtectiveClose('),'virtual callback and intent guard preserved')
ck('TesterStop();' in dca and 'm_seenReady=true' in dca and 'runtime?"RUNTIME":"INIT"' in dca,'fail-closed stop retained with accurate lifecycle label')
ck('GetLastError' not in body(rd('Logger.mqh'),'void Log_Error('),'business error does not append ambient API code')
coord=rd('Recovery/RecoveryExitCoordinatorT177Base.mqh');ck('int apiError=GetLastError();' in coord and 'classifier=UNPROVEN_EXTERNAL' in coord,'callback diagnostics include local API error and classifier context')
wf=(R/'.github/workflows/verify-current.yml').read_text();runner=(R/'BlackDragon_v14/Scripts/BlackDragon/Tests/run_host_gates.py').read_text()
ck('RunT1726ProtectiveSlTests' in wf and 't1726_source_contract.py' in wf and 't1726_integration.py' in runner,'host and native checks enrolled')
for ok,name in checks:
 if not ok:print('FAIL:',name)
print(f'T17.26 source contract: {sum(ok for ok,n in checks)} passed, {sum(not ok for ok,n in checks)} failed')
if all(ok for ok,n in checks):print('SOURCE CONTRACT GREEN')
raise SystemExit(not all(ok for ok,n in checks))
