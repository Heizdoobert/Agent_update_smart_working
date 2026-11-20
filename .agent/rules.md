# Project Rules: Repository

## 1. Environment & Tech Stack
- **Primary Language:** Repository
- **Core Stack:** Standard

## 2. Standard Commands
```bash
# No custom build/test commands detected
```

## 3. Core Coding Conventions
- Maintain clean architecture and modular separation.
- Ensure all unit and integration tests pass before handoff.
- Adhere to official language conventions and safe error handling.

## 4. Autonomous Adaptive Reflexion Protocol
- Bất kỳ lỗi phát sinh (test fail, build break, critic < 100): Agent tự động thực thi chu trình Reflexion từ skill `adaptive-self-healing-agent` (RCA -> Reflect -> Auto-retry max 3 lần -> Record recipe).
- Không yêu cầu người dùng can thiệp trừ khi đã thử 3 lần không thành công (HITL escalation).

## 5. Hierarchical Sub-Agent Token Optimization (Bắt buộc Phân cấp & Tiết kiệm Token)
- **Model chính trong session là Người quản lý cuối (Lead Architect):**
  - Chuyên trách: Lập kế hoạch tổng thể (ToT/GoT DAG), phân tách bài toán, giao việc, tổng hợp báo cáo và nghiệm thu chất lượng cuối cùng.
  - Không trực tiếp làm việc chân tay (chạy test, đọc file log hàng trăm dòng, quét file, sửa lặt vặt).
- **Mỗi tác vụ là 1 Sub-agent độc lập (Parallel / Isolated Tasks):**
  - Tách mọi công việc thành các sub-agent độc lập, chạy song song để tối đa hóa tốc độ và giữ context window session < 3KB.
- **Quy tắc phân bổ Model cho Sub-agent:**
  - **`flash_lite` (Việc tay chân):** Quét file (`find`, `grep`), chạy test runner, đọc log/trace lỗi, tra cứu bộ nhớ (`agent_memory_search`).
  - **`flash` (Triển khai & Kiểm thử):** Viết code tính năng, vá bug cụ thể, viết unit test, kiểm tra định dạng.
  - **`inherit` / `pro` (Đặc thù cấp cao):** Chỉ dành cho thẩm định kiến trúc trừu tượng hoặc audit bảo mật chuyên sâu.

## 6. Session Handoff Ritual (bắt buộc mỗi session)
- **Khởi động:** đọc `claude-progress.txt` + `todo.md`; nếu chưa có, chạy `bash init.sh` (xem `docs/SESSION_RITUAL.md`).
- **Kết thúc:** ghi `claude-progress.txt`, cập nhật `features.json` (chỉ flip `done` khi đã có evidence + commit SHA), rồi commit.
- **Xác nhận done:** chỉ xem là done khi (1) evidence thật, (2) commit SHA, (3) toàn bộ `acceptance_criteria` tick. "Build pass" ≠ "Working".

## 7. Trace-on-Failure (error-taxonomy)
- Mỗi lần lỗi (test fail, build break, critic < 100) sau khi xử lý: ghi 1 trace vào `docs/trace-log/` theo 7 cột của `docs/failure-taxonomy.md`.
- Không xoá trace cũ; tích luỹ cho ERROR_ANALYSIS.

