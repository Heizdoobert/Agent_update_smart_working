# Confirmed Statement of Intent: adaptive-self-healing-agent

- **Date:** 2026-11-02
- **Topic:** Adaptive & Self-Improving Agent Engine with Reflexion Loop, Trace RCA, and Memory Integration
- **Workspace:** `/mnt/second_drive/SKILL/adaptive-self-healing-agent`

---

## 1. Intent Matrix

- **Outcome:** Xây dựng Skill `adaptive-self-healing-agent` tại `/mnt/second_drive/SKILL/adaptive-self-healing-agent` hiện thực hóa kiến trúc Graph 4 bước: **Trace & RCA** ➔ **Reflexion Loop (max 3–5 retries)** ➔ **Human-in-the-Loop Feedback** ➔ **Lessons-Learned DB (Episodic Memory & Dynamic Few-shot)**.
- **User:** AI Agent và Kỹ sư phát triển/kiểm thử cần một agent không bao giờ lặp lại vết xe đổ cũ, tự động sửa lỗi qua từng vòng lặp và thông minh dần theo thời gian.
- **Why now:** Loại bỏ tình trạng Agent lặp lại sai lầm ngớ ngẩn (cú pháp, ngữ cảnh, hallucination) khi rerun; chuyển hóa toàn bộ lỗi đã sửa thành tài sản tri thức dài hạn có thể truy vấn lại.
- **Success:** Cung cấp tài liệu Skill chuẩn hóa (<3KB), module đồ thị State Machine / Reflexion runner độc lập bằng Python (hỗ trợ checkpointing, RCA analyzer, dynamic few-shot injection), và tích hợp trực tiếp với bộ nhớ `agent-system memory`.
- **Constraint:** Vận hành tối ưu trên môi trường local hiện tại; file `SKILL.md` tuân thủ ngân sách context < 3072 bytes và đạt 100/100 điểm qua `agent-system critic`.
- **Out of scope:** Không bắt buộc cài đặt hay phụ thuộc vào cloud SaaS trả phí bên ngoài (LangSmith/Phoenix Cloud token); không can thiệp vào mã nguồn nhị phân lõi của Antigravity CLI.

---

## 2. Core Pillars of the Architecture

1. **Execution Tracing & RCA Critic:**
   - Trích xuất JSON trace (Chain of Thoughts, Tool calls, Tool outputs, Environment errors).
   - Critic Agent / Rule-based RCA phân loại lỗi: Syntax/Compiler, Incomplete Context, Flaky Target, Logic Drift.

2. **Reflexion & Self-Correction Loop:**
   - State graph 4 bước với biến `retry_count` (giới hạn 3-5 lần).
   - Tự động đóng gói `Original Goal` + `Failure Output` + `RCA Diagnosis` thành Reflection Prompt cho lần rerun.

3. **Human-in-the-Loop (HITL) Checkpointer:**
   - Hỗ trợ trạng thái tạm dừng `PENDING_FEEDBACK` khi cần xác nhận hoặc khi rerun do người dùng kích hoạt kèm chỉ thị mới.

4. **Memory-Augmented Reflection & Dynamic Few-shot:**
   - Khi sửa lỗi thành công, tự động trích xuất cặp `{error_signature, recovery_recipe}` và nạp vào Episodic Memory (`agent-system memory recipe-record`).
   - Trước khi thực thi bất kỳ task nào, tự động tra cứu semantic memory (`agent-system memory search`) để nhét các ví dụ thành công tương tự vào prompt (Dynamic Few-shot).
