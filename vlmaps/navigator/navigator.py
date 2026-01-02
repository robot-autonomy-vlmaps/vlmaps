import logging
import numpy as np
import pyvisgraph as vg

from vlmaps.utils.navigation_utils import build_visgraph_with_obs_map, plan_to_pos_v2
from typing import Tuple, List, Dict


logger = logging.getLogger(__name__)

class Navigator:
    def __init__(self):
        self.current_path = None
        self.path_start = None
        self.path_goal = None
        self.last_replan_check = 0

    def build_visgraph(self, obstacle_map: np.ndarray, rowmin: float, colmin: float, vis: bool = False):
        self.obs_map = obstacle_map
        self.visgraph = build_visgraph_with_obs_map(obstacle_map, vis=vis)
        self.rowmin = rowmin
        self.colmin = colmin

    def plan_to(
        self, 
        start_full_map: Tuple[float, float], 
        goal_full_map: Tuple[float, float], 
        vis: bool = False,
        robot_radius_pixels: float = 3.0,
        min_clearance: float = None,
        path_smoothing: bool = True,
        smoothing_method: str = "simple",
        smoothing_factor: float = 0.5
    ) -> List[List[float]]:
        """
        Take full map start (row, col) and full map goal (row, col) as input
        Return a list of full map path points (row, col) as the palnned path
        """
        start = self._convert_full_map_pos_to_cropped_map_pos(start_full_map)
        goal = self._convert_full_map_pos_to_cropped_map_pos(goal_full_map)
        if self._check_if_start_in_graph_obstacle(start):
            self._rebuild_visgraph(start, vis)
        paths = plan_to_pos_v2(
            start, goal, self.obs_map, self.visgraph, vis,
            robot_radius_pixels=robot_radius_pixels,
            min_clearance=min_clearance,
            path_smoothing=path_smoothing,
            smoothing_method=smoothing_method,
            smoothing_factor=smoothing_factor
        )
        paths = self.shift_path(paths, self.rowmin, self.colmin)
        
        # Store path for replanning
        self.current_path = paths
        self.path_start = start_full_map
        self.path_goal = goal_full_map
        self.last_replan_check = 0
        
        return paths

    def shift_path(self, paths: List[List[float]], row_shift: int, col_shift: int) -> List[List[float]]:
        shifted_paths = []
        for point in paths:
            shifted_paths.append([point[0] + row_shift, point[1] + col_shift])
        return shifted_paths

    def _check_if_start_in_graph_obstacle(self, start: Tuple[float, float]):
        startvg = vg.Point(start[0], start[1])
        poly_id = self.visgraph.point_in_polygon(startvg)
        if poly_id != -1 and self.obs_map[int(start[0]), int(start[1])] == 1:
            return True
        return False

    def _rebuild_visgraph(self, start: Tuple[float, float], vis: bool = False):
        self.visgraph = build_visgraph_with_obs_map(
            self.obs_map, use_internal_contour=True, internal_point=start, vis=vis
        )

    def _convert_full_map_pos_to_cropped_map_pos(self, full_map_pos: Tuple[float, float]) -> Tuple[float, float]:
        """
        full_map_pos: (row, col) in full map
        Return (row, col) in cropped_map
        """
        # Validate input types
        if full_map_pos is None:
            raise ValueError("full_map_pos cannot be None")
        
        try:
            row = float(full_map_pos[0])
            col = float(full_map_pos[1])
        except (TypeError, ValueError, IndexError) as e:
            raise ValueError(f"Invalid full_map_pos format: {full_map_pos}. Expected (row, col) tuple of numbers. Error: {e}")
        
        logger.debug("Converting full_map_pos=%s using rowmin=%s colmin=%s", full_map_pos, self.rowmin, self.colmin)
        return [row - self.rowmin, col - self.colmin]

    def _convert_cropped_map_pos_to_full_map_pos(self, cropped_map_pos: Tuple[float, float]) -> Tuple[float, float]:
        """
        cropped_map_pos: (row, col) in cropped map
        Return (row, col) in full map
        """
        return [cropped_map_pos[0] + self.rowmin, cropped_map_pos[1] + self.colmin]

    def check_replan_needed(
        self,
        current_pos: Tuple[float, float],
        deviation_threshold: float = 2.0,
        check_interval: int = 5,
        action_count: int = 0
    ) -> bool:
        """
        Check if replanning is needed based on current position and path deviation.
        
        Args:
            current_pos: Current robot position (row, col) in full map
            deviation_threshold: Maximum allowed deviation from path (in cells)
            check_interval: Number of actions between replan checks
            action_count: Current action count since last check
        
        Returns:
            True if replanning is needed, False otherwise
        """
        if self.current_path is None or len(self.current_path) < 2:
            return False
        
        # Only check at specified intervals
        if action_count - self.last_replan_check < check_interval:
            return False
        
        # Validate current position
        try:
            row = float(current_pos[0])
            col = float(current_pos[1])
        except (TypeError, ValueError, IndexError):
            logger.warning("Invalid current_pos format in check_replan_needed: %s", current_pos)
            return False
        
        self.last_replan_check = action_count
        
        # Find closest point on current path
        # Only check against remaining path (points ahead of current position)
        # This prevents replanning when we're just moving along the path
        path_array = np.array(self.current_path)
        
        # Find which path segment we're closest to
        # Check distance to each path segment (line between consecutive waypoints)
        min_dist = np.inf
        for i in range(len(path_array) - 1):
            p1 = path_array[i]
            p2 = path_array[i + 1]
            
            # Vector from p1 to p2
            seg_vec = p2 - p1
            seg_len_sq = np.sum(seg_vec**2)
            
            if seg_len_sq < 1e-6:  # Degenerate segment
                # Just use point distance
                dist = np.sqrt((row - p1[0])**2 + (col - p1[1])**2)
            else:
                # Project current position onto segment
                curr_vec = np.array([row, col]) - p1
                t = np.clip(np.dot(curr_vec, seg_vec) / seg_len_sq, 0.0, 1.0)
                proj_point = p1 + t * seg_vec
                dist = np.sqrt((row - proj_point[0])**2 + (col - proj_point[1])**2)
            
            min_dist = min(min_dist, dist)
        
        # Also check distance to path endpoints
        for point in path_array:
            dist = np.sqrt((row - point[0])**2 + (col - point[1])**2)
            min_dist = min(min_dist, dist)
        
        # Check if deviation exceeds threshold
        # Add some hysteresis to prevent oscillation
        if min_dist > deviation_threshold * 1.2:  # Require 20% more deviation to trigger
            logger.info("Replanning needed: deviation %.2f > threshold %.2f", min_dist, deviation_threshold)
            return True
        
        return False
