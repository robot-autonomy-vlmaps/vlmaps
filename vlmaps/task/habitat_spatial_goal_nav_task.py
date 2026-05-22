from pathlib import Path
import json
import os
from datetime import datetime
from typing import Dict, List, Tuple, Union, Optional
import logging

from omegaconf import DictConfig
import numpy as np
import hydra
import habitat_sim

from vlmaps.task.habitat_task import HabitatTask
from vlmaps.utils.habitat_utils import agent_state2tf, get_position_floor_objects
from vlmaps.utils.navigation_utils import get_dist_to_bbox_2d
from vlmaps.utils.habitat_utils import display_sample

logger = logging.getLogger(__name__)


class HabitatSpatialGoalNavigationTask(HabitatTask):
    def load_task(self):
        assert hasattr(self, "vlmaps_dataloader"), "Please call setup_scene() first"

        task_path = Path(self.vlmaps_dataloader.data_dir) / "spatial_goal_navigation_tasks.json"
        with open(task_path, "r") as f:
            self.task_dict = json.load(f)

    def setup_task(self, task_id: int):
        json_task_id = self.task_dict[task_id]["task_id"]
        assert json_task_id == task_id, "Task ID mismatch"
        self.task_id = task_id
        self.init_hab_tf = np.array(self.task_dict[task_id]["tf_habitat"], dtype=np.float32).reshape((4, 4))
        self.map_grid_size = self.task_dict[task_id]["map_grid_size"]
        self.map_cell_size = self.task_dict[task_id]["map_cell_size"]
        self.scene = self.task_dict[task_id]["scene"]
        self.instruction = self.task_dict[task_id]["instruction"]
        self.goals = {}
        for goal in self.task_dict[task_id]["goals"]:
            goal_id = goal["goal_id"]
            self.goals[goal_id] = []
            for goal_position in goal["goal_positions"]:
                pos = [goal_position["row"], goal_position["col"]]
                self.goals[goal_id].append(pos)

        # metric
        self.n_subgoals_in_task = len(self.goals)
        self.curr_subgoal_id = 0
        self.finished_subgoals = []
        self.distance_to_subgoals = []
        self.success = False
        self.actions = []
        # Ensure metric fields exist even if the task does not finish
        self.subgoal_success_rate = 0.0

    def test_step(
        self, sim: habitat_sim.Simulator, action: str, agent_map_position: np.array = None, vis: bool = False
    ):
        self.actions.append(action)
        if action != "stop":
            sim.step(action)
            if vis:
                obs = sim.get_sensor_observations(0)
                display_sample({}, obs["color_sensor"], waitkey=self.config.nav.waitkey)
        if self.curr_subgoal_id >= len(self.goals):
            return
        if agent_map_position is None:
            agent = sim.get_agent(0)
            agent_state = agent.get_state()

            habitat_2_cam_pose = np.eye(4)
            habitat_2_cam_pose[1, 1] = -1
            habitat_2_cam_pose[2, 2] = -1
            tf_hab = agent_state2tf(agent_state)
            self.vlmaps_dataloader.from_habitat_tf(tf_hab)
            agent_map_position = self.vlmaps_dataloader.to_full_map_pose()[:2]
            # tf_cam = tf_hab @ self.tf_ro_cam
            # pose = np.linalg.inv(self.map_init_cam_pose) @ tf_cam
            # x, y = pos2grid_id(self.gs, self.cs, pose[0, 3], pose[2, 3])
            # agent_map_position = [x, y]

        row, col = agent_map_position

        min_dist = np.inf
        logger.info("Testing subgoal %s/%s", self.curr_subgoal_id + 1, self.n_subgoals_in_task)
        targets = self.goals[self.curr_subgoal_id]
        for pos in targets:
            trow, tcol = pos[0], pos[1]
            drow, dcol = trow - row, tcol - col
            dist = np.sqrt(drow * drow + dcol * dcol)
            min_dist = dist if dist < min_dist else min_dist
        if min_dist < self.config.nav.valid_range / self.vlmaps_dataloader.cs:
            self.finished_subgoals.append(self.curr_subgoal_id)
            self.n_success_subgoals += 1
            logger.info("Target reached! Distance: %spix.", min_dist)
        logger.debug("Min distance to target: %spix", min_dist)
        self.distance_to_subgoals.append(min_dist * self.vlmaps_dataloader.cs)

        self.curr_subgoal_id += 1

        if len(self.finished_subgoals) == self.n_subgoals_in_task:
            self.success = True
            self.n_success_tasks += 1
            self.n_tot_tasks += 1
            self.n_tot_subgoals += self.n_subgoals_in_task
            self.n_success_subgoals += len(self.finished_subgoals)
            self.subgoal_success_rate = float(len(self.finished_subgoals)) / self.n_subgoals_in_task

    def get_result_dict(
        self,
        run_uuid: str,
        task_key: str,
        scene_folder: str,
        task_type: str,
        scene_id: int,
        provider: str,
        llm_config: dict,
        instruction_response_raw: str,
        instruction_response_sanitized: str,
        forward_dist: float = 0.05,
        turn_angle: float = 1,
        evaluated_from: Optional[str] = None,
    ) -> dict:
        return {
            "uuid": run_uuid,
            "task_key": task_key,
            "scene_folder": scene_folder,
            "task_type": task_type,
            "task_id": self.task_id,
            "scene_id": scene_id,
            "execution_datetime": datetime.now().isoformat(),
            "provider": provider,
            "llm_config": llm_config,
            "evaluated_from": evaluated_from,
            "instruction": self.instruction,
            "instruction_response_raw": instruction_response_raw,
            "instruction_response_sanitized": instruction_response_sanitized,
            "num_subgoals": self.n_subgoals_in_task,
            "num_finished": len(self.finished_subgoals),
            "finished_subgoal_ids": self.finished_subgoals,
            "subgoal_success_rate": self.subgoal_success_rate,
            "success": self.success,
            "distance_to_subgoals": self.distance_to_subgoals,
            "actions": self.actions,
            "init_tf_hab": self.init_hab_tf.tolist(),
            "forward_dist": forward_dist,
            "turn_angle": turn_angle,
        }


@hydra.main(
    version_base=None,
    config_path="../../config",
    config_name="test_config.yaml",
)
def main(config: DictConfig) -> None:
    from vlmaps.dataloader.habitat_dataloader import VLMapsDataloaderHabitat

    data_dir = Path(config.data_paths.vlmaps_data_dir) / "vlmaps_dataset"
    data_dirs = sorted([x for x in data_dir.iterdir() if x.is_dir()])

    dataloader = VLMapsDataloaderHabitat(data_dirs[0], config.map_config)
    task = HabitatSpatialGoalNavigationTask(config)
    task.setup_scene(dataloader)
    task.load_task()
    task.setup_task(0)
    logger.debug("Goals: %s", task.goals)


if __name__ == "__main__":
    main()
