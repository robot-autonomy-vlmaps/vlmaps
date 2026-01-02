import numpy as np
import cv2
import logging
from scipy.spatial.distance import cdist
from scipy.ndimage import distance_transform_edt
import pyvisgraph as vg
import matplotlib.pyplot as plt
from PIL import Image
from typing import Tuple, List, Dict, Optional

logger = logging.getLogger(__name__)

def get_segment_islands_pos(segment_map, label_id, detect_internal_contours=False):
    mask = segment_map == label_id
    mask = mask.astype(np.uint8)
    detect_type = cv2.RETR_EXTERNAL
    if detect_internal_contours:
        detect_type = cv2.RETR_TREE

    contours, hierarchy = cv2.findContours(mask, detect_type, cv2.CHAIN_APPROX_SIMPLE)
    # convert contours back to numpy index order
    contours_list = []
    for contour in contours:
        tmp = contour.reshape((-1, 2))
        tmp_1 = np.stack([tmp[:, 1], tmp[:, 0]], axis=1)
        contours_list.append(tmp_1)

    centers_list = []
    bbox_list = []
    for c in contours_list:
        xmin = np.min(c[:, 0])
        xmax = np.max(c[:, 0])
        ymin = np.min(c[:, 1])
        ymax = np.max(c[:, 1])
        bbox_list.append([xmin, xmax, ymin, ymax])

        centers_list.append([(xmin + xmax) / 2, (ymin + ymax) / 2])

    return contours_list, centers_list, bbox_list, hierarchy


def find_closest_points_between_two_contours(obs_map, contour_a, contour_b):
    a = np.zeros_like(obs_map, dtype=np.uint8)
    b = np.zeros_like(obs_map, dtype=np.uint8)
    cv2.drawContours(a, [contour_a[:, [1, 0]]], 0, 255, 1)
    cv2.drawContours(b, [contour_b[:, [1, 0]]], 0, 255, 1)
    rows_a, cols_a = np.where(a == 255)
    rows_b, cols_b = np.where(b == 255)
    pts_a = np.concatenate([rows_a.reshape((-1, 1)), cols_a.reshape((-1, 1))], axis=1)
    pts_b = np.concatenate([rows_b.reshape((-1, 1)), cols_b.reshape((-1, 1))], axis=1)
    dists = cdist(pts_a, pts_b)
    id = np.argmin(dists)
    ida, idb = np.unravel_index(id, dists.shape)
    return [rows_a[ida], cols_a[ida]], [rows_b[idb], cols_b[idb]]


def point_in_contours(obs_map, contours_list, point):
    """
    obs_map: np.ndarray, 1 free, 0 occupied
    contours_list: a list of cv2 contours [[(col1, row1), (col2, row2), ...], ...]
    point: (row, col)
    """
    row, col = int(point[0]), int(point[1])
    ids = []
    logger.debug("Contours count: %s", len(contours_list))
    for con_i, contour in enumerate(contours_list):
        contour_cv2 = contour[:, [1, 0]]
        con_mask = np.zeros_like(obs_map, dtype=np.uint8)
        cv2.drawContours(con_mask, [contour_cv2], 0, 255, -1)
        # con_mask_copy = con_mask.copy()
        # cv2.circle(con_mask_copy, (col, row), 10, 0, 3)
        # cv2.imshow("contour_mask", con_mask_copy)
        # cv2.waitKey()
        if con_mask[row, col] == 255:
            ids.append(con_i)

    return ids


