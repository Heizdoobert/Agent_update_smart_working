"""Python AST Static Rule Critic Adapter."""

from __future__ import annotations

import ast
from typing import Any, Dict, List, Optional, Set

from agent_system.core.contracts import (
    CriticProtocol,
    CriticReport,
    CriticStatus,
    CriticVerdict,
    DiagnosticItem,
)


class PythonAstAuditor(ast.NodeVisitor):
    """AST NodeVisitor enforcing static safety and compliance rules on Python code."""

    def __init__(
        self,
        forbidden_modules: Optional[Set[str]] = None,
        forbidden_calls: Optional[Set[str]] = None,
        require_type_annotations: bool = False,
    ) -> None:
        self.forbidden_modules = forbidden_modules or {"pdb", "ipdb"}
        self.forbidden_calls = forbidden_calls or {"eval", "exec", "breakpoint"}
        self.require_type_annotations = require_type_annotations
        self.diagnostics: List[DiagnosticItem] = []

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in self.forbidden_modules:
                self.diagnostics.append(
                    DiagnosticItem(
                        code="FORBIDDEN_IMPORT",
                        message=f"Import of forbidden module '{alias.name}' detected.",
                        severity="ERROR",
                        line=node.lineno,
                        column=node.col_offset,
                        fix_recipe=f"Remove import '{alias.name}' and avoid debugging hooks in production code.",
                    )
                )
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in self.forbidden_modules:
                self.diagnostics.append(
                    DiagnosticItem(
                        code="FORBIDDEN_IMPORT",
                        message=f"Import from forbidden module '{node.module}' detected.",
                        severity="ERROR",
                        line=node.lineno,
                        column=node.col_offset,
                        fix_recipe=f"Remove import from '{node.module}'.",
                    )
                )
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        call_name: Optional[str] = None
        if isinstance(node.func, ast.Name):
            if node.func.id in self.forbidden_calls or node.func.id == "breakpoint":
                call_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in {"builtins", "__builtins__"}
                and (
                    node.func.attr in self.forbidden_calls
                    or node.func.attr in {"eval", "exec", "breakpoint"}
                )
            ):
                call_name = f"{node.func.value.id}.{node.func.attr}"
            elif node.func.attr in self.forbidden_calls or node.func.attr in {"eval", "exec", "breakpoint"}:
                call_name = node.func.attr
        elif (
            isinstance(node.func, ast.Call)
            and isinstance(node.func.func, ast.Name)
            and node.func.func.id == "getattr"
        ):
            if (
                len(node.func.args) >= 2
                and isinstance(node.func.args[1], ast.Constant)
                and (
                    node.func.args[1].value in self.forbidden_calls
                    or node.func.args[1].value in {"eval", "exec", "breakpoint"}
                )
            ):
                call_name = f"getattr(..., '{node.func.args[1].value}')"

        if call_name:
            self.diagnostics.append(
                DiagnosticItem(
                    code="FORBIDDEN_CALL",
                    message=f"Dangerous call to '{call_name}()' detected.",
                    severity="ERROR",
                    line=node.lineno,
                    column=node.col_offset,
                    fix_recipe=f"Replace '{call_name}()' with safe static alternatives.",
                )
            )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        if self.require_type_annotations and node.returns is None:
            func_type = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
            self.diagnostics.append(
                DiagnosticItem(
                    code="MISSING_RETURN_TYPE",
                    message=f"Function '{node.name}' lacks return type annotation.",
                    severity="WARNING",
                    line=node.lineno,
                    column=node.col_offset,
                    fix_recipe=f"Add return type annotation to {func_type} {node.name}(...) -> ...",
                )
            )
        self.generic_visit(node)

    visit_AsyncFunctionDef = visit_FunctionDef


class PythonAstCritic:
    """Critic adapter for validating Python source code via static AST inspection."""

    def __init__(
        self,
        forbidden_modules: Optional[List[str]] = None,
        forbidden_calls: Optional[List[str]] = None,
        require_type_annotations: bool = False,
    ) -> None:
        self.forbidden_modules = set(forbidden_modules or ["pdb", "ipdb"])
        self.forbidden_calls = set(forbidden_calls or ["eval", "exec", "breakpoint"])
        self.require_type_annotations = require_type_annotations

    def validate(
        self, artifact: Any, context: Optional[Dict[str, Any]] = None
    ) -> CriticReport:
        if not isinstance(artifact, str):
            return CriticReport(
                verdict=CriticVerdict(
                    status=CriticStatus.PASS,
                    score=100.0,
                    summary="Artifact is not a string; bypassed Python AST checking.",
                ),
                diagnostics=[],
                raw_artifact=str(artifact),
            )

        # Check if context explicitly indicates non-python
        is_python_expected = True
        if context and context.get("language") and context.get("language") != "python":
            is_python_expected = False

        try:
            tree = ast.parse(artifact)
        except SyntaxError as e:
            if not is_python_expected:
                # Non-python artifact, gracefully bypass
                return CriticReport(
                    verdict=CriticVerdict(
                        status=CriticStatus.PASS,
                        score=100.0,
                        summary="Non-Python artifact bypassed AST critic gracefully.",
                    ),
                    diagnostics=[],
                    raw_artifact=artifact,
                )

            # Python syntax error
            diag = DiagnosticItem(
                code="PYTHON_SYNTAX_ERROR",
                message=f"SyntaxError: {e.msg} at line {e.lineno}",
                severity="ERROR",
                line=e.lineno,
                column=e.offset,
                fix_recipe="Fix Python syntax error according to message.",
            )
            return CriticReport(
                verdict=CriticVerdict(
                    status=CriticStatus.REJECT,
                    score=0.0,
                    summary=f"Python syntax error on line {e.lineno}",
                ),
                diagnostics=[diag],
                suggestions=[diag.fix_recipe or ""],
                raw_artifact=artifact,
            )

        auditor = PythonAstAuditor(
            forbidden_modules=self.forbidden_modules,
            forbidden_calls=self.forbidden_calls,
            require_type_annotations=self.require_type_annotations,
        )
        auditor.visit(tree)

        num_errors = sum(1 for d in auditor.diagnostics if d.severity == "ERROR")
        num_warnings = sum(1 for d in auditor.diagnostics if d.severity == "WARNING")

        score = max(0.0, 100.0 - (num_errors * 30.0 + num_warnings * 10.0))
        status = CriticStatus.PASS if num_errors == 0 and score >= 80.0 else CriticStatus.REJECT

        suggestions = [
            f"[Line {d.line or '?'}] {d.fix_recipe}"
            for d in auditor.diagnostics
            if d.fix_recipe
        ]

        return CriticReport(
            verdict=CriticVerdict(
                status=status,
                score=round(score, 2),
                summary=f"AST inspection: {status.value} (Errors: {num_errors}, Warnings: {num_warnings})",
            ),
            diagnostics=auditor.diagnostics,
            suggestions=suggestions,
            raw_artifact=artifact,
        )
