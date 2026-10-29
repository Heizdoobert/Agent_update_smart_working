"""Codebase scanner and heuristic analyzer for brownfield projects.

100% Python standard library. Extracts tech stack, testing workflows,
manifest details, and documentation conventions from existing repositories.
"""
from dataclasses import dataclass, field
import json
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set

MAX_DOC_READ_BYTES = 50_000


@dataclass
class ProjectManifest:
    """Structured representation of detected brownfield repository metadata."""

    root_path: str
    primary_language: str = "Unknown"
    tech_stack: List[str] = field(default_factory=list)
    test_framework: Optional[str] = None
    build_commands: Dict[str, str] = field(default_factory=dict)
    documentation_files: List[str] = field(default_factory=list)
    detected_rules: List[str] = field(default_factory=list)
    extra_metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert manifest to serializable dictionary."""
        return {
            "root_path": self.root_path,
            "primary_language": self.primary_language,
            "tech_stack": list(self.tech_stack),
            "test_framework": self.test_framework,
            "build_commands": dict(self.build_commands),
            "documentation_files": list(self.documentation_files),
            "detected_rules": list(self.detected_rules),
            "extra_metadata": dict(self.extra_metadata),
        }


class CodebaseScanner:
    """Scans and analyzes an existing repository without external dependencies."""

    def __init__(self, root_path: str | Path = "."):
        self.root_path = Path(root_path).resolve()

    def scan(self) -> ProjectManifest:
        """Execute scan across root directory and return populated ProjectManifest."""
        manifest = ProjectManifest(root_path=str(self.root_path))
        manifest_files: List[str] = []
        stack_set: Set[str] = set()

        if not self.root_path.exists() or not self.root_path.is_dir():
            manifest.extra_metadata["manifest_files"] = manifest_files
            return manifest

        # 1. Detect Python
        self._detect_python(manifest, stack_set, manifest_files)

        # 2. Detect Node / TypeScript
        self._detect_node(manifest, stack_set, manifest_files)

        # 3. Detect Rust
        self._detect_rust(manifest, stack_set, manifest_files)

        # 4. Detect Go
        self._detect_go(manifest, stack_set, manifest_files)

        # 5. Detect Generic build tools (Makefile, Dockerfile)
        self._detect_generic_build(manifest, manifest_files)

        # Finalize tech stack & primary language if not already decided
        manifest.tech_stack = sorted(stack_set)
        if manifest.primary_language == "Unknown" and manifest.tech_stack:
            for lang in ["Python", "TypeScript", "JavaScript", "Rust", "Go"]:
                if lang in manifest.tech_stack:
                    manifest.primary_language = lang
                    break

        # 6. Scan documentation and extract rules/conventions
        self._scan_documentation(manifest)

        manifest.extra_metadata["manifest_files"] = manifest_files
        return manifest

    def _safe_read_text(self, path: Path, max_bytes: int = MAX_DOC_READ_BYTES) -> str:
        """Safely read text with byte limit and error suppression."""
        try:
            with open(path, "rb") as f:
                data = f.read(max_bytes)
            return data.decode("utf-8", errors="ignore")
        except (IOError, OSError):
            return ""

    def _detect_python(
        self,
        manifest: ProjectManifest,
        stack_set: Set[str],
        manifest_files: List[str],
    ) -> None:
        """Check for Python manifests (pyproject.toml, setup.py, requirements.txt)."""
        pyproject = self.root_path / "pyproject.toml"
        setup_py = self.root_path / "setup.py"
        req_txt = self.root_path / "requirements.txt"

        has_py = False
        if pyproject.is_file():
            has_py = True
            manifest_files.append("pyproject.toml")
            content = self._safe_read_text(pyproject)
            name_match = re.search(r'name\s*=\s*["\']([^"\']+)["\']', content)
            if name_match and not manifest.extra_metadata.get("project_name"):
                manifest.extra_metadata["project_name"] = name_match.group(1)
            if "pytest" in content:
                manifest.test_framework = "pytest"
                manifest.build_commands.setdefault("test", "pytest")
            # Heuristic dependencies extract
            for dep in ["fastapi", "django", "flask", "numpy", "pandas", "torch", "pydantic"]:
                if dep in content.lower():
                    stack_set.add(dep)

        if setup_py.is_file():
            has_py = True
            manifest_files.append("setup.py")

        if req_txt.is_file():
            has_py = True
            manifest_files.append("requirements.txt")
            content = self._safe_read_text(req_txt)
            for line in content.splitlines():
                line = line.strip().split("==")[0].split(">=")[0].strip()
                if line and not line.startswith("#"):
                    if line.lower() in ["fastapi", "django", "flask", "numpy", "pandas", "pytest"]:
                        stack_set.add(line)

        if has_py:
            stack_set.add("Python")
            if manifest.primary_language == "Unknown":
                manifest.primary_language = "Python"
            if not manifest.test_framework:
                # Check for tests directory
                if (self.root_path / "tests").is_dir():
                    manifest.test_framework = "pytest"
                    manifest.build_commands.setdefault("test", "pytest")

    def _detect_node(
        self,
        manifest: ProjectManifest,
        stack_set: Set[str],
        manifest_files: List[str],
    ) -> None:
        """Check for Node.js / TypeScript (package.json, tsconfig.json)."""
        pkg_json_path = self.root_path / "package.json"
        tsconfig_path = self.root_path / "tsconfig.json"

        is_ts = tsconfig_path.is_file()
        if is_ts:
            manifest_files.append("tsconfig.json")
            stack_set.add("TypeScript")

        if pkg_json_path.is_file():
            manifest_files.append("package.json")
            try:
                content = self._safe_read_text(pkg_json_path)
                data = json.loads(content)
                if "name" in data and not manifest.extra_metadata.get("project_name"):
                    manifest.extra_metadata["project_name"] = str(data["name"])
                scripts = data.get("scripts", {})
                if "test" in scripts:
                    manifest.build_commands["test"] = scripts["test"]
                    if "jest" in scripts["test"]:
                        manifest.test_framework = "jest"
                    elif "vitest" in scripts["test"]:
                        manifest.test_framework = "vitest"
                    else:
                        manifest.test_framework = "npm test"
                if "build" in scripts:
                    manifest.build_commands["build"] = scripts["build"]
                if "dev" in scripts:
                    manifest.build_commands["dev"] = scripts["dev"]

                deps = {**data.get("dependencies", {}), **data.get("devDependencies", {})}
                for dep in deps:
                    dep_lower = dep.lower()
                    if dep_lower in ["next", "react", "vue", "express", "jest", "vitest", "tailwind"]:
                        stack_set.add(dep)

                if is_ts or "typescript" in deps:
                    manifest.primary_language = "TypeScript"
                    stack_set.add("TypeScript")
                elif manifest.primary_language == "Unknown":
                    manifest.primary_language = "JavaScript"
                    stack_set.add("JavaScript")
            except (json.JSONDecodeError, ValueError):
                stack_set.add("JavaScript")

    def _detect_rust(
        self,
        manifest: ProjectManifest,
        stack_set: Set[str],
        manifest_files: List[str],
    ) -> None:
        """Check for Rust manifests (Cargo.toml)."""
        cargo = self.root_path / "Cargo.toml"
        if cargo.is_file():
            manifest_files.append("Cargo.toml")
            stack_set.add("Rust")
            manifest.primary_language = "Rust"
            manifest.test_framework = "cargo test"
            manifest.build_commands.setdefault("test", "cargo test")
            manifest.build_commands.setdefault("build", "cargo build")

    def _detect_go(
        self,
        manifest: ProjectManifest,
        stack_set: Set[str],
        manifest_files: List[str],
    ) -> None:
        """Check for Go manifests (go.mod)."""
        gomod = self.root_path / "go.mod"
        if gomod.is_file():
            manifest_files.append("go.mod")
            stack_set.add("Go")
            manifest.primary_language = "Go"
            manifest.test_framework = "go test"
            manifest.build_commands.setdefault("test", "go test ./...")

    def _detect_generic_build(
        self,
        manifest: ProjectManifest,
        manifest_files: List[str],
    ) -> None:
        """Check for Makefile or Dockerfile."""
        makefile = self.root_path / "Makefile"
        if makefile.is_file():
            manifest_files.append("Makefile")
            content = self._safe_read_text(makefile)
            if re.search(r"^test:", content, re.MULTILINE):
                manifest.build_commands.setdefault("make_test", "make test")

        dockerfile = self.root_path / "Dockerfile"
        if dockerfile.is_file():
            manifest_files.append("Dockerfile")

    def _scan_documentation(self, manifest: ProjectManifest) -> None:
        """Find documentation files and extract headings and rules."""
        candidate_names = ["README.md", "CONTRIBUTING.md", "CLAUDE.md", "AGENTS.md", "GEMINI.md"]
        for name in candidate_names:
            p = self.root_path / name
            if p.is_file():
                manifest.documentation_files.append(name)
                self._extract_rules_from_file(p, manifest)

        # Check docs/ directory for markdown
        docs_dir = self.root_path / "docs"
        if docs_dir.is_dir():
            try:
                for entry in docs_dir.rglob("*.md"):
                    if entry.is_file():
                        rel = str(entry.relative_to(self.root_path))
                        manifest.documentation_files.append(rel)
                        if len(manifest.detected_rules) < 15:
                            self._extract_rules_from_file(entry, manifest)
            except (IOError, OSError):
                pass

    def _extract_rules_from_file(self, file_path: Path, manifest: ProjectManifest) -> None:
        """Parse markdown file to extract rules or bullet guidelines."""
        content = self._safe_read_text(file_path)
        if not content:
            return

        in_rule_section = False
        rule_keywords = ["rule", "convention", "guideline", "standard", "protocol", "architecture"]

        for line in content.splitlines():
            line_str = line.strip()
            # Check headings
            if line_str.startswith("#"):
                header_text = line_str.lstrip("#").strip().lower()
                in_rule_section = any(k in header_text for k in rule_keywords)
                continue

            # Extract bullet items
            if in_rule_section and (line_str.startswith("- ") or line_str.startswith("* ") or re.match(r"^\d+\.\s+", line_str)):
                item_text = re.sub(r"^[-*]|\d+\.\s*", "", line_str).strip()
                if item_text and len(item_text) > 5 and item_text not in manifest.detected_rules:
                    manifest.detected_rules.append(item_text)
                    if len(manifest.detected_rules) >= 20:
                        break