def build_visgraph_with_obs_map(obs_map, use_internal_contour=False, internal_point=None, vis=False, waitkey=False):
    obs_map_vis = (obs_map[:, :, None] * 255).astype(np.uint8)
    obs_map_vis = np.tile(obs_map_vis, [1, 1, 3])
    if vis:
        cv2.imshow("obs", obs_map_vis)
        if waitkey:
            logger.info("Waiting for key press while displaying obstacles map")
            cv2.waitKey()
        else:
            cv2.waitKey(1)

    contours_list, centers_list, bbox_list, hierarchy = get_segment_islands_pos(
        obs_map, 0, detect_internal_contours=use_internal_contour
    )

    if use_internal_contour:
        ids = point_in_contours(obs_map, contours_list, internal_point)
        assert len(ids) == 2, f"The internal point is not in 2 contours, but {len(ids)}"
        point_a, point_b = find_closest_points_between_two_contours(
            obs_map, contours_list[ids[0]], contours_list[ids[1]]
        )
        obs_map = cv2.line((obs_map * 255).astype(np.uint8), (point_a[1], point_a[0]), (point_b[1], point_b[0]), 255, 5)
        obs_map = obs_map == 255
        contours_list, centers_list, bbox_list, hierarchy = get_segment_islands_pos(
            obs_map, 0, detect_internal_contours=False
        )

    poly_list = []

    for contour in contours_list:
        if vis:
            contour_cv2 = contour[:, [1, 0]]
            cv2.drawContours(obs_map_vis, [contour_cv2], 0, (0, 255, 0), 3)
            cv2.imshow("obs", obs_map_vis)
        
        # Simplify contour using cv2.approxPolyDP to reduce points and remove noise
        # This helps eliminate degenerate cases
        contour_cv2_format = contour[:, [1, 0]].astype(np.float32)
        epsilon = 0.1  # Approximation accuracy
        simplified = cv2.approxPolyDP(contour_cv2_format, epsilon, closed=True)
        simplified = simplified.reshape(-1, 2)
        # Convert back to (row, col) format
        simplified_contour = simplified[:, [1, 0]]
        
        contour_pos = []
        # Filter out duplicate consecutive points to avoid degenerate polygons
        prev_point = None
        min_dist_threshold = 0.5  # Minimum distance between consecutive points
        
        for [row, col] in simplified_contour:
            # Skip duplicate points (within threshold)
            if prev_point is not None:
                dist = np.sqrt((row - prev_point[0])**2 + (col - prev_point[1])**2)
                if dist < min_dist_threshold:
                    continue
            contour_pos.append(vg.Point(float(row), float(col)))
            prev_point = (row, col)
        
        # Filter out degenerate polygons (need at least 3 distinct points)
        if len(contour_pos) < 3:
            logger.debug("Skipping degenerate polygon with %d points", len(contour_pos))
            continue
        
        # Check if first and last points are the same (closed polygon)
        if len(contour_pos) > 0:
            first_point = contour_pos[0]
            last_point = contour_pos[-1]
            dist_to_first = np.sqrt((first_point.x - last_point.x)**2 + (first_point.y - last_point.y)**2)
            if dist_to_first < min_dist_threshold:
                # Remove duplicate last point
                contour_pos = contour_pos[:-1]
        
        # Final check: need at least 3 points for a valid polygon
        if len(contour_pos) < 3:
            logger.debug("Skipping degenerate polygon after filtering (only %d points)", len(contour_pos))
            continue
        
        # Check for collinear points that could cause division by zero
        # Remove points that are collinear with their neighbors
        filtered_contour_pos = []
        for i in range(len(contour_pos)):
            prev_idx = (i - 1) % len(contour_pos)
            next_idx = (i + 1) % len(contour_pos)
            
            p1 = contour_pos[prev_idx]
            p2 = contour_pos[i]
            p3 = contour_pos[next_idx]
            
            # Check if three points are collinear (cross product is near zero)
            v1_x = p2.x - p1.x
            v1_y = p2.y - p1.y
            v2_x = p3.x - p2.x
            v2_y = p3.y - p2.y
            
            cross_product = abs(v1_x * v2_y - v1_y * v2_x)
            # If cross product is very small, points are nearly collinear
            if cross_product < 0.01:
                # Skip this point if it's collinear
                continue
            
            filtered_contour_pos.append(p2)
        
        # Need at least 3 points after collinearity check
        if len(filtered_contour_pos) < 3:
            logger.debug("Skipping polygon after collinearity filtering (only %d points)", len(filtered_contour_pos))
            continue
        
        poly_list.append(filtered_contour_pos)
        xlist = [x.x for x in filtered_contour_pos]
        zlist = [x.y for x in filtered_contour_pos]
        if vis:
            # plt.plot(xlist, zlist)
            if waitkey:
                logger.info("Waiting for key press after contour visualization")
                cv2.waitKey()
            else:
                cv2.waitKey(1)
    
    if len(poly_list) == 0:
        logger.warning("No valid polygons found for visibility graph construction")
        # Return empty graph
        g = vg.VisGraph()
        return g
    
    try:
        g = vg.VisGraph()
        g.build(poly_list, workers=4)
    except (ZeroDivisionError, ValueError) as e:
        logger.error("Error building visibility graph: %s. This may be due to degenerate polygons.", e)
        logger.info("Attempting to build with single worker and stricter filtering...")
        # Try with single worker and additional filtering
        # Filter out very small polygons
        filtered_poly_list = []
        for poly in poly_list:
            # Check polygon area (shoelace formula)
            if len(poly) >= 3:
                area = 0.0
                for i in range(len(poly)):
                    j = (i + 1) % len(poly)
                    area += poly[i].x * poly[j].y
                    area -= poly[j].x * poly[i].y
                area = abs(area) / 2.0
                # Only keep polygons with reasonable area
                if area > 0.1:
                    filtered_poly_list.append(poly)
        
        if len(filtered_poly_list) == 0:
            logger.warning("No valid polygons after area filtering")
            g = vg.VisGraph()
            return g
        
        g = vg.VisGraph()
        g.build(filtered_poly_list, workers=1)  # Use single worker for more stability
    
    return g


