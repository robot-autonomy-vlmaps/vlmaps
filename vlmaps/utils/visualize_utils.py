from pathlib import Path
import logging

import numpy as np
import open3d as o3d
from open3d.visualization import rendering
import cv2
from tqdm import tqdm
from scipy.ndimage import distance_transform_edt

logger = logging.getLogger(__name__)


def _ensure_parent(path: Path) -> None:
    logger.debug("Ensuring parent directory exists for %s", path)
    Path(path).parent.mkdir(parents=True, exist_ok=True)


def _check_egl_available() -> bool:
    """Check if EGL is available for headless rendering"""
    import os

    # Check if /dev/dri devices exist
    if not os.path.exists("/dev/dri"):
        return False
    # Try to list DRI devices
    try:
        dri_devices = [d for d in os.listdir("/dev/dri") if d.startswith("card")]
        return len(dri_devices) > 0
    except Exception:
        return False


def _render_pcd_offscreen(pcd: o3d.geometry.PointCloud, output_path: Path) -> None:
    logger.debug("Rendering point cloud offscreen to %s", output_path)
    _ensure_parent(output_path)

    # Check EGL availability before attempting render
    if not _check_egl_available():
        logger.warning("EGL not available (no /dev/dri devices found). Skipping 3D visualization.")
        logger.warning("To enable 3D visualization, ensure GPU devices are mounted and accessible.")
        logger.warning("Consider using index_2d=true for 2D visualizations instead.")
        return

    try:
        # Use OffscreenRenderer to avoid GLFW/X11
        bbox = pcd.get_axis_aligned_bounding_box()
        extent = bbox.get_extent()
        diag = max(extent[0], extent[1], extent[2])
        # heuristics for camera distance and image size
        img_size = 800
        renderer = rendering.OffscreenRenderer(img_size, img_size)
        mat = rendering.MaterialRecord()
        mat.shader = "defaultUnlit"
        renderer.scene.add_geometry("pcd", pcd, mat)
        center = bbox.get_center()
        eye = center + diag * 1.5 * np.array([1, 1, 1])
        up = [0, 0, 1]
        renderer.setup_camera(60, center, eye, up)
        renderer.scene.scene.enable_sun_light(True)
        img = renderer.render_to_image()
        o3d.io.write_image(str(output_path), img)
        logger.info("Saved 3D visualization to %s", output_path)
    except Exception as e:
        logger.error("Failed to render 3D visualization offscreen: %s", e)
        logger.warning(
            "EGL initialization may have failed. Ensure GPU devices are accessible (/dev/dri) and NVIDIA drivers are properly configured."
        )
        logger.warning("Skipping 3D visualization. Consider using index_2d=true for 2D visualizations instead.")
        # Don't raise - gracefully skip instead of crashing


def visualize_rgb_map_3d(pc: np.ndarray, rgb: np.ndarray, gui: bool = True, output_path: Path = None):
    logger.debug(
        "visualize_rgb_map_3d gui=%s output_path=%s pc_shape=%s rgb_shape=%s", gui, output_path, pc.shape, rgb.shape
    )
    grid_rgb = rgb / 255.0

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pc)
    pcd.colors = o3d.utility.Vector3dVector(grid_rgb)
    if gui:
        o3d.visualization.draw_geometries([pcd])
    elif output_path is not None:
        _render_pcd_offscreen(pcd, output_path)
    elif not gui:
        logger.info("3D RGB visualization skipped (no output_path provided)")


def get_heatmap_from_mask_3d(
    pc: np.ndarray, mask: np.ndarray, cell_size: float = 0.05, decay_rate: float = 0.01
) -> np.ndarray:
    logger.debug(
        "get_heatmap_from_mask_3d cell_size=%s decay_rate=%s pc_shape=%s mask_shape=%s",
        cell_size,
        decay_rate,
        pc.shape,
        mask.shape,
    )
    target_pc = pc[mask, :]
    other_ids = np.where(mask == 0)[0]
    other_pc = pc[other_ids, :]

    target_sim = np.ones((target_pc.shape[0], 1))
    other_sim = np.zeros((other_pc.shape[0], 1))
    pbar = tqdm(other_pc, desc="Computing heat", total=other_pc.shape[0])
    for other_p_i, p in enumerate(pbar):
        dist = np.linalg.norm(target_pc - p, axis=1) / cell_size
        min_dist_i = np.argmin(dist)
        min_dist = dist[min_dist_i]
        other_sim[other_p_i] = np.clip(1 - min_dist * decay_rate, 0, 1)

    new_pc = pc.copy()
    heatmap = np.ones((new_pc.shape[0], 1), dtype=np.float32)
    for s_i, s in enumerate(other_sim):
        heatmap[other_ids[s_i]] = s
    return heatmap.flatten()


def visualize_masked_map_3d(
    pc: np.ndarray,
    mask: np.ndarray,
    rgb: np.ndarray,
    transparency: float = 0.5,
    gui: bool = True,
    output_path: Path = None,
):
    logger.debug(
        "visualize_masked_map_3d gui=%s output_path=%s pc_shape=%s mask_shape=%s rgb_shape=%s transparency=%s",
        gui,
        output_path,
        pc.shape,
        mask.shape,
        rgb.shape,
        transparency,
    )
    heatmap = mask.astype(np.float16)
    # Gracefully skip if EGL not available
    try:
        visualize_heatmap_3d(pc, heatmap, rgb, transparency, gui=gui, output_path=output_path)
    except Exception as e:
        logger.warning("3D masked map visualization failed, skipping: %s", e)


