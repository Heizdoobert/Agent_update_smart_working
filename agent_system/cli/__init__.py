"""CLI package for agent_system."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_system.cli.main import main


def __getattr__(name: str) -> Any:
    if name == "main":
        from agent_system.cli.main import main
        return main
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["main"]
