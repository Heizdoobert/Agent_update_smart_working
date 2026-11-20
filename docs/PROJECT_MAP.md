# Agent System — Hierarchical Project Map

Index của `agent_system/` cho context loading theo cấp (Level 2/3). Agent chỉ nạp section liên quan đến task hiện tại.

> **Lưu ý (2026-11-20):** Bản đồ khớp lại với cây thư mục thật sau module `cleanup` (cụm Big-Data đã vào `Archive/bigdata-v04/`).

---

## 1. Core (`agent_system/core/`)
Abstraction thuần, domain-agnostic, session state, context safety.
- `contracts.py` — dataclass cơ sở: `TaskGoal`, `Plan`, `ThoughtNode`, `CriticReport`, `DiagnosticItem`.
- `session.py` — `SessionManager`: persist session token cross-tool.
- `truncator.py` — `StructuralTruncator`: chặn ≤3072 bytes (3KB), giữ nguyên vẹn UTF-8 + JSON/Markdown block.
- **Invariants:** 100% domain-agnostic; không phụ thuộc external.

---

## 2. Reasoning (`agent_system/reasoning/`)
Non-linear thought exploration (Tree/Graph of Thoughts) + pathfinding tất định.
- `graph.py` — `ThoughtGraph`: DAG + cycle detection + thought fusion.
- `astar.py` — `AStarPlanner`: đường tối ưu trên state-action model đã biết.
- `mcts.py` — `MCTSPlanner`: Monte Carlo rollout cho không gian stochastic.
- `transition.py` — `ActionDefinition`, `StateNode`, transition model.
- **Patterns:** state immutability; hash/equality theo dict state keys.

---

## 3. Reflection (`agent_system/reflection/`)
Đánh giá tĩnh đa giai đoạn + self-repair loop in-memory trước output.
- `critic.py` — `CriticEngine`: tổng hợp evaluation từ các critic đăng ký.
- `reflector.py` — `SelfReflector`: vòng auto-patch (max 5 lần) để đạt pass.
- `llm_patcher.py` — (opt-in `AGENT_SYSTEM_LLM_PATCH=1`) gọi model rẻ vá vi phạm mà rule-patcher không sửa được.
- `adapters/python_ast.py` — `PythonAstCritic`: syntax error, cấm `eval`/`exec`/`breakpoint`, type hints.
- `adapters/config_rules.py` — `MarkdownRulesCritic` (budget + fence), `PluginManifestCritic`.
- **Invariants:** Reflection in RAM; chỉ ghi đĩa sau khi đạt green.

---

## 4. 3-Tier Memory (`agent_system/memory/`)
- `episodic.py` — `EpisodicMemory`: recipe problem→recovery (`recipe-record`, `recipe-get`).
- `semantic.py` — `SemanticMemory`: SQLite FTS5 BM25 + fallback pure-Python; optional fastembed.
- `embedder.py` — (opt-in) vector embedding cho semantic search.
- `scratchpad.py` — `WorkingScratchpad`: transient session-scoped KV.
- **Invariants:** thread-safe SQLite WAL qua `storage/sqlite_store.py` (`busy_timeout=5000`).

---

## 5. Storage (`agent_system/storage/`)
- `sqlite_store.py` — `SQLiteStore`: `PRAGMA journal_mode=WAL`, `busy_timeout=5000`.

---

## 6. Skills (`agent_system/skills/`)
- `registry.py` — `SkillRegistry`: scan, validate, inject `SKILL.md`.
- Frontmatter YAML zero-dependency (parse inline trong registry).

---

## 7. SDK & Brownfield (`agent_system/sdk/`)
- `contracts.py` — `BasePlugin`, `PluginManifest`, `EventBus`, lifecycle hooks.
- `registry.py` — `PluginRegistry`: multi-plugin precedence, sandbox isolation, merged rules.
- `scanner.py` — `CodebaseScanner`: phát hiện manifest Python/Node/Go/Rust/Make.
- `ingestion.py` — `KnowledgeIngester`: Tier-1 rules (`.agent/rules.md` ≤3072B) + chunk Tier-2.
- `installer.py` — `agent-system install`: viết marked-block vào client configs (không ghi đè).
- `wizard.py` — `OnboardingWizard`: 4 câu hỏi interactive/non-interactive.

---

## 8. Distillation (`agent_system/distillation/`)
- `distiller.py` — `DistillationEngine`: candidate gen/eval/compress cho system prompt (offline).

---

## 9. MCP Server (`agent_system/mcp/`)
- `server.py` — zero-dependency JSON-RPC 2.0 stdio server (MCP `2024-11-05`).
- `tools.py` — `CognitiveToolsDispatcher`: 8 cognitive tools + FLOW bridge tools.
- **Invariants:** `sys.stdout` chỉ carry newline-delimited JSON-RPC; log → `sys.stderr`.

---

## 10. CLI (`agent_system/cli/`)
- `main.py` — entry point `agent-system`: `init`, `scan`, `mcp`, `plan`, `critic`, `reflect`, `memory`, `skill`, `session`, `install`, `doctor`.

---

## 11. Top-level modules
- `flow.py` — bridge FLOW_SKILL task-engine (`flow-task` CLI): plan → approve → parallel sub-agents → evidence. Absent engine = clear error, không crash.
- `doctor.py` — health report (DB, embeddings, MCP clients, flow-task bridge).
- `feature_flags.py` — utility feature-flag.

---

## 12. Root artifacts
- `CAPABILITY_MAP.md` — map 7 module v2.0 remediation (đã duyệt).
- `docs/specs/SPEC-*.md` — spec từng module.
- `docs/reference/rfc-agent-design.md` — tài liệu THIẾT v2.0 (nguồn chuẩn).
- `docs/failure-taxonomy.md`, `docs/SESSION_RITUAL.md` — module `error-taxonomy`/`handoff`.
- `Archive/bigdata-v04/` — cụm Big-Data đã archive (KHÔNG phải phần chạy).
