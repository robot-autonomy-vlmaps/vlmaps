import json
import logging
import os
import time
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from vlmaps.llm.config import LLMConfig

logger = logging.getLogger(__name__)

_LEADERBOARD_KEYS = [
    "uuid",
    "task_key",
    "scene_folder",
    "task_type",
    "task_id",
    "scene_id",
    "execution_datetime",
    "provider",
    "llm_config",
    "num_subgoals",
    "num_finished",
    "subgoal_success_rate",
    "success",
    "evaluated_from",
]


def uuid7() -> str:
    """Generate a UUID v7 (time-sortable). Compatible with Python 3.8+."""
    ts_ms = int(time.time() * 1000)
    rand = os.urandom(10)
    b = bytearray(16)
    b[0:6] = ts_ms.to_bytes(6, "big")
    b[6] = 0x70 | (rand[0] & 0x0F)
    b[7] = rand[1]
    b[8] = 0x80 | (rand[2] & 0x3F)
    b[9:16] = rand[3:10]
    return str(uuid.UUID(bytes=bytes(b)))


def make_task_key(scene_folder: str, task_type: str, task_id: int) -> str:
    """
    Build a kebab-case task identifier.
    Example: '5LpN3gDmAk7_1', 'obj', 0 -> '5LpN3gDmAk7-1-obj-0'
    """
    folder_kebab = scene_folder.replace("_", "-")
    return f"{folder_kebab}-{task_type}-{task_id}"


def get_llm_run_config(config: LLMConfig) -> dict:
    """Return full parse_instruction config + provider-level fields (base_url, timeout)."""
    if config.provider == "openai" and config.openai:
        c = config.openai
        op = dict(c.parse_instruction)
        op.setdefault("base_url", c.base_url)
        op.setdefault("timeout", c.timeout)
        return op
    if config.provider == "jazari" and config.jazari:
        c = config.jazari
        op = dict(c.parse_instruction)
        op.setdefault("base_url", c.base_url)
        op.setdefault("timeout", c.timeout)
        return op
    return {}


def save_detailed(result: dict, base_dir: Path = Path("evaluations")) -> Path:
    """Write the full result dict to evaluations/detailed/{uuid}.json."""
    dest = base_dir / "detailed"
    dest.mkdir(parents=True, exist_ok=True)
    path = dest / f"{result['uuid']}.json"
    with open(path, "w") as f:
        json.dump(result, f, indent=2)
    logger.debug("Saved detailed result to %s", path)
    return path


def append_leaderboard(result: dict, base_dir: Path = Path("evaluations")) -> None:
    """Append a compact leaderboard row to evaluations/leaderboard.jsonl."""
    base_dir.mkdir(parents=True, exist_ok=True)
    row = {k: result.get(k) for k in _LEADERBOARD_KEYS}
    # num_finished is derived at save time from finished_subgoal_ids if not set
    if row.get("num_finished") is None:
        row["num_finished"] = len(result.get("finished_subgoal_ids", []))
    lb_path = base_dir / "leaderboard.jsonl"
    with open(lb_path, "a") as f:
        f.write(json.dumps(row) + "\n")
    logger.debug("Appended leaderboard entry for task %s", result.get("task_key"))


def compute_aggregate(entries: List[dict]) -> dict:
    """Compute aggregate metrics from a list of result dicts."""
    n_tasks = 0
    n_success_tasks = 0
    n_subgoals = 0
    n_success_subgoals = 0
    per_class: Dict[str, Dict[str, int]] = {}
    consecutive: Dict[int, int] = {}

    for e in entries:
        n_tasks += 1
        n_subgoals += e.get("num_subgoals", 0)
        finished_ids = e.get("finished_subgoal_ids", [])
        num_finished = e.get("num_finished", len(finished_ids))
        n_success_subgoals += num_finished
        if e.get("success", False):
            n_success_tasks += 1

        # Per-class stats (object tasks only)
        goal_classes = e.get("goal_classes")
        if goal_classes:
            for i, cls in enumerate(goal_classes):
                if cls not in per_class:
                    per_class[cls] = {"finished": 0, "all": 0}
                per_class[cls]["all"] += 1
                if i in finished_ids:
                    per_class[cls]["finished"] += 1

        # Consecutive subgoals
        n_consec = 0
        for i in range(e.get("num_subgoals", 4)):
            if i in finished_ids:
                n_consec += 1
            else:
                break
        for i in range(n_consec + 1):
            consecutive[i] = consecutive.get(i, 0) + 1

    return {
        "n_tasks": n_tasks,
        "n_success_tasks": n_success_tasks,
        "task_sr": n_success_tasks / n_tasks if n_tasks else 0.0,
        "n_subgoals": n_subgoals,
        "n_success_subgoals": n_success_subgoals,
        "subgoal_sr": n_success_subgoals / n_subgoals if n_subgoals else 0.0,
        "per_class": per_class,
        "consecutive": consecutive,
    }


def log_aggregate(metrics: dict, _logger=None) -> None:
    """Log aggregate metrics summary."""
    if _logger is None:
        _logger = logger
    _logger.info("=== Aggregate Metrics ===")
    _logger.info(
        "Tasks:    %d total, %d success  SR=%.3f",
        metrics["n_tasks"],
        metrics["n_success_tasks"],
        metrics["task_sr"],
    )
    _logger.info(
        "Subgoals: %d total, %d success  sub_SR=%.3f",
        metrics["n_subgoals"],
        metrics["n_success_subgoals"],
        metrics["subgoal_sr"],
    )
    if metrics["per_class"]:
        _logger.info("Per-class:")
        for cls, counts in sorted(metrics["per_class"].items()):
            _logger.info("  %-20s %d/%d", cls, counts["finished"], counts["all"])
    if metrics["consecutive"]:
        _logger.info("Consecutive subgoals:")
        n_tasks = metrics["n_tasks"] or 1
        for n, count in sorted(metrics["consecutive"].items()):
            _logger.info("  %d subgoals: %d tasks (%.3f)", n, count, count / n_tasks)
