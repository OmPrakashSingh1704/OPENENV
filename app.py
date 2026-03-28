"""
SRE Incident Response OpenEnv — FastAPI application.

Implements the full OpenEnv server spec:
  GET  /health     — health check (required for HF Space deployment validation)
  POST /reset      — start / restart an episode
  POST /step       — submit an action
  GET  /state      — current episode state
  WS   /ws         — persistent WebSocket session (primary OpenEnv client protocol)

Plus hackathon-required additional endpoints:
  GET  /tasks      — task list + action schema
  POST /baseline   — run the baseline inference script
  POST /grader     — grade a single action off-episode
"""

import json
import subprocess
import sys
from typing import Optional

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from environment import SREIncidentEnv
from environment.graders import compute_reward
from environment.models import Action
from environment.tasks import TASKS

app = FastAPI(
    title="SRE Incident Response OpenEnv",
    description=(
        "A real-world OpenEnv environment where AI agents learn to triage production incidents: "
        "identify root causes, assess severity, recommend remediations, and write postmortems."
    ),
    version="1.0.0",
)

# Serve static UI files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Global environment instance for stateless HTTP endpoints
_env = SREIncidentEnv()


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class ResetRequest(BaseModel):
    task_id: str = "easy"


class GraderRequest(BaseModel):
    task_id: str
    incident_id: str
    action: Action


# ---------------------------------------------------------------------------
# Core OpenEnv endpoints
# ---------------------------------------------------------------------------


@app.get("/web", include_in_schema=False)
def web():
    """Interactive UI for testing the environment."""
    return FileResponse("static/index.html")


@app.get("/health")
def health():
    """Health check — required by OpenEnv deployment validation."""
    return {"status": "healthy"}


@app.get("/")
def root():
    return {
        "name": "SRE Incident Response OpenEnv",
        "version": "1.0.0",
        "description": "Real-world SRE incident response environment — triage incidents, write postmortems",
        "endpoints": [
            "/health", "/reset", "/step", "/state",
            "/ws", "/tasks", "/baseline", "/grader", "/docs",
        ],
    }


@app.post("/reset")
def reset(request: Optional[ResetRequest] = None):
    """Reset the environment and return the first observation."""
    task_id = request.task_id if request else "easy"
    try:
        obs = _env.reset(task_id=task_id)
        return obs.model_dump()
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/step")
def step(action: Action):
    """Submit an action and receive the next observation, reward, done, and info."""
    try:
        result = _env.step(action)
        return result.model_dump()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/state")
def state():
    """Return the current episode state."""
    try:
        return _env.state().model_dump()
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ---------------------------------------------------------------------------
# WebSocket endpoint — persistent session (primary OpenEnv client protocol)
# Each connection gets its own isolated environment instance.
# ---------------------------------------------------------------------------


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    Persistent WebSocket session following the OpenEnv wire protocol.

    Message types (client -> server):
      {"type": "reset", "task_id": "easy"}
      {"type": "step", "action": {...}}
      {"type": "state"}

    Message types (server -> client):
      {"type": "reset", "observation": {...}}
      {"type": "step", "observation": {...}|null, "reward": {...}, "done": bool, "info": {...}}
      {"type": "state", "state": {...}}
      {"type": "error", "message": "..."}
    """
    env = SREIncidentEnv()  # Isolated instance per connection
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_json()
            msg_type = data.get("type")

            if msg_type == "reset":
                try:
                    obs = env.reset(task_id=data.get("task_id", "easy"))
                    await websocket.send_json({"type": "reset", "observation": obs.model_dump()})
                except ValueError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})

            elif msg_type == "step":
                try:
                    action = Action(**data.get("action", {}))
                    result = env.step(action)
                    await websocket.send_json({
                        "type": "step",
                        "observation": result.observation.model_dump() if result.observation else None,
                        "reward": result.reward.model_dump(),
                        "done": result.done,
                        "info": result.info,
                    })
                except (RuntimeError, Exception) as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})

            elif msg_type == "state":
                try:
                    st = env.state()
                    await websocket.send_json({"type": "state", "state": st.model_dump()})
                except RuntimeError as exc:
                    await websocket.send_json({"type": "error", "message": str(exc)})

            else:
                await websocket.send_json({"type": "error", "message": f"Unknown message type: {msg_type}"})

    except WebSocketDisconnect:
        pass


# ---------------------------------------------------------------------------
# Hackathon-required additional endpoints
# ---------------------------------------------------------------------------


@app.get("/tasks")
def get_tasks():
    """Return available tasks and the action schema."""
    return {
        "tasks": [
            {
                "id": t["id"],
                "name": t["name"],
                "description": t["description"],
                "difficulty": t["difficulty"],
                "max_steps": t["max_steps"],
                "num_incidents": len(t["incidents"]),
            }
            for t in TASKS.values()
        ],
        "action_schema": Action.model_json_schema(),
    }


@app.post("/baseline")
def baseline():
    """
    Trigger the baseline inference script and return per-task scores.
    Requires HF_TOKEN (or API_KEY) and MODEL_NAME to be set in the environment.
    """
    try:
        result = subprocess.run(
            [sys.executable, "inference.py"],
            capture_output=True,
            text=True,
            timeout=360,
        )
        if result.returncode != 0:
            return JSONResponse(
                status_code=500,
                content={"error": "Baseline script failed", "stderr": result.stderr[-2000:]},
            )
        last_line = [ln for ln in result.stdout.strip().splitlines() if ln.strip()][-1]
        scores = json.loads(last_line)
        return {"status": "success", "baseline_scores": scores}
    except subprocess.TimeoutExpired:
        raise HTTPException(status_code=504, detail="Baseline script timed out")
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.post("/grader")
def grader(request: GraderRequest):
    """Grade a single action against stored ground truth for a given incident."""
    task_id = request.task_id
    incident_id = request.incident_id

    if task_id not in TASKS:
        raise HTTPException(status_code=400, detail=f"Unknown task: {task_id}")

    incident_data = next(
        (i for i in TASKS[task_id]["incidents"] if i["incident_id"] == incident_id), None
    )
    if incident_data is None:
        raise HTTPException(
            status_code=404, detail=f"Incident '{incident_id}' not found in task '{task_id}'"
        )

    grade = compute_reward(task_id, request.action.model_dump(), incident_data["ground_truth"])

    return {
        "task_id": task_id,
        "incident_id": incident_id,
        "score": grade["total"],
        "breakdown": {k: v for k, v in grade.items() if k not in ("total", "feedback")},
        "feedback": grade.get("feedback", ""),
    }


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=7860)