def get_nearby_position(goal: Tuple[float, float], G: vg.VisGraph) -> Tuple[float, float]:
    for dr, dc in zip([-1, 1, -1, 1], [-1, -1, 1, 1]):
        goalvg_new = vg.Point(goal[0] + dr, goal[1] + dc)
        poly_id_new = G.point_in_polygon(goalvg_new)
        if poly_id_new == -1:
            return (goal[0] + dr, goal[1] + dc)


def plan_to_pos_v2(
    start, 
    goal, 
    obstacles, 
    G: vg.VisGraph = None, 
    vis=False, 
    waitkey=False,
    robot_radius_pixels: float = 3.0,
    min_clearance: Optional[float] = None,
    path_smoothing: bool = True,
    smoothing_method: str = "simple",
    smoothing_factor: float = 0.5
):
    """
    plan a path on a cropped obstacles map represented by a graph.
    Start and goal are tuples of (row, col) in the map.
    
    Args:
        start: Start position (row, col)
        goal: Goal position (row, col)
        obstacles: Obstacle map (1 = free, 0 = occupied)
        G: Visibility graph
        vis: Enable visualization
        waitkey: Wait for keypress during visualization
        robot_radius_pixels: Robot footprint radius for path offsetting
        min_clearance: Minimum clearance from obstacles (default: 1.5 * robot_radius)
        path_smoothing: Enable path smoothing
        smoothing_method: Smoothing method ("simple", "douglas_peucker")
        smoothing_factor: Smoothing factor (window_size for simple, epsilon for douglas_peucker)
    """

    logger.info("Planning path: start=%s goal=%s", start, goal)
    if vis:
        obs_map_vis = (obstacles[:, :, None] * 255).astype(np.uint8)
        obs_map_vis = np.tile(obs_map_vis, [1, 1, 3])
        obs_map_vis = cv2.circle(obs_map_vis, (int(start[1]), int(start[0])), 3, (255, 0, 0), -1)
        obs_map_vis = cv2.circle(obs_map_vis, (int(goal[1]), int(goal[0])), 3, (0, 0, 255), -1)
        cv2.imshow("planned path", obs_map_vis)
        if waitkey:
            logger.info("Waiting for key press on planned path visualization")
            cv2.waitKey()
        else:
            cv2.waitKey(1)

    path = []
    startvg = vg.Point(start[0], start[1])
    if obstacles[int(start[0]), int(start[1])] == 0:
        logger.warning("Start position lies in obstacles; snapping to nearest free cell")
        rows, cols = np.where(obstacles == 1)
        dist_sq = (rows - start[0]) ** 2 + (cols - start[1]) ** 2
        id = np.argmin(dist_sq)
        new_start = [rows[id], cols[id]]
        path.append(new_start)
        startvg = vg.Point(new_start[0], new_start[1])

    goalvg = vg.Point(goal[0], goal[1])
    poly_id = G.point_in_polygon(goalvg)
    if obstacles[int(goal[0]), int(goal[1])] == 0:
        logger.warning("Goal position lies in obstacles; adjusting to nearest free cell")
        try:
            goalvg = G.closest_point(goalvg, poly_id, length=1)
        except:
            goal_new = get_nearby_position(goal, G)
            goalvg = vg.Point(goal_new[0], goal_new[1])

        logger.debug("Adjusted goal to %s", goalvg)
    path_vg = G.shortest_path(startvg, goalvg)

    for point in path_vg:
        subgoal = [point.x, point.y]
        path.append(subgoal)
    logger.debug("Computed path with %s waypoints", len(path))

    # Apply path offsetting to prevent corner collisions
    if robot_radius_pixels > 0:
        try:
            path = offset_path_from_obstacles(path, obstacles, robot_radius_pixels, min_clearance)
            logger.debug("Applied path offsetting, path now has %s waypoints", len(path))
        except Exception as e:
            logger.warning("Path offsetting failed: %s, using original path", e)
    
    # Apply path smoothing to reduce jaggedness
    if path_smoothing and len(path) > 2:
        try:
            if smoothing_method == "simple":
                window_size = max(3, int(smoothing_factor * 10))
                if window_size % 2 == 0:
                    window_size += 1
                path = smooth_path_simple(path, window_size)
            elif smoothing_method == "douglas_peucker":
                path = simplify_path_douglas_peucker(path, smoothing_factor)
            logger.debug("Applied path smoothing (%s), path now has %s waypoints", smoothing_method, len(path))
        except Exception as e:
            logger.warning("Path smoothing failed: %s, using original path", e)

    # check the final goal is not in obstacles
    # if obstacles[int(goal[0]), int(goal[1])] == 0:
    #     path = path[:-1]

    if vis:
        obs_map_vis = (obstacles[:, :, None] * 255).astype(np.uint8)
        obs_map_vis = np.tile(obs_map_vis, [1, 1, 3])

        for i, point in enumerate(path):
            subgoal = (int(point[1]), int(point[0]))
            logger.debug("Subgoal %s: %s", i, subgoal)
            obs_map_vis = cv2.circle(obs_map_vis, subgoal, 5, (255, 0, 0), -1)
            if i > 0:
                cv2.line(obs_map_vis, last_subgoal, subgoal, (255, 0, 0), 2)
            last_subgoal = subgoal
        obs_map_vis = cv2.circle(obs_map_vis, (int(start[1]), int(start[0])), 5, (0, 255, 0), -1)
        obs_map_vis = cv2.circle(obs_map_vis, (int(goal[1]), int(goal[0])), 5, (0, 0, 255), -1)

        seg = Image.fromarray(obs_map_vis)
        cv2.imshow("planned path", obs_map_vis)
        if waitkey:
            logger.info("Waiting for key press on planned path window")
            cv2.waitKey()
        else:
            cv2.waitKey(1)

    return path


