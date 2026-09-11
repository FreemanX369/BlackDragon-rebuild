#!/usr/bin/env python3
"""T18.00 tick-fluid wiring/source contract.

This is intentionally a source contract, not a profitability claim. It protects
integration boundaries while MetaEditor/runtime tests provide behavioral evidence.
"""
from pathlib import Path
import re

R = Path(__file__).resolve().parents[4]
I = R / 'BlackDragon_v14/Include/BlackDragon'
checks = []

def ck(ok, name):
    checks.append((bool(ok), name))

def rd(path):
    return (I / path).read_text(encoding='utf-8')

engine = rd('Fluid/FluidRegimeEngine.mqh')
signal = rd('SignalEngine.mqh')
filters = rd('EntryFilters.mqh')
dca = rd('Recovery/RecoveryDcaT1713.mqh')
rh = rd('Recovery/RecoveryArcsStackT177HedgeLadder.mqh')
c4 = rd('Recovery/RecoveryArcsStackT177HedgeLadderC4Base.mqh')

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

# No direct martingale/hedge coverage mutation in the MVP.
for forbidden in ['HedgeCoverage','LotMultiplier','Martingale','Lots=','OrderLots']:
    ck(forbidden not in engine, 'no adaptive economics in T18 MVP: ' + forbidden)

for ok, name in checks:
    if not ok:
        print('FAIL:', name)
print(f'T18.00 Fluid source contract: {sum(ok for ok,_ in checks)} passed, {sum(not ok for ok,_ in checks)} failed')
if all(ok for ok,_ in checks):
    print('SOURCE CONTRACT GREEN')
raise SystemExit(not all(ok for ok,_ in checks))
