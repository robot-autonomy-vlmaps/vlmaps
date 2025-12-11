# 4. Index a VLMap

This guide will help you create and index a Visual Language Map (VLMap) from the generated dataset.

## Prerequisites

- Completed [Generate Dataset](03-generate-dataset.md)
- Generated dataset with RGB, depth, and poses
- Container running with conda environment activated

## Overview

This process has two steps:
1. **Create the VLMap** - Build a 3D map with LSeg embeddings
2. **Index the VLMap** - Query the map with natural language

## Step 1: Create a VLMap

### Configure Map Creation

Edit the map creation config:

```bash
nano config/map_creation_cfg.yaml
```

Key settings:

```yaml
defaults:
  - data_paths: default
  - map_config: vlmaps
  - params: default

scene_id: 0  # Which scene to create map for (0 = first scene in sorted list)
```

### Configure Map Parameters

Edit map resolution and grid size:

```bash
nano config/params/default.yaml
```

Key parameters:
- `cs` - Cell size in meters (smaller = higher resolution)
- `gs` - Grid size (number of cells)

### Configure Camera and Pose Settings

Edit the VLMap configuration:

```bash
nano config/map_config/vlmaps.yaml
```

Important settings in `pose_info`:

```yaml
pose_info:
  pose_type: "camera_base"  # or "mobile_base"
  rot_type: "quat"          # or "mat"
  camera_height: 1.5        # Height relative to base (if mobile_base)
```

**Pose Type Options:**
- `camera_base` - If `poses.txt` contains camera poses (recommended)
- `mobile_base` - If `poses.txt` contains robot base poses

**Rotation Type:**
- `quat` - Quaternion format: `px, py, pz, qx, qy, qz, qw`
- `mat` - 4x4 transformation matrix (flattened)

### Run Map Creation

```bash
cd application
python create_map.py
```

This will:
- Load the dataset for the specified scene
- Build a 3D voxel map
- Embed LSeg features into each voxel
- Save the map to the scene directory

### Expected Output

The map will be saved in the scene directory (under project root):
```
./data/mp3d/tasks/mp3d/5LpN3gDmAk7_1/
├── rgb/
├── depth/
├── semantic/
├── poses.txt
└── map.npz          # Created VLMap
```

## Step 2: Index the VLMap

### Configure Indexing

Edit the indexing config:

```bash
nano config/map_indexing_cfg.yaml
```

Key settings:

```yaml
defaults:
  - data_paths: default
  - map_config: vlmaps
  - params: default

scene_id: 0  # Same scene as map creation

# Indexing parameters
decay_rate: 0.01        # Heatmap decay rate (smaller = clearer transitions)
index_2d: False         # True for 2D visualization, False for 3D
init_categories: True   # Use Matterport3D categories (requires OpenAI API key)
```

### Set Up LLM API (if using init_categories)

If `init_categories: True`, you need an LLM API key. The provider matches `provider` in `config/llm.yaml` (default: `openai`). For OpenAI, set:

```bash
# Inside container
export VLMAPS_LLM_KEY_OPENAI=your_api_key_here

# Or add to ~/.bashrc for persistence
echo 'export VLMAPS_LLM_KEY_OPENAI=your_api_key_here' >> ~/.bashrc
```

**Getting an API Key:**
1. Sign up at [OpenAI](https://openai.com/blog/openai-api)
2. Get your API key from [API Keys page](https://platform.openai.com/account/api-keys)
3. Add payment method to your account

### Run Indexing

```bash
cd application
python index_map.py
```

### Interactive Querying

The script will:
1. Load the created VLMap
2. Display a 3D visualization of the map
3. Prompt you to enter a category/object name
4. Generate a heatmap showing where that object is located
5. Display the heatmap visualization

**Example queries:**
- "chair"
- "table"
- "sofa"
- "bed"
- "door"

## Visualization Options

### 2D vs 3D Visualization

In `config/map_indexing_cfg.yaml`:

```yaml
index_2d: True   # 2D top-down view
index_2d: False  # 3D perspective view
```

### Adjusting Heatmap Appearance

```yaml
decay_rate: 0.01  # Smaller = sharper, more localized heatmap
decay_rate: 0.1   # Larger = smoother, more spread out heatmap
```

## Advanced Configuration

### Custom Map Resolution

Edit `config/params/default.yaml`:

```yaml
cs: 0.05  # 5cm per voxel (higher resolution)
gs: 200   # Grid size
```

### Camera Calibration

Edit `config/map_config/vlmaps.yaml`:

```yaml
cam_calib_mat: [fx, 0, cx, 0, fy, cy, 0, 0, 1]  # Camera intrinsics (flattened)
```

### Frame Skipping

To speed up map creation:

```yaml
skip_frame: 5  # Use every 5th frame
```

### Depth Sampling

To balance speed vs. density:

```yaml
depth_sample_rate: 4  # Sample 1/4 of pixels (faster, sparser)
```

## Troubleshooting

### Map creation fails
- Verify dataset exists and has correct structure
- Check `scene_id` matches available scenes
- Ensure poses.txt format matches `rot_type` setting

### Indexing fails
- Ensure map was created successfully (check for `map.npz`)
- Verify `scene_id` matches the created map
- Check OpenAI API key if using `init_categories: True`

### Visualization doesn't appear
- Check X11 forwarding is set up (for GUI)
- Try setting `index_2d: True` for simpler visualization
- Verify display: `echo $DISPLAY`

### Out of memory
- Reduce grid size (`gs`) in params
- Increase cell size (`cs`) to reduce voxel count
- Use `skip_frame` to process fewer frames

## Verification

Check that the map was created:

```bash
# List scene directory (run from project root)
ls -lh ./data/mp3d/tasks/mp3d/5LpN3gDmAk7_1/

# Should see map.npz file
```

## Next Steps

Once you've created and indexed a VLMap:
- **[05 - Test Navigation](05-test-navigation.md)**

