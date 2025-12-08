# 2. Download MP3D Dataset

This guide will help you download the Matterport3D dataset required for VLMaps.

## Prerequisites

- Completed [Setup](01-setup.md)
- Matterport3D dataset access (requires signing Terms of Use)
- `download_mp.py` script from Matterport3D

## Step 1: Obtain download_mp.py

1. Visit the [Matterport3D Dataset Download page](https://niessner.github.io/Matterport/)
2. Sign the [Terms of Use](http://kaldir.vc.in.tum.de/matterport/MP_TOS.pdf)
3. Request access from the responsible person
4. You will receive an email with a Python script
5. Copy the script content and save it as `download_mp.py` in the project root

```bash
# From the host (outside container)
# Copy the script to the project root
cp /path/to/downloaded/script.py download_mp.py
```

## Step 2: Start the Container

```bash
./scripts/start.bash
```

## Step 3: Run the Download Script

Inside the container, run the download script:

```bash
./scripts/download-mp3d.bash
```

Or with a specific scene ID:

```bash
./scripts/download-mp3d.bash 17DRP5sb8fy
```

### What the Script Does

1. **Checks for download_mp.py** - Verifies the script exists
2. **Creates data directory** - Ensures `data/` is available
3. **Downloads habitat bundle** - Fetches `mp3d_habitat.zip` (~15GB) into `data/`
4. **Extracts data** - Unzips into `data/mp3d/` with `scans/` and `tasks/`

## Step 4: Update Configuration

If you need to point configs to the downloaded data (from the project root), set paths like:
```yaml
habitat_scene_dir: "data/mp3d/scans"
vlmaps_data_dir: "data/mp3d/tasks/mp3d"
```

## Data Structure

After download, your data directory (under the project root) will have this structure:

```
./data/mp3d/
├── scans/
│   └── 17DRP5sb8fy/          # Scene directory
│       ├── 17DRP5sb8fy.glb
│       ├── 17DRP5sb8fy_semantic.ply
│       └── ...
└── tasks/
    └── mp3d/                  # After unzipping
        ├── 5LpN3gDmAk7_1/
        │   └── poses.txt
        ├── gTV8FGcVJC9_1/
        │   └── poses.txt
        └── ...
```

## Troubleshooting

### download_mp.py not found
- Ensure the script is in the project root (visible at `/vlmaps/download_mp.py` in container)
- Check file permissions: `chmod +x download_mp.py` (if needed)

### Download fails
- Check internet connection
- Verify Matterport3D credentials are correct in `download_mp.py`
- Ensure sufficient disk space (~50GB needed)

### Config update fails
- Check file permissions in `config/data_paths/`
- Manually edit `config/data_paths/default.yaml` if needed

## Manual Config Update

If you need to manually update the config:

```bash
# Edit the config file
nano /vlmaps/config/data_paths/default.yaml
```

Set (relative to the project root):
```yaml
habitat_scene_dir: "data/mp3d/scans"
vlmaps_data_dir: "data/mp3d/tasks/mp3d"
```

## Next Steps

Once the dataset is downloaded and config is updated:
- **[03 - Generate Dataset](03-generate-dataset.md)**

