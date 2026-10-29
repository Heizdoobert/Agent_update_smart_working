# Spec: Brownfield Codebase Scanner & Dual-Tier Knowledge Ingestion

## 1. Objective

Enable AI Agent CLIs and developers to automatically onboard existing ("brownfield") repositories into `agent_system` with zero manual questionnaire typing. The system scans repository manifests, configuration files, and documentation to automatically infer tech stack, testing workflows, and coding conventions. It formats findings as structured JSON for conversational confirmation in Agent CLIs, then persists the knowledge into a 2-tier architecture:
- **Tier 1 (Immediate Context):** Condensed `.agent/rules.md` and `agent_plugin.json` strictly bounded to <3KB (3072 bytes) via `StructuralTruncator`.
- **Tier 2 (Deep Retrieval):** Full documentation text, guides, and recipe entries indexed into `SemanticMemory` (SQLite Store) for on-demand query.

---

## 2. Tech Stack & Environment

- **Language:** Python 3.10+ (100% Python Standard Library: `pathlib`, `json`, `re`, `argparse`, `sqlite3`, `dataclasses`).
- **Dependencies:** Zero external runtime dependencies.
- **Persistence:** SQLite with WAL mode (`SQLiteStore`).
- **Target OS:** POSIX (Linux, macOS) & Windows compatible path handling.

---

## 3. Commands

```bash
# Scan repository and print human-readable summary
python3 -m agent_system.cli.main scan --root /path/to/repo

# Scan repository and output machine-readable JSON (used silently by Agent CLI)
python3 -m agent_system.cli.main scan --root /path/to/repo --json

# Interactive / Auto-initialize brownfield project
python3 -m agent_system.cli.main init --auto --root /path/to/repo

# Run full test suite with coverage
PYTHONPATH=. python3 -m pytest tests/test_sdk_scanner.py -v
PYTHONPATH=. python3 -m pytest tests/ -v
```

---

## 4. Project Structure & New Components

```
agent_system/
├── sdk/
│   ├── scanner.py          # NEW: Core codebase scanner & heuristic analyzer
│   ├── ingestion.py        # NEW: 2-tier knowledge builder & memory ingester
│   ├── wizard.py           # ENHANCED: Integrate auto-scan into init workflow
│   └── registry.py         # Existing plugin registry
├── cli/
│   └── main.py             # ENHANCED: Add 'scan' command & '--auto' flag to init
docs/
├── intent/
│   └── brownfield-codebase-scanner-and-knowledge-ingestion.md
└── specs/
    └── SPEC-brownfield-scanner.md
tests/
├── test_sdk_scanner.py     # NEW: Tests for file heuristics and manifest extractors
└── test_sdk_ingestion.py   # NEW: Tests for rules truncation and semantic ingestion
```

---

## 5. Architectural Design & Code Style

### Data Contracts

```python
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any

@dataclass
class ProjectManifest:
    root_path: str
    primary_language: str
    tech_stack: List[str] = field(default_factory=list)
    test_framework: Optional[str] = None
    build_commands: Dict[str, str] = field(default_factory=dict)
    documentation_files: List[str] = field(default_factory=list)
    detected_rules: List[str] = field(default_factory=list)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "root_path": self.root_path,
            "primary_language": self.primary_language,
            "tech_stack": self.tech_stack,
            "test_framework": self.test_framework,
            "build_commands": self.build_commands,
            "documentation_files": self.documentation_files,
            "detected_rules": self.detected_rules,
            "extra_metadata": self.extra_metadata,
        }
```

### Heuristic Extractor Rules

1. **Python:** Look for `pyproject.toml`, `setup.py`, `requirements.txt`, `Pipfile`. Extract `pytest`/`unittest`, linter configs (`ruff`, `flake8`, `mypy`).
2. **Node/TypeScript:** Look for `package.json`, `tsconfig.json`. Extract `scripts.test`, `scripts.build`, frameworks (`next`, `react`, `express`, `vue`), package manager (`npm`, `pnpm`, `yarn`).
3. **Rust:** Look for `Cargo.toml`. Extract cargo test, dependencies.
4. **Go:** Look for `go.mod`. Extract module name, go version.
5. **Generic:** Look for `Makefile`, `Dockerfile`, `.editorconfig`.
6. **Documentation Scanner:** Read `README.md`, `CONTRIBUTING.md`, `docs/**/*.md` (bounded to first 50KB to prevent memory exhaustion). Extract markdown `# ` and `## ` headings to identify architecture and rules.

### Tier 1 vs Tier 2 Ingestion Strategy

```python
# Tier 1: Level 1 Rules (<3072 bytes)
# Synthesizes tech_stack, test_framework, build_commands, and top 5 detected_rules.
# Strictly truncated via StructuralTruncator(max_bytes=3072).

# Tier 2: Semantic Memory Ingestion
# Splits documentation_files into sections (by markdown headings) and indexes each
# into SemanticMemory with metadata={"source": doc_path, "type": "brownfield_doc"}.
```

---

## 6. Testing Strategy

1. **Unit Tests (`tests/test_sdk_scanner.py`):**
   - Mock directory structures for Python, Node.js, and multi-language repos.
   - Verify correct detection of languages, test commands, frameworks.
   - Verify resilience against missing files, empty files, and permission errors.
2. **Ingestion & Budget Tests (`tests/test_sdk_ingestion.py`):**
   - Verify that generated Tier 1 `.agent/rules.md` is strictly $\le 3072$ bytes and scores 100/100 on `MarkdownRulesCritic`.
   - Verify that documentation sections are correctly indexed into `SemanticMemory` SQLite database and retrievable via `memory.search()`.
3. **CLI Integration Tests:**
   - Verify `python3 -m agent_system.cli.main scan --root <mock_dir> --json` produces valid JSON.
   - Verify `agent-system init --auto` generates both files and memory without human prompts.

---

## 7. Boundaries

- **Always:**
  - Keep `agent_system/sdk/scanner.py` 100% standard library (no `pip install` required).
  - Guarantee Tier 1 output $\le 3072$ bytes via `StructuralTruncator`.
  - Pass 100% of the entire test suite before marking work complete.
  - Make `scan` strictly read-only (zero file mutations on source code).
- **Ask First:**
  - Modifying the core `SemanticMemory` schema or table definition.
  - Adding support for proprietary / closed-source manifest formats.
- **Never:**
  - Edit or delete user source code files in the scanned project.
  - Call remote third-party AI APIs or cloud endpoints during scanning.
  - Silence or bypass `CriticEngine` checks.

---

## 8. Success Criteria

1. [ ] `CodebaseScanner` reliably identifies Python, Node.js/TS, Rust, and Go project manifests.
2. [ ] `agent-system scan --json` outputs structured metadata in $<200$ms for typical repositories ($<10,000$ files).
3. [ ] Tier 1 `.agent/rules.md` synthesized output never exceeds 3072 bytes.
4. [ ] Tier 2 ingestion populates `SemanticMemory` with searchable documentation chunks.
5. [ ] 100% test pass rate across all existing (83/83) and new test suites.

---

## 9. Open Questions

1. **Rule File Destination:** When creating Tier 1 rules for brownfield projects, should we default to `.agent/rules.md` (recommended) or create symlinks for `AGENTS.md` / `CLAUDE.md` / `GEMINI.md`?
2. **Doc Chunking Granularity:** For Tier 2 Semantic Memory, should doc chunking be split per H2 (`## `) heading or stored as whole files? (Splitting by H2 produces much higher semantic search precision).
