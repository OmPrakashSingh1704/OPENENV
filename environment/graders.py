"""
Grading logic for the SRE Incident Response OpenEnv.

Each grader returns a dict with:
  - total (float, 0.0-1.0): overall score for this step
  - component scores (float): per-dimension scores
  - feedback (str): human-readable explanation
"""

from typing import Dict, Any

VALID_ROOT_CAUSES = {
    "out_of_memory", "disk_full", "service_crash", "config_error",
    "network_timeout", "dependency_failure", "traffic_spike",
    "deployment_failure", "resource_leak", "certificate_expired",
}

VALID_SEVERITIES = {"p1", "p2", "p3", "p4"}

VALID_REMEDIATIONS = {
    "restart_service", "rollback_deployment", "scale_up", "clear_disk",
    "fix_config", "block_traffic", "failover", "renew_certificate",
    "investigate", "add_resources",
}

# Adjacent root-cause pairs that receive partial credit (closely related causes)
_CLOSE_ROOT_CAUSES = {
    ("out_of_memory", "resource_leak"),
    ("resource_leak", "out_of_memory"),
    ("service_crash", "deployment_failure"),
    ("deployment_failure", "service_crash"),
    ("config_error", "deployment_failure"),
    ("deployment_failure", "config_error"),
    ("network_timeout", "dependency_failure"),
    ("dependency_failure", "network_timeout"),
}

# Severity ordering for adjacent-severity partial credit
_SEVERITY_ORDER = {"p1": 0, "p2": 1, "p3": 2, "p4": 3}

# Remediations that are contextually acceptable alternatives (partial credit)
_CLOSE_REMEDIATIONS = {
    ("restart_service", "rollback_deployment"),
    ("rollback_deployment", "restart_service"),
    ("restart_service", "add_resources"),
    ("add_resources", "restart_service"),
    ("scale_up", "add_resources"),
    ("add_resources", "scale_up"),
    ("fix_config", "rollback_deployment"),
    ("rollback_deployment", "fix_config"),
    ("investigate", "failover"),
    ("failover", "investigate"),
    ("renew_certificate", "fix_config"),
    ("fix_config", "renew_certificate"),
}


def _root_cause_score(predicted: str, true: str) -> float:
    if predicted == true:
        return 1.0
    if (predicted, true) in _CLOSE_ROOT_CAUSES:
        return 0.4
    return 0.0


def _severity_score(predicted: str, true: str) -> float:
    if predicted == true:
        return 1.0
    pred_rank = _SEVERITY_ORDER.get(predicted, -99)
    true_rank = _SEVERITY_ORDER.get(true, -99)
    if abs(pred_rank - true_rank) == 1:
        return 0.5  # Adjacent severity earns partial credit
    return 0.0


def _remediation_score(predicted: str, true: str) -> float:
    if predicted == true:
        return 1.0
    if (predicted, true) in _CLOSE_REMEDIATIONS:
        return 0.4
    return 0.0


def _postmortem_score(postmortem: str, requirements: Dict) -> float:
    """
    Deterministic postmortem quality scorer.

    Checks:
      - Required elements present in postmortem (50%)
      - Structural completeness: timeline + root cause + fix + prevention (30%)
      - Adequate length: 150+ words (20%)
    Penalizes forbidden phrases (-0.2 each, capped at -0.4).
    """
    if not postmortem or not postmortem.strip():
        return 0.0

    text_lower = postmortem.lower()
    words = postmortem.split()

    # --- Required element check (50%) ---
    must_include = requirements.get("must_include", [])
    if must_include:
        matched = sum(
            1 for phrase in must_include
            if phrase.lower() in text_lower
        )
        include_score = matched / len(must_include)
    else:
        include_score = 1.0

    # --- Structural completeness (30%) ---
    # Check for the four postmortem sections
    has_timeline = any(kw in text_lower for kw in [
        "timeline", "at ", "utc", "started", "began", "first detected", "occurred at"
    ])
    has_root_cause = any(kw in text_lower for kw in [
        "root cause", "caused by", "because", "due to", "reason"
    ])
    has_fix = any(kw in text_lower for kw in [
        "fixed", "resolved", "remediated", "rolled back", "restarted", "deployed", "applied"
    ])
    has_prevention = any(kw in text_lower for kw in [
        "prevent", "future", "monitoring", "alert", "process", "improvement",
        "action item", "follow-up", "going forward", "ensure"
    ])
    structure_score = (
        (0.25 if has_timeline else 0.0)
        + (0.25 if has_root_cause else 0.0)
        + (0.25 if has_fix else 0.0)
        + (0.25 if has_prevention else 0.0)
    )

    # --- Length adequacy (20%) ---
    min_words = requirements.get("min_words", 150)
    length_score = min(1.0, len(words) / min_words)

    raw = (include_score * 0.5) + (structure_score * 0.3) + (length_score * 0.2)

    # --- Forbidden phrase penalty ---
    must_not = requirements.get("must_not_include", [])
    penalty = min(0.4, sum(0.2 for phrase in must_not if phrase.lower() in text_lower))

    return round(max(0.0, min(1.0, raw - penalty)), 4)


def grade_easy(action_data: Dict, ground_truth: Dict) -> Dict[str, Any]:
    """Easy task: root cause accuracy only."""
    rc = _root_cause_score(action_data.get("root_cause", ""), ground_truth["root_cause"])

    marks = {1.0: "[ok]", 0.4: "[partial]"}.get(rc, "[wrong]")
    feedback = (
        f"RootCause: {marks} "
        f"(predicted='{action_data.get('root_cause')}', expected='{ground_truth['root_cause']}')"
    )
    return {"total": rc, "root_cause": rc, "feedback": feedback}


