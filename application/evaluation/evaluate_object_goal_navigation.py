import logging
import os
from omegaconf import DictConfig
import hydra

from vlmaps.task.habitat_object_nav_task import HabitatObjectNavigationTask
from vlmaps.robot.habitat_lang_robot import HabitatLanguageRobot
from vlmaps.utils.llm_utils import parse_instruction
from vlmaps.utils.matterport3d_categories import mp3dcat
from vlmaps.utils.logging_utils import setup_logging


logger = logging.getLogger(__name__)


@hydra.main(
    version_base=None,
    config_path="../../config",
    config_name="object_goal_navigation_cfg",
)
def main(config: DictConfig) -> None:
    os.environ["MAGNUM_LOG"] = "quiet"
    os.environ["HABITAT_SIM_LOG"] = "quiet"
    robot = HabitatLanguageRobot(config)
    object_nav_task = HabitatObjectNavigationTask(config)
    object_nav_task.reset_metrics()
    scene_ids = []
    if isinstance(config.scene_id, int):
        scene_ids.append(config.scene_id)
    else:
        scene_ids = config.scene_id

    for scene_i, scene_id in enumerate(scene_ids):
        robot.setup_scene(scene_id)
        robot.map.init_categories(mp3dcat.copy())
        object_nav_task.setup_scene(robot.vlmaps_dataloader)
        object_nav_task.load_task()

        for task_id in range(len(object_nav_task.task_dict)):
            object_nav_task.setup_task(task_id)
            result_code = parse_instruction(object_nav_task.instruction)
            logger.info("Instruction: %s", object_nav_task.instruction)
            robot.empty_recorded_actions()
            robot.set_agent_state(object_nav_task.init_hab_tf)

            for line in result_code.split("\n"):
                logger.info("Evaluating line: %s", line)
                if line:
                    eval(line)

            recorded_actions_list = robot.get_recorded_actions()
            robot.set_agent_state(object_nav_task.init_hab_tf)
            for action in recorded_actions_list:
                object_nav_task.test_step(robot.sim, action, vis=config.nav.vis)

            save_dir = robot.vlmaps_dataloader.data_dir / (config.map_config.map_type + "_obj_nav_results")
            os.makedirs(save_dir, exist_ok=True)
            save_path = save_dir / f"{task_id:02}.json"
            object_nav_task.save_single_task_metric(save_path)


if __name__ == "__main__":
    setup_logging()
    main()
