"""Tests for In-Memory Self-Reflection Engine."""

import pytest

from agent_system.core.contracts import CriticStatus, DiagnosticItem
from agent_system.reflection.adapters.python_ast import PythonAstCritic
from agent_system.reflection.critic import CriticEngine
from agent_system.reflection.reflector import SelfReflector


def test_reflection_clean_code_immediate_pass():
    critic = CriticEngine([PythonAstCritic()])
    reflector = SelfReflector(critic)

    clean_code = "def add(x: int, y: int) -> int:\n    return x + y\n"
    res = reflector.reflect_and_patch(clean_code)

    assert res.success is True
    assert res.iterations == 1
    assert res.patched is False


def test_reflection_auto_patches_violations():
    critic = CriticEngine([PythonAstCritic(require_type_annotations=True)])
    reflector = SelfReflector(critic)

    # Has forbidden import pdb and missing return type
    dirty_code = "import pdb\n\ndef calculate(a: int, b: int):\n    return a * b\n"
    res = reflector.reflect_and_patch(dirty_code)

    assert res.success is True
    assert res.iterations == 2
    assert res.patched is True
    assert "pdb" not in res.final_artifact or "# [Self-Reflection" in res.final_artifact
    assert "-> Any:" in res.final_artifact


def test_reflection_bounds_iterations_on_unresolvable():
    critic = CriticEngine([PythonAstCritic()])
    reflector = SelfReflector(critic, max_iterations=3)

    # Severe unresolvable syntax error
    broken_code = "def invalid syntax {{{(()"
    res = reflector.reflect_and_patch(broken_code)

    assert res.success is False
    assert res.iterations <= 3
    assert "Unresolvable diagnostics" in res.message or "Max iteration" in res.message


def test_reflection_oscillation_detection():
    critic = CriticEngine([PythonAstCritic()])

    # Patcher that alternates between two states
    def oscillating_patcher(artifact: str, diags: list):
        if "state_A" in artifact:
            return "import pdb\n# state_B"
        return "import pdb\n# state_A"

    reflector = SelfReflector(critic, custom_patcher=oscillating_patcher, max_iterations=4)
    res = reflector.reflect_and_patch("import pdb\n# state_A")

    assert res.success is False
    assert "Oscillation detected" in res.message
