import logging
import os
import uuid
from datetime import datetime
from pathlib import Path
import json

from omegaconf import DictConfig
import hydra

from vlmaps.task.habitat_object_nav_task import HabitatObjectNavigationTask
from vlmaps.robot.habitat_lang_robot import HabitatLanguageRobot
from vlmaps.utils.matterport3d_categories import mp3dcat
from vlmaps.utils.logging_utils import setup_logging


logger = logging.getLogger(__name__)


@hydra.main(
    version_base=None,
    config_path="../../config",
    config_name="object_goal_navigation_cfg",
)
def main(config: DictConfig) -> None:
    """
    Re-evaluate a previously saved object-goal navigation execution using the
    stored sanitized response, without calling the LLM API again.

    The full JSON result file path to re-evaluate must be provided via Hydra overrides:
        result_path=<path/to/result.json>
    """
    os.environ["MAGNUM_LOG"] = "quiet"
    os.environ["HABITAT_SIM_LOG"] = "quiet"

    if "result_path" not in config or not config.result_path:
        raise ValueError("result_path must be provided as a Hydra override, e.g. result_path=data/task_results/...")

    orig_path = Path(str(config.result_path))
    if not orig_path.is_file():
        raise FileNotFoundError(f"Result file not found: {orig_path}")

    # Load original execution metadata
    with open(orig_path, "r") as f:
        orig_data = json.load(f)

    execution_id = str(orig_data.get("execution_id", ""))
    scene_id = int(orig_data["scene_id"])
    task_id = int(orig_data["task_id"])

    instruction_provider = orig_data.get("instruction_provider", "unknown")
    instruction_response_raw = orig_data.get("instruction_response_raw", "")
    instruction_response_sanitized = orig_data.get("instruction_response_sanitized", "")

    logger.info(
        "Re-evaluating object-goal navigation execution %s (scene=%s, task_id=%s)",
        execution_id,
        scene_id,
        task_id,
    )

    # Set up robot and task
    robot = HabitatLanguageRobot(config)
    object_nav_task = HabitatObjectNavigationTask(config)
    object_nav_task.reset_metrics()

    robot.setup_scene(scene_id)
    robot.map.init_categories(mp3dcat.copy())
    object_nav_task.setup_scene(robot.vlmaps_dataloader)
    object_nav_task.load_task()
    object_nav_task.setup_task(task_id)

    # Sanity check: instruction should match
    if "instruction" in orig_data:
        if orig_data["instruction"] != object_nav_task.instruction:
            logger.warning(
                "Instruction mismatch between saved result and task definition. "
                "Using instruction from saved result."
            )
            object_nav_task.instruction = orig_data["instruction"]

    # Replay the sanitized response to generate actions
    logger.info("Instruction: %s", object_nav_task.instruction)
    robot.empty_recorded_actions()
    robot.set_agent_state(object_nav_task.init_hab_tf)

    for line in instruction_response_sanitized.split("\n"):
        logger.info("Re-evaluating line: %s", line)
        if line:
            eval(line)

    recorded_actions_list = robot.get_recorded_actions()
    robot.set_agent_state(object_nav_task.init_hab_tf)
    for action in recorded_actions_list:
        object_nav_task.test_step(robot.sim, action, vis=config.nav.vis)

    # Create a new execution id and timestamp for the re-evaluation
    new_execution_id = str(uuid.uuid4())
    execution_datetime = datetime.now().isoformat()

    object_nav_task.save_single_task_metric(
        scene_id=scene_id,
        task_id=task_id,
        execution_id=new_execution_id,
        execution_datetime=execution_datetime,
        instruction_provider=instruction_provider,
        instruction_response_raw=instruction_response_raw,
        instruction_response_sanitized=instruction_response_sanitized,
        evaluated_from=execution_id,
    )


if __name__ == "__main__":
    setup_logging()
    main()


