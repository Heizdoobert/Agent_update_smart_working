"""
distributed_queue package
-------------------------
Production queue orchestration and resilient task dispatching.
"""

from .task_dispatcher import TaskDispatcher

__all__ = ["TaskDispatcher"]
