# VLMAPS CLI (Typer + Hydra)

This repo now ships a Typer-powered CLI that wraps the existing Hydra entrypoints. Prefer the installed console script `vlmaps ...`; `python -m application ...` remains available.

## Install
- Python 3.8
- `pip install -r requirements.txt` (includes `typer>=0.7,<0.10` compatible with 3.8)
- Optional: `pip install -e .` to enable the `vlmaps` console script.

## Commands
- `vlmaps dataset generate [OVERRIDES...]`
- `vlmaps dataset collect [OVERRIDES...]`
- `vlmaps map create [OVERRIDES...]`
- `vlmaps map index [OVERRIDES...]`
- `vlmaps eval object [OVERRIDES...]`
- `vlmaps eval object-compute [OVERRIDES...]`
- `vlmaps eval spatial [OVERRIDES...]`
- `vlmaps eval spatial-compute [OVERRIDES...]`
- (Alternatively) `python -m application ...` for the same subcommands.

Run `--help` after any command to see details, e.g. `vlmaps map --help`.

## Hydra overrides
All commands accept Hydra overrides as positional args (the same syntax used when calling the scripts directly). Examples:
- `vlmaps map create scene_id=0 data_paths.vlmaps_data_dir=/abs/path`
- `vlmaps dataset collect scene_names=[17DRP5sb8fy] data_paths.habitat_scene_dir=/abs/path`

Hydra still controls working directories and output logging; runs are stored under `outputs/` by default. Use `hydra.run.dir=.` if you want to keep outputs in-place.

