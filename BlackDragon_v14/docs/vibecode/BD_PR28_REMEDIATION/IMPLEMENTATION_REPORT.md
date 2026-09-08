# Completion report — v15.02 / T17.25

## Kết luận source và giới hạn nghiệm thu

Phạm vi source đã duyệt được triển khai và host-verify; full PRD acceptance vẫn false vì thiếu native compile/runtime, B1 benchmark qualification và independent audit. Cùng một agent đảm nhiệm BUILDER rồi VERIFIER; self-review không phải independent reviewer.

Baseline audit B0: `d3b5ce19cfdde52b9cb49fe14f1b50915fd0604d`. Baseline triển khai upstream: `40c424cfa71b6742414b012e9d67d3294003f38e`, tree `ce4749ef21409b599f54e195826780dad3c25b4e`. Checkpoint local trước T17.25: `b02d7eeb4a0b9e0a3f0ac23e488cbf0fb94c5d3f`. Candidate HEAD/tree cuối nằm trong package MANIFEST.json để tránh tự tham chiếu hash trong commit. Remote branch được kiểm lại khi bàn giao, không có upstream drift so với baseline triển khai.

| Requirement | Implementation | Source (relative to Include/BlackDragon unless stated) | Acceptance còn lại |
|---|---|---|---|
| R-001 — Provenance / authority | PR branch rechecked at 40c424cf; full candidate tree, input surface and source/test hashes bound in delivery manifest. | `BASELINE_SOURCE.json; BUILD_AUTHORITY.json; package MANIFEST.json` | Exact native artifact correlation remains Q43. |
| R-002 — Pre-arm exposure | Preserves upstream WAIT_UNFUNDED guard; no arm/modify before funding; positive progression, final live checks and trim obligations retained. | `Pyramid/PyramidProtection.mqh; Pyramid/PyramidProtectionPolicy.mqh` | Native BUY/SELL, actual RH trim, monotone floor under ADD/partial. |
| R-003 — Durable async outcomes | Scoped durable INTENT before send; pending/unknown/applied/partial/no-effect/settled lifecycle; terminal retained until durable consumer ACK; live order and immutable-ID checks; restart restoration. | `OperationResultStore.mqh; ExecutionLayer.mqh; Pyramid/PyramidProtection.mqh` | Native callback permutations, crash boundary and broker request/partial-fill behavior. |
| R-004 — Replay and correction | Exact receipt dedup, direction-first replay, bounded overlap, scan watermark, timestamp/deal merge sort, UPDATE/DELETE undo+apply, historic funding classification and atomic cash/receipt checkpoint. | `Recovery/RecoveryArcsLedger.mqh; Recovery/RecoveryArcsStack.mqh` | Native crash/late callbacks; missing or ambiguous historical phase goes to reconciliation. |
| R-005 — Commission identity / validity | History by POSITION_IDENTIFIER, missing history remains invalid, bounded retry restores readiness without a new topology event. | `BasketManager.mqh` | Native ticket rollover and broker history availability. |
| R-006 — Daily cash | Shared booking-day reducer includes profit/swap/commission/fee, exact opening ownership, entry fees, correction and rollover; floating avoids double booking. | `CashLedger.mqh; BasketManager.mqh; Recovery/RecoveryT165GuardScope.mqh` | Native Core/Recovery parity and broker fee attribution. |
| R-007 — Daily denominator | D-202 scoped denominator preserved; host external-deposit, restart and rollover cases. | `StrategyT176Base.mqh; Recovery/RecoveryT165GuardScope.mqh` | This is not exact midnight account balance; native scope parity pending. |
| R-008 — PositionBook | Immutable decision observation with ID index, role/direction/generation aggregates, stable order index, live cash refresh, revision/validity and explicit scope end. | `PositionBook.mqh; Recovery/RecoveryArcsBook.mqh` | One whole-account capture per Recovery decision remains; native missed-event/final mutation freshness qualification. |
| R-009 — Incremental campaign | Sorted exact deal/owner cache; ordinary owned exit uses delta; corrections reduce cached records; history bootstrap only for initialization, campaign change, revision gap or recovery. OFF mode integrated. | `Pyramid/CampaignLedger.mqh; Pyramid/CorePyramid.mqh` | Native callback-order/history stress and behavior trace. |
| R-010 — Streaming aggregates | Sum/count uses scoped aggregates; saturation no longer builds/sorts Core book; ordered consumers retain time/ticket ordering. | `PositionBook.mqh; Recovery/RecoveryArcsBook.mqh; Recovery/RecoveryArcsStack.mqh` | Native LIFO/oldest/threshold parity and scan counts. |
| R-011 — Bounded persistence | Atomic validated payloads, settled-prefix outcome compaction, receipt/epoch retention floors, RH tombstone retirement only after durable receipt proof, PY v1/v2 and flat OFF watermark loading. | `Diagnostics/AtomicSnapshot.mqh; OperationResultStore.mqh; Recovery/RecoveryArcsLedger.mqh; Pyramid/PyramidProtection.mqh` | Native MQL POD layout, atomic replace/crash, active-state migration and rollback qualification. |
| R-012 — Retry scheduler | Persisted 1/2/4/8/16/30 second deadlines; 8 definitive rejects reconcile while retaining obligation. Unknown outcomes never become no-effect from timeout. | `Pyramid/PyramidProtection.mqh` | Native server clock, restart and emergency exit liveness. |
| R-013 — Local diagnostics | Default-OFF handler/subsystem histograms and counters for pool calls, visits, selection, sort items, logical allocation requests, state bytes/I/O time, transport and reconciliation. No network or per-tick logging. | `Diagnostics/LocalMetrics.mqh; Experts/BlackDragon/BlackDragon.mq5` | Native wrapper compile and actual measurements; histograms return intervals, allocation bytes are logical requests. |
| R-014 — Controlled benchmark | Paired native-export validator checks five pairs, hashes, environment/set/data/profile/model/warmup/end date, trace equality and noise; reports medians/spreads and latency intervals. | `Scripts/BlackDragon/Tests/compare_benchmark.py; BENCHMARK_PLAN.json` | B1 is not natively qualified/frozen. No native benchmark, 50% scan gain or 5% latency claim; D-206 budget remains proposed. |
| R-015 — ADX validity | Inherited fail-closed policy retained; rejects invalid handle, absent buffer, NaN, infinity and EMPTY_VALUE. | `Filters/AdxFilter.mqh` | Native initialization/warmup and exit liveness. |
| R-016 — Profit oracle | Validation-only OrderCalcProfit cash oracle with explicit costs/reserve and bounded integer-tick bisection; BUY/SELL, bracket, monotonicity and failure guards. | `ProfitOracle.mqh; Scripts/BlackDragon/Tests/RunT1725Modules.mq5` | Broker account-currency proof pending. Runtime SL/funding formula replacement remains conditional under D-205. |
| R-017 — Phased composition | State/cache/persistence concerns extracted behind existing compatibility interfaces. Full inheritance teardown is deliberately conditional on a qualified native trace. | `PositionBook.mqh; CashLedger.mqh; Pyramid/CampaignLedger.mqh; OperationResultStore.mqh; Recovery/RecoveryArcsLedger.mqh` | Native differential trace required before removing further wrappers; full teardown is not claimed. |
| R-018 — Delivery / re-audit | Full source, patch, docs, reproducible host runner and exact-tree package evidence. Same agent performed builder and verifier roles; no independent-human audit claim. | `HOST_VERIFY.md; TEST_EXECUTION.json; RETRO_REVIEW.md; package MANIFEST.json` | Native compile delegated to owner, independent audit and native acceptance remain open. |

