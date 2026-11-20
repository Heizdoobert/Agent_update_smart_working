"""
data_pipeline.worker
--------------------
Production-grade DuckDB Worker implementing bounded memory allocation
and NVMe automatic disk spilling to eliminate Linux OOM (Exit 137).
"""

import os
import io
import tempfile
from typing import List, Dict, Any, Optional
import duckdb


class DuckDBWorker:
    """Bounded-memory analytical worker powered by DuckDB.

    Spills intermediate hash tables and external sorts to disk when RAM is constrained.
    """

    def __init__(
        self,
        max_memory_mb: int = 2048,
        threads: int = 2,
        temp_dir: Optional[str] = None,
    ):
        self.max_memory_mb = max_memory_mb
        self.threads = threads
        self.temp_dir = temp_dir or os.path.join(tempfile.gettempdir(), "duckdb_spill")
        os.makedirs(self.temp_dir, exist_ok=True)

        self._con = duckdb.connect()
        self._con.execute(f"PRAGMA max_memory='{self.max_memory_mb}MB';")
        self._con.execute(f"PRAGMA temp_directory='{self.temp_dir}';")
        self._con.execute(f"PRAGMA threads={self.threads};")

    def query(self, sql_query: str, parameters: Optional[List[Any]] = None) -> List[Dict[str, Any]]:
        """Execute arbitrary SQL query safely within memory limits and return list of dicts."""
        params = parameters or []
        cursor = self._con.execute(sql_query, params)
        if cursor.description is None:
            return []
        cols = [desc[0] for desc in cursor.description]
        rows = cursor.fetchall()
        return [dict(zip(cols, row)) for row in rows]

    def process_csv_payload(
        self,
        csv_bytes: bytes,
        query: str,
        table_name: str = "chunk_data",
    ) -> List[Dict[str, Any]]:
        """Register CSV bytes as an in-memory virtual table and execute transformation query.

        Query should reference ``table_name`` (default: ``chunk_data``).
        """
        if not csv_bytes or not csv_bytes.strip():
            return []
        # Register in-memory CSV stream via DuckDB relation
        rel = self._con.read_csv(io.BytesIO(csv_bytes), header=True)
        self._con.register(table_name, rel)
        return self.query(query)

    def process_csv_file_slice(
        self,
        file_path: str,
        query: str,
        table_name: str = "chunk_data",
    ) -> List[Dict[str, Any]]:
        """Read CSV directly from file path using DuckDB's multi-threaded morsel scanner."""
        rel = self._con.read_csv(file_path, header=True)
        self._con.register(table_name, rel)
        return self.query(query)

    def close(self):
        """Close connection and clean up resources."""
        try:
            self._con.close()
        except Exception:
            pass
