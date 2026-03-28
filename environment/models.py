from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class Observation(BaseModel):
    task_id: str = Field(..., description="Current task identifier (easy/medium/hard)")
    incident_id: str = Field(..., description="Unique incident identifier")
    service_name: str = Field(..., description="Name of the affected service")
    alert_title: str = Field(..., description="PagerDuty-style alert title")
    alert_description: str = Field(..., description="Alert body / description")
    error_logs: str = Field(..., description="Relevant log lines from the affected service")
    metrics: Dict[str, str] = Field(..., description="Key service metrics at time of incident")
    recent_changes: str = Field(..., description="Recent deployments or config changes")
    on_call_notes: str = Field(..., description="Context notes from the previous on-call engineer")
    step_count: int = Field(..., description="Current step in the episode")
    max_steps: int = Field(..., description="Maximum steps allowed in this episode")
    task_description: str = Field(..., description="What the agent must do for this task")


class Action(BaseModel):
    root_cause: str = Field(
        ...,
        description=(
            "Root cause category: out_of_memory | disk_full | service_crash | "
            "config_error | network_timeout | dependency_failure | traffic_spike | "
            "deployment_failure | resource_leak | certificate_expired"
        ),
    )
    severity: str = Field(
        ...,
        description="Incident severity: p1 (total outage) | p2 (major) | p3 (partial) | p4 (minor)",
    )
    remediation: str = Field(
        ...,
        description=(
            "Immediate remediation action: restart_service | rollback_deployment | "
            "scale_up | clear_disk | fix_config | block_traffic | failover | "
            "renew_certificate | investigate | add_resources"
        ),
    )
    postmortem_summary: Optional[str] = Field(
        None,
        description="Postmortem write-up (required for hard task): timeline, root cause, fix, prevention",
    )
    reproduction_steps: Optional[str] = Field(
        None,
        description="Step-by-step instructions to reproduce the failure (required for reproduce task)",
    )


class Reward(BaseModel):
    value: float = Field(..., description="Step reward in range [-1.0, 1.0]")
    breakdown: Dict[str, float] = Field(default_factory=dict)
    feedback: str = Field(default="")


class StepResult(BaseModel):
    observation: Optional[Observation] = Field(None)
    reward: Reward
    done: bool
    info: Dict[str, Any] = Field(default_factory=dict)


class EnvironmentState(BaseModel):
    task_id: str
    step_count: int
    max_steps: int
    cumulative_reward: float
    incidents_processed: int
    done: bool
    episode_scores: List[float]
