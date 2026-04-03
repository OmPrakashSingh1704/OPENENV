#!/usr/bin/env python3
"""
Inference Script — SRE Incident Response OpenEnv
=================================================
MANDATORY environment variables:
    API_BASE_URL        The API endpoint for the LLM.
    MODEL_NAME          The model identifier to use.
    HF_TOKEN            Your Hugging Face / API key.
    IMAGE_NAME          (optional) Local Docker image name — if set, env is
                        launched via openenv-core from_docker_image(); otherwise
                        the local SREIncidentEnv class is used directly.

STDOUT FORMAT (one [START], N [STEP]s, one [END] per task episode):
    [START] task=<task> env=<benchmark> model=<model>
    [STEP]  step=<n> action=<str> reward=<0.00> done=<true|false> error=<msg|null>
    [END]   success=<true|false> steps=<n> score=<0.000> rewards=<r1,r2,...>

Usage:
    API_BASE_URL=https://router.huggingface.co/v1 \\
    MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct \\
    HF_TOKEN=hf_... \\
    python inference.py
"""

import asyncio
import json
import os
import sys
from typing import List, Optional

from dotenv import load_dotenv

load_dotenv()

from openai import OpenAI

IMAGE_NAME = os.getenv("IMAGE_NAME")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
MODEL_NAME = os.getenv("MODEL_NAME")
TASK_NAME = os.getenv("TASK_NAME")  # if set, run only this task
BENCHMARK = "sre-incident-response-env"

TEMPERATURE = 0.0
MAX_TOKENS = 2048
SUCCESS_SCORE_THRESHOLD = 0.5

FALLBACK_ACTION_DATA = {
    "root_cause": "service_crash",
    "severity": "p2",
    "remediation": "investigate",
    "postmortem_summary": None,
    "reproduction_steps": None,
}


# ---------------------------------------------------------------------------
# Logging helpers (mandatory stdout protocol)
# ---------------------------------------------------------------------------

def log_start(task: str, env: str, model: str) -> None:
    print(f"[START] task={task} env={env} model={model}", flush=True)


def log_step(step: int, action: str, reward: float, done: bool, error: Optional[str]) -> None:
    error_val = error if error else "null"
    done_val = str(done).lower()
    print(
        f"[STEP] step={step} action={action} reward={reward:.2f} done={done_val} error={error_val}",
        flush=True,
    )


def log_end(success: bool, steps: int, score: float, rewards: List[float]) -> None:
    rewards_str = ",".join(f"{r:.2f}" for r in rewards)
    print(
        f"[END] success={str(success).lower()} steps={steps} score={score:.3f} rewards={rewards_str}",
        flush=True,
    )


# ---------------------------------------------------------------------------
# Prompt builder
# ---------------------------------------------------------------------------

def build_prompt(obs_dict: dict) -> str:
    metrics_str = "\n".join(f"  {k}: {v}" for k, v in obs_dict["metrics"].items())
    return f"""You are an on-call SRE triaging a production incident. Analyse the data below.

TASK: {obs_dict['task_description']}

--- INCIDENT ---
ID: {obs_dict['incident_id']} | Service: {obs_dict['service_name']}
Alert: {obs_dict['alert_title']}
Description: {obs_dict['alert_description']}

Logs:
{obs_dict['error_logs']}

Metrics:
{metrics_str}

Recent changes: {obs_dict['recent_changes']}
On-call notes: {obs_dict['on_call_notes']}
--- END INCIDENT ---

Step {obs_dict['step_count'] + 1}/{obs_dict['max_steps']}. Output JSON only, no other text:
{{
  "root_cause": "out_of_memory|disk_full|service_crash|config_error|network_timeout|dependency_failure|traffic_spike|deployment_failure|resource_leak|certificate_expired",
  "severity": "p1|p2|p3|p4",
  "remediation": "restart_service|rollback_deployment|scale_up|clear_disk|fix_config|block_traffic|failover|renew_certificate|investigate|add_resources",
  "postmortem_summary": "required for hard task, else null",
  "reproduction_steps": "required for reproduce task (numbered steps to trigger the failure), else null"
}}"""


# ---------------------------------------------------------------------------
# Docker-image-based env wrapper (openenv-core async client)
# ---------------------------------------------------------------------------

async def _make_env_from_docker(image_name: str):
    """Connect to env running inside a local Docker container."""
    try:
        from openenv_core import from_docker_image  # type: ignore
        return await from_docker_image(image_name)
    except ImportError:
        print("[DEBUG] openenv-core not available; falling back to direct env", flush=True)
        return None


# ---------------------------------------------------------------------------
# Task runner
# ---------------------------------------------------------------------------

