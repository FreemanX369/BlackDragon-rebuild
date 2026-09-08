# Nghiệm thu MT5 native — T17.26

## Compile và nguồn

1. Giải nén gói, copy `BlackDragon_v14/Experts`, `Include`, `Scripts` vào MQL5 của terminal thử nghiệm riêng.
2. Mở `Experts/BlackDragon/BlackDragon.mq5` trong MetaEditor, compile và lưu nguyên compile log: 0 errors / 0 warnings. File sinh ra theo entry point là `BlackDragon.ex5`; version phải 15.03, banner T17.26.
3. Ghi SHA-256 EX5 và source tree/manifest gói. Không dùng lại EX5 T17.25. Chưa có EX5 hay native compile PASS được giao kèm.
4. Compile và chạy `RunT1726ProtectiveSlTests.mq5` trên chart thử nghiệm, yêu cầu 15 passed / 0 failed / ALL GREEN. Script không trade và chỉ ghi/xóa file riêng tên BD_T1726_TEST_*.bin. Chạy thêm 34 script còn lại theo workflow. Script PASS không phải Strategy Tester PASS.

## Replay đúng incident

- XAUUSDm, M1, broker profile Exness-MT5Real38 như log.
- Every tick based on real ticks; execution delay 150 ms.
- 2026.08.26 00:00 → 2026.09.06 00:00; deposit 10000 USD; leverage 1:1000.
- Nạp `reproduction/BD-EA-T1725-Recovered-20260906.set`. Đây là 150 giá trị trích log, giữ nguyên; không có optimization ranges/flags. Symbol/timeframe/date/deposit/leverage/delay đặt riêng trong Tester. Native import chưa được xác minh ở môi trường build.
- Giữ RecoveryTesterResumeState_=false như incident để chạy fresh/clean. Nếu kết quả dữ liệu/tick broker khác, ghi rõ thay vì khẳng định đã replay cùng tape.
- Xác nhận đi qua 2026.08.27 14:43:31, không external latch do hai SL #1415/#1416 hoặc sự kiện tương ứng. Ticket có thể khác nếu tick tape khác; đối chiếu position/deal identity, volume và giá.
- Yêu cầu hoàn tất đến cuối khoảng test/last available tick; log cũ đồng bộ dữ liệu đến 2026.09.04 (cuối tuần không tự là lỗi). Không lấy “Test passed” làm tiêu chí duy nhất; không có early TesterStop. Xuất HTML/XML và full agent journal.

## Matrix execution và persistence

| Gate | Thử nghiệm | Chấp nhận |
|---|---|---|
| G1/G2 | BUY/SELL own SL, gap 0/small/0.981/extreme, thay spread; owner/cycle/symbol/position/SL sai | Own proof không đổi vì quote; unknown/manual không được nhận nhầm |
| G3 | Hai SL và Overlap với mọi thứ tự callback, đặc biệt deal lớn đến trước deal nhỏ | Không bỏ sót deal, không double cash, không false external latch |
| G4 | Partial fill, fees/swap/commission; UPDATE/DELETE/duplicate | Actual delta đúng; không projected credit hoặc negative unit underflow |
| G5 | Restart trước/sau refresh, trước/sau atomic replace, sau coordinator retirement | Receipt/cash/topology khôi phục đồng nhất; callback lặp không ghi lần hai |
| G5 migration | Bản sao checkpoint V1 với exposure, rồi V2; lỗi checksum/short write/replace failure | Không mất cash; không invent proof; lỗi giữ fail-closed |
| G6 | Ownership không xác định; readiness INIT/RUNTIME; emergency exit | Entry/risk additions chặn đúng; stop reason đúng; emergency management được kiểm riêng |
| G7 | Replay incident trọn kỳ + hash binding | Có compile/EX5/params/tick provenance và không early stop |
| G8 | Burst fills, nhiều inventory, missing history rồi retry, gap/spread shock | Liveness và cash đúng; đo p95/p99/max handler trước khi tuyên bố tối ưu tốc độ |

## Upgrade / rollback

Schema V2 đọc V1 qua loader có kiểm checksum/identity và giữ cash. Receipt V1 không chứa protective proof, nên classifier chỉ có thể tái dựng từ history và durable target/intent còn đủ; nếu dữ liệu mơ hồ thì phải reconcile. Không suy diễn host migration PASS thành native migration PASS.

Bản cũ T17.25 không đọc schema V2. Trước khi thử migration, giữ bản sao toàn bộ state từ terminal đã dừng và source/EX5 cũ. Rollback phải đi cùng checkpoint tương ứng; không lấy snapshot cũ để ghi đè account đã phát sinh giao dịch mới. Live rollout không thuộc bàn giao này.

Bằng chứng gửi lại: source/EX5/set hashes, build MT5, symbol profile, compile log, 35 native script logs, full agent log, HTML/XML test, restart/failure matrix và timing nếu đánh giá hiệu năng.
