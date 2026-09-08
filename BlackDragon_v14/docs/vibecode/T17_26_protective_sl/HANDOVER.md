# Bàn giao v15.03 / T17.26 — sửa lỗi dừng Tester

Bản vá source theo audit `20260906.log`, baseline `9d3a76eef330411cabda154dff27a7cb6207ec1a`. User đã duyệt: “Tiến hành fix update theo plan. Dùng @Vibecode MQL5 full mode”.

## Thay đổi

1. Nhận diện broker SL không còn phụ thuộc chênh lệch giá khớp hoặc spread hiện tại. Hai nhánh refresh và callback cùng gọi classifier; terminal broker reentry cũng dùng classifier này. Shared identity helper kiểm tra programmed SL khớp target hợp lệ; generic MODIFY boolean không bỏ qua một programmed SL khác target.
2. Xác thực symbol, close entry, opening position identifier, owner, direction, comment cycle, generation và campaign epoch. Receipt đã xác nhận cho đúng deal vẫn được dùng khi layer/campaign hiện tại đã chuyển tiếp. Receipt cũ không chứng minh một deal mới.
3. Protective receipt lưu cùng actual cash và layer state trong checkpoint atomic trước khi Overlap finalizer trả thành công. Hai SL có thể được đối soát trước callback; callback đến muộn không ghi cash lần hai.
4. Không dùng high-water cursor để loại deal broker SL chưa có receipt. Regression đã phát hiện và khóa trường hợp #1416 đến trước #1415; cả 6 hoán vị callback hai SL/Overlap đều đạt trên fixture trích production methods.
5. Giữ nguyên phép tính cash từ profit + swap + commission + fee, inverse correction/delete và không tạo credit từ giá SL dự kiến. Nếu một receipt trong batch lỗi sau khi receipt trước đã cập nhật RAM, khóa persistence để không commit nửa batch.
6. Checkpoint ARCS mới dùng envelope version 2, vẫn đọc version 1 theo layout cũ; không tự tạo protective proof cho receipt cũ. Tên file `.t1725` được giữ để phát hiện/đọc checkpoint hiện hữu, không tạo namespace mới rồi bỏ qua state cũ.
7. Gate vẫn gọi TesterStop khi Recovery thật sự không ready. Thông báo có phase INIT/RUNTIME theo việc gate đã quan sát engine ready, không gắn nhãn startup cho mọi lỗi. Callback external ghi deal/position/reason/owner/programmed SL/fill; lỗi API được chụp ngay ở call site. Business error không gắn ambient LastError.
8. Chế độ SL ảo giữ đường callback cũ; input/default/type/order giữ nguyên. Các giá trị 0.5%, ladder 20→120 và threshold 14/16 không tự đổi.

## Kiểm chứng

Lệnh duy nhất chạy toàn bộ gate host từ thư mục chứa `BlackDragon_v14`:

```bash
python3 BlackDragon_v14/Scripts/BlackDragon/Tests/run_host_gates.py --out /absolute/new/output
```

Bộ gate hiện có 60 nhóm regression/source, 364 production assertions (132 mới), 14 mutation và 13 UBSan/bounds fixtures. Kết quả chính thức của lượt bàn giao nằm trong `verification/HOST_GATE_RESULTS.json` ở ZIP; file này ghi lệnh, output và hash source. Chỉ coi PASS khi manifest thực tế báo PASS.

132 kiểm tra mới trích các hàm thật về opening identity, classifier, repair, receipt/cash, atomic ledger, coordinator router và readiness gate. API history/filesystem, vị thế live, exact MODIFY proof và một số adapter MT5 được cung cấp bởi host seams. Đây không phải native OnTradeTransaction queue hoặc ABI MT5. Kiểm tra migration V1/V2 trên host không thay thế native restart/migration.

Native script mới: `Scripts/BlackDragon/Tests/RunT1726ProtectiveSlTests.mq5` — 15 kiểm tra pure identity + native POD receipt file round-trip, không gửi lệnh trade. Tổng 35 native scripts được enroll; chưa chạy ở môi trường hiện tại.

## Chưa có bằng chứng native

Không có MetaEditor/MT5/Wine hoặc canonical compile backend trong môi trường thực hiện. Compile EX5, 35 scripts native, chạy lại khoảng test đầy đủ, restart/interleaving native và profiling đều UNTESTABLE/NOT_RUN. Không có EX5 trong ZIP; release/forward/live đều false. Đây là source candidate để owner compile và nghiệm thu, không phải live-ready.

## Files

- `EA-SPEC.yaml`, `DECISIONS.yaml`, `AI-BUILD-CONTRACT.json`: phạm vi và decision đã duyệt.
- `TASK_GRAPH.md`: task graph và các vai trò CONTRACTOR/BUILDER/VERIFIER thực hiện tuần tự bởi cùng một agent.
- `NATIVE_RUNBOOK.md`: cài candidate, compile, replay và bằng chứng cần xuất.
- `BASELINE_INPUTS.json`: so sánh input với source trước sửa.
- `RETRO.md`: lỗ hổng coverage đã khóa; giới hạn còn lại.

Lịch sử PRD T17.25 trong `BD_PR28_REMEDIATION` giữ nguyên; không dùng các báo cáo cũ để chứng nhận bản T17.26. Không ghi đè EA đang chạy hoặc checkpoint đang được terminal sử dụng khi cài candidate. Dùng terminal thử nghiệm riêng để tái hiện incident.