async def run_task(client: OpenAI, task_id: str) -> float:
    """Run one task episode and emit [START]/[STEP]/[END] lines. Returns mean score."""
    # Build env — prefer docker image if IMAGE_NAME is set
    env = None
    use_async = False
    if IMAGE_NAME:
        env = await _make_env_from_docker(IMAGE_NAME)
        use_async = env is not None

    if env is None:
        from environment.env import SREIncidentEnv
        from environment.models import Action
        env = SREIncidentEnv()

    log_start(task=task_id, env=BENCHMARK, model=MODEL_NAME or "unknown")

    rewards: List[float] = []
    steps_taken = 0
    score = 0.0
    success = False
    error_msg: Optional[str] = None

    try:
        if use_async:
            result = await env.reset(task_id=task_id)
            obs_dict = result.observation.__dict__ if hasattr(result.observation, "__dict__") else dict(result.observation)
            done = result.done
        else:
            from environment.models import Action
            obs = env.reset(task_id=task_id)
            obs_dict = obs.model_dump()
            done = False

        max_steps = obs_dict.get("max_steps", 10)

        for step in range(1, max_steps + 1):
            if done:
                break

            prompt = build_prompt(obs_dict)
            action_data = dict(FALLBACK_ACTION_DATA)
            error_msg = None

            try:
                response = client.chat.completions.create(
                    model=MODEL_NAME,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are an expert SRE. "
                                "Respond ONLY with a valid JSON object — no markdown, no explanation."
                            ),
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=TEMPERATURE,
                    max_tokens=MAX_TOKENS,
                )
                raw = (response.choices[0].message.content or "").strip()
                start = raw.find("{")
                end = raw.rfind("}")
                if start == -1 or end == -1 or end <= start:
                    raise ValueError(f"No JSON in response: {raw[:100]!r}")
                parsed = json.loads(raw[start : end + 1])
                parsed.setdefault("postmortem_summary", None)
                parsed.setdefault("reproduction_steps", None)
                action_data = parsed
            except Exception as exc:
                error_msg = str(exc)[:120]
                print(f"[DEBUG] step {step} parse error: {exc}", file=sys.stderr, flush=True)

            action_str = f"root_cause={action_data.get('root_cause','?')},sev={action_data.get('severity','?')}"

            if use_async:
                from environment.models import Action  # dynamic import to avoid circular issues
                step_result = await env.step(action_data)
                reward = step_result.reward if isinstance(step_result.reward, float) else getattr(step_result.reward, "value", 0.0)
                done = step_result.done
                if not done:
                    obs_dict = step_result.observation.__dict__ if hasattr(step_result.observation, "__dict__") else dict(step_result.observation)
            else:
                from environment.models import Action
                action = Action(**action_data)
                step_result = env.step(action)
                reward = step_result.reward.value
                done = step_result.done
                if not done and step_result.observation is not None:
                    obs_dict = step_result.observation.model_dump()

            rewards.append(reward)
            steps_taken = step
            log_step(step=step, action=action_str, reward=reward, done=done, error=error_msg)

        score = sum(rewards) / len(rewards) if rewards else 0.0
        score = min(max(score, 0.0), 1.0)
        success = score >= SUCCESS_SCORE_THRESHOLD

    except Exception as exc:
        print(f"[DEBUG] run_task error: {exc}", file=sys.stderr, flush=True)
        if not rewards:
            rewards = [0.0]
            steps_taken = 0

    finally:
        try:
            if use_async:
                await env.close()
            else:
                env.close()
        except Exception as e:
            print(f"[DEBUG] env.close() error: {e}", file=sys.stderr, flush=True)
        log_end(success=success, steps=steps_taken, score=score, rewards=rewards)

    return score


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

async def main() -> None:
    if not API_KEY:
        print("Error: HF_TOKEN (or API_KEY) environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not MODEL_NAME:
        print("Error: MODEL_NAME environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    task_list = [TASK_NAME] if TASK_NAME else ["easy", "medium", "hard", "reproduce"]

    scores: dict = {}
    for task_id in task_list:
        print(f"\n{'='*50}", file=sys.stderr, flush=True)
        print(f"Task: {task_id}", file=sys.stderr, flush=True)
        print(f"{'='*50}", file=sys.stderr, flush=True)
        score = await run_task(client, task_id)
        scores[task_id] = round(score, 4)
        print(f"-> score: {score:.4f}", file=sys.stderr, flush=True)

    print("\nResults:", file=sys.stderr)
    for tid, s in scores.items():
        print(f"  {tid:10s}: {s:.4f}", file=sys.stderr)

    # Machine-readable last line consumed by /baseline endpoint
    print(json.dumps(scores), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
