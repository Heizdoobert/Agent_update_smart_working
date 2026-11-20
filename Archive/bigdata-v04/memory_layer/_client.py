# Singleton client for Milvus Lite
import os
import sys
import yaml
import logging
import threading
from pathlib import Path

# Attempt to import MilvusClient; fallback to local venv or mock if unavailable
try:
    from pymilvus import MilvusClient
except ImportError:  # pragma: no cover
    _venv_site = Path(__file__).resolve().parent / "venv" / "lib" / "python3.11" / "site-packages"
    if _venv_site.exists() and str(_venv_site) not in sys.path:
        sys.path.insert(0, str(_venv_site))
    try:
        from pymilvus import MilvusClient
    except ImportError:
        from .mock_milvus import MilvusClient  # type: ignore

log = logging.getLogger(__name__)
log.setLevel(logging.INFO)

# Module‑level singleton for Milvus client
_client_instance = None
_client_uri = None
_init_lock = threading.Lock()

_CFG = Path(__file__).with_name("config.yaml")
_config_cache = None


def _load_config():
    global _config_cache
    if _config_cache is None:
        _config_cache = yaml.safe_load(_CFG.read_text())
    return _config_cache


def reset_client():
    """Reset the singleton client instance, forcing reinitialization on next call."""
    global _client_instance, _client_uri
    with _init_lock:
        if _client_instance is not None:
            try:
                client = _client_instance[0]
                if hasattr(client, "close"):
                    client.close()
            except Exception:
                pass
        _client_instance = None
        _client_uri = None
        ml = sys.modules.get("memory_layer")
        if ml is not None:
            ml._client_instance = None
        try:
            from .cache import vector_cache
            vector_cache.clear()
        except Exception:
            pass


def get_client():
    """Return a singleton ``(client, collection, dim)`` for Milvus Lite.

    Thread-safe double-checked lock avoids redundant config loading and
    reconnects safely if MEMORY_DB changes.
    """
    global _client_instance, _client_uri

    # Detect if memory_layer module manually reset _client_instance
    ml = sys.modules.get("memory_layer")
    if _client_instance is not None and ml is not None and getattr(ml, "_client_instance", True) is None:
        reset_client()

    current_env_db = os.getenv("MEMORY_DB")
    canonical_env = Path(current_env_db).resolve().as_posix() if current_env_db else None

    if _client_instance is not None:
        if canonical_env is None and _client_uri is not None:
            return _client_instance
        if canonical_env is not None and _client_uri == canonical_env:
            return _client_instance

    with _init_lock:
        if _client_instance is not None and ml is not None and getattr(ml, "_client_instance", True) is None:
            _client_instance = None
            _client_uri = None

        cfg = _load_config()["milvus"]
        base = cfg.get("collection_base", cfg.get("collection"))
        version = cfg.get("collection_version")
        coll = f"{base}_{version}" if version else cfg["collection"]
        dim = int(cfg["dimension"])

        raw_db = os.getenv("MEMORY_DB")
        if raw_db:
            uri = Path(raw_db).resolve().as_posix()
        else:
            path = Path(cfg.get("lite_path", "./milvus_lite.db"))
            uri = (path if path.is_absolute() else _CFG.parent / path).resolve().as_posix()

        if _client_instance is not None and _client_uri != uri:
            try:
                old_client = _client_instance[0]
                if hasattr(old_client, "close"):
                    old_client.close()
            except Exception:
                pass
            _client_instance = None
            _client_uri = None

        if _client_instance is not None and _client_uri == uri:
            return _client_instance

        client = MilvusClient(uri=uri)
        # Ensure the collection exists. In test environments we create it if missing.
        try:
            if not client.has_collection(coll):
                client.create_collection(collection_name=coll, dimension=dim, metric_type="L2", auto_id=True)
        except Exception as e:
            log.debug(f"Collection creation skipped or failed: {e}")
        # Load collection for queries (Milvus Lite may require explicit load)
        try:
            client.load_collection(coll)
        except Exception as e:
            log.debug(f"Load collection ignored or failed: {e}")

        _client_instance = (client, coll, dim)
        _client_uri = uri
        if ml is not None:
            ml._client_instance = _client_instance
        return _client_instance
