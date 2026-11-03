#!/usr/bin/env python3
"""
Check Milvus connection using the configuration in config.yaml.
Prints SUCCESS if connection and collection are reachable, otherwise prints error.
"""
import sys
import yaml
from pymilvus import connections, Collection

def main():
    cfg_path = "/mnt/second_drive/SKILL/memory_layer/config.yaml"
    try:
        with open(cfg_path, "r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f)
        mil = cfg.get("milvus", {})
        host = mil.get("host", "localhost")
        port = mil.get("port", 19530)
        collection_name = mil.get("collection", "agent_insights")
        connections.connect("default", host=host, port=port)
        coll = Collection(collection_name)
        print(f"SUCCESS: Connected to Milvus at {host}:{port}, collection '{collection_name}' exists.")
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
