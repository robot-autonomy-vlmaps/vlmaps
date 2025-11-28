from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
import uuid
from typing import Optional

import numpy as np
import open3d as o3d
import cv2
from tqdm import tqdm
from scipy.ndimage import distance_transform_edt


DEFAULT_RENDER_WIDTH = int(os.environ.get("VLMAPS_RENDER_WIDTH", 1280))
DEFAULT_RENDER_HEIGHT = int(os.environ.get("VLMAPS_RENDER_HEIGHT", 720))
DEFAULT_RENDER_DIR = Path(os.environ.get("VLMAPS_RENDER_DIR", "/tmp/vlmaps_renders"))


def _render_point_cloud_offscreen(
    pc: np.ndarray, colors: np.ndarray, file_prefix: str, background: Optional[np.ndarray] = None
) -> Optional[Path]:
    if pc.size == 0 or colors.size == 0:
        print("[OffscreenRenderer] Point cloud is empty, skipping render.")
        return None

    DEFAULT_RENDER_DIR.mkdir(parents=True, exist_ok=True)

    pcd = o3d.geometry.PointCloud()
    pcd.points = o3d.utility.Vector3dVector(pc.astype(np.float32))
    pcd.colors = o3d.utility.Vector3dVector(colors.astype(np.float32))

    renderer = o3d.visualization.rendering.OffscreenRenderer(DEFAULT_RENDER_WIDTH, DEFAULT_RENDER_HEIGHT)
    if background is None:
        background = np.array([0.0, 0.0, 0.0, 0.0], dtype=np.float32)
    renderer.scene.set_background(background.tolist())

    material = o3d.visualization.rendering.MaterialRecord()
    material.shader = "defaultUnlit"
    geom_name = f"pcd_{uuid.uuid4().hex}"
    renderer.scene.add_geometry(geom_name, pcd, material)

    bbox = pcd.get_axis_aligned_bounding_box()
    center = bbox.get_center()
    extent = bbox.get_extent()
    radius = np.linalg.norm(extent)
    if radius < 1e-3:
        radius = 1.0
    eye = center + np.array([radius, radius, radius])
    up = np.array([0.0, 0.0, 1.0])
    renderer.setup_camera(60.0, center, eye, up)

    image = renderer.render_to_image()
    renderer.release_resources()
    del renderer

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
    output_path = DEFAULT_RENDER_DIR / f"{file_prefix}_{timestamp}.png"
    o3d.io.write_image(str(output_path), image)
    print(f"[OffscreenRenderer] Saved visualization to {output_path}")
    return output_path


def visualize_rgb_map_3d(pc: np.ndarray, rgb: np.ndarray) -> Optional[Path]:
    grid_rgb = (rgb / 255.0).astype(np.float32)
    return _render_point_cloud_offscreen(pc, grid_rgb, "rgb_map_3d")


def get_heatmap_from_mask_3d(
    pc: np.ndarray, mask: np.ndarray, cell_size: float = 0.05, decay_rate: float = 0.01
) -> np.ndarray:
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


def visualize_masked_map_3d(pc: np.ndarray, mask: np.ndarray, rgb: np.ndarray, transparency: float = 0.5):
    heatmap = mask.astype(np.float16)
    visualize_heatmap_3d(pc, heatmap, rgb, transparency)


def visualize_heatmap_3d(
    pc: np.ndarray, heatmap: np.ndarray, rgb: np.ndarray, transparency: float = 0.5
) -> Optional[Path]:
    sim_new = (heatmap * 255).astype(np.uint8)
    if sim_new.ndim == 1:
        sim_new = sim_new.reshape(-1, 1)
    heat = cv2.applyColorMap(sim_new, cv2.COLORMAP_JET)
    heat = heat.reshape(-1, 3)[:, ::-1].astype(np.float32)
    heat_rgb = heat * transparency + rgb * (1 - transparency)
    return visualize_rgb_map_3d(pc, heat_rgb)


def pool_3d_label_to_2d(mask_3d: np.ndarray, grid_pos: np.ndarray, gs: int) -> np.ndarray:
    mask_2d = np.zeros((gs, gs), dtype=bool)
    for i, pos in enumerate(grid_pos):
        row, col, h = pos
        mask_2d[row, col] = mask_3d[i] or mask_2d[row, col]

    return mask_2d


def pool_3d_rgb_to_2d(rgb: np.ndarray, grid_pos: np.ndarray, gs: int) -> np.ndarray:
    rgb_2d = np.zeros((gs, gs, 3), dtype=np.uint8)
    height = -100 * np.ones((gs, gs), dtype=np.int32)
    for i, pos in enumerate(grid_pos):
        row, col, h = pos
        if h > height[row, col]:
            rgb_2d[row, col] = rgb[i]

    return rgb_2d


def get_heatmap_from_mask_2d(mask: np.ndarray, cell_size: float = 0.05, decay_rate: float = 0.01) -> np.ndarray:
    dists = distance_transform_edt(mask == 0) / cell_size
    tmp = np.ones_like(dists) - (dists * decay_rate)
    heatmap = np.where(tmp < 0, np.zeros_like(tmp), tmp)

    return heatmap


def visualize_rgb_map_2d(rgb: np.ndarray):
    """visualize rgb image

    Args:
        rgb (np.ndarray): (gs, gs, 3) element range [0, 255] np.uint8
    """
    rgb = rgb.astype(np.uint8)
    bgr = rgb[:, :, ::-1]
    cv2.imshow("rgb map", bgr)
    cv2.waitKey(0)


def visualize_heatmap_2d(rgb: np.ndarray, heatmap: np.ndarray, transparency: float = 0.5):
    """visualize heatmap

    Args:
        rgb (np.ndarray): (gs, gs, 3) element range [0, 255] np.uint8
        heatmap (np.ndarray): (gs, gs) element range [0, 1] np.float32
    """
    sim_new = (heatmap * 255).astype(np.uint8)
    heat = cv2.applyColorMap(sim_new, cv2.COLORMAP_JET)
    heat = heat[:, :, ::-1].astype(np.float32)  # convert to RGB
    heat_rgb = heat * transparency + rgb * (1 - transparency)
    visualize_rgb_map_2d(heat_rgb)


def visualize_masked_map_2d(rgb: np.ndarray, mask: np.ndarray):
    """visualize masked map

    Args:
        rgb (np.ndarray): (gs, gs, 3) element range [0, 255] np.uint8
        mask (np.ndarray): (gs, gs) element range [0, 1] np.uint8
    """
    visualize_heatmap_2d(rgb, mask.astype(np.float32))
