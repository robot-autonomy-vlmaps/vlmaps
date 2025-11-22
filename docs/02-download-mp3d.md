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

## Step 2: Run the Download Script

The download script can be run from the project root directory, either locally or inside a Docker container.

### Option A: Run Locally (from project root)

```bash
# From project root directory
./scripts/data/download-mp3d.bash
```

Or with a specific scene ID:

```bash
./scripts/data/download-mp3d.bash 17DRP5sb8fy
```

**Note**: Requires Python and `download_mp.py` to be available in your local environment.

### Option B: Run in Docker Container

If you prefer to run it inside the Docker container:

```bash
# Start the container
./scripts/docker/start.bash

# Inside the container, run:
./scripts/data/download-mp3d.bash
```

Or with a specific scene ID:

```bash
./scripts/data/download-mp3d.bash 17DRP5sb8fy
```

### What the Script Does

1. **Checks for download_mp.py** - Verifies the script exists
2. **Checks data directory** - Warns if data already exists
3. **Downloads scans** - Downloads scene data for the specified scene ID
4. **Downloads tasks** - Downloads habitat task data
5. **Organizes data** - Structures data into `scans/` and `tasks/` directories
6. **Updates config** - Prompts to update `config/data_paths/default.yaml`

### Script Options

When data already exists, you'll be prompted:
- **yes** - Overwrite existing data
- **skip** - Skip download and only update config
- **no** - Abort (still prompts for config update)

## Step 5: Update Configuration

The script will ask if you want to update the config file. If you choose **yes**, it will automatically update:

- `config/data_paths/default.yaml`

The config will be updated to:
```yaml
habitat_scene_dir: "data/mp3d/scans"
vlmaps_data_dir: "data/vlmaps"
```

A backup of the original config will be saved as `config/data_paths/default.yaml.bak`.

## Data Structure

After download, your data directory will have this structure:

```
data/
├── mp3d/
│   ├── scans/
│   │   └── 17DRP5sb8fy/          # Scene directory
│   │       ├── 17DRP5sb8fy.glb
│   │       ├── 17DRP5sb8fy_semantic.ply
│   │       └── ...
│   └── tasks/
│       └── mp3d/                  # After unzipping
│           ├── 5LpN3gDmAk7_1/
│           │   └── poses.txt
│           ├── gTV8FGcVJC9_1/
│           │   └── poses.txt
│           └── ...
└── vlmaps/                    # Will be populated by generate_dataset.py
```

## Troubleshooting

### download_mp.py not found
- Ensure the script is in the project root (visible at `/vlmaps/download_mp.py` in container)
- Check file permissions: `chmod +x download_mp.py` (if needed)

### Data directory issues
- The `data/` directory is created automatically in the project root
- Ensure you have sufficient disk space (~50GB needed)
- Check file permissions if download fails

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

Set:
```yaml
habitat_scene_dir: "data/mp3d/scans"
vlmaps_data_dir: "data/vlmaps"
```

## Next Steps

Once the dataset is downloaded and config is updated:
- **[03 - Generate Dataset](03-generate-dataset.md)**

