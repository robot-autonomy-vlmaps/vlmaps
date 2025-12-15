import os
from pathlib import Path
import numpy as np
import json
import logging
from omegaconf import DictConfig
import hydra
from typing import List, Dict, Union
from vlmaps.utils.logging_utils import setup_logging


logger = logging.getLogger(__name__)

def load_metric(filepath: Union[str, Path]):
    with open(filepath, "r") as f:
        data = json.load(f)

        num_subgoals = data["num_subgoals"]
        num_success_subgoals = len(data["finished_subgoal_ids"])
        success = num_success_subgoals == 4

    return num_subgoals, success, num_success_subgoals, data


def compute_metric(data_dir: Union[str, Path], scene_ids: List[int], metric_folder_name="vlmap_obj_nav_results"):
    vlmaps_data_save_dirs = [
        data_dir / x for x in sorted(os.listdir(data_dir)) if x != ".DS_Store"
    ]  # ignore artifact generated in MacOS
    vlmaps_data_save_dirs = [vlmaps_data_save_dirs[i] for i in scene_ids]
    n_tot_tasks = 0
    n_tot_subgoals = 0
    n_suc_tasks = 0
    n_suc_subgoals = 0
    per_class_suc_dict = {}
    subgoals_suc_dict = {}

    for scene_i, vlmaps_data_dir in enumerate(vlmaps_data_save_dirs):
        metric_save_dir = vlmaps_data_dir / metric_folder_name

        metric_paths_list = sorted(os.listdir(metric_save_dir))

        metric_paths_list = [metric_save_dir / x for x in metric_paths_list if x != ".DS_Store"]

        for metric_i, metric_path in enumerate(metric_paths_list):
            logger.debug("Metric path: %s", metric_path)
            n_sub, suc, n_suc_sub, data = load_metric(metric_path)
            # nav_info = NavInfo()
            # nav_info.load_metric_details(metric_path)
            for subgoal_i, subgoal in enumerate(data["goal_classes"]):
                if subgoal not in per_class_suc_dict:
                    per_class_suc_dict[subgoal] = {"finished": 0, "all": 0}
                per_class_suc_dict[subgoal]["all"] += 1
                if subgoal_i in data["finished_subgoal_ids"]:
                    per_class_suc_dict[subgoal]["finished"] += 1

            n_finished_continue_subgoals = 0
            for i in range(4):
                if i in data["finished_subgoal_ids"]:
                    n_finished_continue_subgoals += 1
                    continue
                break

            for i in range(n_finished_continue_subgoals, -1, -1):
                if i not in subgoals_suc_dict:
                    subgoals_suc_dict[i] = 0
                subgoals_suc_dict[i] += 1

            if n_suc_sub != len(data["finished_subgoal_ids"]):
                logger.warning(
                    "Mismatch between counted and finished subgoals: %s vs %s for %s",
                    n_suc_sub,
                    data["finished_subgoal_ids"],
                    metric_path,
                )

            if n_sub != 4:
                logger.warning("Unexpected subgoal count (%s) success=%s finished=%s", n_sub, suc, n_suc_sub)
                logger.warning("Metric path: %s", metric_path)
            n_tot_tasks += 1
            n_tot_subgoals += n_sub
            n_suc_tasks += suc
            # n_suc_subgoals += n_suc_sub
            n_suc_subgoals += len(data["finished_subgoal_ids"])

    sr = float(n_suc_tasks) / n_tot_tasks
    sub_sr = float(n_suc_subgoals) / n_tot_subgoals
    logger.info("Total tasks number is %s.", n_tot_tasks)
    logger.info("Total subgoals number is %s.", n_tot_subgoals)
    logger.info("Task success rate is %s", sr)
    logger.info("Subgoal success rate is %s", sub_sr)
    for k, v in per_class_suc_dict.items():
        finished = v["finished"]
        all = v["all"]
        logger.info("%s %s/%s", k, finished, all)
    # for n_subgoal in subgoals_suc_dict.keys():
    for n_subgoal in range(5):
        if n_subgoal not in subgoals_suc_dict:
            break
        logger.info(
            "Success tasks finishing %s subgoals consecutively: %s (%.3f)",
            n_subgoal,
            subgoals_suc_dict[n_subgoal],
            float(subgoals_suc_dict[n_subgoal]) / n_tot_tasks,
        )
    return sr, sub_sr


@hydra.main(
    version_base=None,
    config_path="../../config",
    config_name="spatial_goal_navigation_cfg",
)
def main(config: DictConfig) -> None:
    data_dir = Path(config.data_paths.vlmaps_data_dir)
    scene_ids = []
    if isinstance(config.scene_id, int):
        scene_ids.append(config.scene_id)
    else:
        scene_ids = config.scene_id

    compute_metric(data_dir, scene_ids)


if __name__ == "__main__":
    setup_logging()
    main()
