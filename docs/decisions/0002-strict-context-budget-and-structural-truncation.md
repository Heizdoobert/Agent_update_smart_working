# ADR-002: Giới hạn ngân sách Context (<3KB) và bộ cắt an toàn cấu trúc UTF-8/Markdown

## Status
Accepted

## Date
2026-10-28

## Context
Trong các mô hình ngôn ngữ lớn (LLM), việc tiêm ngữ cảnh (context injection) không giới hạn từ logs, tài liệu semantic memory hoặc trace execution dễ dẫn đến:
1. Tràn context window hoặc chi phí suy luận tăng đột biến.
2. Cắt chuỗi thô theo byte (`[:3072]`) làm rách các ký tự UTF-8 đa byte (như tiếng Việt: "tiếng Việt" thành "ti\xe1..."), gây lỗi `UnicodeDecodeError`.
3. Làm vỡ cấu trúc cú pháp JSON khiến parser sập.
4. Cắt ngang các khối mã nguồn Markdown (code fences ```` ``` ````), để lại cú pháp markdown chưa đóng làm sai lệch format prompt của agent.

## Decision
Hiện thực hóa module [`StructuralTruncator`](file:///mnt/second_drive/Agent_system/agent_system/core/truncator.py):
1. **Ranh giới ký tự UTF-8:** Cắt theo byte an toàn với cơ chế giải mã `errors="ignore"` và lùi về ranh giới ký tự hợp lệ gần nhất.
2. **Cắt tỉa JSON cú pháp:** `truncate_json` ưu tiên giữ nguyên cấu trúc object/mảng hợp lệ; nếu vượt quá giới hạn thì fallback về object tối giản `{}` hoặc danh sách rỗng `[]` thay vì chuỗi JSON cụt lỗi cú pháp.
3. **Bảo toàn Markdown Fence:** Nếu sau khi cắt phát hiện số lượng dấu ```` ``` ```` là số lẻ, hệ thống tự động chèn `\n```\n` trước chuỗi hậu tố `...[TRUNCATED]`.
4. **Ngân sách mặc định:** Áp dụng ngưỡng cố định 3072 bytes (3KB) cho mọi payload tiêm vào prompt.

## Alternatives Considered

### 1. Cắt thô theo số lượng ký tự (`text[:1000]`)
- **Ưu điểm:** Đơn giản, nhanh.
- **Nhược điểm:** Số lượng ký tự không phản ánh dung lượng byte thực tế trong UTF-8 (ký tự tiếng Việt hoặc Emoji chiếm 2-4 bytes), không kiểm soát được byte budget của mạng hoặc token buffer; không đảm bảo JSON hợp lệ.
- **Lý do bác bỏ:** Nguy cơ phá vỡ cú pháp rất cao.

### 2. Sử dụng thư viện ngoài như `tiktoken`
- **Ưu điểm:** Tính toán chính xác số token của OpenAI.
- **Nhược điểm:** Phụ thuộc thư viện C/Rust bên ngoài, cài đặt nặng, không tương thích với nguyên tắc zero-dependency của core.
- **Lý do bác bỏ:** Vi phạm tiêu chí thuần Python Standard Library.

## Consequences
- Mọi dữ liệu tiêm từ Semantic Memory, Skills hoặc Project Rules đều đảm bảo <3KB và parse được 100%.
- Không bao giờ gặp lỗi `UnicodeDecodeError` hay `JSONDecodeError` trong quá trình truyền context qua CLI hoặc socket.
