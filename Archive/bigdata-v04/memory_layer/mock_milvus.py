# Mock implementation of pymilvus.MilvusClient for test environments
"""A lightweight in‑memory mock of MilvusClient used when the real
pymilvus package is unavailable. It implements the subset of the API
required by the memory_layer package and its test suite.
"""

import re
import time
from typing import Any, Dict, List

_mock_id_counter = int(time.time() * 1000)


class MilvusClient:
    def __init__(self, uri: str = "memory://") -> None:
        self.uri = uri
        self._collections: Dict[str, List[Dict[str, Any]]] = {}
        self._meta: Dict[str, Dict[str, Any]] = {}

    # ---------- collection management ----------
    def has_collection(self, name: str) -> bool:
        return name in self._collections

    def create_collection(
        self,
        collection_name: str,
        dimension: int,
        metric_type: str = "L2",
        auto_id: bool = True,
    ) -> None:
        self._collections[collection_name] = []
        self._meta[collection_name] = {"dimension": dimension, "metric_type": metric_type, "auto_id": auto_id}

    def load_collection(self, name: str) -> None:
        # No-op for in‑memory mock
        pass

    # ---------- data operations ----------
    def insert(self, collection_name: str, data: List[Dict[str, Any]]) -> Dict[str, Any]:
        global _mock_id_counter
        if collection_name not in self._collections:
            raise ValueError(f"Collection {collection_name} does not exist")
        inserted_ids = []
        for entry in data:
            # Simulate auto_id if not provided
            if "insight_id" not in entry or not entry["insight_id"]:
                _mock_id_counter += 1
                entry["insight_id"] = _mock_id_counter
            inserted_ids.append(entry["insight_id"])
            self._collections[collection_name].append(entry.copy())
        return {"insert_count": len(inserted_ids), "ids": inserted_ids}

    def _match_expr(self, item: Dict[str, Any], expr: str) -> bool:
        """Small expression parser supporting:
        - empty or '1==1': match all
        - equality: field == value (with optional quotes, handles empty strings)
        - like: field like 'prefix%'
        """
        if not expr:
            return True
        expr = expr.strip()
        if not expr or expr == "1==1" or expr == "1 == 1":
            return True

        # Equality check: field == value (supports empty string values)
        eq_match = re.fullmatch(r"(\w+)\s*==\s*'?([^']*)'?", expr)
        if eq_match:
            field, value = eq_match.groups()
            return str(item.get(field, "")) == value

        # Like pattern: field like 'prefix%'
        like_match = re.fullmatch(r"(\w+)\s+like\s+'([^']+)'", expr, re.IGNORECASE)
        if like_match:
            field, pattern = like_match.groups()
            prefix = pattern.rstrip("%")
            return str(item.get(field, "")).startswith(prefix)

        return False

    def query(
        self,
        collection_name: str,
        filter: str = "",
        output_fields: List[str] = None,
        limit: int = None,
        **kwargs: Any,
    ) -> List[Dict[str, Any]]:
        if collection_name not in self._collections:
            raise ValueError(f"Collection {collection_name} does not exist")
        expr = filter or kwargs.get("expr", "")
        results = []
        fields = output_fields or []
        wildcard = "*" in fields
        for item in self._collections[collection_name]:
            if self._match_expr(item, expr):
                if wildcard:
                    row = item.copy()
                else:
                    row = {field: item.get(field) for field in fields}
                results.append(row)
                if limit is not None and len(results) >= limit:
                    break
        return results

    def search(
        self,
        collection_name: str,
        data: List[List[float]],
        limit: int = 5,
        output_fields: List[str] = None,
        **kwargs: Any,
    ) -> List[List[Dict[str, Any]]]:
        """Mock similarity search for retriever compatibility."""
        if collection_name not in self._collections:
            raise ValueError(f"Collection {collection_name} does not exist")
        fields = output_fields or ["insight_id", "content", "user_id", "task_id"]
        hits_per_query = []
        for _ in data:
            query_hits = []
            for item in self._collections[collection_name][:limit]:
                entity = {field: item.get(field) for field in fields}
                query_hits.append({
                    "id": item.get("insight_id"),
                    "distance": 0.05,
                    "entity": entity,
                })
            hits_per_query.append(query_hits)
        return hits_per_query

    def delete(self, collection_name: str, expr: str = "", filter: str = None, **kwargs: Any) -> Dict[str, Any]:
        target = filter if filter is not None else expr
        if collection_name not in self._collections:
            raise ValueError(f"Collection {collection_name} does not exist")
        before_count = len(self._collections[collection_name])
        self._collections[collection_name] = [
            item for item in self._collections[collection_name] if not self._match_expr(item, target)
        ]
        deleted_count = before_count - len(self._collections[collection_name])
        return {"delete_count": deleted_count}

    def flush(self, collection_name: str) -> None:
        # No-op for mock
        pass

    def __repr__(self) -> str:
        return f"MockMilvusClient(uri={self.uri!r})"
