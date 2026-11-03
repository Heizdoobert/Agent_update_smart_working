#!/usr/bin/env python3
"""
Memory Reflection Script
-----------------------
Purpose: After a task finishes, the Agent writes a temporary JSON file containing
short insight objects. This script reads that file, embeds each insight text,
and stores the embedding together with metadata in a Milvus vector database.

The script is invoked from `reflexion_runner.py` with the following environment
variables set:
- `TASK_ID`   – identifier of the current reflexion session
- `USER_ID`   – identifier of the user (default: "default_user")
- `INSIGHT_FILE` – path to the JSON file with insights

The script does **not** raise errors on failure; it logs to stdout/stderr and
removes the temporary file.
"""
import json
import os
import sys
import logging
from pathlib import Path
from typing import List, Dict, Any

# ------------------- Logging Setup -------------------
logging.basicConfig(level=logging.INFO, format="[MemoryReflection] %(message)s")
log = logging.getLogger()

# ------------------- Helper Functions -------------------
def load_insights(file_path: str) -> List[Dict[str, Any]]:
    """Load insight objects from the JSON file.

    Expected format:
    [
        {"insight": "User prefers short answers", "type": "preference"},
        ...
    ]
    """
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            raise ValueError("Insight file must contain a JSON array.")
        return data
    except Exception as e:
        log.error(f"Failed to read insight file '{file_path}': {e}")
        return []

def dummy_embed(text: str, dim: int = 128) -> List[float]:
    """A placeholder embedding function.
    Generates a deterministic pseudo‑vector by hashing the text.
    Ensures enough bytes are available for the requested dimension.
    """
    import hashlib
    import struct
    # Initial hash
    h = hashlib.sha256(text.encode("utf-8")).digest()
    # Extend hash bytes until we have dim * 4 bytes (4 bytes per float)
    while len(h) < dim * 4:
        h += hashlib.sha256(h).digest()
    # Convert hash bytes to floats in range [0, 1)
    floats = [struct.unpack("<I", h[i*4:(i+1)*4])[0] / (2**32) for i in range(dim)]
    return floats

def get_milvus_client(config_path: str = "/mnt/second_drive/SKILL/memory_layer/config.yaml"):
    """Create a Milvus client with fallback to Milvus Lite.
    Returns (client, dimension, collection_name).
    """
    try:
        import yaml
        from pymilvus import connections, Collection, FieldSchema, CollectionSchema, DataType, MilvusClient
    except Exception as e:
        log.error(f"Missing dependencies for Milvus: {e}")
        return None, None, None
    try:
        with open(config_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        mil = cfg.get("milvus", {})
        host = mil.get("host", "localhost")
        port = mil.get("port", 19530)
        collection_name = mil.get("collection", "agent_insights")
        dim = int(mil.get("dimension", 128))
        # Attempt standard Milvus connection
        connections.connect("default", host=host, port=port)
        if Collection.exists(collection_name):
            collection = Collection(collection_name)
        else:
            fields = [
                FieldSchema(name="user_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="task_id", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="timestamp", dtype=DataType.VARCHAR, max_length=64),
                FieldSchema(name="insight_type", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="source", dtype=DataType.VARCHAR, max_length=32),
                FieldSchema(name="content", dtype=DataType.VARCHAR, max_length=512),
                FieldSchema(name="embedding", dtype=DataType.FLOAT_VECTOR, dim=dim),
            ]
            schema = CollectionSchema(fields, description="Agent insight storage")
            collection = Collection(name=collection_name, schema=schema)
            collection.create_index(field_name="embedding", index_params={"metric_type": "L2", "index_type": "IVF_FLAT", "params": {"nlist": 128}})
        return collection, dim, collection_name
    except Exception as e:
        log.warning(f"Standard Milvus connection failed ({e}), falling back to Milvus Lite.")
        # Milvus Lite fallback
        # relative path resolves against config.yaml's folder (same as memory_layer.get_client)
        lite_path = Path(config_path).parent / (os.getenv("MEMORY_DB") or mil.get("lite_path", "milvus_lite.db"))
        client = MilvusClient(uri=str(lite_path))
        # create once; never drop, or every run wipes earlier insights
        if not client.has_collection(collection_name):
            client.create_collection(
                collection_name=collection_name,
                dimension=dim,
                metric_type="L2",
                auto_id=True,
            )
        # Wrapper to provide same insert interface
        class LiteWrapper:
            def __init__(self, client, name):
                self.client = client
                self.name = name
            def insert(self, payload_vectors):
                payload, vectors = payload_vectors
                # Combine each payload dict with its corresponding vector under the field name 'embedding'
                data = []
                for p, v in zip(payload, vectors):
                    entry = p.copy()
                    entry["vector"] = v
                    data.append(entry)
                self.client.insert(self.name, data=data)

        return LiteWrapper(client, collection_name), dim, collection_name


def upsert_insights(collection, dim: int, insights: List[Dict[str, Any]], metadata: Dict[str, Any]):
    """Insert embeddings into Milvus.
    Milvus expects a list of vectors and a list of dicts for the payload.
    """
    if not insights:
        return
    vectors = []
    payload = []
    for item in insights:
        txt = item.get("insight") or item.get("text") or ""
        typ = item.get("type", "generic")
        vec = dummy_embed(txt, dim)
        vectors.append(vec)
        payload.append({
            "user_id": metadata.get("user_id", "unknown"),
            "task_id": metadata.get("task_id", "unknown"),
            "timestamp": metadata.get("timestamp", ""),
            "insight_type": typ,
            "source": metadata.get("source", "reflection"),
            "content": txt,
        })
    try:
        # Milvus insert expects fields separately; handle both MilvusClient and LiteWrapper.
        if hasattr(collection, "insert") and collection.__class__.__name__ == "LiteWrapper":
            # LiteWrapper expects a tuple (payload, vectors)
            collection.insert((payload, vectors))
        else:
            # Standard MilvusClient expects a list [payload, vectors]
            collection.insert([payload, vectors])
        log.info(f"Inserted {len(insights)} insights into Milvus collection.")
    except Exception as e:
        log.error(f"Milvus insertion failed: {e}")

def main():
    task_id = os.getenv("TASK_ID", "unknown")
    user_id = os.getenv("USER_ID", "default_user")
    insight_file = os.getenv("INSIGHT_FILE")

    if not insight_file:
        log.error("Environment variable INSIGHT_FILE not set; nothing to do.")
        sys.exit(1)

    insights = load_insights(insight_file)
    if not insights:
        log.info("No insights to store; exiting.")
        # Clean up the empty file to avoid re‑processing.
        try:
            Path(insight_file).unlink(missing_ok=True)
        except Exception:
            pass
        sys.exit(0)

    collection, dim, _ = get_milvus_client()
    if collection is None:
        log.error("Milvus client not available; aborting.")
        sys.exit(1)

    meta = {
        "user_id": user_id,
        "task_id": task_id,
        "timestamp": "".join(["" for _ in []]),  # placeholder, can be datetime.now().isoformat()
        "source": "reflection",
    }
    upsert_insights(collection, dim, insights, meta)
    # Remove the temporary insight file after successful upload.
    try:
        Path(insight_file).unlink(missing_ok=True)
        log.info(f"Removed temporary insight file '{insight_file}'.")
    except Exception as e:
        log.warning(f"Failed to delete insight file: {e}")

if __name__ == "__main__":
    main()
