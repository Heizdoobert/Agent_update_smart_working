from memory_layer import get_client
from memory_layer.scripts.memory_reflection import dummy_embed


def retrieve(query, k=5):
    """Top-k stored insights (dicts with content/user_id/task_id) closest to query."""
    client, coll, dim = get_client()
    res = client.search(collection_name=coll, data=[dummy_embed(query, dim)], limit=k,
                        output_fields=["content", "user_id", "task_id"])
    return [h["entity"] for h in res[0]]
