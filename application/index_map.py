from pathlib import Path
import logging
import hydra
from omegaconf import DictConfig
from vlmaps.map.vlmap import VLMap
from vlmaps.utils.matterport3d_categories import mp3dcat
from vlmaps.utils.visualize_utils import (
    pool_3d_label_to_2d,
    pool_3d_rgb_to_2d,
    visualize_rgb_map_3d,
    visualize_masked_map_2d,
    visualize_heatmap_2d,
    visualize_heatmap_3d,
    visualize_masked_map_3d,
    get_heatmap_from_mask_2d,
    get_heatmap_from_mask_3d,
)

logger = logging.getLogger(__name__)


@hydra.main(
    version_base=None,
    config_path="../config",
    config_name="map_indexing_cfg.yaml",
)
def main(config: DictConfig) -> None:
    data_dir = Path(config.data_paths.vlmaps_data_dir)
    data_dirs = sorted([x for x in data_dir.iterdir() if x.is_dir()])
    logger.info("Indexing scene_id=%s from %s", config.scene_id, data_dir)
    logger.debug("Available scenes: %s", data_dirs)
    vlmap = VLMap(config.map_config, data_dir=data_dirs[config.scene_id])
    vlmap.load_map(data_dirs[config.scene_id])
    output_dir = Path(config.viz.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)
    logger.info("Saving outputs to %s", output_dir)
    visualize_rgb_map_3d(vlmap.grid_pos, vlmap.grid_rgb, gui=config.viz.gui, output_path=output_dir / "rgb_map.png")
    cat = input("What is your interested category in this scene?")
    # cat = "chair"

    vlmap._init_clip()
    logger.info("Considering categories (MP3D subset): %s", mp3dcat[1:-1])
    if config.init_categories:
        vlmap.init_categories(mp3dcat[1:-1])
        mask = vlmap.index_map(cat, with_init_cat=True)
    else:
        mask = vlmap.index_map(cat, with_init_cat=False)

    cat_slug = cat.replace(" ", "_")

    if config.index_2d:
        logger.info("Using 2D indexing visualization")
        mask_2d = pool_3d_label_to_2d(mask, vlmap.grid_pos, config.params.gs)
        rgb_2d = pool_3d_rgb_to_2d(vlmap.grid_rgb, vlmap.grid_pos, config.params.gs)
        visualize_masked_map_2d(rgb_2d, mask_2d, gui=config.viz.gui, output_path=output_dir / f"mask_2d_{cat_slug}.png")
        heatmap = get_heatmap_from_mask_2d(mask_2d, cell_size=config.params.cs, decay_rate=config.decay_rate)
        visualize_heatmap_2d(rgb_2d, heatmap, gui=config.viz.gui, output_path=output_dir / f"heatmap_2d_{cat_slug}.png")
    else:
        logger.info("Using 3D indexing visualization")
        visualize_masked_map_3d(
            vlmap.grid_pos, mask, vlmap.grid_rgb, gui=config.viz.gui, output_path=output_dir / f"mask_3d_{cat_slug}.png"
        )
        heatmap = get_heatmap_from_mask_3d(
            vlmap.grid_pos, mask, cell_size=config.params.cs, decay_rate=config.decay_rate
        )
        visualize_heatmap_3d(
            vlmap.grid_pos,
            heatmap,
            vlmap.grid_rgb,
            gui=config.viz.gui,
            output_path=output_dir / f"heatmap_3d_{cat_slug}.png",
        )


if __name__ == "__main__":
    main()
