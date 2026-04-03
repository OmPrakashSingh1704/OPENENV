"""
SREIncidentEnv — OpenEnv-compliant SRE incident response environment.

An AI agent acts as an on-call SRE, triaging production incidents by
identifying root causes, assessing severity, recommending remediations,
and (for the hard task) writing postmortem reports.
"""

from typing import Optional

from .graders import compute_reward
from .models import Action, EnvironmentState, Observation, Reward, StepResult
from .tasks import TASKS


class SREIncidentEnv:
    """
    OpenEnv environment for real-world SRE incident response.

    API:
      reset(task_id) -> Observation
      step(action)   -> StepResult(observation, reward, done, info)
      state()        -> EnvironmentState
    """

    def __init__(self) -> None:
        self._state: Optional[EnvironmentState] = None
        self._task_data: Optional[dict] = None
        self._incident_index: int = 0

    # ------------------------------------------------------------------
    # Core OpenEnv interface
    # ------------------------------------------------------------------

    def reset(self, task_id: str = "easy") -> Observation:
        """Reset the environment for the given task and return the first observation."""
        if task_id not in TASKS:
            raise ValueError(
                f"Unknown task_id '{task_id}'. Valid options: {list(TASKS.keys())}"
            )

        task_data = TASKS[task_id]
        self._task_data = task_data
        self._incident_index = 0
        self._state = EnvironmentState(
            task_id=task_id,
            step_count=0,
            max_steps=task_data["max_steps"],
            cumulative_reward=0.0,
            incidents_processed=0,
            done=False,
            episode_scores=[],
        )
        return self._build_observation()

    def step(self, action: Action) -> StepResult:
        """
        Apply an action to the current incident.

        Returns the next observation (or None when done), the step reward,
        a done flag, and an info dict with grading details.
        """
        if self._state is None:
            raise RuntimeError("Environment not initialised — call reset() first.")
        if self._state.done:
            raise RuntimeError("Episode is finished — call reset() to start a new episode.")

        incidents = self._task_data["incidents"]
        current_incident = incidents[self._incident_index]
        ground_truth = current_incident["ground_truth"]

        # Grade the action
        grade = compute_reward(self._state.task_id, action.model_dump(), ground_truth)
        reward = Reward(
            value=grade["total"],
            breakdown={k: v for k, v in grade.items() if k not in ("total", "feedback")},
            feedback=grade.get("feedback", ""),
        )

        # Advance state
        self._incident_index += 1
        self._state.step_count += 1
        self._state.incidents_processed += 1
        self._state.cumulative_reward = round(
            self._state.cumulative_reward + reward.value, 4
        )
        self._state.episode_scores.append(reward.value)

        done = (
            self._incident_index >= len(incidents)
            or self._state.step_count >= self._state.max_steps
        )
        self._state.done = done

        next_obs = None if done else self._build_observation()

        avg = self._state.cumulative_reward / self._state.incidents_processed
        info = {
            "incident_id": current_incident["incident_id"],
            "step": self._state.step_count,
            "grade_breakdown": grade,
            "cumulative_reward": self._state.cumulative_reward,
            "episode_avg_score": round(avg, 4),
        }

        return StepResult(observation=next_obs, reward=reward, done=done, info=info)

    def state(self) -> EnvironmentState:
        """Return the current environment state."""
        if self._state is None:
            raise RuntimeError("Environment not initialised — call reset() first.")
        return self._state

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_observation(self) -> Observation:
        incident = self._task_data["incidents"][self._incident_index]
        return Observation(
            task_id=self._state.task_id,
            incident_id=incident["incident_id"],
            service_name=incident["service_name"],
            alert_title=incident["alert_title"],
            alert_description=incident["alert_description"],
            error_logs=incident["error_logs"],
            metrics=incident["metrics"],
            recent_changes=incident["recent_changes"],
            on_call_notes=incident["on_call_notes"],
            step_count=self._state.step_count,
            max_steps=self._state.max_steps,
            task_description=self._task_data["description"],
        )

    def close(self) -> None:
        """No-op cleanup — satisfies the openenv-core async client interface."""
        pass

    def get_episode_score(self) -> float:
        """Return the mean score across all steps taken so far (0.0-1.0)."""
        if not self._state or not self._state.episode_scores:
            return 0.0
        return round(
            sum(self._state.episode_scores) / len(self._state.episode_scores), 4
        )
