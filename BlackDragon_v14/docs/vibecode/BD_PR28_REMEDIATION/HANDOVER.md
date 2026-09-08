# BlackDragon v15.02 / T17.25 — bàn giao source

Đã triển khai phần source trong phạm vi PRD và các quyết định đã duyệt. Các khoảng trống source T17.24 về outcome store, receipts/correction, indexes, incremental campaign, retention, diagnostics và oracle đã có implementation. Native acceptance của PRD vẫn chưa hoàn tất.

Gói `BD-EA-v15.02-T17.25-Handover.zip` chứa source đầy đủ, docs, patch từ upstream `40c424cf`, host evidence và SHA-256 manifest. Giải nén dùng trực tiếp; không áp patch lần nữa lên source đã có trong ZIP. Entry point: `BlackDragon_v14/Experts/BlackDragon/BlackDragon.mq5`. Tên thư mục v14 giữ để tương thích đường dẫn; product version là 15.02.

Kết quả host cuối phải khớp `evidence/final/HOST_GATE_RESULTS.json`: 59 nhóm regression, 232 assertion production fixture, 11 mutation bị bắt và 12 fixture qua UBSan/bounds. Gói còn có một lượt chạy độc lập từ source archive để chứng minh không phụ thuộc working tree hoặc file tạm. Đây là các tầng bằng chứng khác nhau, không cộng thành số case PRD đã nghiệm thu.

Owner đã chọn tự compile sau. Gói không có EX5; Windows MetaEditor, 34 native scripts, Strategy Tester, async runtime, benchmark và independent audit chưa PASS. `release_eligible`, `forward_eligible`, `live_eligible` đều false.

Đọc `IMPLEMENTATION_REPORT.md` để xem từng thuật toán; `REQUIREMENT_STATUS.json` đối chiếu R-001…R-018; `TEST_EXECUTION.json` giữ riêng 56 planned cases; `NATIVE_BUILD_RUNBOOK.md` có lệnh compile và migration/rollback. Profit oracle chỉ để validation theo D-205; full inheritance teardown chờ native trace. Không có claim tăng tốc định lượng.
