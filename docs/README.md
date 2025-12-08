# VLMAPS Documentation

Welcome to the VLMAPS documentation! This directory contains comprehensive documentation to help team members understand and work with the VLMAPS codebase.

## 📖 Documentation Index

### [Architecture Documentation](ARCHITECTURE.md)
**Comprehensive guide to VLMAPS architecture and components**

- System overview and architecture
- **LSEG Integration**: How LSEG is used, initialized, and can be modified
- **LLM Integration**: How LLMs are used for instruction parsing and category matching
- Map creation pipeline
- Map indexing system
- Navigation system
- Key components and their relationships
- Configuration system
- Extension points for customization

**Start here** if you're new to the codebase or need to understand how components work together.

### [Quick Reference Guide](QUICK_REFERENCE.md)
**Fast lookup for common tasks and code locations**

- Code location tables for LSEG, LLM, Map, and Navigation
- Common modification patterns
- Debugging tips
- Workflow examples
- Extension checklist

**Use this** when you need to quickly find where something is implemented or how to make a specific change.

## 🎯 For New Team Members

1. **Start with**: [ARCHITECTURE.md](ARCHITECTURE.md) - Read the overview and sections relevant to your work
2. **Bookmark**: [QUICK_REFERENCE.md](QUICK_REFERENCE.md) - Keep this handy for quick lookups
3. **Explore**: The main [README.md](../README.md) for setup and usage instructions

## 🔍 Finding Information

### I want to understand...
- **How LSEG works**: See [ARCHITECTURE.md - LSEG Integration](ARCHITECTURE.md#lseg-integration)
- **How LLM calls are made**: See [ARCHITECTURE.md - LLM Integration](ARCHITECTURE.md#llm-integration)
- **The map creation process**: See [ARCHITECTURE.md - Map Creation Pipeline](ARCHITECTURE.md#map-creation-pipeline)
- **How navigation works**: See [ARCHITECTURE.md - Navigation System](ARCHITECTURE.md#navigation-system)

### I want to modify...
- **LSEG model**: See [QUICK_REFERENCE.md - Change LSEG Model](QUICK_REFERENCE.md#change-lseg-model)
- **LLM provider**: See [QUICK_REFERENCE.md - Change LLM Provider](QUICK_REFERENCE.md#change-llm-provider)
- **Instruction parsing**: See [QUICK_REFERENCE.md - Modify Instruction Parsing](QUICK_REFERENCE.md#modify-instruction-parsing)
- **Map resolution**: See [QUICK_REFERENCE.md - Change Map Resolution](QUICK_REFERENCE.md#change-map-resolution)

### I need to find...
- **Code locations**: See [QUICK_REFERENCE.md - Code Locations](QUICK_REFERENCE.md#-code-locations)
- **Configuration files**: See [ARCHITECTURE.md - Configuration System](ARCHITECTURE.md#configuration-system)
- **Extension points**: See [ARCHITECTURE.md - Extension Points](ARCHITECTURE.md#extension-points)

## 📝 Documentation Structure

```
docs/
├── README.md              # This file - documentation index
├── ARCHITECTURE.md        # Comprehensive architecture guide
└── QUICK_REFERENCE.md     # Quick lookup guide
```

## 🔄 Keeping Documentation Updated

When making significant changes:

1. **LSEG changes**: Update [ARCHITECTURE.md - LSEG Integration](ARCHITECTURE.md#lseg-integration) and [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
2. **LLM changes**: Update [ARCHITECTURE.md - LLM Integration](ARCHITECTURE.md#llm-integration) and [QUICK_REFERENCE.md](QUICK_REFERENCE.md)
3. **New features**: Add to relevant sections in [ARCHITECTURE.md](ARCHITECTURE.md)
4. **New code locations**: Update [QUICK_REFERENCE.md - Code Locations](QUICK_REFERENCE.md#-code-locations)

## 💡 Tips

- All documentation includes **direct links** to source code files
- Code links use GitHub-style line references (e.g., `#L229`)
- Configuration examples reference actual config files
- Extension points include step-by-step instructions

## 🆘 Need Help?

- Check the [main README](../README.md) for setup and usage
- Review [ARCHITECTURE.md](ARCHITECTURE.md) for detailed explanations
- Use [QUICK_REFERENCE.md](QUICK_REFERENCE.md) for quick lookups
- Open an issue on the repository for questions

---

*Documentation last updated: 2024*

