from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict
import threading

app = FastAPI()

# In‑memory store (would be Redis in production)
_state: Dict[str, str] = {}
_lock = threading.Lock()

class LockRequest(BaseModel):
    repo: str
    branch: str
    requester: str

class VersionRequest(BaseModel):
    repo: str
    branch: str
    bump: str = "minor"  # major / minor / patch

@app.post("/lock_tag")
def lock_tag(req: LockRequest):
    key = f"{req.repo}:{req.branch}"
    with _lock:
        if _state.get(key) == "locked":
            raise HTTPException(status_code=409, detail="Tag already locked")
        _state[key] = "locked"
    return {"status": "locked", "key": key, "by": req.requester}

@app.post("/unlock_tag")
def unlock_tag(req: LockRequest):
    key = f"{req.repo}:{req.branch}"
    with _lock:
        if _state.get(key) != "locked":
            raise HTTPException(status_code=404, detail="No lock found")
        _state.pop(key)
    return {"status": "unlocked", "key": key}

@app.get("/release_state/{repo}/{branch}")
def release_state(repo: str, branch: str):
    key = f"{repo}:{branch}"
    status = _state.get(key, "free")
    return {"repo": repo, "branch": branch, "status": status}

@app.post("/next_version")
def next_version(req: VersionRequest):
    # Very simple version bump logic using a dummy stored version
    key = f"{req.repo}:{req.branch}:version"
    with _lock:
        current = _state.get(key, "0.0.0")
        major, minor, patch = map(int, current.split('.'))
        if req.bump == "major":
            major += 1; minor = 0; patch = 0
        elif req.bump == "minor":
            minor += 1; patch = 0
        else:
            patch += 1
        new_version = f"{major}.{minor}.{patch}"
        _state[key] = new_version
    return {"next_version": new_version, "repo": req.repo, "branch": req.branch}