def grade_medium(action_data: Dict, ground_truth: Dict) -> Dict[str, Any]:
    """Medium task: root cause (40%) + severity (30%) + remediation (30%)."""
    rc = _root_cause_score(action_data.get("root_cause", ""), ground_truth["root_cause"])
    sev = _severity_score(action_data.get("severity", ""), ground_truth["severity"])
    rem = _remediation_score(action_data.get("remediation", ""), ground_truth["remediation"])

    total = round((rc * 0.4) + (sev * 0.3) + (rem * 0.3), 4)

    def mark(s):
        return {1.0: "[ok]", 0.5: "[partial]", 0.4: "[partial]"}.get(s, "[wrong]")

    feedback = (
        f"RootCause: {mark(rc)} | Severity: {mark(sev)} | Remediation: {mark(rem)} "
        f"-> score={total:.2f}"
    )
    return {
        "total": total,
        "root_cause": rc,
        "severity": sev,
        "remediation": rem,
        "feedback": feedback,
    }


def grade_hard(action_data: Dict, ground_truth: Dict) -> Dict[str, Any]:
    """Hard task: root cause (20%) + severity (10%) + remediation (10%) + postmortem (60%)."""
    rc = _root_cause_score(action_data.get("root_cause", ""), ground_truth["root_cause"])
    sev = _severity_score(action_data.get("severity", ""), ground_truth["severity"])
    rem = _remediation_score(action_data.get("remediation", ""), ground_truth["remediation"])

    req = ground_truth.get("postmortem_requirements", {})
    pm = _postmortem_score(action_data.get("postmortem_summary") or "", req)

    total = round((rc * 0.2) + (sev * 0.1) + (rem * 0.1) + (pm * 0.6), 4)

    def mark(s):
        return "[ok]" if s >= 0.9 else ("[partial]" if s > 0 else "[wrong]")

    feedback = (
        f"RootCause: {mark(rc)} | Severity: {mark(sev)} | "
        f"Remediation: {mark(rem)} | Postmortem: {pm:.2f} -> score={total:.2f}"
    )
    return {
        "total": total,
        "root_cause": rc,
        "severity": sev,
        "remediation": rem,
        "postmortem": pm,
        "feedback": feedback,
    }


def _reproduction_steps_score(steps: str, requirements: Dict) -> float:
    """
    Deterministic reproduction steps scorer.

    Checks:
      - Required technical keywords present (50%)
      - Numbered/sequential step structure (25%)
      - Adequate length: 80+ words and 5+ steps (25%)
    """
    if not steps or not steps.strip():
        return 0.0

    text_lower = steps.lower()
    words = steps.split()

    # --- Required keyword check (50%) ---
    must_include = requirements.get("must_include", [])
    if must_include:
        matched = sum(1 for kw in must_include if kw.lower() in text_lower)
        keyword_score = matched / len(must_include)
    else:
        keyword_score = 1.0

    # --- Numbered step structure (25%) ---
    import re
    numbered = len(re.findall(r'(?:step\s*\d+|^\s*\d+[\.\):])', steps, re.IGNORECASE | re.MULTILINE))
    has_steps = numbered >= 3
    step_score = 1.0 if numbered >= 5 else (0.6 if numbered >= 3 else 0.0)

    # --- Length adequacy (25%) ---
    min_words = requirements.get("min_words", 80)
    word_score = min(1.0, len(words) / min_words)

    return round(max(0.0, min(1.0, (keyword_score * 0.5) + (step_score * 0.25) + (word_score * 0.25))), 4)


def grade_reproduce(action_data: Dict, ground_truth: Dict) -> Dict[str, Any]:
    """Reproduce task: root cause (30%) + reproduction steps quality (70%)."""
    rc = _root_cause_score(action_data.get("root_cause", ""), ground_truth["root_cause"])

    req = ground_truth.get("reproduction_requirements", {})
    repro = _reproduction_steps_score(action_data.get("reproduction_steps") or "", req)

    total = round((rc * 0.3) + (repro * 0.7), 4)

    def mark(s):
        return "[ok]" if s >= 0.9 else ("[partial]" if s > 0 else "[wrong]")

    feedback = (
        f"RootCause: {mark(rc)} | ReproSteps: {repro:.2f} -> score={total:.2f}"
    )
    return {
        "total": total,
        "root_cause": rc,
        "reproduction_steps": repro,
        "feedback": feedback,
    }


def compute_reward(task_id: str, action_data: Dict, ground_truth: Dict) -> Dict[str, Any]:
    """
    Entry point: compute reward for a given task, action, and ground truth.

    Returns a dict with 'total' (float, 0.0 to 1.0), component scores,
    and a 'feedback' string.
    """
    graders = {"easy": grade_easy, "medium": grade_medium, "hard": grade_hard, "reproduce": grade_reproduce}

    grader = graders.get(task_id)
    if grader is None:
        return {"total": 0.001, "feedback": f"Unknown task_id: {task_id}"}

    result = grader(action_data, ground_truth)

    # Penalize invalid action fields (0.5x multiplier per invalid field)
    multiplier = 1.0
    warnings = []
    if action_data.get("root_cause") not in VALID_ROOT_CAUSES:
        multiplier *= 0.5
        warnings.append("[invalid root_cause]")
    if action_data.get("severity") not in VALID_SEVERITIES:
        multiplier *= 0.5
        warnings.append("[invalid severity]")
    if action_data.get("remediation") not in VALID_REMEDIATIONS:
        multiplier *= 0.5
        warnings.append("[invalid remediation]")

    if warnings:
        result["feedback"] += " | " + " ".join(warnings)

    # Scores must be strictly within (0, 1) — never exactly 0.0 or 1.0
    result["total"] = round(max(0.001, min(0.999, result["total"] * multiplier)), 4)
    return result
