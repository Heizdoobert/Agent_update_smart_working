# Package-level re-exports for memory_layer
from ._client import get_client, reset_client, _client_instance
from .agent_hooks import pre_task_hook, post_task_hook
from .api import (
    compute_blake3_uid,
    mark_insight_as_kb,
    mark_insight_as_trash,
    get_ready_vectors,
    get_kb_vectors,
    purge_trash,
    purge_shortterm,
    set_status_for_task,
    mark_insight,
)

__all__ = [
    "compute_blake3_uid",
    "get_client",
    "reset_client",
    "_client_instance",
    "pre_task_hook",
    "post_task_hook",
    "mark_insight_as_kb",
    "mark_insight_as_trash",
    "get_ready_vectors",
    "get_kb_vectors",
    "purge_trash",
    "purge_shortterm",
    "set_status_for_task",
    "mark_insight",
]
