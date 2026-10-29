# Architecture Decision Records (ADRs)

Tài liệu ghi nhận toàn bộ các quyết định kiến trúc cốt lõi, bối cảnh, phương án đánh đổi (trade-offs) và lý do lựa chọn trong quá trình thiết kế và phát triển [`agent_system`](file:///mnt/second_drive/Agent_system).

## Danh mục ADR

| Mã ADR | Tiêu đề | Trạng thái | Ngày quyết định |
|---|---|---|---|
| [ADR-001](file:///mnt/second_drive/Agent_system/docs/decisions/0001-domain-agnostic-cognitive-engine.md) | Xây dựng lõi nhận thức Domain-Agnostic độc lập thuần Python | **ACCEPTED** | 2026-10-28 |
| [ADR-002](file:///mnt/second_drive/Agent_system/docs/decisions/0002-strict-context-budget-and-structural-truncation.md) | Giới hạn ngân sách Context (<3KB) và bộ cắt an toàn cấu trúc UTF-8/Markdown | **ACCEPTED** | 2026-10-28 |
| [ADR-003](file:///mnt/second_drive/Agent_system/docs/decisions/0003-pluggable-sdk-and-instance-isolated-plugins.md) | Kiến trúc Pluggable SDK, Cô lập Instance và Onboarding Wizard | **ACCEPTED** | 2026-10-29 |
| [ADR-004](file:///mnt/second_drive/Agent_system/docs/decisions/0004-concurrency-hardened-sqlite-wal-and-3-tier-memory.md) | Hệ thống lưu trữ đồng thời SQLite WAL và Bộ nhớ 3 tầng (Episodic, Semantic, Scratchpad) | **ACCEPTED** | 2026-10-29 |
| [ADR-005](file:///mnt/second_drive/Agent_system/docs/decisions/0005-context-engineering-hierarchy-and-budget-governance.md) | Thiết kế phân tầng Ngữ cảnh (Context Hierarchy) và Quản trị Ngân sách Context Chủ động (<3KB) | **ACCEPTED** | 2026-10-29 |
| [ADR-006](file:///mnt/second_drive/Agent_system/docs/decisions/0006-zero-dependency-mcp-server-protocol.md) | Giao thức Model Context Protocol (MCP) Server thuần Python độc lập, không phụ thuộc thư viện ngoài | **ACCEPTED** | 2026-10-29 |
