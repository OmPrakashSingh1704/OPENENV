---
title: SRE Incident Response OpenEnv
emoji: 🚨
colorFrom: red
colorTo: blue
sdk: docker
app_port: 7860
pinned: false
---

# SRE Incident Response OpenEnv

An OpenEnv-compliant environment where AI agents learn to handle real-world
production incidents: **identify root causes → assess severity → plan remediation → write postmortems**.

Every company running software at scale needs on-call engineers who can triage
incidents quickly and accurately under pressure. Training AI agents on this task
has immediate commercial value and provides a rigorous benchmark for evaluating
technical reasoning, diagnostic skill, and structured communication.

---

## Environment Description

The agent acts as an on-call SRE, receiving realistic production incident alerts
(PagerDuty-style) complete with error logs, metrics, recent changes, and on-call notes.
It must make structured triage decisions at each step.

Each episode consists of one task (easy / medium / hard). The agent processes
incidents one at a time, receiving a reward signal after each step.

---

## Observation Space

| Field | Type | Description |
|---|---|---|
| `task_id` | string | Current task (`easy` / `medium` / `hard`) |
| `incident_id` | string | Unique incident identifier |
| `service_name` | string | Name of the affected service |
| `alert_title` | string | PagerDuty-style alert title |
| `alert_description` | string | Alert body with incident details |
| `error_logs` | string | Relevant log lines from the affected service |
| `metrics` | dict | Key service metrics at time of incident |
| `recent_changes` | string | Recent deployments or config changes |
| `on_call_notes` | string | Context notes from the previous on-call engineer |
| `step_count` | int | Steps taken so far in the episode |
| `max_steps` | int | Maximum steps for this task |
| `task_description` | string | What the agent must do |

---

## Action Space

| Field | Type | Values | Required |
|---|---|---|---|
| `root_cause` | string | `out_of_memory` \| `disk_full` \| `service_crash` \| `config_error` \| `network_timeout` \| `dependency_failure` \| `traffic_spike` \| `deployment_failure` \| `resource_leak` \| `certificate_expired` | Always |
| `severity` | string | `p1` \| `p2` \| `p3` \| `p4` | Always |
| `remediation` | string | `restart_service` \| `rollback_deployment` \| `scale_up` \| `clear_disk` \| `fix_config` \| `block_traffic` \| `failover` \| `renew_certificate` \| `investigate` \| `add_resources` | Always |
| `postmortem_summary` | string \| null | Postmortem write-up: timeline, root cause, fix, prevention | Required for hard task |

---

## Tasks

### Easy — Root Cause Classification
- **Goal:** Identify the root cause of each production incident.
- **Episodes:** 10 incidents per episode.
- **Grader:** Exact root cause match (1.0), adjacent/related cause partial credit (0.4).
- **Expected difficulty:** A capable LLM should score 0.7–0.95.

### Medium — Incident Triage and Response Planning
- **Goal:** Identify root cause (40%), assess severity (30%), and select remediation (30%).
- **Episodes:** 10 incidents per episode.
- **Grader:** Weighted sum; adjacent severity earns 0.5× credit, related remediation earns 0.4× credit.
- **Expected difficulty:** 0.5–0.75 for frontier models.

### Hard — Full Incident Response with Postmortem
- **Goal:** Full triage plus writing a complete postmortem report.
- **Episodes:** 5 complex incidents per episode.
- **Grader:** Root cause (20%) + severity (10%) + remediation (10%) + postmortem quality (60%).
  Postmortem quality checks: required keywords present, structural completeness (timeline + root cause + fix + prevention), adequate length (150+ words).
- **Expected difficulty:** 0.35–0.6 — genuinely challenges frontier models on the hardest cases.

---

## Reward Function

Rewards are **dense** (issued per step, not just at episode end):

- **Easy:** `score ∈ [0.0, 1.0]` based on root cause accuracy.
- **Medium:** `score ∈ [0.0, 1.0]` as a weighted combination of root cause, severity, and remediation.
- **Hard:** `score ∈ [0.0, 1.0]` with heavy weight on postmortem quality.
- Invalid action fields (not in the allowed enum) incur a 0.5× multiplier per field.

Episode score = mean of per-step rewards.

---

## API Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check — returns `{"status":"healthy"}` |
| `GET` | `/web` | Interactive testing UI |
| `POST` | `/reset` | Start/restart episode. Body: `{"task_id": "easy"}` |
| `POST` | `/step` | Submit action. Body: Action JSON object |
| `GET` | `/state` | Current episode state |
| `WS` | `/ws` | Persistent WebSocket session (primary OpenEnv client protocol) |
| `GET` | `/tasks` | Task list + action schema |
| `POST` | `/baseline` | Run baseline inference script |
| `POST` | `/grader` | Grade a single action off-episode |

---

## Setup and Usage

### Local (Python)

```bash
pip install -r requirements.txt

# Copy and fill in your credentials
cp .env.example .env
# Edit .env with your HF_TOKEN and MODEL_NAME

uvicorn app:app --host 0.0.0.0 --port 7860
```

Then open http://localhost:7860/web for the interactive UI, or http://localhost:7860/docs for Swagger.

### Local (Docker)

```bash
docker build -t sre-incident-env .
docker run -p 7860:7860 --env-file .env sre-incident-env
```

### Quick API test

```bash
# Reset to easy task
curl -X POST http://localhost:7860/reset \
  -H "Content-Type: application/json" \
  -d '{"task_id": "easy"}'

# Submit an action
curl -X POST http://localhost:7860/step \
  -H "Content-Type: application/json" \
  -d '{"root_cause": "out_of_memory", "severity": "p1", "remediation": "restart_service", "postmortem_summary": null}'

# Check state
curl http://localhost:7860/state
```

### Run baseline inference

```bash
# Set credentials in .env or pass directly
HF_TOKEN=hf_... MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct python inference.py
```

---

## Baseline Scores

Expected scores for `meta-llama/Llama-3.1-8B-Instruct` (temperature=0):

| Task | Expected Score |
|---|---|
| easy | 0.70–0.90 |
| medium | 0.50–0.75 |
| hard | 0.35–0.60 |

*(Scores are reproducible — set `temperature=0` and use the same model.)*

---

## Project Structure

```
.
├── openenv.yaml          # Environment metadata
├── Dockerfile            # Container definition
├── requirements.txt      # Python dependencies
├── app.py                # FastAPI application
├── inference.py          # Baseline inference script
├── client.py             # HTTP + WebSocket client
├── static/
│   └── index.html        # Interactive testing UI
└── environment/
    ├── env.py            # SREIncidentEnv class
    ├── models.py         # Pydantic models (Observation, Action, Reward, ...)
    ├── tasks.py          # Task definitions + incident datasets with ground truth
    └── graders.py        # Deterministic grading functions
```
