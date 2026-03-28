#!/usr/bin/env python3
"""
Inference script for SRE Incident Response OpenEnv.

Runs a language model (via the OpenAI API client) against all three tasks
and produces reproducible per-task scores.

Mandatory environment variables:
    API_BASE_URL   The API endpoint for the LLM (e.g. https://router.huggingface.co/v1)
    MODEL_NAME     The model identifier to use for inference
    HF_TOKEN       Your Hugging Face / API key

Usage:
    API_BASE_URL=https://router.huggingface.co/v1 \\
    MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct \\
    HF_TOKEN=hf_... \\
    python inference.py

Output:
    Per-task progress is written to stderr.
    The final line of stdout is a JSON object: {"easy": 0.xx, "medium": 0.xx, "hard": 0.xx}
"""

import json
import os
import sys

from dotenv import load_dotenv
load_dotenv()

from openai import OpenAI

from environment.env import SREIncidentEnv
from environment.models import Action

API_BASE_URL = os.getenv("API_BASE_URL", "https://router.huggingface.co/v1")
API_KEY = os.getenv("HF_TOKEN") or os.getenv("API_KEY")
MODEL_NAME = os.getenv("MODEL_NAME")

TEMPERATURE = 0.0
MAX_TOKENS = 2048  # Enough for reasoning preamble + JSON on any task
FALLBACK_ACTION = Action(
    root_cause="service_crash",
    severity="p2",
    remediation="investigate",
    postmortem_summary=None,
)


def build_prompt(obs: dict) -> str:
    metrics_str = "\n".join(f"  {k}: {v}" for k, v in obs["metrics"].items())
    return f"""You are an on-call SRE triaging a production incident. Analyse the data below.

TASK: {obs['task_description']}

--- INCIDENT ---
ID: {obs['incident_id']} | Service: {obs['service_name']}
Alert: {obs['alert_title']}
Description: {obs['alert_description']}

Logs:
{obs['error_logs']}

Metrics:
{metrics_str}

Recent changes: {obs['recent_changes']}
On-call notes: {obs['on_call_notes']}
--- END INCIDENT ---

Step {obs['step_count'] + 1}/{obs['max_steps']}. Output JSON only, no other text:
{{
  "root_cause": "out_of_memory|disk_full|service_crash|config_error|network_timeout|dependency_failure|traffic_spike|deployment_failure|resource_leak|certificate_expired",
  "severity": "p1|p2|p3|p4",
  "remediation": "restart_service|rollback_deployment|scale_up|clear_disk|fix_config|block_traffic|failover|renew_certificate|investigate|add_resources",
  "postmortem_summary": "required for hard task, else null",
  "reproduction_steps": "required for reproduce task (numbered steps to trigger the failure), else null"
}}"""


def run_task(client: OpenAI, env: SREIncidentEnv, task_id: str) -> float:
    """Run the inference agent on one task and return the mean episode score."""
    obs = env.reset(task_id=task_id)
    obs_dict = obs.model_dump()

    total_reward = 0.0
    steps = 0

    while True:
        prompt = build_prompt(obs_dict)
        try:
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an expert SRE (Site Reliability Engineer). "
                            "Respond ONLY with a valid JSON object — no markdown, no explanation."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=TEMPERATURE,
                max_tokens=MAX_TOKENS,
            )
            raw = (response.choices[0].message.content or "").strip()

            # Extract the JSON object robustly — find outermost { ... }
            start = raw.find("{")
            end = raw.rfind("}")
            if start == -1 or end == -1 or end <= start:
                raise ValueError(f"No JSON object found in response: {raw[:200]!r}")
            action_data = json.loads(raw[start : end + 1])
            if "postmortem_summary" not in action_data:
                action_data["postmortem_summary"] = None
            if "reproduction_steps" not in action_data:
                action_data["reproduction_steps"] = None

            action = Action(**action_data)

        except Exception as exc:
            print(f"  [warn] step {steps + 1} parse error: {exc}", file=sys.stderr)
            action = FALLBACK_ACTION

        result = env.step(action)
        total_reward += result.reward.value
        steps += 1

        print(
            f"  step {steps:2d} | reward={result.reward.value:.4f} | {result.reward.feedback}",
            file=sys.stderr,
        )

        if result.done:
            break

        obs_dict = result.observation.model_dump()

    return round(total_reward / steps, 4) if steps > 0 else 0.0


def main() -> dict:
    if not API_KEY:
        print("Error: HF_TOKEN (or API_KEY) environment variable is not set.", file=sys.stderr)
        sys.exit(1)
    if not MODEL_NAME:
        print("Error: MODEL_NAME environment variable is not set.", file=sys.stderr)
        sys.exit(1)

    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)
    env = SREIncidentEnv()

    scores: dict = {}
    for task_id in ["easy", "medium", "hard", "reproduce"]:
        print(f"\n{'='*50}", file=sys.stderr)
        print(f"Task: {task_id}", file=sys.stderr)
        print(f"{'='*50}", file=sys.stderr)
        score = run_task(client, env, task_id)
        scores[task_id] = score
        print(f"-> Final score for '{task_id}': {score:.4f}", file=sys.stderr)

    print("\nResults:", file=sys.stderr)
    for task_id, score in scores.items():
        print(f"  {task_id:8s}: {score:.4f}", file=sys.stderr)

    # Machine-readable last line consumed by /baseline endpoint
    print(json.dumps(scores))
    return scores


if __name__ == "__main__":
    main()
