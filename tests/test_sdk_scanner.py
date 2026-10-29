"""Tests for CodebaseScanner & ProjectManifest in agent_system.sdk.scanner."""
import json
import os
import tempfile
from pathlib import Path
import pytest

from agent_system.sdk.scanner import CodebaseScanner, ProjectManifest


def test_project_manifest_defaults_and_serialization():
    manifest = ProjectManifest(
        root_path="/tmp/sample",
        primary_language="Python",
        tech_stack=["Python", "pytest"],
        test_framework="pytest",
        build_commands={"test": "pytest"},
        documentation_files=["README.md"],
        detected_rules=["Must pass tests"],
        extra_metadata={"custom": 123},
    )
    d = manifest.to_dict()
    assert d["primary_language"] == "Python"
    assert "pytest" in d["tech_stack"]
    assert d["test_framework"] == "pytest"
    assert d["build_commands"]["test"] == "pytest"
    assert d["documentation_files"] == ["README.md"]
    assert d["detected_rules"] == ["Must pass tests"]
    assert d["extra_metadata"]["custom"] == 123


def test_scanner_python_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Create pyproject.toml
        pyproject = tmppath / "pyproject.toml"
        pyproject.write_text("""[project]
name = "my_app"
dependencies = ["fastapi", "uvicorn"]

[tool.pytest.ini_options]
testpaths = ["tests"]
""")
        # Create a README
        readme = tmppath / "README.md"
        readme.write_text("""# My App
A high-performance FastAPI service.

## Architecture
Microservice backend with Redis cache.

## Rules
- Always use type hints
- Never commit secrets
""")
        scanner = CodebaseScanner(root_path=tmppath)
        manifest = scanner.scan()

        assert manifest.primary_language == "Python"
        assert "Python" in manifest.tech_stack
        assert "fastapi" in [t.lower() for t in manifest.tech_stack]
        assert manifest.test_framework == "pytest"
        assert "pytest" in manifest.build_commands.get("test", "")
        assert "README.md" in manifest.documentation_files
        assert any("type hints" in r.lower() for r in manifest.detected_rules)


def test_scanner_node_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Create package.json
        pkg_json = tmppath / "package.json"
        pkg_json.write_text(json.dumps({
            "name": "frontend-app",
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "test": "jest --coverage"
            },
            "dependencies": {
                "next": "14.0.0",
                "react": "18.2.0"
            },
            "devDependencies": {
                "typescript": "^5.0.0",
                "jest": "^29.0.0"
            }
        }))
        scanner = CodebaseScanner(root_path=tmppath)
        manifest = scanner.scan()

        assert manifest.primary_language in ("TypeScript", "JavaScript")
        assert any(t.lower() == "next" for t in manifest.tech_stack)
        assert any(t.lower() == "react" for t in manifest.tech_stack)
        assert manifest.test_framework == "jest"
        assert manifest.build_commands.get("test") == "jest --coverage"
        assert manifest.build_commands.get("build") == "next build"


def test_scanner_rust_and_go_and_makefile():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        (tmppath / "Cargo.toml").write_text("""[package]
name = "rusty_tool"
version = "0.1.0"
edition = "2021"
""")
        (tmppath / "Makefile").write_text("""all: build

build:
\tcargo build --release

test:
\tcargo test
""")
        scanner = CodebaseScanner(root_path=tmppath)
        manifest = scanner.scan()

        assert manifest.primary_language == "Rust"
        assert "Rust" in manifest.tech_stack
        assert manifest.build_commands.get("test") == "cargo test"
        assert "Makefile" in manifest.extra_metadata.get("manifest_files", [])


def test_scanner_bounded_read_and_resilience():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        # Large file > 50KB
        huge_doc = tmppath / "README.md"
        huge_doc.write_text("# Title\n" + ("x" * 60000) + "\n## Section 2\n")

        # Corrupted non-utf8 file
        bad_file = tmppath / "CONTRIBUTING.md"
        bad_file.write_bytes(b"\xff\xfe\xfa\x80InvalidUTF8")

        scanner = CodebaseScanner(root_path=tmppath)
        manifest = scanner.scan()

        # Scanner should not crash
        assert isinstance(manifest, ProjectManifest)
        assert "README.md" in manifest.documentation_files


def test_scanner_empty_repo():
    with tempfile.TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)
        scanner = CodebaseScanner(root_path=tmppath)
        manifest = scanner.scan()

        assert manifest.primary_language == "Unknown"
        assert manifest.tech_stack == []
        assert manifest.documentation_files == []