def visualize_heatmap_3d(
    pc: np.ndarray,
    heatmap: np.ndarray,
    rgb: np.ndarray,
    transparency: float = 0.5,
    gui: bool = True,
    output_path: Path = None,
):
    logger.debug(
        "visualize_heatmap_3d gui=%s output_path=%s pc_shape=%s heatmap_shape=%s rgb_shape=%s transparency=%s",
        gui,
        output_path,
        pc.shape,
        heatmap.shape,
        rgb.shape,
        transparency,
    )
    sim_new = (heatmap * 255).astype(np.uint8)
    heat = cv2.applyColorMap(sim_new, cv2.COLORMAP_JET)
    heat = heat.reshape(-1, 3)[:, ::-1].astype(np.float32)
    heat_rgb = heat * transparency + rgb * (1 - transparency)
    # Gracefully skip if EGL not available
    try:
        visualize_rgb_map_3d(pc, heat_rgb, gui=gui, output_path=output_path)
    except Exception as e:
        logger.warning("3D heatmap visualization failed, skipping: %s", e)


def pool_3d_label_to_2d(mask_3d: np.ndarray, grid_pos: np.ndarray, gs: int) -> np.ndarray:
    logger.debug("pool_3d_label_to_2d gs=%s mask_3d_shape=%s grid_pos_shape=%s", gs, mask_3d.shape, grid_pos.shape)
    mask_2d = np.zeros((gs, gs), dtype=bool)
    for i, pos in enumerate(grid_pos):
        row, col, h = pos
        mask_2d[row, col] = mask_3d[i] or mask_2d[row, col]

    return mask_2d


def pool_3d_rgb_to_2d(rgb: np.ndarray, grid_pos: np.ndarray, gs: int) -> np.ndarray:
    logger.debug("pool_3d_rgb_to_2d gs=%s rgb_shape=%s grid_pos_shape=%s", gs, rgb.shape, grid_pos.shape)
    rgb_2d = np.zeros((gs, gs, 3), dtype=np.uint8)
    height = -100 * np.ones((gs, gs), dtype=np.int32)
    for i, pos in enumerate(grid_pos):
        row, col, h = pos
        if h > height[row, col]:
            rgb_2d[row, col] = rgb[i]

    return rgb_2d


def get_heatmap_from_mask_2d(mask: np.ndarray, cell_size: float = 0.05, decay_rate: float = 0.01) -> np.ndarray:
    logger.debug("get_heatmap_from_mask_2d cell_size=%s decay_rate=%s mask_shape=%s", cell_size, decay_rate, mask.shape)
    dists = distance_transform_edt(mask == 0) / cell_size
    tmp = np.ones_like(dists) - (dists * decay_rate)
    heatmap = np.where(tmp < 0, np.zeros_like(tmp), tmp)

    return heatmap


def visualize_rgb_map_2d(rgb: np.ndarray, gui: bool = True, output_path: Path = None):
    """visualize rgb image

    Args:
        rgb (np.ndarray): (gs, gs, 3) element range [0, 255] np.uint8
    """
    logger.debug("visualize_rgb_map_2d gui=%s output_path=%s rgb_shape=%s", gui, output_path, rgb.shape)
    rgb = rgb.astype(np.uint8)
    bgr = rgb[:, :, ::-1]
    if output_path is not None:
        _ensure_parent(output_path)
        cv2.imwrite(str(output_path), bgr)
        logger.info("Saved 2D RGB visualization to %s", output_path)
    if gui:
        cv2.imshow("rgb map", bgr)
        cv2.waitKey(0)
    elif not gui:
        logger.info("2D RGB visualization skipped (no output_path provided)")


def visualize_heatmap_2d(
    rgb: np.ndarray, heatmap: np.ndarray, transparency: float = 0.5, gui: bool = True, output_path: Path = None
):
    """visualize heatmap

    Args:
        rgb (np.ndarray): (gs, gs, 3) element range [0, 255] np.uint8
        heatmap (np.ndarray): (gs, gs) element range [0, 1] np.float32
    """
    logger.debug(
        "visualize_heatmap_2d gui=%s output_path=%s rgb_shape=%s heatmap_shape=%s transparency=%s",
        gui,
        output_path,
        rgb.shape,
        heatmap.shape,
        transparency,
    )
    sim_new = (heatmap * 255).astype(np.uint8)
    heat = cv2.applyColorMap(sim_new, cv2.COLORMAP_JET)
    heat = heat[:, :, ::-1].astype(np.float32)  # convert to RGB
    heat_rgb = heat * transparency + rgb * (1 - transparency)
    visualize_rgb_map_2d(heat_rgb, gui=gui, output_path=output_path)


def visualize_masked_map_2d(rgb: np.ndarray, mask: np.ndarray, gui: bool = True, output_path: Path = None):
    """visualize masked map

    Args:
        rgb (np.ndarray): (gs, gs, 3) element range [0, 255] np.uint8
        mask (np.ndarray): (gs, gs) element range [0, 1] np.uint8
    """
    logger.debug(
        "visualize_masked_map_2d gui=%s output_path=%s rgb_shape=%s mask_shape=%s",
        gui,
        output_path,
        rgb.shape,
        mask.shape,
    )
    visualize_heatmap_2d(rgb, mask.astype(np.float32), gui=gui, output_path=output_path)
