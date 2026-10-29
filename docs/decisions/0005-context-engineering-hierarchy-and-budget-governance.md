# ADR-005: Thiết kế phân tầng Ngữ cảnh (Context Hierarchy) và Quản trị Ngân sách Context Chủ động (<3KB)

## Status
Accepted

## Date
2026-10-29

## Context
Chất lượng sinh mã và giải quyết vấn đề của AI Agent phụ thuộc trực tiếp vào chất lượng ngữ cảnh (Context Engineering). Hai thái cực sai lầm phổ biến là:
1. **Đói ngữ cảnh (Context Starvation):** Agent tự phỏng đoán API, vi phạm quy ước dự án do thiếu file chỉ dẫn rõ ràng.
2. **Lụt ngữ cảnh (Context Flooding):** Nạp toàn bộ kho mã nguồn, logs dài hàng nghìn dòng, hoặc tài liệu thô khiến sự chú ý của mô hình bị phân tán (hiệu ứng "Lost-in-the-Middle"), dẫn đến suy giảm độ chính xác và chi phí suy luận tăng đột biến.

Hệ thống cần một cấu trúc phân tầng ngữ cảnh rõ ràng, cơ chế kiểm soát ngân sách chủ động ở mức 75% ngưỡng tải (<3KB / 3072 bytes) và đảm bảo tính kết hợp an toàn khi nhiều plugin SDK cùng đóng góp luật dự án.

## Decision
1. **Phân tầng Ngữ cảnh 5 cấp (Context Hierarchy):**
   - **Cấp 1 - Rules Files (`CLAUDE.md`, `GEMINI.md`, `AGENTS.md`, `.agent/rules.md`):** Luôn nạp đầu tiên, quy định tech stack, lệnh kiểm thử, quy ước cốt lõi và ranh giới bất biến. File luật bắt buộc phải vượt qua [`MarkdownRulesCritic`](file:///mnt/second_drive/Agent_system/agent_system/reflection/adapters/config_rules.py#L12-L65) với điểm số 100/100 và dung lượng dưới 3072 bytes.
   - **Cấp 2 - Spec & Kiến trúc:** Nạp lát cắt tính năng liên quan thay vì toàn bộ đặc tả lớn.
   - **Cấp 3 - File mã nguồn liên quan:** Đọc file cần sửa, file test tương ứng và ví dụ mẫu hiện có trong dự án trước khi sửa đổi.
   - **Cấp 4 - Kết quả lỗi & Kiểm thử (Error Output):** Chỉ truyền chính xác thông báo lỗi / stack trace của bài test thất bại thay vì toàn bộ output hàng trăm dòng.
   - **Cấp 5 - Lịch sử hội thoại & Nén ngữ cảnh:** Cắt tỉa tại ngưỡng 75% dung lượng, tóm tắt bài học thay vì giữ vết thất bại, và sắp xếp tài liệu quan trọng nhất (task hiện tại, lỗi cần gỡ) ở vị trí cuối cùng sát điểm sinh text.

2. **Kiểm soát Ngân sách Đa Plugin (`PluginRegistry.get_project_rules`):**
   - [`PluginRegistry.get_project_rules`](file:///mnt/second_drive/Agent_system/agent_system/sdk/registry.py#L237-L241) tự động bọc chuỗi luật tổng hợp qua [`StructuralTruncator.truncate_text(..., max_bytes=3072)`](file:///mnt/second_drive/Agent_system/agent_system/core/truncator.py). Khi nhiều plugin cùng đóng góp luật dự án, dung lượng xuất ra luôn tuyệt đối bảo toàn bất biến <3KB và đóng kín các code block Markdown còn dang dở.

3. **Ranh giới Phiên làm việc Tái khởi động (Restartable Session Boundaries):**
   - Trước khi reset hoặc chuyển đổi tác vụ, Agent lưu lại trạng thái mục tiêu, quyết định và vết kiểm thử vào [`SessionManager`](file:///mnt/second_drive/Agent_system/agent_system/core/session.py) và [`WorkingScratchpad`](file:///mnt/second_drive/Agent_system/agent_system/memory/scratchpad.py).

## Alternatives Considered

### 1. Nạp toàn bộ tài liệu không giới hạn (Unbounded Injection)
- **Ưu điểm:** Đơn giản, không cần module cắt chuỗi.
- **Nhược điểm:** Phá vỡ ngân sách prompt, chi phí token cao, giảm hiệu suất suy luận của Agent do nhiễu thông tin.
- **Lý do bác bỏ:** Vi phạm Non-Negotiable Core Rule 2 của hệ thống.

### 2. Cắt chuỗi thô theo byte hoặc ký tự (`[:3072]`)
- **Ưu điểm:** Nhanh chóng.
- **Nhược điểm:** Làm rách ký tự đa byte UTF-8 và làm vỡ cấu trúc cú pháp Markdown / JSON.
- **Lý do bác bỏ:** Nguy cơ crash parser rất cao, đã được giải quyết triệt để bởi `StructuralTruncator`.

## Consequences
- Hệ thống duy trì sự ổn định tối đa trong các phiên làm việc dài hoặc phức tạp.
- Toàn bộ các file luật dự án và luật tổng hợp từ plugin đều tuân thủ 100% ngân sách 3KB với định dạng Markdown chuẩn chỉnh.
