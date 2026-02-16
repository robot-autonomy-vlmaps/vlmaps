import logging
import os
import uuid
from datetime import datetime
from omegaconf import DictConfig
import hydra

from vlmaps.task.habitat_spatial_goal_nav_task import HabitatSpatialGoalNavigationTask
from vlmaps.robot.habitat_lang_robot import HabitatLanguageRobot
from vlmaps.utils.llm_utils import parse_instruction
from vlmaps.utils.matterport3d_categories import mp3dcat
from vlmaps.utils.logging_utils import setup_logging
from vlmaps.llm.config import load_llm_config


logger = logging.getLogger(__name__)

@hydra.main(
    version_base=None,
    config_path="../../config",
    config_name="spatial_goal_navigation_cfg",
)
def main(config: DictConfig) -> None:
    os.environ["MAGNUM_LOG"] = "quiet"
    os.environ["HABITAT_SIM_LOG"] = "quiet"
    robot = HabitatLanguageRobot(config)
    spatial_nav_task = HabitatSpatialGoalNavigationTask(config)
    spatial_nav_task.reset_metrics()
    scene_ids = []
    if isinstance(config.scene_id, int):
        scene_ids.append(config.scene_id)
    else:
        scene_ids = config.scene_id

    for scene_i, scene_id in enumerate(scene_ids):
        robot.setup_scene(scene_id)
        robot.map.init_categories(mp3dcat.copy())
        spatial_nav_task.setup_scene(robot.vlmaps_dataloader)
        spatial_nav_task.load_task()

        for task_id in range(len(spatial_nav_task.task_dict)):
            spatial_nav_task.setup_task(task_id)
            
            # Generate execution metadata
            execution_id = str(uuid.uuid4())
            execution_datetime = datetime.now()
            
            # Get LLM provider name
            llm_config = load_llm_config()
            instruction_provider = llm_config.provider
            
            # Parse instruction and get both raw and sanitized responses
            instruction_response_raw, instruction_response_sanitized = parse_instruction(spatial_nav_task.instruction)
            
            logger.info("Instruction: %s", spatial_nav_task.instruction)
            robot.empty_recorded_actions()
            robot.set_agent_state(spatial_nav_task.init_hab_tf)

            for line in instruction_response_sanitized.split("\n"):
                logger.info("Evaluating line: %s", line)
                if line:
                    eval(line)

            recorded_actions_list = robot.get_recorded_actions()
            robot.set_agent_state(spatial_nav_task.init_hab_tf)
            for action in recorded_actions_list:
                spatial_nav_task.test_step(robot.sim, action, vis=config.nav.vis)

            # Save with new folder structure and metadata
            spatial_nav_task.save_single_task_metric(
                scene_id=robot.scene_id,
                task_id=task_id,
                execution_id=execution_id,
                execution_datetime=execution_datetime.isoformat(),
                instruction_provider=instruction_provider,
                instruction_response_raw=instruction_response_raw,
                instruction_response_sanitized=instruction_response_sanitized,
            )


if __name__ == "__main__":
    setup_logging()
    main()
