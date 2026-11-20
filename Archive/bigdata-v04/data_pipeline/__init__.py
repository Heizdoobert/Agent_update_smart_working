"""
data_pipeline package
---------------------
Core data processing and chunking engine with bounded memory safety.
"""

from .chunker import QuoteAwareChunker
from .worker import DuckDBWorker

__all__ = ["QuoteAwareChunker", "DuckDBWorker"]
