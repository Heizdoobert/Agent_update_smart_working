"""Optional local text embeddings. Returns None when fastembed is absent, so the core stays zero-dependency."""

from __future__ import annotations

import os
from array import array
from typing import List, Optional

MODEL = "snowflake/snowflake-arctic-embed-xs"  # 384-dim, ~90MB ONNX, local CPU
_model = None
_unavailable = False


QUERY_PREFIX = "Represent this sentence for searching relevant passages: "  # required by arctic-embed for queries


def embed(texts: List[str], query: bool = False) -> Optional[List[List[float]]]:
    """Embed texts (query=True for search queries), or None if embeddings are disabled or fastembed is missing."""
    global _model, _unavailable
    if _unavailable or os.environ.get("AGENT_SYSTEM_NO_EMBED") == "1":
        return None
    if _model is None:
        try:
            from fastembed import TextEmbedding

            _model = TextEmbedding(MODEL)
        except Exception:
            _unavailable = True
            return None
    prefix = QUERY_PREFIX if query else ""
    return [v.tolist() for v in _model.embed([prefix + str(t) for t in texts])]


def pack(vec: List[float]) -> bytes:
    return array("f", vec).tobytes()


def unpack(blob: bytes) -> List[float]:
    a = array("f")
    a.frombytes(blob)
    return a.tolist()


def cosine(a: List[float], b: List[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    return dot / (na * nb) if na and nb else 0.0
