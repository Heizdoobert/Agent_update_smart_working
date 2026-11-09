# Release Notes

## v0.4.4 – 2026-11-05

- Thêm **Tenant‑aware vector store** dựa trên **Milvus Lite** (`scripts/tenant_vector_store.py`) với hỗ trợ isolation, persistence và delete‑all.
- Cập nhật **test suite** (`tests/test_tenant_vector_store_milvus.py`) để kiểm chứng isolation và model persistence.
- Thêm **CLI** (`scripts/run_agent.py`) cho các agent Claude, OpenCode, Hermes, Antigravity, với khả năng tự động chọn phiên bản model nhẹ (`SMALL_MODEL`).
- Cấu hình model trong `cli/agents_config.py` (default & lite).
- Cập nhật `pyproject.toml` lên phiên bản `v0.4.4`.
- Đảm bảo toàn bộ **113 tests** đều PASS.

---

*Generated from README release section.*