## Thuật toán đã áp dụng

| Thành phần | Cách xử lý và độ phức tạp | Giới hạn thực tế |
|---|---|---|
| Outcome store | Sorted nonce + exact ID, binary lookup; atomic snapshot, settled-prefix compaction | Tối đa 512; pending/unknown/unconsumed pin retention; đầy hoặc I/O lỗi chặn admission và giữ nghĩa vụ |
| ARCS receipts | Exact deal-ID binary search; O(n log n) merge sort theo timestamp/deal; undo-old/apply-new | Insert và checkpoint O(n); 65.536 records/epochs, retire cycle cũ với coverage floor; ngoài proof reconcile |
| PositionBook | Capture O(P), ID/order/scope indexes; binary queries và aggregate count/units/weighted numerator | Một account enumeration cho mỗi Recovery decision; sorted-array index build O(P log P); giữ live validation trước mutation |
| Campaign history | Normal owned exit áp cash delta; correction/ownership change reduce cached records O(D) RAM | Full broker history chỉ bootstrap/reasoned rebuild; capacity 65.536, thiếu history không coi là zero |
| Retry | Deadline scheduler O(1) theo obligation, không Sleep | 1/2/4/8/16/30s, cap 8 reject; UNKNOWN không retry theo timeout |
| Profit oracle | Integer-tick bisection tối đa 54 vòng với bracket/monotonicity | Validation only; mỗi bước dùng OrderCalcProfit cho các legs, không đổi runtime funding/SL |
| Diagnostics | Fixed 64-bin log2 histogram; counters trong RAM, xuất CSV ở deinit | Default OFF; percentile là khoảng bucket; requested allocation bytes không phải heap usage |