def get_bbox(center, size):
    """
    Return min corner and max corner coordinate
    """
    min_corner = center - size / 2
    max_corner = center + size / 2
    return min_corner, max_corner


def get_dist_to_bbox_2d(center, size, pos):
    min_corner_2d, max_corner_2d = get_bbox(center, size)

    dx = pos[0] - center[0]
    dy = pos[1] - center[1]

    if pos[0] < min_corner_2d[0] or pos[0] > max_corner_2d[0]:
        if pos[1] < min_corner_2d[1] or pos[1] > max_corner_2d[1]:
            """
            star region
            *  |  |  *
            ___|__|___
               |  |
            ___|__|___
               |  |
            *  |  |  *
            """

            dx_c = np.abs(dx) - size[0] / 2
            dy_c = np.abs(dy) - size[1] / 2
            dist = np.sqrt(dx_c * dx_c + dy_c * dy_c)
            return dist
        else:
            """
            star region
               |  |
            ___|__|___
            *  |  |  *
            ___|__|___
               |  |
               |  |
            """
            dx_b = np.abs(dx) - size[0] / 2
            return dx_b
    else:
        if pos[1] < min_corner_2d[1] or pos[1] > max_corner_2d[1]:
            """
            star region
               |* |
            ___|__|___
               |  |
            ___|__|___
               |* |
               |  |
            """
            dy_b = np.abs(dy) - size[1] / 2
            return dy_b

        """
        star region
           |  |  
        ___|__|___
           |* |   
        ___|__|___
           |  |   
           |  |  
        """
        return 0


