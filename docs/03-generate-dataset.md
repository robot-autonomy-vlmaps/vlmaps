# 3. Generate Dataset

This guide will help you generate RGB-D videos from the Matterport3D dataset using Habitat-Sim.

## Prerequisites

- Completed [Download MP3D Dataset](02-download-mp3d.md)
- Config file updated with correct paths
- Container running with conda environment activated

## Step 1: Verify Configuration

Check that `config/data_paths/default.yaml` has the correct paths:

```bash
cat config/data_paths/default.yaml
```

Should show:
```yaml
habitat_scene_dir: "data/mp3d/scans"
vlmaps_data_dir: "data/mp3d/tasks/mp3d"
```

## Step 2: Configure Dataset Generation

Edit the dataset generation config:

```bash
nano config/generate_dataset.yaml
```

### Key Configuration Options

1. **Scene Names** - Specify which scenes to generate:
   ```yaml
   scene_names:
     - 5LpN3gDmAk7_1
     - gTV8FGcVJC9_1
     - jh4fc5c5qoQ_1
     # ... add more as needed
   ```

2. **Data Configuration**:
   ```yaml
   data_cfg:
     rgb: true          # Generate RGB images
     depth: true        # Generate depth images
     semantic: true     # Generate semantic images
     resolution:
       w: 1080          # Image width
       h: 720           # Image height
     camera_height: 1.5 # Camera height in meters
   ```

3. **Data Paths** - Should already be set to `default`:
   ```yaml
   defaults:
     - data_paths: default
   ```

## Step 3: Generate the Dataset

Run the dataset generation script:

```bash
cd application/dataset
python generate_dataset.py
```

### What Happens

1. **Downloads pose metadata** - Downloads the VLMaps dataset with pose information
2. **Generates RGB-D videos** - For each scene, generates:
   - RGB images (`rgb/000000.png`, `rgb/000001.png`, ...)
   - Depth images (`depth/000000.npy`, `depth/000001.npy`, ...)
   - Semantic images (`semantic/000000.png`, `semantic/000001.png`, ...)
3. **Saves to data directory** - Data is saved in `vlmaps_data_dir` specified in config

### Expected Output Structure

After generation, your data directory (under the project root) will look like:

```
./data/mp3d/tasks/mp3d/
├── 5LpN3gDmAk7_1/
│   ├── rgb/
│   │   ├── 000000.png
│   │   ├── 000001.png
│   │   └── ...
│   ├── depth/
│   │   ├── 000000.npy
│   │   ├── 000001.npy
│   │   └── ...
│   ├── semantic/
│   │   ├── 000000.png
│   │   ├── 000001.png
│   │   └── ...
│   └── poses.txt
├── gTV8FGcVJC9_1/
│   └── ...
└── ...
```

## Step 4: Monitor Progress

The script will show a progress bar for each scene:

```
Scene 5LpN3gDmAk7_1  : 100%|████████████| 1000/1000 [05:23<00:00, 3.10it/s]
Scene gTV8FGcVJC9_1  : 100%|████████████| 1000/1000 [05:15<00:00, 3.17it/s]
...
```

## Customization Options

### Generate Only Specific Data Types

To save disk space or time, you can disable certain data types:

```yaml
data_cfg:
  rgb: true
  depth: false      # Skip depth generation
  semantic: false    # Skip semantic generation
```

### Adjust Resolution

Lower resolution = faster generation, less disk space:

```yaml
data_cfg:
  resolution:
    w: 640   # Lower width
    h: 480   # Lower height
```

### Adjust Camera Height

Change the camera height relative to robot base:

```yaml
data_cfg:
  camera_height: 1.2  # Lower camera height
```

## Collecting Custom Data

If you want to collect your own data in Habitat-Sim:

```bash
python application/dataset/collect_custom_dataset.py scene_names=["gTV8FGcVJC9"]
```

This will create a new folder `<scene_name>_<id>` under `vlmaps_data_dir`. The `<id>` is automatically incremented if folders already exist.

## Troubleshooting

### Habitat-Sim errors
- Ensure habitat-sim is installed: `conda list | grep habitat-sim`
- Check GPU availability: `nvidia-smi` (if using GPU)
- Verify scene files exist in `habitat_scene_dir`

### Out of memory
- Reduce resolution in config
- Generate fewer scenes at a time
- Close other applications

### Slow generation
- Use GPU if available (should be automatic)
- Reduce image resolution
- Generate only required data types (disable unused ones)

### Missing scene files
- Verify `habitat_scene_dir` points to correct location
- Check that scene `.glb` files exist
- Ensure scene names in config match downloaded scenes

## Verification

After generation, verify the data:

```bash
# Check a scene directory (run from project root)
ls -la ./data/mp3d/tasks/mp3d/5LpN3gDmAk7_1/

# Should see:
# rgb/, depth/, semantic/, poses.txt

# Check number of frames
ls ./data/mp3d/tasks/mp3d/5LpN3gDmAk7_1/rgb/ | wc -l
```

## Next Steps

Once dataset generation is complete:
- **[04 - Index a VLMap](04-index-vlmap.md)**

