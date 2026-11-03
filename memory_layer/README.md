# 3‑Tầng Lưu Trữ Dữ Liệu cho Agent

## Mục tiêu
- **Long‑term Memory**: Lưu trữ các *insights*, sở thích, quy tắc và kiến thức cốt lõi của người dùng sau mỗi task.
- **Vector Database**: Dùng để lưu embedding của các insight ngắn, hỗ trợ truy vấn ngữ cảnh nhanh.
- **Memory Reflection Task**: Khi một task kết thúc, Agent không lưu raw file mà sẽ gọi task phụ `memory_reflection` để tạo một đoạn insight ngắn, embed và lưu vào Vector DB kèm metadata.

## Kiến trúc 3‑tầng
```
Long‑Term Memory (metadata + embeddings)   <-- Chroma / Milvus / Qdrant / Pinecone
│
└─ Insight Queue (temporary JSON)          <-- /tmp/agent_insights.json
   
└─ Reflection Runner (Python script)       <-- scripts/memory_reflection.py
```

### 1. Long‑Term Memory
- Thư mục: `.agent/long_term_memory/`
- Mỗi insight được lưu dưới dạng một document trong Vector DB, metadata bao gồm:
  - `user_id`
  - `task_id`
  - `timestamp`
  - `insight_type` (e.g., `preference`, `rule`, `core_knowledge`)
  - `source` (ID của task gốc)

### 2. Vector Database
- **Mặc định**: **Chroma** – thư viện pure‑Python, không cần server riêng.
- Cấu hình có thể thay đổi trong `config.yaml` để dùng Milvus / Qdrant / Pinecone.

### 3. Memory Reflection Task
1. Agent xuất một JSON tạm thời (`/tmp/agent_insights.json`) chứa:
   ```json
   [{"insight":"User prefers concise summaries","type":"preference"}, ...]
   ```
2. `memory_reflection.py` sẽ:
   - Đọc file JSON.
   - Dùng hàm `embed(text)` (placeholder; bạn có thể thay bằng API embedding thực tế).
   - Ghi embedding + metadata vào Vector DB.
   - Xóa file tạm.

## Quy trình tích hợp vào Agent
1. **Sau mỗi task**: Agent gọi `memory_reflection.py` (sub‑process) với env var `TASK_ID` và `USER_ID`.
2. Script tự động xử lý và cập nhật Long‑Term Memory.
3. Các task tiếp theo có thể truy vấn Long‑Term Memory bằng:
   ```python
   results = db.query(query_text, filter={"user_id": USER_ID})
   ```
   để lấy các insight liên quan.

---

> **Lưu ý**: Nếu bạn muốn dùng DB khác, chỉ cần cập nhật `config.yaml` và cài đặt thư viện tương ứng.