def offset_path_from_obstacles(
    path: List[List[float]], 
    obstacle_map: np.ndarray, 
    robot_radius_pixels: float = 3.0,
    min_clearance: Optional[float] = None
) -> List[List[float]]:
    """
    Offset path waypoints away from obstacles to prevent corner collisions.
    
    Args:
        path: List of waypoints [[row, col], ...]
        obstacle_map: Binary obstacle map (1 = free, 0 = occupied)
        robot_radius_pixels: Robot footprint radius in map pixels
        min_clearance: Minimum distance from obstacles (default: 1.5 * robot_radius)
    
    Returns:
        Offset path with waypoints pushed away from obstacles
    """
    if len(path) < 2:
        return path
    
    if min_clearance is None:
        min_clearance = 1.5 * robot_radius_pixels
    
    # Create distance transform: distance from each free cell to nearest obstacle
    # Invert obstacle map: 0 = free, 1 = occupied for distance transform
    obs_inverted = 1 - obstacle_map.astype(np.uint8)
    dist_transform = distance_transform_edt(obs_inverted)
    
    # Convert path to numpy array for easier manipulation
    path_array = np.array(path)
    offset_path = path_array.copy()
    
    # Process each waypoint (skip first and last to preserve start/goal)
    for i in range(1, len(path) - 1):
        row, col = int(path_array[i, 0]), int(path_array[i, 1])
        
        # Check bounds
        if row < 0 or row >= obstacle_map.shape[0] or col < 0 or col >= obstacle_map.shape[1]:
            continue
        
        # Get current distance to obstacle
        current_dist = dist_transform[row, col]
        
        # If too close to obstacle, push away
        if current_dist < min_clearance:
            # Find direction away from nearest obstacle using gradient
            # Sample nearby points to estimate gradient
            offsets = [(-1, -1), (-1, 0), (-1, 1), (0, -1), (0, 1), (1, -1), (1, 0), (1, 1)]
            max_dist = current_dist
            best_offset = (0, 0)
            
            for dr, dc in offsets:
                r, c = row + dr, col + dc
                if 0 <= r < obstacle_map.shape[0] and 0 <= c < obstacle_map.shape[1]:
                    dist = dist_transform[r, c]
                    if dist > max_dist:
                        max_dist = dist
                        best_offset = (dr, dc)
            
            # Push waypoint in direction of increasing distance
            if best_offset != (0, 0):
                push_distance = min_clearance - current_dist
                dr, dc = best_offset
                # Normalize direction
                norm = np.sqrt(dr**2 + dc**2)
                if norm > 0:
                    dr_norm = dr / norm
                    dc_norm = dc / norm
                    offset_path[i, 0] += dr_norm * push_distance
                    offset_path[i, 1] += dc_norm * push_distance
                    
                    # Verify new position is still in free space
                    new_row, new_col = int(offset_path[i, 0]), int(offset_path[i, 1])
                    if (0 <= new_row < obstacle_map.shape[0] and 
                        0 <= new_col < obstacle_map.shape[1] and
                        obstacle_map[new_row, new_col] == 0):
                        # Revert if moved into obstacle
                        offset_path[i] = path_array[i]
    
    return offset_path.tolist()


