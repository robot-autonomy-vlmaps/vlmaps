import logging
from pathlib import Path
from typing import List, Tuple

import hydra
from omegaconf import DictConfig
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

from vlmaps.map.vlmap import VLMap
from vlmaps.utils.logging_utils import setup_logging
from vlmaps.utils.matterport3d_categories import mp3dcat
from vlmaps.utils.visualize_utils import visualize_rgb_map_3d_async


logger = logging.getLogger(__name__)


def load_scene_vlmap(config: DictConfig) -> VLMap:
    """Load VLMap for the given scene_id from config."""
    data_dir = Path(config.data_paths.vlmaps_data_dir)
    data_dirs = sorted([x for x in data_dir.iterdir() if x.is_dir()])
    scene_path = data_dirs[config.scene_id]
    logger.info("Inspecting scene at %s", scene_path)

    vlmap = VLMap(config.map_config, data_dir=scene_path)
    vlmap.load_map(scene_path)
    return vlmap


def show_obstacle_map(vlmap: VLMap, h_min: float = 0.0, h_max: float = 1.5) -> None:
    """Generate and display the cropped obstacle map.
    
    Args:
        vlmap: VLMap object
        h_min: Minimum height (m) of voxels considered as obstacles
        h_max: Maximum height (m) of voxels considered as obstacles
    """
    logger.info("Generating obstacle map")
    vlmap.generate_obstacle_map(h_min, h_max)
    obstacles_cropped = vlmap.get_obstacle_cropped()

    plt.figure(figsize=(6, 6))
    plt.title("Obstacle map (1=free, 0=obstacle)")
    plt.imshow(obstacles_cropped, cmap="gray")
    plt.axis("off")
    plt.show(block=False)

def show_obstacle_map_3d(vlmap: VLMap, h_min: float = 0.0, h_max: float = 1.5) -> None:
    """Visualize obstacles as a 3D point cloud.

    Voxels whose height lies within [h_min, h_max] and are occupied are shown as red points.
    """
    if vlmap.occupied_ids is None:
        logger.warning("occupied_ids not available on VLMap; did you load the map correctly?")
        return

    heights = np.arange(0, vlmap.occupied_ids.shape[-1]) * vlmap.cs
    height_mask = np.logical_and(heights >= h_min, heights <= h_max)
    occ_volume = vlmap.occupied_ids[..., height_mask] > 0  # (gs, gs, vh_sub)

    if not np.any(occ_volume):
        logger.warning("No occupied voxels found in height range [%s, %s]", h_min, h_max)
        return

    voxel_ids = vlmap.occupied_ids[..., height_mask][occ_volume]  # flat voxel indices into grid_pos / grid_rgb
    pc = vlmap.grid_pos[voxel_ids]  # use grid indices for geometry; scale is consistent with features

    colors = np.zeros((pc.shape[0], 3), dtype=np.float32)
    colors[:] = np.array([255.0, 0.0, 0.0], dtype=np.float32)  # red for obstacles

    visualize_rgb_map_3d_async(pc, colors)


def compute_category_map(vlmap: VLMap) -> Tuple[np.ndarray, List[str], np.ndarray]:
    """Compute a 2D category label map over the grid using MP3D categories,
    and return per-voxel predictions as well.
    """
    vlmap._init_clip()
    categories = mp3dcat.copy()
    logger.info("Computing category scores for %d classes", len(categories))

    scores_mat = vlmap.init_categories(categories)  # (N, C+1) with extra "other"
    num_labels = scores_mat.shape[1]
    label_names = categories + ["other"]

    # Per-voxel predicted label index
    pred = np.argmax(scores_mat, axis=1)  # (N,)

    # Build a full 2D label map over the grid
    label_2d = -1 * np.ones((vlmap.gs, vlmap.gs), dtype=np.int32)
    for idx, pos in enumerate(vlmap.grid_pos):
        row, col, _ = pos
        if 0 <= row < vlmap.gs and 0 <= col < vlmap.gs:
            label_2d[row, col] = pred[idx]

    # Crop to occupied area if obstacle cropping has been computed; otherwise use full map
    if hasattr(vlmap, "rmin") and hasattr(vlmap, "rmax") and hasattr(vlmap, "cmin") and hasattr(vlmap, "cmax"):
        rmin, rmax, cmin, cmax = vlmap.rmin, vlmap.rmax, vlmap.cmin, vlmap.cmax
    else:
        rmin, rmax, cmin, cmax = 0, vlmap.gs - 1, 0, vlmap.gs - 1
    labels_cropped = label_2d[rmin : rmax + 1, cmin : cmax + 1]
    return labels_cropped, label_names, pred


