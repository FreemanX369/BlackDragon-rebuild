#!/usr/bin/env python3
"""T18.01 tick-fluid wiring + hardening source contract.

This protects integration boundaries and enrolls focused model/A-B harness tests.
MetaEditor/native/runtime evidence remains the authority for executable behavior.
"""
from pathlib import Path
import re
import subprocess
import sys

R = Path(__file__).resolve().parents[4]
I = R / 'BlackDragon_v14/Include/BlackDragon'
T = R / 'BlackDragon_v14/Scripts/BlackDragon/Tests'
checks = []

def ck(ok, name):
    checks.append((bool(ok), name))

def rd(path):
    return (I / path).read_text(encoding='utf-8')

def run_script(path, *args):
    p = subprocess.run([sys.executable, str(path), *args], cwd=R,
                       text=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    print(p.stdout, end='')
    return p.returncode, p.stdout

engine = rd('Fluid/FluidRegimeEngine.mqh')
signal = rd('SignalEngine.mqh')
filters = rd('EntryFilters.mqh')
dca = rd('Recovery/RecoveryDcaT1713.mqh')
rh = rd('Recovery/RecoveryArcsStackT177HedgeLadder.mqh')
c4 = rd('Recovery/RecoveryArcsStackT177HedgeLadderC4Base.mqh')
money = rd('MoneyGuard.mqh')
identity = rd('Recovery/RecoveryExecutionIdentity.mqh')
identity_test = (T / 'RunRecoveryIdentityTests.mq5').read_text(encoding='utf-8')

# Safe-by-default / optimizer surface.
ck(re.search(r'input\s+bool\s+UseFluidRegime\s*=\s*false\s*;', engine),
   'Fluid is disabled by default')
ck(re.search(r'input\s+int\s+FluidMode\s*=\s*0\s*;', engine),
   'Fluid default mode is SHADOW')
for name in ['FluidFastWindow','FluidSlowWindow','FluidReThreshold','FluidCriticalThreshold']:
    ck(re.search(r'input\s+[^;]*\b' + name + r'\b', engine), 'input exists: ' + name)

# Data contract: native current MqlTick only. No DOM, no Python, no external feed.
ck('SymbolInfoTick(_Symbol, tick)' in engine and 'MqlTick tick;' in engine,
   'native MqlTick acquisition')
ck('tick.volume_real' in engine and 'tick.volume' in engine,
   'native real/tick volume hierarchy')
for forbidden in ['MarketBookAdd','MarketBookGet','OnBookEvent','WebRequest','CopyTicksRange','Python']:
    ck(forbidden not in engine, 'no external/DOM dependency: ' + forbidden)

# Engine must stay decision-only; no order mutation primitives are allowed here.
for forbidden in ['OrderSend','CTrade','OpenMarket','PositionClose','PositionModify','EXEC_CMD_']:
    ck(forbidden not in engine, 'engine sends no orders: ' + forbidden)

# Tick state updates before legacy signal publication, but legacy signal equations remain present.
ck('#include "Fluid/FluidRegimeEngine.mqh"' in signal and 'Fluid_UpdateCurrentTick();' in signal,
   'SignalEngine observes every strategy tick')
ck('CopyBuffer(m_hRsi, 0, 1, 1, rsiBuf)' in signal and
   'if((d >= Up_Level   || !Use_Stoh) && flagBD == -1)' in signal and
   'if((d <= Down_Level || !Use_Stoh) && flagBD ==  1)' in signal,
   'legacy RSI/Stoch entry signal unchanged')

# DCA gate: additional admission only, before Recovery state logic.
ck('#include "../Fluid/FluidRegimeEngine.mqh"' in dca and
   'if(!Fluid_AllowDca(dir))' in dca and
   dca.index('if(!Fluid_AllowDca(dir))') < dca.index('if(RecoveryMode_ != recovery_ACTIVE)'),
   'Core DCA receives additive Fluid gate')

# PY gate: new-series chain remains the hook; seed is fail-open without same-side Core exposure.
ck('#include "Fluid/FluidRegimeEngine.mqh"' in filters and
   'return Fluid_AllowNewSeriesChain(dir);' in filters,
   'new-series/PY chain reads Fluid admission')
ck('if(!Fluid_HasCoreExposure(dir)) return true;' in engine and
   'return Fluid_AllowPyramid(dir);' in engine,
   'fresh Seed stays legacy; existing Core side may gate PY ADD')

# RH: verified C4Base stays Fluid-free. Wrapper gates only later children.
ck('Fluid' not in c4, 'verified C4Base remains Fluid-free')
ck('g_t18RhInitialChild = (live <= 0);' in rh and
   'Fluid_AllowRecoveryHedge(bdHedgeDir, initialChild)' in rh,
   'generation-local live units distinguish first/later RH child')
ck('if(initialChild) return true;' in engine,
   'first RH child is never blocked')
ck('if(!contextMatches) return true;' in rh,
   'unexpected RH wrapper context fails open to T17 behavior')
ck('#define Recovery_ArcsLayerUnits Recovery_T18ArcsLayerUnits' in rh and
   '#define Recovery_OneOrderPerBarAllows Recovery_T18OneOrderPerBarAllows' in rh,
   'C4Base interception is narrow and local')

# Mode semantics: OFF/SHADOW/warmup fail-open; progressive gates only.
ck('if(!UseFluidRegime || FluidMode < 1 || !Fluid_Ready()) return true;' in engine,
   'DCA OFF/SHADOW/warmup fail-open')
ck('if(!UseFluidRegime || FluidMode < 2 || !Fluid_Ready()) return true;' in engine,
   'PY OFF/SHADOW/warmup fail-open')
ck('if(!UseFluidRegime || FluidMode < 3 || !Fluid_Ready()) return true;' in engine,
   'RH child OFF/SHADOW/warmup fail-open')

# T18.01 observability in all enabled modes.
for token in ['Fluid READY','Fluid HEARTBEAT','Fluid DCA BLOCK','Fluid PY BLOCK','Fluid RH BLOCK',
              'dcaEvaluated','dcaBlocked','pyEvaluated','pyBlocked','rhEvaluated','rhBlocked']:
    ck(token in engine, 'runtime evidence token: ' + token)
ck('if(FluidMode == 0 && Fluid_Ready()' not in engine,
   'heartbeat no longer restricted to SHADOW')

# MoneyGuard hardening: positive account TP reserves liquidation cost while
# account loss-stop remains an independent immediate branch.
ck('MG_AccountLiquidationReserveCash()' in money and
   'MG_MoneyTpHitBuffered(accountFloating, m_tpAccount, reserve)' in money,
   'account Money TP requires liquidation reserve')
ck('if(MG_MoneySlHit(accountFloating, m_slAccount))' in money,
   'account Money SL remains immediate')
ck('Money TP All account WAIT' in money and 'tpaccreserve' in money,
   'account TP reserve wait is observable')

# Protective-SL identity: fill slippage cannot override immutable identity;
# exact MODIFY proof may recover a moved durable target, but wrong owner/reason
# remains fail-closed in the native suite.
ck('return programmedMatch || confirmedModifyProof;' in identity,
   'protective SL accepts exact target or exact MODIFY proof')
ck('4647.318' in identity_test and '4647.340' in identity_test and
   'moved target without proof remains external' in identity_test,
   'native identity suite locks observed incident and negative control')

# No direct martingale/hedge coverage mutation in the Fluid engine.
for forbidden in ['HedgeCoverage','LotMultiplier','Martingale','Lots=','OrderLots']:
    ck(forbidden not in engine, 'no adaptive economics in T18 MVP: ' + forbidden)

# Focused executable Python regressions are enrolled through this canonical
# source-contract entry point, so repository policy still has one workflow.
model_rc, model_out = run_script(T / 't1801_hardening_model.py')
ck(model_rc == 0 and 'HARDENING MODEL GREEN' in model_out,
   'T18.01 hardening model green')
ab_rc, ab_out = run_script(T / 't1801_ab_matrix.py', '--self-test')
ck(ab_rc == 0 and '5 variants PASS' in ab_out,
   'T18.01 A/B set+evidence harness self-test green')

for ok, name in checks:
    if not ok:
        print('FAIL:', name)
print(f'T18.01 Fluid/hardening source contract: {sum(ok for ok,_ in checks)} passed, {sum(not ok for ok,_ in checks)} failed')
if all(ok for ok,_ in checks):
    print('SOURCE CONTRACT GREEN')
raise SystemExit(not all(ok for ok,_ in checks))
