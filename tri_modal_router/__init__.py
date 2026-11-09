"""
tri_modal_router package
------------------------
Token economics routing engine.
"""

from .router import ExecutionTier, TaskDomain, route_execution_tier

__all__ = ["ExecutionTier", "TaskDomain", "route_execution_tier"]
