# 5. Test Navigation

This guide will help you test object goal navigation and spatial goal navigation using your created VLMap.

## Prerequisites

- Completed [Index a VLMap](04-index-vlmap.md)
- Created and indexed VLMap
- OpenAI API key set up (for navigation tasks)
- Navigation task files in scene directories

## Step 1: Set Up OpenAI API Key

Ensure your OpenAI API key is set:

```bash
# Check if set
echo $OPENAI_KEY

# If not set, set it
export OPENAI_KEY=your_api_key_here

# For persistence, add to ~/.bashrc
echo 'export OPENAI_KEY=your_api_key_here' >> ~/.bashrc
source ~/.bashrc
```

**Note:** You need an OpenAI account with a payment method. Get your key from [OpenAI API Keys](https://platform.openai.com/account/api-keys).

## Step 2: Object Goal Navigation

Object goal navigation involves navigating to a specific object (e.g., "go to the chair").

### Configure Object Goal Navigation

Edit the config:

```bash
nano config/object_goal_navigation_cfg.yaml
```

Key settings:

```yaml
defaults:
  - data_paths: default
  - map_config: vlmaps
  - params: default

nav:
  vis: True              # Enable visualization
  valid_range: 1         # Valid navigation range
  tasks_per_scene: 20    # Number of tasks per scene

scene_id: 0              # Scene to evaluate (or [0,1,2] for multiple)
```

### Run Object Goal Navigation

```bash
cd application/evaluation
python evaluate_object_goal_navigation.py
```

### What Happens

1. Loads tasks from `<scene_folder>/object_navigation_tasks.json`
2. For each task, uses VLMap to find the goal location
3. Plans and executes navigation path
4. Saves results to `<scene_folder>/vlmap_obj_nav_results/`

### Compute Metrics

After evaluation, compute final metrics:

```bash
cd application/evaluation
python compute_object_goal_navigation_metrics.py
```

This will output success rate, SPL (Success weighted by Path Length), and other navigation metrics.

## Step 3: Spatial Goal Navigation

Spatial goal navigation involves navigating to a location described relative to objects (e.g., "go to the area near the chair").

### Configure Spatial Goal Navigation

Edit the config:

```bash
nano config/spatial_goal_navigation_cfg.yaml
```

Key settings:

```yaml
defaults:
  - data_paths: default
  - map_config: vlmaps
  - params: default

nav:
  vis: True              # Enable visualization
  valid_range: 1         # Valid navigation range
  tasks_per_scene: 20    # Number of tasks per scene

scene_id: 0              # Scene to evaluate (or [0,1,2] for multiple)
```

### Run Spatial Goal Navigation

```bash
cd application/evaluation
python evaluate_spatial_goal_navigation.py
```

### What Happens

1. Loads tasks from `<scene_folder>/spatial_goal_navigation_tasks.json`
2. Uses VLMap to interpret spatial language queries
3. Plans and executes navigation path
4. Saves results to `<scene_folder>/vlmap_spatial_nav_results/`

### Compute Metrics

After evaluation, compute final metrics:

```bash
cd application/evaluation
python compute_spatial_goal_navigation_metrics.py
```

## Visualization

### Enable Visualization

Set `nav.vis: True` in the config files to see:
- **POV (Point of View)** - Robot's camera view
- **Top-down trajectory** - Bird's eye view of navigation path
- **Predicted goal** - Heatmap showing predicted goal location

### Viewing Results

Results are saved in JSON format in the scene directories:
- `vlmap_obj_nav_results/` - Object goal navigation results
- `vlmap_spatial_nav_results/` - Spatial goal navigation results

## Configuration Options

### Evaluate Multiple Scenes

```yaml
scene_id: [0, 1, 2, 3]  # Evaluate multiple scenes
```

### Adjust Task Count

```yaml
nav:
  tasks_per_scene: 50  # More tasks per scene
```

### Adjust Navigation Range

```yaml
nav:
  valid_range: 2.0  # Larger valid range
```

## Troubleshooting

### OpenAI API errors
- Verify API key is set: `echo $OPENAI_KEY`
- Check account has credits/payment method
- Verify internet connection

### Navigation tasks not found
- Ensure task JSON files exist in scene directories
- Check file names: `object_navigation_tasks.json` and `spatial_goal_navigation_tasks.json`
- Verify scene_id matches available scenes

### Navigation fails
- Ensure VLMap was created and indexed
- Check obstacle map exists (may need to generate)
- Verify map paths in config are correct

### Visualization doesn't work
- Check X11 forwarding: `echo $DISPLAY`
- Try setting `vis: False` to disable visualization
- Verify GUI libraries are installed

### Out of memory
- Reduce number of tasks: `tasks_per_scene: 10`
- Evaluate scenes one at a time
- Close other applications

## Understanding Results

### Success Metrics
- **Success Rate** - Percentage of tasks completed successfully
- **SPL (Success weighted by Path Length)** - Considers path efficiency
- **Distance to Goal** - Average distance from goal when task fails

### Result Files
Results include:
- Task ID
- Success/failure status
- Path taken
- Goal location
- Execution time

## Advanced Usage

### Custom Navigation Tasks

You can create custom task files following the format in the existing JSON files:

```json
{
  "tasks": [
    {
      "task_id": 0,
      "instruction": "go to the chair",
      "goal_position": [x, y, z]
    }
  ]
}
```

### Testing on Custom Scenes

1. Ensure your custom scene has a created VLMap
2. Update `scene_id` in config to match your scene index
3. Create task files in your scene directory
4. Run evaluation as normal

## Next Steps

Congratulations! You've completed the full VLMaps workflow:

1. ✅ Set up development environment
2. ✅ Downloaded MP3D dataset
3. ✅ Generated RGB-D dataset
4. ✅ Created and indexed a VLMap
5. ✅ Tested navigation tasks

### Further Exploration

- Experiment with different map resolutions
- Try different scene configurations
- Collect and use your own custom datasets
- Develop custom navigation applications
- Explore the codebase for advanced features

## Additional Resources

- Original [README.md](../README.md) for detailed technical information
- [VLMaps Project Page](https://vlmaps.github.io/)
- [Paper](https://arxiv.org/pdf/2210.05714.pdf)

---

**Happy Mapping! 🗺️**

