# VLMaps Documentation

Welcome to the VLMaps documentation! This guide will walk you through the complete workflow for setting up and using VLMaps with the dev container.

## Quick Start Guide

Follow these steps in order:

1. **[Setup](01-setup.md)** - Set up the development environment with Docker
2. **[Download MP3D Dataset](02-download-mp3d.md)** - Download the Matterport3D dataset
3. **[Generate Dataset](03-generate-dataset.md)** - Generate RGB-D videos from the MP3D dataset
4. **[Index a VLMap](04-index-vlmap.md)** - Create and index a Visual Language Map
5. **[Test Navigation](05-test-navigation.md)** - Test object goal and spatial goal navigation

## Overview

VLMaps (Visual Language Maps) is a spatial map representation where pretrained visual-language model features are fused into a 3D reconstruction of the physical world. This enables natural language indexing in the map for zero-shot spatial goal navigation.

## Prerequisites

- Docker and Docker Compose installed
- NVIDIA GPU with CUDA support (for GPU acceleration)
- Matterport3D dataset access (requires signing Terms of Use)
- LLM API key (default provider OpenAI; set `VLMAPS_LLM_KEY_OPENAI` or other provider key per `config/llm.yaml` with matching `provider`)
For language model setup details, see [06 - LLM usage and configuration](06-llm.md).

## Getting Help

If you encounter issues:
- Check the troubleshooting sections in each guide
- Review the original [README.md](../README.md) for additional details
- Ensure all prerequisites are met

---

**Next Step:** [01 - Setup](01-setup.md)

