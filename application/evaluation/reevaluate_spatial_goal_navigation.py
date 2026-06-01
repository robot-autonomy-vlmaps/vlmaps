import logging
import os
import json
from pathlib import Path

from omegaconf import DictConfig
import hydra

from vlmaps.task.habitat_spatial_goal_nav_task import HabitatSpatialGoalNavigationTask
from vlmaps.robot.habitat_lang_robot import HabitatLanguageRobot
from vlmaps.utils.matterport3d_categories import mp3dcat
from vlmaps.utils.logging_utils import setup_logging
from vlmaps.eval.results import uuid7, make_task_key, save_detailed, append_leaderboard


logger = logging.getLogger(__name__)


@hydra.main(
    version_base=None,
    config_path="../../config",
    config_name="spatial_goal_navigation_cfg",
)
def main(config: DictConfig) -> None:
    """
    Re-evaluate a previously saved spatial-goal navigation execution using the
    stored sanitized response, without calling the LLM API again.

    Requires a result file from the new evaluations/detailed/ format:
        result_path=evaluations/detailed/{uuid}.json
    """
    os.environ["MAGNUM_LOG"] = "quiet"
    os.environ["HABITAT_SIM_LOG"] = "quiet"

    if "result_path" not in config or not config.result_path:
        raise ValueError("result_path must be provided, e.g. result_path=evaluations/detailed/{uuid}.json")

    orig_path = Path(str(config.result_path))
    if not orig_path.is_file():
        raise FileNotFoundError(f"Result file not found: {orig_path}")

    with open(orig_path, "r") as f:
        orig_data = json.load(f)

    evaluated_from = orig_data["uuid"]
    scene_id = int(orig_data["scene_id"])
    task_id = int(orig_data["task_id"])
    scene_folder = orig_data["scene_folder"]
    provider = orig_data["provider"]
    llm_config = orig_data["llm_config"]
    instruction_response_raw = orig_data.get("instruction_response_raw", "")
    instruction_response_sanitized = orig_data.get("instruction_response_sanitized", "")

    logger.info(
        "Re-evaluating spatial-goal navigation %s (scene=%s, task_id=%s)",
        evaluated_from,
        scene_id,
        task_id,
    )

    robot = HabitatLanguageRobot(config)
    spatial_nav_task = HabitatSpatialGoalNavigationTask(config)
    spatial_nav_task.reset_metrics()

    robot.setup_scene(scene_id)
    robot.map.init_categories(mp3dcat.copy())
    spatial_nav_task.setup_scene(robot.vlmaps_dataloader)
    spatial_nav_task.load_task()
    spatial_nav_task.setup_task(task_id)

    if "instruction" in orig_data and orig_data["instruction"] != spatial_nav_task.instruction:
        logger.warning("Instruction mismatch — using saved instruction")
        spatial_nav_task.instruction = orig_data["instruction"]

    logger.info("Instruction: %s", spatial_nav_task.instruction)
    robot.empty_recorded_actions()
    robot.set_agent_state(spatial_nav_task.init_hab_tf)

    for line in instruction_response_sanitized.split("\n"):
        logger.info("Re-evaluating line: %s", line)
        if line:
            eval(line)

    recorded_actions_list = robot.get_recorded_actions()
    robot.set_agent_state(spatial_nav_task.init_hab_tf)
    for action in recorded_actions_list:
        spatial_nav_task.test_step(robot.sim, action, vis=config.nav.vis)

    run_uuid = uuid7()
    task_key = make_task_key(scene_folder, "spt", task_id)

    result_dict = spatial_nav_task.get_result_dict(
        run_uuid=run_uuid,
        task_key=task_key,
        scene_folder=scene_folder,
        task_type="spt",
        scene_id=scene_id,
        provider=provider,
        llm_config=llm_config,
        instruction_response_raw=instruction_response_raw,
        instruction_response_sanitized=instruction_response_sanitized,
        evaluated_from=evaluated_from,
    )

    save_detailed(result_dict)
    append_leaderboard(result_dict)

    logger.info(
        "Re-evaluation done | success=%s sub_sr=%.2f | uuid=%s",
        result_dict["success"],
        result_dict["subgoal_success_rate"],
        run_uuid,
    )


if __name__ == "__main__":
    setup_logging()
    main()
