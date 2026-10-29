# Statement of Intent: Brownfield Codebase Scanner & Knowledge Ingestion

**Status:** CONFIRMED  
**Date:** 2026-10-29  
**Source:** User Interview (`interview-me` session)

---

## 1. Core Intent

- **Outcome:** Bổ sung tính năng quét mã nguồn dự án cũ (`agent-system scan --json` & `agent-system init --auto`) và cơ chế nạp tri thức 2 tầng (Level 1 Rules <3KB + Semantic Memory SQLite) qua hội thoại tự nhiên trong AI Agent CLI.
- **User:** Lập trình viên tích hợp `agent_system` vào các dự án cũ có sẵn (brownfield projects), cần Agent lập tức hiểu bối cảnh mà không phải nhập lại từ đầu.
- **Why now:** `agent_system` hiện tại chỉ có wizard hỏi đáp 4 câu hỏi thủ công, chưa tự động tận dụng kho tri thức có sẵn trong các file tài liệu (`README`, `docs/`) và cấu hình (`package.json`, `pyproject.toml`, Makefile, v.v.).
- **Success:** Mở Agent CLI trong dự án cũ lần đầu → Agent tự động chạy quét ngầm → tóm tắt tri thức cũ (stack, test runner, coding rules, docs) ngay trong chatbox → bạn gõ "Yes" → hệ thống tự tạo `.agent/rules.md` (<3KB), `agent_plugin.json` và nạp toàn bộ chi tiết sâu vào Semantic Memory.
- **Constraint:** 100% Python standard library (không cài thêm dependency bên ngoài), bảo toàn ngân sách ngữ cảnh <3072 bytes (`StructuralTruncator`), lưu trữ SQLite WAL an toàn.
- **Out of scope:** Không can thiệp hay sửa đổi bất kỳ file mã nguồn gốc nào của dự án cũ; không dùng các mô hình vector embedding nặng hay dịch vụ cloud bên ngoài.

---

## 2. Architectural Highlights Confirmed

1. **Dual-Tier Knowledge Allocation:**
   - **Tier 1 (Immediate Context <3KB):** Summarized tech stack, core constraints, architecture pointers written to `.agent/rules.md` (and `agent_plugin.json`). Strict budget cap enforced by `StructuralTruncator`.
   - **Tier 2 (Deep Retrieval Store):** Full documentation text, extracted README sections, troubleshooting/recipe notes indexed into `SemanticMemory` (`SQLiteStore`). Retrievable on-demand via `agent-system memory search`.

2. **Dual-Mode Execution:**
   - **Machine-readable JSON (`agent-system scan --json`):** Agent CLI in session runs this background command silently, consumes the JSON payload, and formats natural language conversational summaries for the user in chat.
   - **Interactive Terminal (`agent-system init --auto`):** For manual developer setup outside AI Agent chat.
