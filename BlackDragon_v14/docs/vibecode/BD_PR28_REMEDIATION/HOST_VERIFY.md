# Host verification — T17.25

Yêu cầu Python 3.10+ và g++ C++17 có UBSan/bounds. Runner không cài dependencies, không chạy MT5 và không gửi lệnh giao dịch.

```bash
python3 BlackDragon_v14/Scripts/BlackDragon/Tests/run_host_gates.py --out /absolute/new/output
```

Chạy từ root source giải nén hoặc checkout. Evidence cuối có 59 groups = 42 C++ model suites + 17 source/validator checks. Production fixtures: cash 30, protection 15, observation 19; persistence 30, ADX 12, accounting 11; outcome 23, ARCS checkpoint 26, campaign 16, oracle 10, ARCS replay 25, execution outcomes 15: tổng 232. Assertion count không thay cho số case native/PRD đã đạt.

M01…M11 inject riêng trên fixture đã trích, không sửa production: unfunded fallthrough, reject cleanup, replay direction, fee, commission ID, retry budget, invalid ADX, receipt undo, early ACK, premature terminal và campaign duplicate. Mutant chỉ tính KILLED nếu compile thành công rồi behavioral assertion fail. 12 fixture tiếp tục qua `-fsanitize=undefined,bounds -fno-sanitize-recover=all`.

`HOST_GATE_RESULTS.json` ghi command/exit code/compiler, source hashes gồm cả `.hpp` adapter; logs và generated fixture sources nằm trong evidence. Portable archive rerun phải có cùng source hash list với lượt final. `repository_contract.py` kiểm include reachability, version parity và enrollment; input/default contract bảo toàn input declaration surface.

Host adapters thay MQL arrays/file/broker APIs bằng C++ seams. Native POD alignment, MetaEditor templates, trade callback ordering, OS atomic replace và broker calculation chưa được chứng minh. Native compile/MT5/backtest/benchmark đều giữ trạng thái riêng. `compare_benchmark_test.py` có 7 synthetic validator tests, không phải 7 native benchmark runs.
