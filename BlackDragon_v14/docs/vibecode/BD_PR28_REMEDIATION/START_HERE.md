# Bắt đầu với source T17.25

1. Đọc HANDOVER.md và REQUIREMENT_STATUS.json: source hoàn tất trong phạm vi đã duyệt, native qualification còn mở.
2. Kiểm MANIFEST.json và SHA256SUMS.txt ở root gói. Dùng source giải nén, không cần checkout hay áp patch.
3. Compile theo NATIVE_BUILD_RUNBOOK.md trong thư mục kiểm thử riêng.
4. Chạy native scripts theo workflow và các scenario trong TEST_MATRIX.json; ghi lại đúng case chưa chạy/fail.
5. Bàn giao EX5 mới, log 0/0, source/toolchain hashes và native evidence cho verifier. Không dùng binary cũ hoặc xóa state để ép chạy.
