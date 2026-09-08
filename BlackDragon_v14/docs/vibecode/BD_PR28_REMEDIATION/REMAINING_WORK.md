# Phần còn lại sau source T17.25

Không còn hạng mục source bắt buộc được đánh dấu PARTIAL như T17.24 trong phạm vi đã duyệt. Đây chưa phải full PRD acceptance hoặc live-ready. Các việc còn lại là:

1. **Owner native compile (G2):** MetaEditor Windows, probe + EA + 34 scripts; 0 errors/0 warnings, EX5 mới và source/toolchain hashes. Nếu compiler phát hiện lỗi, sửa candidate rồi chạy lại gate liên quan.
2. **Native integration (G3):** đủ callback permutations REQUEST/DEAL/ORDER/POSITION, reject/partial/unknown/restart; actual ID/ticket rollover, correction/late/suppressed receipt và atomic crash boundaries. Host mocks không thay tầng này.
3. **Migration / scenarios (G3/G4):** PY v1/v2, ARCS legacy→T17.25 với open/pending obligations, cùng-ms phase ambiguity, OFF/VIRTUAL/BROKER BUY/SELL, RH trim thật, exit liveness và monotone floor. Thực hiện bằng terminal/test state riêng.
4. **Performance (G5):** qualify correctness-only B1 từ lịch sử/diff, freeze nguồn/data/profile/set/budget, rồi ít nhất 5 paired runs B1→C đã hoàn tất end date. Thu metrics/trace/memory/wall time và kiểm bằng comparator. Chưa có chứng minh 50% scan hoặc 5% latency.
5. **Independent audit (G6):** người khác kiểm lại F01…F07, source/hash/test matrix và native evidence. Self-review đã có; independent review chưa thực hiện.

**Tùy chọn có điều kiện:** D-205 chỉ duyệt oracle validation; thay công thức SL/funding runtime cần broker evidence và quyết định tương ứng. R-017 đã áp composition từng phần, giữ wrappers; tháo toàn bộ inheritance chỉ sau differential trace native. Đây không phải module source bị quên triển khai.

Release/forward/live/merge vẫn false; gói bàn giao không cấp quyền kích hoạt trading.
