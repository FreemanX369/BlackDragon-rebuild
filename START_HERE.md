# T17.26 incident fix — 2026-09-08

This package fixes the audited v15.03 / T17.26 baseline. It is not a replacement for a separately developed T17.27 branch. Forward-port the small production patch when combining branches; do not overwrite later source.

Read BlackDragon_v14/docs/vibecode/T1726_INCIDENT_20260908/EA-SPEC.yaml, DECISIONS.yaml and VERIFICATION.json. The older governance files describe historical builds.

Changes: extend protective HistorySelect horizon to TimeCurrent()+1; include bounded mismatch diagnostics; preserve DCA runtime readiness and first TesterStop cause. No inputs, cash rules, receipt schema or exact-proof predicate changed.

Build entry: BlackDragon_v14/Experts/BlackDragon/BlackDragon.mq5. Copy Include/Experts/Scripts into a dedicated MT5 MQL5 tree and compile with MetaEditor. The runtime banner remains v15.03; use the supplied source/EX5 hashes to distinguish this patch.

Host regression:
python3 BlackDragon_v14/Scripts/BlackDragon/Tests/t1726_integration.py --out build-incident
python3 BlackDragon_v14/Scripts/BlackDragon/Tests/t1726_source_contract.py

Native history probe (tester only): Scripts/BlackDragon/Tests/HistoryBoundaryProbe20260908.mq5 is an EA-style probe. Copy it to a tester Experts location; it refuses non-tester init, performs eight isolated test transactions and compares both history endpoints.

Native full EA result: BT-20260908-083024-AAB184, XAUUSDm M1 real ticks, 150ms, 10000 USD, 1:1000, 2026.08.26 to 2026.09.08. Last tick 2026.09.07 23:59:58. No TesterStop/stop-out/mismatch. Inputs matched 150/150 from INCIDENT.set. Real6 differs from original Real38; no live eligibility.

The compiled EX5 exists on Tunnel in the job directory. Current bridge exposes text artifacts only, so this archive does not contain a downloaded EX5. Do not reuse the earlier pre-fix binary.
