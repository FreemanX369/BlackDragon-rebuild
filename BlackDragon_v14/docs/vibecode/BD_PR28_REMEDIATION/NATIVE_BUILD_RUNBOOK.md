# Native build / verification — v15.02 / T17.25

Owner đã chọn nhận full ZIP và tự compile. Linux host không có MetaEditor/MT5/PowerShell runtime; script dưới đây chưa được chạy trên Windows trong lượt bàn giao.

## Compile

Giải nén vào thư mục kiểm thử riêng, không cần Git hoặc áp patch. `RepositoryRoot` là thư mục chứa `BlackDragon_v14`. OutputDirectory phải chưa tồn tại. Script không cài phần mềm, đăng nhập account, chạy EA hoặc bật trading.

```powershell
.\BlackDragon_v14\Scripts\BlackDragon\Tests\BuildCandidate.ps1 `
  -RepositoryRoot 'C:\work\BD-ea-remake' `
  -MetaEditor 'C:\Program Files\MetaTrader 5\metaeditor64.exe' `
  -OutputDirectory 'C:\work\bd-t1725-native-build'
```

Script tạo staging, chuyển UTF-8 sang UTF-16LE BOM, hash source trước/sau, compile ProbeEA + 34 native scripts + EA. Mọi log phải mới, Result 0 errors/0 warnings và EX5 không rỗng. Thành công tạo `BlackDragon.ex5`, compile logs, SOURCE_MANIFEST.json và BUILD_MANIFEST.json. ZIP không có .git thì Git fields là null; hash source vẫn bắt buộc. Lỗi compiler phải tạo candidate sửa mới, không dùng binary cũ.

Chạy 34 scripts theo `.github/workflows/verify-current.yml`, đối chiếu từng expected count. RunT1724CashLedgerTests kỳ vọng 30/0; RunT1725Modules kỳ vọng 13/0. Probe T17.25 bật diagnostic wrappers, kiểm volatile outcome store, native POD snapshot và OrderCalcProfit tại giá mở (không gửi trade); đây không phải full async integration harness.

## Native acceptance bổ sung

Chạy TEST_MATRIX.json Q01…Q56 đúng tier. Đặc biệt: actual partial fill trước/sau REQUEST/DONE; duplicate/late REQUEST/DEAL/ORDER; request timeout và restart; ticket đổi nhưng ID giữ nguyên; terminal chưa ACK; crash trước/sau intent Save, send, receipt Save và consumer ACK; invalid history hồi phục; phase transition trùng millisecond; coordinator suppression; RH trim không tạo Core credit; BUY/SELL và OFF/VIRTUAL/BROKER; day rollover/external cash; emergency exits trong WAIT/reconcile. Strategy Tester sync fallback không chứng minh async broker lifecycle. Không tự bật demo/live từ runbook này.

Gửi lại toolchain/probe log, source manifest, 35 compile logs (EA + 34 scripts), 34 runtime logs, EX5 hashes/bytes, broker profile/.set/dataset/model/date-completion, native trace/restart/crash evidence. Nếu từ Actions, thêm repo/head/tree/run ID/attempt/numeric job ID/Windows runner/artifact hashes. Không kèm secret.

## State migration và rollback

Sao lưu toàn bộ file state theo account/symbol/CoreMagic/RecoveryMagic trước thử bằng terminal riêng. PY writer vẫn dùng disk v2, reader hỗ trợ v1; retry deadline/budget và nonce watermark phải tồn tại sau reload. OFF chỉ chấp nhận checkpoint thực sự flat, không pending/cash/reconcile; active/corrupt state không bị bỏ qua chỉ vì đổi mode.

ARCS thêm checkpoint atomic có suffix `.t1725`; nếu chưa có file mới sẽ đọc legacy qua reader hiện hữu rồi tạo phase epoch/migration cutoff. File mới chứa đồng thời directions, pending, layers, receipts và epochs cùng identity/counts/checksum. Legacy file được giữ, không dùng nó để rollback tùy tiện. Deal đã nằm trong legacy cutoff có thể replay-skip; correction hoặc late deal cần phase proof không có trước migration sẽ reconcile. Fresh start và compacted history có watermark khác nhau; không coi deal ngoài retained proof là fresh history.

Outcome store mới có scope account/symbol/magic, state schema riêng và durable intent trước send. Chỉ settled prefix được retire, giữ 32 recent outcomes; cap 512 không đẩy bỏ unknown/pending. ARCS records/epochs và PY member/op limits kiểm tại 65.536; compaction chỉ khi chứng minh consumed/durable. Capacity hoặc checksum/I/O lỗi giữ trạng thái blocked/reconcile, không viết payload không đọc lại được.

Không rollback sang binary cũ với open position/pending obligation hoặc receipt chưa settle. Chỉ rollback khi đã flat/settled và state tương thích được xác nhận, hoặc dùng migration/reconcile do team kiểm chứng. Không xóa state để ép EA chạy; giữ cả checkpoint, source version và trace khi điều tra.

## Diagnostics / benchmark

Trong bản compile kiểm thử riêng, đặt `#define BD_DIAGNOSTICS` và `#define BD_BUILD_ID "<candidate-source-id>"` trước includes của EA; bind hash của chính source instrumented đó. Mặc định production không có define. CSV `BD_METRICS_<id>_<tick>.csv` xuất cục bộ ở deinit; không gửi mạng. Run đủ end date để flush, giữ file CSV/hash cùng canonical ordered intent/economic trace, memory peak, wall time và configuration hashes.

Xem BENCHMARK_RUNBOOK.md để tạo paired input và chạy comparator. PositionsTotal calls + visits là hai chỉ số khác nhau; không coi mọi call là một complete enumeration. `PERSIST_IO_US` đo tổng write/flush/move, không bao gồm toàn bộ serialization/checksum. Allocation bytes là logical requested bytes. Handler p50/p95/p99 là log2 intervals; dùng profiler/raw native samples nếu cần phân giải ngưỡng 5%.

Chữ ký wrapper đối chiếu tài liệu chính thức: [FileFlush](https://www.mql5.com/en/docs/files/fileflush), [FileMove](https://www.mql5.com/en/docs/files/filemove), [FileWriteLong](https://www.mql5.com/en/docs/files/filewritelong), [ArraySort](https://www.mql5.com/en/docs/array/arraysort), [OrderCalcProfit](https://www.mql5.com/en/docs/trading/ordercalcprofit). Đối chiếu API không thay native compile.
