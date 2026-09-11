#!/usr/bin/env python3
"""T18.01 focused model/source regression for runtime hardening."""
from pathlib import Path
import math

ROOT = Path(__file__).resolve().parents[4]
INC = ROOT / "BlackDragon_v14/Include/BlackDragon"
checks = []

def ck(ok, name):
    checks.append((bool(ok), name))
    if not ok:
        print("FAIL:", name)

def money_tp_buffered(profit, target, reserve):
    return target > 0 and math.isfinite(reserve) and reserve >= 0 and profit + 1e-9 >= target + reserve

def reserve_leg(spread, deviation, lots, tick_size, tick_value):
    if lots <= 0:
        return 0.0
    if tick_size <= 0 or tick_value <= 0:
        return math.inf
    move = 2.0 * max(spread, tick_size) + max(deviation, tick_size)
    return move / tick_size * tick_value * lots

def protective_sl(owner, position, reason_sl, programmed, target, deal_price, sl_tol, fill_tol, modify_proof):
    if not owner or not position or not reason_sl:
        return False
    vals = [programmed, target, deal_price, sl_tol, fill_tol]
    if not all(math.isfinite(x) for x in vals):
        return False
    if programmed <= 0 or target <= 0 or deal_price <= 0 or sl_tol < 0 or fill_tol < 0:
        return False
    programmed_match = abs(programmed - target) <= sl_tol + 1e-12
    if modify_proof and not programmed_match:
        return False
    return programmed_match

def flatten_before(cushion_a, ticket_a, cushion_b, ticket_b):
    a_valid = math.isfinite(cushion_a)
    b_valid = math.isfinite(cushion_b)
    if a_valid != b_valid:
        return a_valid
    if not a_valid:
        return ticket_a < ticket_b
    if abs(cushion_a - cushion_b) > 1e-9:
        return cushion_a > cushion_b
    return ticket_a < ticket_b

money = (INC / "MoneyGuard.mqh").read_text(encoding="utf-8")
identity = (INC / "Recovery/RecoveryExecutionIdentity.mqh").read_text(encoding="utf-8")
execution = (INC / "ExecutionLayer.mqh").read_text(encoding="utf-8")
fluid = (INC / "Fluid/FluidRegimeEngine.mqh").read_text(encoding="utf-8")
identity_test = (ROOT / "BlackDragon_v14/Scripts/BlackDragon/Tests/RunRecoveryIdentityTests.mq5").read_text(encoding="utf-8")

# Incident economics: the raw +122.51 trigger must not be interpreted as a
# guaranteed +100 realized result when liquidation reserve is not funded.
ck(122.51 >= 100.0, "incident raw account TP threshold is reached")
ck(not money_tp_buffered(122.51, 100.0, 30.0), "account TP waits when target plus reserve is not funded")
ck(money_tp_buffered(135.0, 100.0, 30.0), "account TP arms after target plus reserve is funded")
ck(not money_tp_buffered(1000.0, 100.0, math.inf), "invalid liquidation economics fail closed for positive TP")
ck(abs(reserve_leg(0.20, 0.10, 1.0, 0.01, 1.0) - 50.0) < 1e-9,
   "liquidation leg reserve formula locks two spreads plus deviation")

# Production source must use the reserve only on positive ACCOUNT TP. SL path
# remains the original immediate floating stop after the TP-reserve branch.
ck("MG_MoneyTpHitBuffered(accountFloating, m_tpAccount, reserve)" in money,
   "production account TP uses buffered admission")
ck("MG_AccountLiquidationReserveCash()" in money and "tpaccreserve" in money,
   "production account TP computes and reports liquidation reserve")
sl_pos = money.find("if(MG_MoneySlHit(accountFloating, m_slAccount))")
tp_pos = money.find("MG_MoneyTpHitBuffered(accountFloating, m_tpAccount, reserve)")
ck(tp_pos >= 0 and sl_pos > tp_pos, "account SL remains immediate independent path after TP reserve")

# Account-wide liquidation must realize current cash cushion first using a
# deterministic policy, while still routing every close through ExecutionLayer.
ck(flatten_before(25.0, 200, -5.0, 100), "positive cushion is ordered before negative")
ck(flatten_before(25.0, 200, 10.0, 100), "larger cushion is ordered first")
ck(flatten_before(10.0, 100, 10.0, 200), "equal cushion uses ticket tie-break")
ck("Recovery_AccountFlattenBeforePure" in identity,
   "pure account flatten comparator is present")
ck("PositionGetDouble(POSITION_PROFIT)" in execution and
   "PositionGetDouble(POSITION_SWAP)" in execution and
   "Recovery_AccountFlattenBeforePure(keyCushion, keyTicket" in execution,
   "CloseAllAccount snapshots cash cushion and sorts deterministically")
ck("ClosePositionEx(tickets[i])" in execution,
   "ordered flatten still routes through ExecutionLayer close primitive")

# Protective-SL incident: fill slippage must not destroy ownership. Programmed
# target identity remains authoritative; MODIFY proof cannot rescue a mismatch.
ck(protective_sl(True, True, True, 4647.318, 4647.318, 4647.340, 0.001, 0.001, False),
   "4647.318 programmed SL with 4647.340 fill remains internal")
ck(not protective_sl(True, True, True, 4647.318, 4647.300, 4647.340, 0.001, 0.001, True),
   "MODIFY proof cannot override moved durable target")
ck(not protective_sl(True, True, True, 4647.318, 4647.300, 4647.340, 0.001, 0.001, False),
   "moved target without proof remains external")
ck("if(confirmedModifyProof && !programmedMatch)" in identity and "return programmedMatch;" in identity,
   "production identity preserves programmed-target authority")
ck("4647.318" in identity_test and "4647.340" in identity_test,
   "native identity suite locks observed incident prices")

# Fluid observability must be present in every enabled mode without changing
# the six-input optimizer surface. BLOCK tokens are composed at runtime by the
# generic logger plus gate-specific callsites, so validate composition instead
# of requiring impossible literal full strings in source.
for token in ["Fluid READY", "Fluid HEARTBEAT", "dcaEvaluated", "pyEvaluated", "rhEvaluated", "counters(eval/block)"]:
    ck(token in fluid, "Fluid telemetry source: " + token)
ck('Print("Fluid ", gate, " BLOCK | dir="' in fluid,
   "Fluid generic block logger composes runtime BLOCK tokens")
for gate in ["DCA", "PY", "RH"]:
    ck(f'Fluid_LogBlock("{gate}"' in fluid,
       f"Fluid {gate} block telemetry wired")
ck("if(FluidMode == 0" not in fluid[fluid.find("Fluid_LogEvidence"):fluid.find("bool Fluid_StrongTransport")],
   "Fluid heartbeat is not limited to SHADOW mode")

fails = [name for ok, name in checks if not ok]
print(f"T18.01 hardening model: {len(checks)-len(fails)} passed, {len(fails)} failed")
if not fails:
    print("HARDENING MODEL GREEN")
raise SystemExit(bool(fails))
