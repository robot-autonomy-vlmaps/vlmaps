from pathlib import Path
from typing import Callable, List, Optional

import hydra
from omegaconf import DictConfig
import typer

from application.create_map import main as create_map_main
from application.dataset.collect_custom_dataset import main as collect_dataset_main
from application.dataset.generate_dataset import main as generate_dataset_main
from application.evaluation.compute_object_goal_navigation_metrics import main as compute_object_goal_nav_main
from application.evaluation.compute_spatial_goal_navigation_metrics import main as compute_spatial_goal_nav_main
from application.evaluation.evaluate_object_goal_navigation import main as eval_object_goal_nav_main
from application.evaluation.evaluate_spatial_goal_navigation import main as eval_spatial_goal_nav_main
from application.index_map import main as index_map_main
from vlmaps.utils.logging_utils import setup_logging


CONFIG_DIR = Path(__file__).resolve().parent.parent / "config"


def _compose_and_call(entrypoint: Callable, config_name: str, overrides: Optional[List[str]]) -> None:
    """
    Compose Hydra config from the repo config directory and call the wrapped function.
    Bypasses Hydra's decorator to avoid config_path resolution issues when installed as a package.
    """
    ov = list(overrides) if overrides else []
    with hydra.initialize_config_dir(config_dir=str(CONFIG_DIR), version_base=None):
        cfg: DictConfig = hydra.compose(config_name=config_name, overrides=ov)
    # hydra.main uses functools.wraps, so __wrapped__ points to the original function
    entrypoint.__wrapped__(cfg)  # type: ignore[attr-defined]


app = typer.Typer(help="VLMAPS command-line interface")
dataset_app = typer.Typer(help="Dataset workflows")
map_app = typer.Typer(help="Map workflows")
eval_app = typer.Typer(help="Evaluation workflows")

# Configure logging once for all CLI commands
setup_logging()


@dataset_app.command("collect", help="Collect dataset")
def dataset_collect(overrides: Optional[List[str]] = typer.Argument(None, help="Hydra overrides, e.g., scene_id=0")) -> None:
    _compose_and_call(collect_dataset_main, "collect_dataset.yaml", overrides)


@dataset_app.command("generate", help="Generate dataset from predefined sequences")
def dataset_generate(overrides: Optional[List[str]] = typer.Argument(None, help="Hydra overrides, e.g., scene_id=0")) -> None:
    _compose_and_call(generate_dataset_main, "generate_dataset.yaml", overrides)


@map_app.command("create", help="Create a map")
def map_create(overrides: Optional[List[str]] = typer.Argument(None, help="Hydra overrides, e.g., scene_id=0")) -> None:
    _compose_and_call(create_map_main, "map_creation_cfg.yaml", overrides)


@map_app.command("index", help="Index a map")
def map_index(overrides: Optional[List[str]] = typer.Argument(None, help="Hydra overrides, e.g., scene_id=0")) -> None:
    _compose_and_call(index_map_main, "map_indexing_cfg.yaml", overrides)


@eval_app.command("object", help="Run object-goal navigation evaluation")
def eval_object(overrides: Optional[List[str]] = typer.Argument(None, help="Hydra overrides, e.g., scene_id=0")) -> None:
    _compose_and_call(eval_object_goal_nav_main, "object_goal_navigation_cfg", overrides)


@eval_app.command("object-compute", help="Compute metrics for object-goal navigation")
def eval_object_compute(overrides: Optional[List[str]] = typer.Argument(None, help="Hydra overrides, e.g., scene_id=0")) -> None:
    _compose_and_call(compute_object_goal_nav_main, "object_goal_navigation_cfg", overrides)


@eval_app.command("spatial", help="Run spatial-goal navigation evaluation")
def eval_spatial(overrides: Optional[List[str]] = typer.Argument(None, help="Hydra overrides, e.g., scene_id=0")) -> None:
    _compose_and_call(eval_spatial_goal_nav_main, "spatial_goal_navigation_cfg", overrides)


@eval_app.command("spatial-compute", help="Compute metrics for spatial-goal navigation")
def eval_spatial_compute(overrides: Optional[List[str]] = typer.Argument(None, help="Hydra overrides, e.g., scene_id=0")) -> None:
    _compose_and_call(compute_spatial_goal_nav_main, "spatial_goal_navigation_cfg", overrides)


app.add_typer(dataset_app, name="dataset")
app.add_typer(map_app, name="map")
app.add_typer(eval_app, name="eval")


if __name__ == "__main__":
    app()

