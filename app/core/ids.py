from __future__ import annotations

from uuid import uuid4


def _generate(prefixed_name: str) -> str:
    return f"{prefixed_name}_{uuid4().hex[:12]}"


def generate_run_id() -> str:
    return _generate("run")


def generate_task_id() -> str:
    return _generate("task")


def generate_event_id() -> str:
    return _generate("evt")


def generate_goal_id() -> str:
    return _generate("goal")


def generate_step_id() -> str:
    return _generate("step")


def generate_eval_id() -> str:
    return _generate("eval")
