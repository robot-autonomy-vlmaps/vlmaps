"""
Evaluation orchestrator.

Runs multiple LLM configurations against all available scenes and tasks.
Each task × config combination is evaluated independently; failures are
caught per-task so the run continues even when a model produces bad code
or an API call times out.

For configs with n_samples > 1 the LLM is called n_samples times per prompt
so that pass@k, self-consistency and output diversity can be measured later.

Usage:
    vlmaps eval orchestrate
    vlmaps eval orchestrate --config path/to/custom_orchestrator.yaml
"""
import json
import logging
import os
from pathlib import Path
from typing import Dict, List, Optional

import hydra
import yaml
from omegaconf import DictConfig

from vlmaps.llm.config import JazariConfig, LLMConfig, OpenAIConfig
from vlmaps.llm.factory import create_llm_provider
from vlmaps.eval.naming import make_run_name
from vlmaps.eval.results import (
    append_leaderboard,
    compute_aggregate,
    log_aggregate,
    make_failed_result,
    make_task_key,
    save_detailed,
    uuid7,
)
from vlmaps.robot.habitat_lang_robot import HabitatLanguageRobot
from vlmaps.task.habitat_object_nav_task import HabitatObjectNavigationTask
from vlmaps.task.habitat_spatial_goal_nav_task import HabitatSpatialGoalNavigationTask
from vlmaps.utils.llm_utils import parse_instruction
from vlmaps.utils.logging_utils import setup_logging
from vlmaps.utils.matterport3d_categories import mp3dcat

logger = logging.getLogger(__name__)

_CONFIG_DIR = Path(__file__).resolve().parents[2] / "config"
_DEFAULT_ORCH_CFG = _CONFIG_DIR / "orchestrator.yaml"

_TASK_FILE = {
    "obj": "object_navigation_tasks.json",
    "spt": "spatial_goal_navigation_tasks.json",
}


# ---------------------------------------------------------------------------
# Config helpers
# ---------------------------------------------------------------------------

def _load_orch_cfg(path: Optional[str] = None) -> dict:
    cfg_path = Path(path) if path else _DEFAULT_ORCH_CFG
    if not cfg_path.exists():
        raise FileNotFoundError(f"Orchestrator config not found: {cfg_path}")
    with open(cfg_path) as f:
        return yaml.safe_load(f) or {}


def _build_llm_config(entry: dict) -> LLMConfig:
    provider = entry["provider"]
    parse_cfg = dict(entry.get("parse_instruction") or {})
    find_cfg = dict(entry.get("find_similar_category") or {})
    base_url = entry.get("base_url")
    timeout = entry.get("timeout")

    if provider == "openai":
        return LLMConfig(
            provider="openai",
            openai=OpenAIConfig(
                base_url=base_url,
                timeout=timeout,
                parse_instruction=parse_cfg,
                find_similar_category=find_cfg,
            ),
        )
    if provider == "jazari":
        return LLMConfig(
            provider="jazari",
            jazari=JazariConfig(
                base_url=base_url,
                timeout=timeout,
                parse_instruction=parse_cfg,
                find_similar_category=find_cfg,
            ),
        )
    raise ValueError(f"Unsupported provider: {provider}")


def _llm_run_config_dict(entry: dict, eval_seed: int = 0) -> Dict[str, object]:
    """Flatten parse_instruction settings + provider-level and sampling fields for storage."""
    op: Dict[str, object] = dict(entry.get("parse_instruction") or {})
    op.setdefault("base_url", entry.get("base_url"))
    op.setdefault("timeout", entry.get("timeout"))
    op.setdefault("n_samples", entry.get("n_samples", 1))
    op.setdefault("eval_seed", eval_seed)
    return op


# ---------------------------------------------------------------------------
# Scene discovery
# ---------------------------------------------------------------------------

