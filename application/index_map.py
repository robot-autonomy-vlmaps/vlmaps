import logging
from pathlib import Path

import cv2
import hydra
from omegaconf import DictConfig
from vlmaps.map.vlmap import VLMap
from vlmaps.utils.logging_utils import setup_logging
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
    logger.info("Indexing scene at %s", data_dirs[config.scene_id])
    vlmap = VLMap(config.map_config, data_dir=data_dirs[config.scene_id])
    vlmap.load_map(data_dirs[config.scene_id])
    visualize_rgb_map_3d(vlmap.grid_pos, vlmap.grid_rgb)
    
    # Initialize CLIP and categories once
    vlmap._init_clip()
    if config.init_categories:
        logger.info("Initializing categories: %s", mp3dcat[1:-1])
        vlmap.init_categories(mp3dcat[1:-1])
    
    # Interactive query loop
    logger.info("Enter queries to index the map. Press Ctrl+C to exit.")
    try:
        while True:
            cat = input("\nWhat is your interested category in this scene? (Ctrl+C to exit): ").strip()
            if not cat:
                logger.warning("Empty query, skipping...")
                continue
            
            logger.info("Indexing category: %s", cat)
            mask = vlmap.index_map(cat, with_init_cat=config.init_categories)

            if config.index_2d:
                cv2.destroyAllWindows()
                mask_2d = pool_3d_label_to_2d(mask, vlmap.grid_pos, config.params.gs)
                rgb_2d = pool_3d_rgb_to_2d(vlmap.grid_rgb, vlmap.grid_pos, config.params.gs)
                visualize_masked_map_2d(rgb_2d, mask_2d, waitkey=False)
                heatmap = get_heatmap_from_mask_2d(mask_2d, cell_size=config.params.cs, decay_rate=config.decay_rate)
                visualize_heatmap_2d(rgb_2d, heatmap, waitkey=True)
            else:
                visualize_masked_map_3d(vlmap.grid_pos, mask, vlmap.grid_rgb)
                heatmap = get_heatmap_from_mask_3d(
                    vlmap.grid_pos, mask, cell_size=config.params.cs, decay_rate=config.decay_rate
                )
                visualize_heatmap_3d(vlmap.grid_pos, heatmap, vlmap.grid_rgb)
    except (KeyboardInterrupt, EOFError):
        logger.info("\nExiting...")
    finally:
        cv2.destroyAllWindows()


if __name__ == "__main__":
    setup_logging()
    main()
