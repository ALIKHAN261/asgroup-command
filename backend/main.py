#!/usr/bin/env python3
"""AS GROUP Command — backend. The agent team lives here.

Run:  python main.py        (from the backend/ folder)
Docs: http://127.0.0.1:8000/docs  (interactive API)
"""
import pathlib, yaml
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import secrets
import agents as registry
from core import store, orchestrator
from core.security import configure, require_token, require_local_client
from core import commands as voice_commands
from core import control as pc_control
from fastapi.responses import FileResponse, StreamingResponse

BASE = pathlib.Path(__file__).parent
cfg = yaml.safe_load((BASE / "config.yaml").read_text())

store.init(BASE / cfg.get("db_path", "data/command.db"))
configure(cfg.get("api_token", "CHANGE_ME"))
_ctrl = cfg.get("control", {}) or {}
pc_control.configure(_ctrl.get("enabled", False),
                     _ctrl.get("auto_allow", []),
                     BASE / "data" / "shots")
registry.load_all()
_stop = orchestrator.start(registry.AGENTS, cfg)
store.log("system", "ok",
          f"command center online — {len(registry.AGENTS)} agents: "
          + ", ".join(sorted(registry.AGENTS)))

app = FastAPI(title="AS GROUP Command", docs_url="/docs", redoc_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=cfg.get("cors_origins", ["*"]),
    allow_methods=["*"], allow_headers=["*"],
)

class Decision(BaseModel):
    decision: str  # "approved" | "rejected"

class Command(BaseModel):
    text: str

class PauseRequest(BaseModel):
    paused: bool

@app.get("/api/health")
def health():
    return {"ok": True, "agents": len(registry.AGENTS)}

@app.get("/api/agents", dependencies=[Depends(require_token)])
def agents():
    return store.get_agents()

@app.get("/api/activity", dependencies=[Depends(require_token)])
def activity(limit: int = 80, agent: str = ""):
    return store.get_activity(max(1, min(limit, 500)), agent or None)

@app.post("/api/agents/{name}/pause", dependencies=[Depends(require_token)])
def pause_agent(name: str, body: PauseRequest):
    if name not in registry.AGENTS:
        raise HTTPException(status_code=404, detail="unknown agent")
    store.set_agent_paused(name, body.paused)
    return {"ok": True, "name": name,
            "status": "paused" if body.paused else "idle"}

@app.get("/api/approvals", dependencies=[Depends(require_token)])
def approvals(status: str = "pending"):
    return store.get_approvals(status if status in ("pending", "approved", "rejected") else "pending")

@app.post("/api/approvals/{approval_id}", dependencies=[Depends(require_token)])
def decide(approval_id: int, body: Decision):
    if body.decision not in ("approved", "rejected"):
        return {"ok": False, "error": "decision must be approved|rejected"}
    item = store.get_approval(approval_id)
    if not item or item["status"] != "pending":
        return {"ok": False, "error": "not found or already decided"}
    # Control proposals execute the moment you approve them.
    exec_result = None
    if item.get("kind") == "control" and body.decision == "approved":
        import json
        try:
            spec = json.loads(item["detail"])
            ok, msg = pc_control.execute(spec.get("action"), spec.get("params", {}))
            exec_result = {"ok": ok, "message": msg}
        except Exception as e:
            exec_result = {"ok": False, "message": f"{type(e).__name__}: {e}"}
    ok = store.decide_approval(approval_id, body.decision)
    if ok:
        store.log("you", "ok",
                  f"#{approval_id} {body.decision}" +
                  (f" → {exec_result['message']}" if exec_result else ""))
    return {"ok": ok, "executed": exec_result}

@app.post("/api/command", dependencies=[Depends(require_token)])
def command(body: Command):
    reply = voice_commands.handle(body.text)
    store.log("voice", "info", f"Q: {body.text[:120]} → A: {reply[:120]}")
    return {"reply": reply}

@app.get("/api/screen", dependencies=[Depends(require_token), Depends(require_local_client)])
def screen():
    from agents.screen_eye import latest_path
    p = latest_path()
    if not p:
        return {"ok": False, "error": "no screenshot yet"}
    return FileResponse(str(p), media_type="image/png")

@app.get("/api/shots/{name}", dependencies=[Depends(require_token), Depends(require_local_client)])
def shot(name: str):
    p = (BASE / "data" / "shots" / name)
    if not p.exists() or ".." in name:
        return {"ok": False, "error": "not found"}
    return FileResponse(str(p), media_type="image/png")

_API_TOKEN = cfg.get("api_token", "CHANGE_ME")
_SCREEN = cfg.get("screen", {}) or {}

@app.get("/api/screen/live", dependencies=[Depends(require_local_client)])
def screen_live(token: str = "", fps: int = 5):
    """Live MJPEG screen stream. <img> tags can't send headers, so the
    token travels as a query param here (documented tradeoff; the stream
    is useless without your token)."""
    if not token or not secrets.compare_digest(token, _API_TOKEN):
        from fastapi import HTTPException
        raise HTTPException(status_code=401, detail="bad token")
    fps = max(1, min(int(fps or 5), 15))
    width = int(_SCREEN.get("live_width", 960))
    quality = int(_SCREEN.get("live_quality", 60))
    delay = 1.0 / fps

    def gen():
        import io, time
        try:
            from PIL import ImageGrab
        except Exception:
            return
        while True:
            try:
                img = ImageGrab.grab()
                img.thumbnail((width, width))
                buf = io.BytesIO()
                img.save(buf, format="JPEG", quality=quality)
                frame = buf.getvalue()
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n"
                       b"Content-Length: " + str(len(frame)).encode() +
                       b"\r\n\r\n" + frame + b"\r\n")
            except GeneratorExit:
                break  # viewer closed the stream
            except Exception:
                time.sleep(1.0)
                continue
            time.sleep(delay)

    return StreamingResponse(
        gen(), media_type="multipart/x-mixed-replace; boundary=frame")

if __name__ == "__main__":
    import uvicorn
    if cfg.get("api_token") == "CHANGE_ME_TO_A_LONG_RANDOM_STRING":
        print("!! Set api_token in config.yaml first (make it long and random).")
    uvicorn.run(app, host=cfg.get("host", "127.0.0.1"),
                port=int(cfg.get("port", 8000)), log_level="warning")
