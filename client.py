"""
SRE Incident Response OpenEnv — Python client.

Provides both synchronous HTTP and async WebSocket access to the environment.

Usage (sync HTTP):
    from client import SREIncidentClient

    client = SREIncidentClient(base_url="http://localhost:7860")
    obs = client.reset("easy")
    result = client.step({
        "root_cause": "out_of_memory",
        "severity": "p1",
        "remediation": "restart_service",
        "postmortem_summary": None
    })
    print(result["reward"])

Usage (async WebSocket):
    import asyncio
    from client import SREIncidentWSClient

    async def main():
        async with SREIncidentWSClient("ws://localhost:7860/ws") as client:
            obs = await client.reset("easy")
            result = await client.step({...})

    asyncio.run(main())
"""

import json
from typing import Any, Dict, Optional

import httpx


class SREIncidentClient:
    """Synchronous HTTP client for the SRE Incident Response OpenEnv."""

    def __init__(self, base_url: str = "http://localhost:7860") -> None:
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(base_url=self.base_url, timeout=30.0)

    # ------------------------------------------------------------------
    # Core OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self, task_id: str = "easy") -> Dict[str, Any]:
        """Reset the environment and return the first observation."""
        resp = self._http.post("/reset", json={"task_id": task_id})
        resp.raise_for_status()
        return resp.json()

    def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        """Submit an action and receive observation, reward, done, info."""
        resp = self._http.post("/step", json=action)
        resp.raise_for_status()
        return resp.json()

    def state(self) -> Dict[str, Any]:
        """Return the current episode state."""
        resp = self._http.get("/state")
        resp.raise_for_status()
        return resp.json()

    # ------------------------------------------------------------------
    # Additional endpoints
    # ------------------------------------------------------------------

    def tasks(self) -> Dict[str, Any]:
        """Return available tasks and the action schema."""
        resp = self._http.get("/tasks")
        resp.raise_for_status()
        return resp.json()

    def health(self) -> Dict[str, Any]:
        resp = self._http.get("/health")
        resp.raise_for_status()
        return resp.json()

    def grader(self, task_id: str, incident_id: str, action: Dict[str, Any]) -> Dict[str, Any]:
        resp = self._http.post("/grader", json={
            "task_id": task_id, "incident_id": incident_id, "action": action
        })
        resp.raise_for_status()
        return resp.json()

    def close(self) -> None:
        self._http.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()


class SREIncidentWSClient:
    """Async WebSocket client for the SRE Incident Response OpenEnv."""

    def __init__(self, ws_url: str = "ws://localhost:7860/ws") -> None:
        self.ws_url = ws_url
        self._ws = None

    async def __aenter__(self):
        try:
            import websockets  # type: ignore
        except ImportError:
            raise ImportError("pip install websockets to use SREIncidentWSClient")
        self._ws = await websockets.connect(self.ws_url)
        return self

    async def __aexit__(self, *args):
        if self._ws:
            await self._ws.close()

    async def reset(self, task_id: str = "easy") -> Dict[str, Any]:
        await self._ws.send(json.dumps({"type": "reset", "task_id": task_id}))
        msg = json.loads(await self._ws.recv())
        if msg.get("type") == "error":
            raise RuntimeError(msg["message"])
        return msg.get("observation", {})

    async def step(self, action: Dict[str, Any]) -> Dict[str, Any]:
        await self._ws.send(json.dumps({"type": "step", "action": action}))
        msg = json.loads(await self._ws.recv())
        if msg.get("type") == "error":
            raise RuntimeError(msg["message"])
        return msg

    async def state(self) -> Dict[str, Any]:
        await self._ws.send(json.dumps({"type": "state"}))
        msg = json.loads(await self._ws.recv())
        if msg.get("type") == "error":
            raise RuntimeError(msg["message"])
        return msg.get("state", {})