Không đưa ML/ONNX/Kalman/adaptive entry vào phạm vi này. Sorted arrays được chọn theo PRD; chưa có benchmark chứng minh cần hash/tree phức tạp hơn. Các wrappers T17 cũ còn reachable vẫn là compatibility layers, không phải EA khác.

## Event order đã giữ

| Handler | Thứ tự source hiện tại | Freshness / persistence boundary |
|---|---|---|
| OnTick | Build context → signal/WMF → Basket update → PY observe → PositionBook begin → Recovery tick → PositionBook end → Strategy tick | Snapshot chỉ sống trong lượt Recovery; policy/executor giữ emergency priority và final live checks bên trong module |
| OnTimer | News → executor watchdog → Recovery flush → exit coordinator → mobile nếu được cấu hình → day rollover/save | Không tạo worker thread; pending outcome không bị timeout thành no-effect |
| OnTradeTransaction | Invalidate observation → campaign/revision → executor → PY → exit coordinator/Recovery receipts → day-cash observation | Exact deal/ID dedup; suppression ghi receipt; cash và marker checkpoint cùng payload |

## Bằng chứng và giới hạn

59/59 regression groups; 232 production-body assertions (64 + 53 + 115); 11/11 mutations killed; 12/12 UBSan/bounds fixtures. Production MQL methods được trích vào C++ với API seam/file system mô phỏng; không phải native MQL compile. Native 34 scripts chỉ enrolled; runbook có lệnh compile. Q01…Q56 là acceptance matrix riêng, nhiều case vẫn native pending.

B1 correctness-only chưa được qualify bằng native. Source optimizations được bàn giao để owner compile theo lệnh tiếp tục full source; thứ tự acceptance B1→C vẫn bắt buộc trước claim performance. Không sử dụng B0 hoặc host runtime làm số liệu speedup. Bộ comparator từ chối dữ liệu thiếu/khác trace và chỉ trả MEASURED_NOT_QUALIFIED hoặc INCONCLUSIVE khi dữ liệu hợp lệ.

Migration pre-existing legacy state, phase chuyển cùng millisecond, broker corrections sau proof retention và mọi native crash boundary là các tình huống cần kiểm thử riêng. Khi không xác định được phase/ownership, source yêu cầu reconcile thay vì đoán funding. Xem NATIVE_BUILD_RUNBOOK.md.