def show_category_map(labels_cropped: np.ndarray, label_names: List[str]) -> None:
    """Display a multi-category map with a legend."""
    no_map_mask = labels_cropped < 0
    try:
        floor_idx = label_names.index("floor")
    except ValueError:
        floor_idx = None
    floor_mask = labels_cropped == floor_idx if floor_idx is not None else np.zeros_like(labels_cropped, dtype=bool)

    num_labels = len(label_names)
    cmap = plt.get_cmap("tab20", num_labels)
    h, w = labels_cropped.shape
    seg_rgba = np.ones((h, w, 4), dtype=np.float32)
    seg_rgba[..., :3] = 225.0 / 255.0  # default light gray
    seg_rgba[..., 3] = 1.0

    for label_id in range(num_labels):
        mask = labels_cropped == label_id
        if not np.any(mask):
            continue
        color = np.array(cmap(label_id))  # RGBA in [0,1]
        seg_rgba[mask] = color

    # Gray out no-map and floor cells
    gray = np.array([225.0 / 255.0, 225.0 / 255.0, 225.0 / 255.0, 1.0], dtype=np.float32)
    seg_rgba[no_map_mask] = gray
    seg_rgba[floor_mask] = gray

    # Build legend patches (skip labels not present)
    unique_labels = np.unique(labels_cropped[~no_map_mask])
    patches: List[mpatches.Patch] = []
    for label_id in unique_labels:
        if label_id < 0 or label_id >= len(label_names):
            continue
        if floor_idx is not None and label_id == floor_idx:
            continue  # floor is shown as gray background
        color = cmap(int(label_id))
        patches.append(
            mpatches.Patch(
                facecolor=color[:3],
                edgecolor="black",
                label=label_names[int(label_id)],
            )
        )

    plt.figure(figsize=(10, 6), dpi=120)
    if patches:
        plt.legend(handles=patches, loc="upper left", bbox_to_anchor=(1.0, 1), prop={"size": 10})
    plt.axis("off")
    plt.title("VLMaps category map")
    plt.imshow(seg_rgba)
    plt.show()


def show_category_map_3d(pred: np.ndarray, label_names: List[str], vlmap: VLMap) -> None:
    """Display a 3D category map by coloring each voxel according to its label, plus a legend."""
    num_labels = len(label_names)
    cmap = plt.get_cmap("tab20", num_labels)

    # Build per-voxel RGB colors from predicted labels
    colors = np.zeros_like(vlmap.grid_rgb, dtype=np.float32)
    gray = np.array([225.0, 225.0, 225.0], dtype=np.float32)

    for idx, label_id in enumerate(pred):
        if label_id < 0 or label_id >= num_labels:
            colors[idx] = gray
            continue
        color_rgba = np.array(cmap(int(label_id)))  # RGBA in [0,1]
        colors[idx] = color_rgba[:3] * 255.0

    visualize_rgb_map_3d_async(vlmap.grid_pos, colors)

    # Show a legend for the colormap used in 3D visualization.
    # Only include labels that actually appear in the predictions.
    present_ids = np.unique(pred[pred >= 0])
    patches: List[mpatches.Patch] = []
    for label_id in present_ids:
        if label_id < 0 or label_id >= len(label_names):
            continue
        name = label_names[int(label_id)]
        color = cmap(int(label_id))
        patches.append(
            mpatches.Patch(
                facecolor=color[:3],
                edgecolor="black",
                label=name,
            )
        )

    # Use a small figure so the legend doesn't dominate the screen
    plt.figure(figsize=(3, 10), dpi=120)
    plt.axis("off")
    if patches:
        plt.legend(handles=patches, loc="center", prop={"size": 10})
    plt.show()


@hydra.main(
    version_base=None,
    config_path="../config",
    config_name="inspect_map_cfg.yaml",
)
def main(config: DictConfig) -> None:
    """Inspect a VLMap in 2D or 3D mode."""
    vlmap = load_scene_vlmap(config)
    # Determine mode: explicit config.mode overrides legacy vis_3d flag
    mode = getattr(config, "mode", None)
    if mode is None:
        mode = "3d" if getattr(config, "vis_3d", False) else "2d"

    if mode == "2d":
        show_obstacle_map(vlmap, config.obs.height.min, config.obs.height.max)
        labels_cropped, label_names, _ = compute_category_map(vlmap)
        show_category_map(labels_cropped, label_names)
    elif mode == "3d":
        show_obstacle_map_3d(vlmap, config.obs.height.min, config.obs.height.max)
        _, label_names, pred = compute_category_map(vlmap)
        show_category_map_3d(pred, label_names, vlmap)
    else:
        logger.error("Unknown inspect_map mode='%s'. Use '2d' or '3d'.", mode)


if __name__ == "__main__":
    setup_logging()
    main()


