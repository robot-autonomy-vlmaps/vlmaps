# VLMAPS Quick Reference Guide

Quick links and common tasks for team members working on VLMAPS.

## 🚀 Getting Started

### First Time Setup
1. Read: [Main README](../README.md)
2. Read: [Architecture Documentation](ARCHITECTURE.md)
3. Understand: LSEG and LLM integration sections

### Key Concepts
- **LSEG**: Language-driven Segmentation model that produces dense visual features
- **CLIP**: Used to match text queries to LSEG features
- **LLM**: Used to parse natural language instructions into robot commands
- **VLMap**: 3D voxel map storing LSEG features per voxel

---

## 📍 Code Locations

### LSEG Integration

| Task | File | Line/Function |
|------|------|---------------|
| Model initialization | [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) | `_init_lseg()` (229) |
| Feature extraction | [`vlmaps/utils/lseg_utils.py`](../vlmaps/utils/lseg_utils.py) | `get_lseg_feat()` (15) |
| Model architecture | [`vlmaps/lseg/modules/models/lseg_net.py`](../vlmaps/lseg/modules/models/lseg_net.py) | `LSegEncNet` |
| Usage in map building | [`vlmaps/map/vlmap_builder.py`](../vlmaps/map/vlmap_builder.py) | `create_mobile_base_map()` (100+) |

### LLM Integration

| Task | File | Line/Function |
|------|------|---------------|
| Client setup | [`vlmaps/utils/llm_client.py`](../vlmaps/utils/llm_client.py) | `get_llm_client()` (31) |
| Object goal parsing | [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py) | `parse_object_goal_instruction()` (38) |
| Spatial instruction parsing | [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py) | `parse_spatial_instruction()` (268) |
| Category matching | [`vlmaps/utils/index_utils.py`](../vlmaps/utils/index_utils.py) | `find_similar_category_id()` (34) |

### Map System

| Task | File | Line/Function |
|------|------|---------------|
| Map creation entry | [`application/create_map.py`](../application/create_map.py) | `main()` |
| Map class | [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) | `VLMap` |
| Map indexing | [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) | `index_map()` (146) |
| Map loading | [`vlmaps/map/vlmap.py`](../vlmaps/map/vlmap.py) | `load_map()` (72) |

### Navigation System

| Task | File | Line/Function |
|------|------|---------------|
| Robot primitives | [`vlmaps/robot/lang_robot.py`](../vlmaps/robot/lang_robot.py) | `LangRobot` |
| Path planning | [`vlmaps/navigator/navigator.py`](../vlmaps/navigator/navigator.py) | `Navigator` |
| Action execution | [`vlmaps/controller/controller.py`](../vlmaps/controller/controller.py) | `Controller` |

---

## 🔧 Common Modifications

### Change LSEG Model

1. **Modify model architecture**:
   ```python
   # File: vlmaps/map/vlmap_builder.py
   # Function: _init_lseg() around line 238
   lseg_model = LSegEncNet("", arch_option=0, block_depth=0, ...)
   ```

2. **Update checkpoint path**:
   ```python
   checkpoint_path = checkpoint_dir / "your_checkpoint.ckpt"
   ```

3. **Adjust processing parameters**:
   ```python
   crop_size = 480  # Change if needed
   base_size = 520  # Change if needed
   ```

### Change LLM Provider

1. **Set environment variables**:
   ```bash
   export VLMAPS_LLM_BASE_URL=http://your-server:port/v1
   export VLMAPS_LLM_CHAT_MODEL=your-model-name
   export VLMAPS_LLM_API_KEY=your-key
   ```

2. **Or modify client directly**:
   ```python
   # File: vlmaps/utils/llm_client.py
   # Function: get_llm_client() around line 31
   ```

### Modify Instruction Parsing

1. **Update few-shot examples**:
   ```python
   # File: vlmaps/utils/llm_utils.py
   # Function: parse_spatial_instruction() around line 277
   # Add new examples to the messages list
   ```

2. **Add new robot command**:
   - Add method to [`vlmaps/robot/lang_robot.py`](../vlmaps/robot/lang_robot.py)
   - Implement in [`vlmaps/robot/habitat_lang_robot.py`](../vlmaps/robot/habitat_lang_robot.py)
   - Add example to parser in [`vlmaps/utils/llm_utils.py`](../vlmaps/utils/llm_utils.py)

### Change Map Resolution

Edit [`config/map_config/vlmaps.yaml`](../config/map_config/vlmaps.yaml):
```yaml
cell_size: 0.05    # Voxel size in meters
grid_size: 2000    # Grid dimensions
```

---

## 🔍 Debugging Tips

### LSEG Issues

- **Check model loading**: Verify checkpoint exists and is correct format
- **Check feature dimensions**: Should match CLIP dimension (512 for ViT-B/32)
- **Check image preprocessing**: Normalization must match training

### LLM Issues

- **Check API connection**: Verify base URL and API key
- **Check model name**: Ensure model exists on your server
- **Check prompt format**: Follow few-shot pattern exactly

### Map Issues

- **Check data paths**: Verify RGB, depth, and pose files exist
- **Check coordinate frames**: Verify pose transformations
- **Check voxel grid**: Ensure grid_size is large enough

---

## 📚 Workflow Examples

### Creating a Map

```bash
cd application
python create_map.py
```

**Config**: [`config/map_creation_cfg.yaml`](../config/map_creation_cfg.yaml)

### Indexing a Map

```bash
cd application
python index_map.py
```

**Config**: [`config/map_indexing_cfg.yaml`](../config/map_indexing_cfg.yaml)

### Running Navigation

```bash
cd application/evaluation
python evaluate_object_goal_navigation.py
```

**Config**: [`config/object_goal_navigation_cfg.yaml`](../config/object_goal_navigation_cfg.yaml)

---

## 🎯 Extension Checklist

When adding new functionality:

- [ ] Identify which component to modify (LSEG, LLM, Map, Navigation)
- [ ] Check existing similar functionality for patterns
- [ ] Update configuration files if needed
- [ ] Add tests/examples if applicable
- [ ] Update documentation

---

## 🔗 Important Links

- **Main Documentation**: [ARCHITECTURE.md](ARCHITECTURE.md)
- **Project README**: [README.md](../README.md)
- **Paper**: https://arxiv.org/pdf/2210.05714.pdf
- **Project Page**: https://vlmaps.github.io/

---

*Quick reference for VLMAPS development. For detailed explanations, see [ARCHITECTURE.md](ARCHITECTURE.md).*

