#!/usr/bin/env python3
"""
Migration utility for Milvus Lite collection versions.
Creates a new collection (e.g. agent_insights_v2), copies all existing insights,
and updates the config.yaml to point to the new collection.

Usage:
    python migrate_collection.py --new-version v2
"""
import argparse
import yaml
from pathlib import Path
import os

# Import get_client from memory_layer (will give us a client bound to current collection)
from memory_layer import get_client

def load_config():
    cfg_path = Path(__file__).parents[2] / "memory_layer" / "config.yaml"
    with open(cfg_path, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)
    return cfg, cfg_path

def save_config(cfg, cfg_path):
    with open(cfg_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(cfg, f)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--new-version", required=True, help="Version suffix, e.g. v2")
    args = parser.parse_args()

    cfg, cfg_path = load_config()
    mil = cfg["milvus"]
    base = mil.get("collection_base")
    old_coll = mil.get("collection")
    new_coll = f"{base}_{args.new_version}"
    dim = int(mil["dimension"])

    # Get a client (connected to the current DB file)
    client, _, _ = get_client()

    # Create new collection if it does not exist
    if not client.has_collection(new_coll):
        client.create_collection(collection_name=new_coll, dimension=dim, metric_type="L2", auto_id=True)
        client.load_collection(new_coll)
        print(f"Created new collection '{new_coll}'")
    else:
        print(f"Collection '{new_coll}' already exists")

    # Retrieve all data from old collection
    # Simple full scan (no filters). Adjust if dataset grows large.
    old_data = client.query(
        collection_name=old_coll,
        filter="",
        output_fields=["user_id", "task_id", "timestamp", "insight_type", "source", "content", "embedding"]
    )
    if not old_data:
        print("No data to migrate.")
    else:
        # Insert directly – we already have embedding vectors in the rows.
        client.insert(collection_name=new_coll, data=old_data)
        print(f"Migrated {len(old_data)} records to '{new_coll}'.")

    # Update config to point to new collection
    mil["collection"] = new_coll
    save_config(cfg, cfg_path)
    print(f"Config updated: collection set to '{new_coll}'.")

if __name__ == "__main__":
    main()
