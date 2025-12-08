# VLMAPS Architecture Documentation

This document provides a comprehensive guide to understanding how VLMAPS works, with a focus on LSEG and LLM integration, to help new team members get oriented quickly.

## Table of Contents

1. [Project Overview](#project-overview)
2. [System Architecture](#system-architecture)
3. [LSEG Integration](#lseg-integration)
4. [LLM Integration](#llm-integration)
5. [Map Creation Pipeline](#map-creation-pipeline)
6. [Map Indexing System](#map-indexing-system)
7. [Navigation System](#navigation-system)
8. [Key Components](#key-components)
9. [Configuration System](#configuration-system)
10. [Extension Points](#extension-points)

---

## Project Overview

VLMAPS (Visual Language Maps) is a spatial map representation system that fuses pretrained visual-language model features into a 3D reconstruction of the physical world. This enables natural language indexing in the map for zero-shot spatial goal navigation.

**Key Capabilities:**
- Create 3D maps with visual-language embeddings stored per voxel
- Index maps using natural language queries
- Navigate to objects and spatial locations using language instructions
- Support for both simulated (Habitat) and real-world environments

**Main Workflow:**
1. **Data Collection**: Collect RGB-D images with poses
2. **Map Creation**: Build 3D map with LSEG embeddings
3. **Map Indexing**: Query maps using natural language
4. **Navigation**: Execute navigation tasks using language instructions

---

## System Architecture

### High-Level Architecture

```
┌─────────────────┐
│  Data Collection│  (RGB-D + Poses)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Map Creation   │  ──► LSEG Model ──► 3D Voxel Map
│  (VLMapBuilder) │      (Embeddings)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Map Indexing   │  ──► CLIP + LLM ──► Object Locations
│  (VLMap.index)  │      (Query Matching)
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  Navigation     │  ──► LLM Parser ──► Robot Actions
│  (LangRobot)    │      (Path Planning)
└─────────────────┘
```

### Core Components

- **Map Creation**: [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) - Builds 3D maps with LSEG features
- **Map Storage**: [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) - Manages map data and indexing
- **LSEG Utils**: [`vlmaps/utils/lseg_utils.py`](../vlmaps/utils/lseg_utils.py) - LSEG feature extraction
- **LLM Client**: [`vlmaps/utils/llm_client.py`](../vlmaps/utils/llm_client.py) - LLM API abstraction
- **LLM Utils**: [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py) - Language instruction parsing
- **Navigation**: [`vlmaps/navigator/navigator.py`](../vlmaps/navigator/navigator.py) - Path planning
- **Robot Control**: [`vlmaps/robot/lang_robot.py`](../vlmaps/robot/lang_robot.py) - Robot primitives

---

## LSEG Integration

### What is LSEG?

LSEG (Language-driven Segmentation) is a vision-language model that produces dense feature embeddings for images. Each pixel/voxel gets a feature vector that can be matched against text queries using CLIP.

### How LSEG is Used in VLMAPS

#### 1. Model Initialization

**Location**: [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) - `_init_lseg()` method (lines 229-267)

The LSEG model is initialized when creating a map:

```python
def _init_lseg(self):
    # Creates LSegEncNet model
    lseg_model = LSegEncNet("", arch_option=0, block_depth=0, activation="lrelu", crop_size=480)
    # Loads pretrained checkpoint
    checkpoint_path = checkpoint_dir / "demo_e200.ckpt"
    # Downloads if not present
    # Returns model, transform, and normalization parameters
```

**Key Parameters:**
- `crop_size=480`: Input image crop size
- `base_size=520`: Base image size for resizing
- Normalization: `mean=[0.5, 0.5, 0.5]`, `std=[0.5, 0.5, 0.5]`

**Checkpoint**: Automatically downloaded from Google Drive if missing

#### 2. Feature Extraction

**Location**: [`vlmaps/utils/lseg_utils.py`](../vlmaps/utils/lseg_utils.py) - `get_lseg_feat()` function (lines 15-114)

This function processes images through LSEG to extract dense features:

```python
def get_lseg_feat(
    model: LSegEncNet,
    image: np.array,
    labels,  # Text labels for segmentation
    transform,
    device,
    crop_size=480,
    base_size=520,
    ...
):
    # Handles large images with sliding window approach
    # Returns: (B, D, H, W) feature tensor
```

**Key Features:**
- Handles images larger than crop_size using sliding window
- Supports multiple text labels for segmentation
- Returns dense feature maps (not just segmentation masks)

#### 3. Map Building Integration

**Location**: [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) - `create_mobile_base_map()` method

During map creation:
1. For each RGB frame:
   - Extract LSEG features using `get_lseg_feat()`
   - Back-project depth to 3D points
   - Associate LSEG features with 3D voxels
   - Accumulate features in voxel grid

**Code Flow:**
```python
# Initialize LSEG (line 82)
lseg_model, lseg_transform, ... = self._init_lseg()

# For each frame (in processing loop):
# 1. Load RGB image
# 2. Extract features
lseg_feat = get_lseg_feat(lseg_model, image, labels, ...)
# 3. Back-project to 3D
points_3d = self._backproject_depth(depth, calib_mat, ...)
# 4. Voxelize and store features
```

#### 4. LSEG Model Architecture

**Location**: [`vlmaps/lseg/modules/models/lseg_net.py`](../vlmaps/lseg/modules/models/lseg_net.py)

The LSEG model consists of:
- **Encoder**: Vision Transformer (ViT) or ResNet backbone
- **Decoder**: Segmentation head that produces dense features
- **Text Encoder**: CLIP text encoder for label embeddings

**Key Classes:**
- `LSegEncNet`: Encoder-only network (used in VLMAPS)
- `LSegNet`: Full segmentation network

### Modifying LSEG Integration

#### To Change LSEG Model:

1. **Modify Model Architecture**: Edit [`vlmaps/lseg/modules/models/lseg_net.py`](../vlmaps/lseg/modules/models/lseg_net.py)
2. **Update Initialization**: Modify `_init_lseg()` in [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py)
3. **Change Feature Extraction**: Update `get_lseg_feat()` in [`vlmaps/utils/lseg_utils.py`](../vlmaps/utils/lseg_utils.py)

#### To Use Different Checkpoint:

Change checkpoint path in `_init_lseg()`:
```python
checkpoint_path = checkpoint_dir / "your_checkpoint.ckpt"
```

#### To Adjust Processing Parameters:

Modify in `_init_lseg()`:
- `crop_size`: Affects memory usage and processing speed
- `base_size`: Affects image resizing
- Normalization parameters: Must match training

### LSEG Feature Dimensions

- Default output dimension: 512 (CLIP ViT-B/32 compatible)
- Stored per voxel in 3D map
- Used for text-image matching via CLIP

---

## LLM Integration

### What LLMs are Used For

1. **Instruction Parsing**: Convert natural language to robot commands
2. **Category Matching**: Map user queries to predefined categories
3. **Spatial Reasoning**: Parse complex spatial instructions

### LLM Client Architecture

#### 1. Client Initialization

**Location**: [`vlmaps/utils/llm_client.py`](../vlmaps/utils/llm_client.py)

The LLM client is a thin wrapper around OpenAI-compatible APIs:

```python
@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    """Returns configured OpenAI client with optional base-url override."""
    # Supports:
    # - OpenAI API (default)
    # - Local servers (Ollama, vLLM, etc.)
    # - Custom base URLs
```

**Environment Variables:**
- `VLMAPS_LLM_API_KEY` or `OPENAI_KEY`: API key
- `VLMAPS_LLM_BASE_URL` or `OPENAI_API_BASE`: Base URL (for local servers)
- `VLMAPS_LLM_CHAT_MODEL` or `OPENAI_CHAT_MODEL`: Model name
- `VLMAPS_LLM_COMPLETION_MODEL`: Legacy completion model

**Default Models:**
- Chat: `gpt-4-turbo`
- Completion: `gpt-3.5-turbo-instruct`

#### 2. Local LLM Support

**Docker Setup**: The project includes Ollama support via docker-compose:

```yaml
# docker-compose.yml
llm:
  image: ollama/ollama
  # Exposes OpenAI-compatible API at http://llm:11434/v1
```

**Usage**: Set environment variables:
```bash
export VLMAPS_LLM_BASE_URL=http://llm:11434/v1
export VLMAPS_LLM_CHAT_MODEL=mistral
```

#### 3. Instruction Parsing

**Location**: [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py)

##### Object Goal Navigation Parsing

**Function**: `parse_object_goal_instruction()` (lines 38-120)

Converts instructions like "go to kitchen then toilet" into landmark lists:

```python
def parse_object_goal_instruction(language_instr):
    # Uses few-shot prompting with examples
    response = client.chat.completions.create(
        model=get_chat_model_name(),
        messages=[...few-shot examples..., user_query]
    )
    # Returns: ["kitchen", "toilet"]
```

**Example Usage:**
- Input: "first go to the kitchen and then go to the toilet"
- Output: `["kitchen", "toilet"]`

**Few-Shot Examples**: Lines 44-114 contain example prompts

##### Spatial Goal Navigation Parsing

**Function**: `parse_spatial_instruction()` (lines 268-346)

Converts spatial instructions to robot API calls:

```python
def parse_spatial_instruction(language_instr):
    # Converts: "move to the right of the refrigerator"
    # To: "robot.move_to_right('refrigerator')"
```

**Supported Commands:**
- `robot.move_to_right('object')`
- `robot.move_in_between('obj1', 'obj2')`
- `robot.face('object')`
- `robot.turn(angle)`
- `robot.move_forward(meters)`
- And many more...

**Few-Shot Examples**: Lines 277-339 contain comprehensive examples

#### 4. Category Matching

**Location**: [`vlmaps/utils/index_utils.py`](../vlmaps/utils/index_utils.py) - `find_similar_category_id()` (lines 34-68)

Maps user queries to predefined categories using LLM:

```python
def find_similar_category_id(class_name, classes_list):
    # If exact match, return index
    # Otherwise, use LLM to find closest match
    response = client.chat.completions.create(
        model=get_chat_model_name(),
        messages=[...few-shot examples...]
    )
    # Returns index of matched category
```

**Use Case**: User queries "TV" but categories have "tv_monitor"

### Modifying LLM Integration

#### To Change LLM Provider:

1. **Update Client**: Modify `get_llm_client()` in [`vlmaps/utils/llm_client.py`](../vlmaps/utils/llm_client.py)
2. **Set Environment Variables**: Configure base URL and model name
3. **Test Compatibility**: Ensure API matches OpenAI format

#### To Modify Instruction Parsing:

1. **Update Prompts**: Edit few-shot examples in:
   - `parse_object_goal_instruction()` - [`vlmaps/utils/llm_utils.py:44-114`](../vlmaps/utils/llm_utils.py#L44-L114)
   - `parse_spatial_instruction()` - [`vlmaps/utils/llm_utils.py:277-339`](../vlmaps/utils/llm_utils.py#L277-L339)

2. **Add New Commands**: 
   - Add examples to few-shot prompt
   - Implement corresponding robot method in [`vlmaps/robot/lang_robot.py`](../vlmaps/robot/lang_robot.py)

#### To Use Different Model:

Set environment variable:
```bash
export VLMAPS_LLM_CHAT_MODEL=your-model-name
```

#### To Add New LLM Functionality:

1. Create new function in [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py)
2. Use `get_llm_client()` to get client
3. Use `get_chat_model_name()` for model name
4. Follow existing few-shot prompting pattern

### LLM Call Patterns

**All LLM calls follow this pattern:**
1. Get client: `client = get_llm_client()`
2. Get model: `model = get_chat_model_name()`
3. Build few-shot prompt with examples
4. Call API: `client.chat.completions.create(...)`
5. Parse response

**Error Handling**: Currently minimal - consider adding retry logic and error handling

---

## Map Creation Pipeline

### Overview

The map creation process converts RGB-D sequences into 3D voxel maps with LSEG embeddings.

### Entry Point

**Location**: [`application/create_map.py`](../application/create_map.py)

```python
@hydra.main(config_path="../config", config_name="map_creation_cfg.yaml")
def main(config: DictConfig):
    vlmap = VLMap(config.map_config)
    vlmap.create_map(data_dirs[config.scene_id])
```

### Step-by-Step Process

#### 1. Setup and Initialization

**Location**: [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) - `create_map()` (lines 44-70)

```python
def create_map(self, data_dir):
    self._setup_paths(data_dir)  # Sets up file paths
    # Choose builder based on pose type
    if pose_type == "mobile_base":
        self.map_builder = VLMapBuilder(...)
    elif pose_type == "camera_base":
        self.map_builder = VLMapBuilderCam(...)
```

#### 2. Map Builder Initialization

**Location**: [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) - `__init__()` (lines 36-53)

Sets up:
- Data paths (RGB, depth, poses)
- Camera calibration
- Base-to-camera transformation
- Map configuration

#### 3. LSEG Model Initialization

**Location**: [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) - `_init_lseg()` (lines 229-267)

- Loads LSEG model
- Downloads checkpoint if needed
- Sets up transforms and normalization

#### 4. Map Grid Initialization

**Location**: [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) - `_init_map()` (lines 198-227)

Creates 3D voxel grid:
- `grid_feat`: Stores LSEG features (N, D) where N=voxels, D=feature_dim
- `grid_pos`: Stores 3D positions (N, 3)
- `grid_rgb`: Stores RGB colors (N, 3)
- `weight`: Accumulation weights for averaging

#### 5. Frame Processing Loop

**Location**: [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) - `create_mobile_base_map()` (lines 100+)

For each frame:

```python
# 1. Load RGB and depth
rgb = cv2.imread(rgb_path)
depth = load_depth_npy(depth_path)

# 2. Extract LSEG features
lseg_feat = get_lseg_feat(lseg_model, rgb, labels, ...)
# Shape: (1, D, H, W)

# 3. Back-project depth to 3D points
points_3d = self._backproject_depth(depth, calib_mat, ...)
# Shape: (N_points, 3)

# 4. Transform to map frame
points_map = transform_pc(points_3d, cam_tf)

# 5. Voxelize and accumulate features
for each point:
    grid_id = base_pos2grid_id_3d(point, ...)
    grid_feat[grid_id] += lseg_feat[point_2d]
    weight[grid_id] += 1
```

#### 6. Map Saving

**Location**: [`vlmaps/utils/mapping_utils.py`](../vlmaps/utils/mapping_utils.py) - `save_3d_map()`

Saves to HDF5 file:
- `grid_feat`: Normalized features (averaged by weight)
- `grid_pos`: 3D positions
- `grid_rgb`: RGB colors
- `occupied_ids`: Which voxels are occupied
- `mapped_iter_list`: Frame indices used

**Output**: `{data_dir}/vlmap/vlmaps.h5df`

### Configuration

**Location**: [`config/map_creation_cfg.yaml`](../config/map_creation_cfg.yaml)

Key parameters:
- `scene_id`: Which scene to process
- `map_config`: Map configuration (see [`config/map_config/vlmaps.yaml`](../config/map_config/vlmaps.yaml))
  - `cell_size`: Voxel size in meters
  - `grid_size`: Grid dimensions
  - `depth_sample_rate`: Sampling rate for depth points
  - `cam_calib_mat`: Camera intrinsics
  - `pose_info`: Pose configuration

### Customization Points

1. **Change Voxel Size**: Modify `cell_size` in config
2. **Change Feature Extraction**: Modify `get_lseg_feat()` call
3. **Add Preprocessing**: Add steps before LSEG extraction
4. **Change Accumulation**: Modify feature averaging logic

---

## Map Indexing System

### Overview

Map indexing allows querying the 3D map using natural language to find object locations.

### Entry Point

**Location**: [`application/index_map.py`](../application/index_map.py)

```python
vlmap = VLMap(config.map_config, data_dir=...)
vlmap.load_map(data_dir)
vlmap._init_clip()  # Initialize CLIP for text matching
mask = vlmap.index_map(category, with_init_cat=True)
```

### Step-by-Step Process

#### 1. Load Map

**Location**: [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) - `load_map()` (lines 72-107)

Loads pre-built map from HDF5 file:
- `grid_feat`: LSEG features per voxel
- `grid_pos`: 3D positions
- `grid_rgb`: RGB colors

#### 2. Initialize CLIP

**Location**: [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) - `_init_clip()` (lines 109-132)

```python
def _init_clip(self, clip_version="ViT-B/32"):
    self.clip_model, self.preprocess = clip.load(clip_version)
    # CLIP is used to match text queries to LSEG features
```

**Why CLIP?**: LSEG features are CLIP-compatible, so we use CLIP's text encoder to match queries.

#### 3. Initialize Categories (Optional)

**Location**: [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) - `init_categories()` (lines 134-144)

Pre-computes scores for a set of categories:

```python
def init_categories(self, categories: List[str]):
    # Compute CLIP text features for all categories
    # Match against all voxel features
    # Store scores: (N_voxels, N_categories)
    self.scores_mat = get_lseg_score(...)
```

**Use Case**: When you know the set of objects you'll query (e.g., Matterport3D categories)

#### 4. Index Map

**Location**: [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) - `index_map()` (lines 146-167)

```python
def index_map(self, language_desc: str, with_init_cat: bool = True):
    if with_init_cat:
        # Use pre-computed scores
        cat_id = find_similar_category_id(language_desc, self.categories)
        # Uses LLM to map "TV" -> "tv_monitor"
        mask = self.scores_mat[:, cat_id] > threshold
    else:
        # Compute on-the-fly
        scores = get_lseg_score(self.clip_model, [language_desc], ...)
        mask = scores > threshold
    return mask  # Boolean mask of matching voxels
```

#### 5. Score Computation

**Location**: [`vlmaps/utils/index_utils.py`](../vlmaps/utils/index_utils.py) - `get_lseg_score()` (lines 100-144)

```python
def get_lseg_score(clip_model, landmarks, lseg_map, clip_feat_dim, ...):
    # 1. Get text features using CLIP
    text_feats = get_text_feats_multiple_templates(landmarks, ...)
    # 2. Match against voxel features
    scores = map_feats @ text_feats.T
    return scores  # (N_voxels, N_landmarks)
```

**Multiple Templates**: Uses multiple text templates (e.g., "a photo of {}", "there is {}") for robustness.

**Location**: [`vlmaps/utils/clip_utils.py`](../vlmaps/utils/clip_utils.py) - `multiple_templates` (lines 10-74)

#### 6. Category Matching (LLM)

**Location**: [`vlmaps/utils/index_utils.py`](../vlmaps/utils/index_utils.py) - `find_similar_category_id()` (lines 34-68)

When user queries don't match category names exactly:

```python
def find_similar_category_id(class_name, classes_list):
    # Uses LLM to find closest match
    # Example: "TV" -> "tv_monitor"
    response = client.chat.completions.create(...)
    return classes_list.index(matched_name)
```

### Visualization

**Location**: [`application/index_map.py`](../application/index_map.py) (lines 43-54)

After indexing, visualize:
- 2D/3D masked maps
- Heatmaps with decay
- RGB overlay

### Configuration

**Location**: [`config/map_indexing_cfg.yaml`](../config/map_indexing_cfg.yaml)

- `init_categories`: Whether to use predefined categories
- `index_2d`: Visualize 2D or 3D
- `decay_rate`: Heatmap decay parameter

---

## Navigation System

### Overview

The navigation system executes language instructions by:
1. Parsing instructions with LLM
2. Finding object locations via map indexing
3. Planning paths
4. Executing robot actions

### Architecture

```
Language Instruction
        │
        ▼
┌───────────────┐
│  LLM Parser   │  ──► Robot API Calls
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  LangRobot    │  ──► Map Queries ──► Object Positions
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Navigator    │  ──► Path Planning
└───────┬───────┘
        │
        ▼
┌───────────────┐
│  Controller   │  ──► Robot Actions
└───────────────┘
```

### Components

#### 1. Language Robot

**Location**: [`vlmaps/robot/lang_robot.py`](../vlmaps/robot/lang_robot.py)

Base class providing robot primitives:

```python
class LangRobot:
    def move_to(self, pos)          # Move to 2D position
    def turn(self, angle_deg)       # Rotate
    def face(self, name)            # Face object
    def move_to_object(self, name)  # Navigate to object
    def move_to_right(self, name)   # Move relative to object
    # ... many more primitives
```

**Habitat Implementation**: [`vlmaps/robot/habitat_lang_robot.py`](../vlmaps/robot/habitat_lang_robot.py)

#### 2. Navigator

**Location**: [`vlmaps/navigator/navigator.py`](../vlmaps/navigator/navigator.py)

Path planning using visibility graphs:

```python
class Navigator:
    def build_visgraph(self, obstacle_map)  # Build visibility graph
    def plan_to(self, start, goal)         # Plan path
```

**Algorithm**: Uses `pyvisgraph` for visibility graph path planning

#### 3. Controller

**Location**: [`vlmaps/controller/controller.py`](../vlmaps/controller/controller.py)

Converts paths to robot actions:
- Discrete actions: [`vlmaps/controller/discrete_nav_controller.py`](../vlmaps/controller/discrete_nav_controller.py)
- Continuous actions: [`vlmaps/controller/continuous_nav_controller.py`](../vlmaps/controller/continuous_nav_controller.py)

### Navigation Workflow

#### Object Goal Navigation

**Location**: [`application/object_goal_navigation.py`](../application/object_goal_navigation.py)

```python
# 1. Parse instruction
landmarks = parse_object_goal_instruction("go to kitchen then toilet")
# Returns: ["kitchen", "toilet"]

# 2. For each landmark:
for landmark in landmarks:
    # 3. Find object position
    pos = robot.map.get_pos(landmark)  # Uses map indexing
    
    # 4. Navigate to position
    robot.move_to_object(landmark)
```

#### Spatial Goal Navigation

**Location**: [`application/evaluation/evaluate_spatial_goal_navigation.py`](../application/evaluation/evaluate_spatial_goal_navigation.py)

```python
# 1. Parse instruction to robot code
code = parse_spatial_instruction("move to the right of the refrigerator")
# Returns: "robot.move_to_right('refrigerator')"

# 2. Execute code
exec(code)  # Executes robot API calls
```

### Map Integration

**Location**: [`vlmaps/map/map.py`](../vlmaps/map/map.py)

The Map class provides spatial queries:

```python
class Map:
    def get_pos(self, name)              # Get object positions
    def get_left_pos(self, ...)         # Get position relative to object
    def get_right_pos(self, ...)
    def get_north_pos(self, ...)
    # ... spatial queries
```

These methods use the indexed map to find object locations.

---

## Key Components

### Map Classes

- **`Map`** ([`vlmaps/map/map.py`](../vlmaps/map/map.py)): Base map class with obstacle generation
- **`VLMap`** ([`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py)): Visual-language map with indexing
- **`VLMapBuilder`** ([`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py)): Builds maps from mobile base poses
- **`VLMapBuilderCam`** ([`vlmaps/map/vlmap_builder_cam.py`](../vlmaps/map/vlmap_builder_cam.py)): Builds maps from camera poses

### Utility Modules

- **`lseg_utils.py`** ([`vlmaps/utils/lseg_utils.py`](../vlmaps/utils/lseg_utils.py)): LSEG feature extraction
- **`clip_utils.py`** ([`vlmaps/utils/clip_utils.py`](../vlmaps/utils/clip_utils.py)): CLIP text/image encoding
- **`llm_client.py`** ([`vlmaps/utils/llm_client.py`](../vlmaps/utils/llm_client.py)): LLM API client
- **`llm_utils.py`** ([`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py)): Instruction parsing
- **`index_utils.py`** ([`vlmaps/utils/index_utils.py`](../vlmaps/utils/index_utils.py)): Map indexing utilities
- **`mapping_utils.py`** ([`vlmaps/utils/mapping_utils.py`](../vlmaps/utils/mapping_utils.py)): 3D mapping utilities
- **`navigation_utils.py`** ([`vlmaps/utils/navigation_utils.py`](../vlmaps/utils/navigation_utils.py)): Path planning utilities

### Task Modules

- **`habitat_object_nav_task.py`** ([`vlmaps/task/habitat_object_nav_task.py`](../vlmaps/task/habitat_object_nav_task.py)): Object goal navigation
- **`habitat_spatial_goal_nav_task.py`** ([`vlmaps/task/habitat_spatial_goal_nav_task.py`](../vlmaps/task/habitat_spatial_goal_nav_task.py)): Spatial goal navigation

---

## Configuration System

### Configuration Files

All configurations use Hydra and YAML:

- **Map Creation**: [`config/map_creation_cfg.yaml`](../config/map_creation_cfg.yaml)
- **Map Indexing**: [`config/map_indexing_cfg.yaml`](../config/map_indexing_cfg.yaml)
- **Map Config**: [`config/map_config/vlmaps.yaml`](../config/map_config/vlmaps.yaml)
- **Navigation**: [`config/object_goal_navigation_cfg.yaml`](../config/object_goal_navigation_cfg.yaml)
- **Data Paths**: [`config/data_paths/default.yaml`](../config/data_paths/default.yaml)

### Key Configuration Parameters

#### Map Creation

```yaml
# config/map_config/vlmaps.yaml
cell_size: 0.05          # Voxel size (meters)
grid_size: 2000          # Grid dimensions
depth_sample_rate: 4     # Depth sampling rate
cam_calib_mat: [...]     # Camera intrinsics
pose_info:
  pose_type: "mobile_base"  # or "camera_base"
  camera_height: 1.5
  # ... more pose config
```

#### LLM Configuration

Set via environment variables (see [LLM Integration](#llm-integration)):
- `VLMAPS_LLM_BASE_URL`
- `VLMAPS_LLM_CHAT_MODEL`
- `VLMAPS_LLM_API_KEY`

---

## Extension Points

### Adding New LSEG Models

1. **Add Model Class**: [`vlmaps/lseg/modules/models/`](../vlmaps/lseg/modules/models/)
2. **Update Builder**: Modify `_init_lseg()` in [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py)
3. **Update Utils**: Modify `get_lseg_feat()` if needed

### Adding New LLM Functionality

1. **Add Function**: [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py)
2. **Use Client**: `get_llm_client()` from [`vlmaps/utils/llm_client.py`](../vlmaps/utils/llm_client.py)
3. **Follow Pattern**: Use few-shot prompting like existing functions

### Adding New Robot Primitives

1. **Add Method**: [`vlmaps/robot/lang_robot.py`](../vlmaps/robot/lang_robot.py)
2. **Implement**: In specific robot class (e.g., `HabitatLanguageRobot`)
3. **Add to Parser**: Update `parse_spatial_instruction()` with examples

### Adding New Map Queries

1. **Add Method**: [`vlmaps/map/map.py`](../vlmaps/map/map.py) or [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py)
2. **Use Indexing**: Leverage `index_map()` for object queries
3. **Add Spatial Logic**: Implement relative positioning

### Customizing Feature Extraction

1. **Modify LSEG**: [`vlmaps/utils/lseg_utils.py`](../vlmaps/utils/lseg_utils.py)
2. **Add Preprocessing**: In map builder before `get_lseg_feat()`
3. **Change Templates**: Modify `multiple_templates` in [`vlmaps/utils/clip_utils.py`](../vlmaps/utils/clip_utils.py)

---

## Quick Reference

### Common Tasks

#### Change LSEG Model
- Edit: [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) - `_init_lseg()`
- Check: [`vlmaps/lseg/modules/models/lseg_net.py`](../vlmaps/lseg/modules/models/lseg_net.py)

#### Change LLM Provider
- Edit: [`vlmaps/utils/llm_client.py`](../vlmaps/utils/llm_client.py)
- Set: Environment variables for base URL and model

#### Modify Instruction Parsing
- Edit: [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py)
- Update: Few-shot examples in parsing functions

#### Add New Robot Command
- Add: Method to [`vlmaps/robot/lang_robot.py`](../vlmaps/robot/lang_robot.py)
- Implement: In [`vlmaps/robot/habitat_lang_robot.py`](../vlmaps/robot/habitat_lang_robot.py)
- Update: Parser in [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py)

#### Change Map Resolution
- Edit: [`config/map_config/vlmaps.yaml`](../config/map_config/vlmaps.yaml)
- Parameters: `cell_size`, `grid_size`

### File Locations Summary

| Component | File |
|-----------|------|
| LSEG Model Init | [`vlmaps/map/vlmap_builder.py:229`](../vlmaps/map/vlmap_builder.py#L229) |
| LSEG Feature Extract | [`vlmaps/utils/lseg_utils.py:15`](../vlmaps/utils/lseg_utils.py#L15) |
| LLM Client | [`vlmaps/utils/llm_client.py:31`](../vlmaps/utils/llm_client.py#L31) |
| Instruction Parse | [`vlmaps/utils/llm_utils.py:38`](../vlmaps/utils/llm_utils.py#L38) |
| Map Creation | [`vlmaps/map/vlmap_builder.py:55`](../vlmaps/map/vlmap_builder.py#L55) |
| Map Indexing | [`vlmaps/map/vlmap.py:146`](../vlmaps/map/vlmap.py#L146) |
| Navigation | [`vlmaps/navigator/navigator.py:17`](../vlmaps/navigator/navigator.py#L17) |
| Robot Primitives | [`vlmaps/robot/lang_robot.py:65`](../vlmaps/robot/lang_robot.py#L65) |

---

## Additional Resources

- **Main README**: [`README.md`](../README.md) - Installation and usage
- **Paper**: [Visual Language Maps for Robot Navigation](https://arxiv.org/pdf/2210.05714.pdf)
- **Project Page**: https://vlmaps.github.io/

---

*Last Updated: 2024*
*For questions or contributions, see the main README or open an issue.*