def _discover_scenes(
    data_dir: Path,
    task_types: List[str],
    scene_ids_filter: Optional[List[int]],
) -> List[int]:
    """Return sorted scene_id integers that have at least one task of any requested type."""
    scene_dirs = sorted([d for d in data_dir.iterdir() if d.is_dir()])
    result = []
    for idx, scene_dir in enumerate(scene_dirs):
        if scene_ids_filter is not None and idx not in scene_ids_filter:
            continue
        for tt in task_types:
            task_file = scene_dir / _TASK_FILE[tt]
            if task_file.exists():
                with open(task_file) as f:
                    if len(json.load(f)) > 0:
                        result.append(idx)
                        break
    return result


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def _load_done_set(lb_path: Path) -> set:
    """Load (task_key, run_name, sample_idx) tuples already successfully recorded."""
    done: set = set()
    if not lb_path.exists():
        return done
    with open(lb_path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                r = json.loads(line)
                if not r.get("failed", True):
                    done.add((r["task_key"], r["run_name"], int(r.get("sample_idx", 0))))
            except Exception:
                pass
    return done


def main(config_path: Optional[str] = None) -> None:
    setup_logging()
    os.environ["MAGNUM_LOG"] = "quiet"
    os.environ["HABITAT_SIM_LOG"] = "quiet"

    orch_cfg = _load_orch_cfg(config_path)
    task_types: List[str] = orch_cfg.get("task_types", ["obj", "spt"])
    nav_cfg: dict = orch_cfg.get("nav", {})
    scene_ids_filter: Optional[List[int]] = orch_cfg.get("scene_ids")

    eval_cfg: dict = orch_cfg.get("eval", {})
    eval_seed: int = int(eval_cfg.get("seed", 0))

    # --- Resume: skip already-completed (task_key, run_name, sample_idx) ---
    lb_path = Path(orch_cfg.get("leaderboard_path", "evaluations/leaderboard.jsonl"))
    done_set = _load_done_set(lb_path)
    if done_set:
        logger.info("Resume mode: %d samples already recorded — will skip.", len(done_set))

    # --- Build providers ---
    providers = []
    for entry in orch_cfg.get("llm_configs", []):
        run_name: str = entry.get("run_name") or make_run_name()
        llm_config = _build_llm_config(entry)
        provider_obj = create_llm_provider(llm_config)
        llm_run_cfg = _llm_run_config_dict(entry, eval_seed)
        n_samples = int(entry.get("n_samples", 1))
        providers.append(
            {
                "run_name": run_name,
                "provider_name": entry["provider"],
                "provider": provider_obj,
                "llm_config": llm_run_cfg,
                "n_samples": n_samples,
            }
        )
        logger.info(
            "Config registered: %s  (%s / %s)  n_samples=%d",
            run_name,
            entry["provider"],
            (entry.get("parse_instruction") or {}).get("model", "?"),
            n_samples,
        )

    if not providers:
        logger.error("No llm_configs defined in orchestrator config — nothing to run.")
        return

    # --- Compose Hydra config for robot / task setup ---
    nav_overrides = [
        f"nav.valid_range={nav_cfg.get('valid_range', 1)}",
        "nav.vis=false",
        "nav.waitkey=false",
    ]
    with hydra.initialize_config_dir(config_dir=str(_CONFIG_DIR), version_base=None):
        cfg: DictConfig = hydra.compose(
            config_name="object_goal_navigation_cfg", overrides=nav_overrides
        )

    # --- Discover scenes ---
    data_dir = Path(str(cfg.data_paths.vlmaps_data_dir))
    scene_ids = _discover_scenes(data_dir, task_types, scene_ids_filter)
    logger.info(
        "Scenes: %s | task_types: %s | configs: %d",
        scene_ids,
        task_types,
        len(providers),
    )

    # --- Setup robot and task objects (reused across scenes) ---
    robot = HabitatLanguageRobot(cfg)
    obj_task = HabitatObjectNavigationTask(cfg)
    spt_task = HabitatSpatialGoalNavigationTask(cfg)

    run_results = []

    for scene_id in scene_ids:
        robot.setup_scene(scene_id)
        robot.map.init_categories(mp3dcat.copy())
        scene_folder = robot.vlmaps_dataloader.data_dir.name

        for task_type in task_types:
            task = obj_task if task_type == "obj" else spt_task
            task.reset_metrics()
            task.setup_scene(robot.vlmaps_dataloader)

            try:
                task.load_task()
            except FileNotFoundError:
                logger.warning("No %s tasks for scene %s — skipping", task_type, scene_folder)
                continue

            n_tasks = len(task.task_dict)
            if n_tasks == 0:
                logger.info("Scene %s has 0 %s tasks — skipping", scene_folder, task_type)
                continue

            logger.info(
                "Scene %s | %s | %d tasks | %d configs",
                scene_folder,
                task_type,
                n_tasks,
                len(providers),
            )

            for task_id in range(n_tasks):
                task.setup_task(task_id)
                task_key = make_task_key(scene_folder, task_type, task_id)
                instruction = task.instruction
                init_hab_tf = task.init_hab_tf
                num_subgoals = task.n_subgoals_in_task

                for p in providers:
                    run_name = p["run_name"]
                    provider_obj = p["provider"]
                    provider_name = p["provider_name"]
                    llm_run_cfg = p["llm_config"]
                    n_samples = p["n_samples"]

                    logger.info("  %s | %s | n_samples=%d", task_key, run_name, n_samples)

                    for sample_idx in range(n_samples):
                        if (task_key, run_name, sample_idx) in done_set:
                            logger.debug("Skipping %s [%s] si=%d — already done", task_key, run_name, sample_idx)
                            continue

                        run_uuid = uuid7()

                        # Phase 1: LLM call
                        try:
                            raw, sanitized = parse_instruction(instruction, provider=provider_obj)
                        except Exception as exc:
                            logger.warning(
                                "llm_error %s [%s] sample=%d: %s",
                                task_key, run_name, sample_idx, exc,
                            )
                            result = make_failed_result(
                                run_uuid, task_key, scene_folder, task_type, task_id,
                                scene_id, provider_name, llm_run_cfg, run_name,
                                "llm_error", str(exc), num_subgoals=num_subgoals,
                                sample_idx=sample_idx, n_samples=n_samples,
                            )
                            save_detailed(result)
                            append_leaderboard(result)
                            run_results.append(result)
                            continue

                        # Phase 2: Code execution → record actions
                        robot.empty_recorded_actions()
                        robot.set_agent_state(init_hab_tf)
                        try:
                            for line in sanitized.split("\n"):
                                if line:
                                    eval(line)
                        except Exception as exc:
                            logger.warning(
                                "code_error %s [%s] sample=%d: %s",
                                task_key, run_name, sample_idx, exc,
                            )
                            result = make_failed_result(
                                run_uuid, task_key, scene_folder, task_type, task_id,
                                scene_id, provider_name, llm_run_cfg, run_name,
                                "code_error", str(exc), num_subgoals=num_subgoals,
                                raw=raw, sanitized=sanitized,
                                sample_idx=sample_idx, n_samples=n_samples,
                            )
                            save_detailed(result)
                            append_leaderboard(result)
                            run_results.append(result)
                            continue

                        # Phase 3: Simulation replay
                        recorded_actions = robot.get_recorded_actions()
                        robot.set_agent_state(init_hab_tf)
                        task.setup_task(task_id)  # reset per-sample metrics before replay
                        try:
                            for action in recorded_actions:
                                task.test_step(robot.sim, action, vis=False)
                        except Exception as exc:
                            logger.warning(
                                "sim_error %s [%s] sample=%d: %s",
                                task_key, run_name, sample_idx, exc,
                            )
                            result = make_failed_result(
                                run_uuid, task_key, scene_folder, task_type, task_id,
                                scene_id, provider_name, llm_run_cfg, run_name,
                                "sim_error", str(exc), num_subgoals=num_subgoals,
                                raw=raw, sanitized=sanitized,
                                sample_idx=sample_idx, n_samples=n_samples,
                            )
                            save_detailed(result)
                            append_leaderboard(result)
                            run_results.append(result)
                            continue

                        result = task.get_result_dict(
                            run_uuid=run_uuid,
                            task_key=task_key,
                            scene_folder=scene_folder,
                            task_type=task_type,
                            scene_id=scene_id,
                            provider=provider_name,
                            llm_config=llm_run_cfg,
                            instruction_response_raw=raw,
                            instruction_response_sanitized=sanitized,
                        )
                        result["sample_idx"] = sample_idx
                        result["n_samples"] = n_samples
                        result["run_name"] = run_name
                        result["failed"] = False
                        result["error_type"] = None

                        save_detailed(result)
                        append_leaderboard(result)
                        run_results.append(result)

                        logger.info(
                            "  %s [%s] sample=%d success=%s sub_sr=%.2f",
                            task_key,
                            run_name,
                            sample_idx,
                            result["success"],
                            result["subgoal_success_rate"],
                        )

    metrics = compute_aggregate(run_results)
    log_aggregate(metrics, logger)


if __name__ == "__main__":
    main()
