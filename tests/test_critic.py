"""Tests for Critic Coordinator and PythonAstCritic adapter."""

import pytest

from agent_system.core.contracts import CriticStatus
from agent_system.reflection.adapters.python_ast import PythonAstCritic
from agent_system.reflection.critic import CriticEngine, SchemaCritic


def test_schema_critic():
    critic = SchemaCritic(required_keys=["name", "version", "entrypoint"])

    # Valid dictionary
    valid_data = {"name": "agent", "version": "1.0", "entrypoint": "main.py"}
    report = critic.validate(valid_data)
    assert report.is_passed is True
    assert report.verdict.score == 100.0

    # Missing keys in JSON string
    invalid_json = '{"name": "agent"}'
    report2 = critic.validate(invalid_json)
    assert report2.verdict.status == CriticStatus.REJECT
    assert len(report2.diagnostics) == 2  # missing version and entrypoint


def test_python_ast_critic_clean_code():
    clean_code = """
def compute_sum(a: int, b: int) -> int:
    \"\"\"Compute sum of two numbers.\"\"\"
    return a + b
"""
    critic = PythonAstCritic(require_type_annotations=True)
    report = critic.validate(clean_code)
    assert report.verdict.status == CriticStatus.PASS
    assert report.verdict.score == 100.0
    assert len(report.diagnostics) == 0


def test_python_ast_critic_forbidden_rules():
    bad_code = """
import pdb

def execute_user_query(query: str):
    eval(query)
"""
    critic = PythonAstCritic(require_type_annotations=True)
    report = critic.validate(bad_code)

    assert report.verdict.status == CriticStatus.REJECT
    assert report.verdict.score < 80.0

    codes = [d.code for d in report.diagnostics]
    assert "FORBIDDEN_IMPORT" in codes
    assert "FORBIDDEN_CALL" in codes
    assert "MISSING_RETURN_TYPE" in codes
    assert len(report.suggestions) >= 2


def test_python_ast_critic_non_python_graceful():
    markdown_content = "# Title\n\nThis is a markdown doc with unquoted symbols: { [ ( <>"
    critic = PythonAstCritic()
    # Explicit language context
    report = critic.validate(markdown_content, context={"language": "markdown"})
    assert report.verdict.status == CriticStatus.PASS


def test_critic_engine_aggregation():
    engine = CriticEngine()
    engine.register_critic(SchemaCritic(required_keys=["role"]))
    engine.register_critic(PythonAstCritic())

    payload = {"role": "worker"}
    report = engine.evaluate(payload)
    assert report.verdict.status == CriticStatus.PASS
    assert report.verdict.score == 100.0
