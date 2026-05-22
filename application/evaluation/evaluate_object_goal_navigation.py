import logging
import os
from pathlib import Path

from omegaconf import DictConfig
import hydra

from vlmaps.task.habitat_object_nav_task import HabitatObjectNavigationTask
from vlmaps.robot.habitat_lang_robot import HabitatLanguageRobot
from vlmaps.utils.llm_utils import parse_instruction
from vlmaps.utils.matterport3d_categories import mp3dcat
from vlmaps.utils.logging_utils import setup_logging
from vlmaps.llm.config import load_llm_config
from vlmaps.eval.results import uuid7, make_task_key, get_llm_run_config, save_detailed, append_leaderboard, compute_aggregate, log_aggregate


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

    llm_config = load_llm_config()
    provider = llm_config.provider
    llm_run_cfg = get_llm_run_config(llm_config)

    scene_ids = [config.scene_id] if isinstance(config.scene_id, int) else list(config.scene_id)

    run_results = []
    for scene_id in scene_ids:
        robot.setup_scene(scene_id)
        robot.map.init_categories(mp3dcat.copy())
        object_nav_task.setup_scene(robot.vlmaps_dataloader)
        object_nav_task.load_task()

        scene_folder = robot.vlmaps_dataloader.data_dir.name

        for task_id in range(len(object_nav_task.task_dict)):
            object_nav_task.setup_task(task_id)

            run_uuid = uuid7()
            task_key = make_task_key(scene_folder, "obj", task_id)

            instruction_response_raw, instruction_response_sanitized = parse_instruction(
                object_nav_task.instruction
            )

            logger.info("Task %s | Instruction: %s", task_key, object_nav_task.instruction)
            robot.empty_recorded_actions()
            robot.set_agent_state(object_nav_task.init_hab_tf)

            for line in instruction_response_sanitized.split("\n"):
                logger.info("Evaluating line: %s", line)
                if line:
                    eval(line)

            recorded_actions_list = robot.get_recorded_actions()
            robot.set_agent_state(object_nav_task.init_hab_tf)
            for action in recorded_actions_list:
                object_nav_task.test_step(robot.sim, action, vis=config.nav.vis)

            result_dict = object_nav_task.get_result_dict(
                run_uuid=run_uuid,
                task_key=task_key,
                scene_folder=scene_folder,
                task_type="obj",
                scene_id=scene_id,
                provider=provider,
                llm_config=llm_run_cfg,
                instruction_response_raw=instruction_response_raw,
                instruction_response_sanitized=instruction_response_sanitized,
            )

            save_detailed(result_dict)
            append_leaderboard(result_dict)
            run_results.append(result_dict)

            logger.info(
                "Task %s done | success=%s sub_sr=%.2f",
                task_key,
                result_dict["success"],
                result_dict["subgoal_success_rate"],
            )

    metrics = compute_aggregate(run_results)
    log_aggregate(metrics, logger)


if __name__ == "__main__":
    setup_logging()
    main()