def smooth_path_simple(path: List[List[float]], window_size: int = 3) -> List[List[float]]:
    """
    Smooth path using moving average.
    
    Args:
        path: List of waypoints [[row, col], ...]
        window_size: Size of moving average window (must be odd)
    
    Returns:
        Smoothed path
    """
    if len(path) < 3:
        return path
    
    if window_size % 2 == 0:
        window_size += 1
    
    path_array = np.array(path)
    smoothed = path_array.copy()
    half_window = window_size // 2
    
    # Keep first and last points unchanged
    for i in range(1, len(path) - 1):
        start_idx = max(0, i - half_window)
        end_idx = min(len(path), i + half_window + 1)
        smoothed[i] = np.mean(path_array[start_idx:end_idx], axis=0)
    
    return smoothed.tolist()


def simplify_path_douglas_peucker(path: List[List[float]], epsilon: float = 1.0) -> List[List[float]]:
    """
    Simplify path using Douglas-Peucker algorithm.
    
    Args:
        path: List of waypoints [[row, col], ...]
        epsilon: Maximum distance for simplification
    
    Returns:
        Simplified path
    """
    if len(path) <= 2:
        return path
    
    def perpendicular_distance(point, line_start, line_end):
        """Calculate perpendicular distance from point to line segment"""
        x0, y0 = point
        x1, y1 = line_start
        x2, y2 = line_end
        
        # Vector from line_start to line_end
        dx = x2 - x1
        dy = y2 - y1
        
        if dx == 0 and dy == 0:
            # Line segment is a point
            return np.sqrt((x0 - x1)**2 + (y0 - y1)**2)
        
        # Parameter t for closest point on line
        t = max(0, min(1, ((x0 - x1) * dx + (y0 - y1) * dy) / (dx**2 + dy**2)))
        
        # Closest point on line segment
        closest_x = x1 + t * dx
        closest_y = y1 + t * dy
        
        return np.sqrt((x0 - closest_x)**2 + (y0 - closest_y)**2)
    
    def douglas_peucker_recursive(points, start_idx, end_idx, epsilon):
        """Recursive Douglas-Peucker algorithm"""
        if end_idx - start_idx <= 1:
            return [start_idx]
        
        # Find point with maximum distance
        max_dist = 0
        max_idx = start_idx
        
        for i in range(start_idx + 1, end_idx):
            dist = perpendicular_distance(points[i], points[start_idx], points[end_idx])
            if dist > max_dist:
                max_dist = dist
                max_idx = i
        
        # If max distance is greater than epsilon, recursively simplify
        if max_dist > epsilon:
            # Recursive call for left and right segments
            left = douglas_peucker_recursive(points, start_idx, max_idx, epsilon)
            right = douglas_peucker_recursive(points, max_idx, end_idx, epsilon)
            return left[:-1] + right
        else:
            # All points between start and end can be approximated by line
            return [start_idx, end_idx]
    
    path_array = np.array(path)
    indices = douglas_peucker_recursive(path_array, 0, len(path) - 1, epsilon)
    return [path[i] for i in sorted(set(indices))]
