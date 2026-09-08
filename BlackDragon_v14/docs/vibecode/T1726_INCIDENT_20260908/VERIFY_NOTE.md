# Verification

222/222 production-method host checks pass, including six callback orders, partial TP funding, retained G1 and active G2, duplicate/correction/delete accounting and checkpoint reload. These are host transport seams, not a full native crash matrix.

234 source-contract checks pass (T17.13/14/23/25/26). Reverting the history endpoint kills the mutation with 27 failing checks. Native isolated probe sees 7/8 deals absent from the old endpoint and 8/8 visible with +1 second.

Native full EA: 0 errors / 0 warnings, job BT-20260908-083024-AAB184. Last actual tick 2026.09.07 23:59:58; 150 inputs match. No TesterStop, stop-out, protective mismatch or reconcile-required event. One nonfatal broker modify rejection 10016 for #28 was handled by retaining state; position was later market-closed. No claim of zero broker rejections.

Exact uploaded EX5 hash was not supplied for the original incident. Real6/6182 replay is not exact Real38/5320 parity. No native 35-suite rerun or full native restart matrix is claimed for this patch.

Diagnostic baseline replay BT-20260908-082203-636956 was intentionally cancelled after passing the original incident time without reproduction. Its persisted bridge state still says TESTING with cancel_requested=true; do not classify it as completed-period PASS. Fixed replay above completed independently.

API basis: https://www.mql5.com/en/docs/trading/historyselect and https://www.mql5.com/en/docs/dateandtime/timecurrent describe history ranges and last-known server time. Actual omission/repair claim is grounded in the included native probe, not inferred only from documentation.
