# Paired native benchmark input

Không có native benchmark trong gói. B1 correctness-only chưa qualified; phải khóa B1 trước khi dùng comparator kết luận. BENCHMARK_PLAN.json giữ D-206 budgets ở PROPOSED_NOT_MEASURED.

`compare_benchmark.py` nhận JSON `{ "runs": [...] }`, tối thiểu 5 pairs, mỗi pair có một B1 và một C. Mỗi run cần các fields sau; paths tương đối dưới thư mục JSON, files phải tồn tại và khớp SHA-256. B1/C trong mỗi pair phải cùng environment/set/data/profile/model/warmup/start/end và trace hash.

```json
{
  "pair": 1, "variant": "C", "build": "actual-source-build-id",
  "environment": "controlled-host-and-mt5-build-id",
  "set_sha256": "actual-hash", "data_sha256": "actual-hash",
  "profile_sha256": "actual-hash", "model": "real-ticks",
  "warmup": "declared-protocol", "start": "actual-start", "end": "actual-end",
  "actual_end": "actual-end", "completed": true,
  "wall_seconds": 123.4, "memory_peak_bytes": 12345678,
  "metrics_path": "pair1/C.csv", "metrics_sha256": "actual-hash",
  "trace_path": "pair1/C.trace", "trace_sha256": "actual-hash"
}
```

Giá trị trên chỉ minh họa schema, không phải kết quả đo. Chuẩn hóa trace bằng protocol cố định từ trước; giữ ordered intents, IDs/scopes, units/cash và rounding tolerance đã duyệt, không bỏ khác biệt sau khi thấy fail. Report thiếu end-date/hash hoặc khác trace bị INVALID.

```bash
python3 BlackDragon_v14/Scripts/BlackDragon/Tests/compare_benchmark.py native-pairs.json --out paired-result.json
```

Kết quả gồm median/min/max/spread wall time/memory, các cặp percentile intervals và position visit reduction. Noisy wall-time spread >10% trả INCONCLUSIVE; input hợp lệ khác trả MEASURED_NOT_QUALIFIED. Nó không tự xác minh native provenance/B1 correctness hoặc approve budgets; verifier vẫn phải kiểm các gate này riêng. Log2 latency buckets thường không đủ phân giải 5%.

Metric keys: 0 Tick; 1 Timer; 2 Transaction; 3 Signal; 4 Basket; 5 Protection; 6 Recovery; 7 Strategy; 8 Executor; 9 Position visits; 10 History visits; 11 HistorySelect calls; 12 HistorySelectByPosition calls; 13 sort items; 14 logical allocation bytes; 15 allocation requests; 16 selected-position refreshes; 17 state bytes written; 18 sends; 19 transport rejects; 20 ARCS reconcile entries; 21 PositionsTotal calls; 22 persistence write/flush/move microseconds. Counter scopes phải được giữ giống nhau trong B1 và C.
