# Whispera Voice Command Model - Claude Instructions

This document provides context for Claude to work effectively on this project.

## Project Overview

Whispera is a config-driven fine-tuned LLM that converts natural language voice commands into executable macOS bash commands.

**Key insight**: The model learns to extract intent/parameters, the config file defines the actual commands.

## Architecture

```
User speech → WhisperKit (STT) → Fine-tuned LLM → JSON → Config lookup → Bash command

Example:
"open chrome" → Model → {"category":"apps","operation":"open","app":"chrome"}
                                    ↓
                        macos_operations.json lookup
                                    ↓
                        open -a "Google Chrome"
```

## Key Files

| File | Purpose | When to Update |
|------|---------|----------------|
| `macos_operations.json` | **Main config**: templates + NLP patterns | Adding commands |
| `whispera_config.json` | App/folder name mappings | Auto-generated |
| `generate_dataset.py` | Reads config, creates train.jsonl | Rarely |
| `whispera.py` | CLI that runs model + template lookup | Rarely |
| `README.md` | Project documentation | When features change |

## The Config File (`macos_operations.json`)

This is the **single source of truth**. It has three sections:

### 1. `categories` - Command Templates
```json
{
  "categories": {
    "apps": {
      "open": "open -a \"{app}\"",
      "quit": "osascript -e 'tell application \"{app}\" to quit'"
    },
    "git": {
      "commit": "git commit -m \"{message}\""
    }
  }
}
```

### 2. `nlp_patterns` - Training Patterns
```json
{
  "nlp_patterns": {
    "apps": {
      "open": ["open {app}", "launch {app}", "start {app}"],
      "quit": ["quit {app}", "close {app}", "exit {app}"]
    }
  }
}
```

### 3. `sample_values` - Example Values for Training
```json
{
  "sample_values": {
    "apps": ["safari", "chrome", "slack"],
    "packages": ["node", "python", "git"]
  }
}
```

## Adding New Commands

### Simple (No Retrain)
Add app to `whispera_config.json`:
```json
{"apps": {"myapp": "My App"}}
```

### New Operation (Requires Retrain)
1. Add template to `categories` in `macos_operations.json`
2. Add patterns to `nlp_patterns`
3. Add sample values if needed
4. Run: `python generate_dataset.py`
5. Run: `mlx_lm.lora --model ./qwen-base --data . --train --iters 1500 --batch-size 4 --num-layers 8`
6. Update README if significant

## Model Output Format

The model outputs JSON like:
```json
{"category": "apps", "operation": "open", "app": "chrome"}
{"category": "git", "operation": "commit", "message": "fix bug"}
{"category": "volume", "operation": "set", "level": "50"}
```

`whispera.py` looks up the template and fills in parameters.

## Documentation Maintenance

When making changes:

### README.md Updates
- Update when adding new categories/operations
- Update supported commands tables
- Update architecture if flow changes

### This File (CLAUDE.md) Updates
- Update when config structure changes
- Update when adding new parameter transformations
- Update when workflow changes

## Current Capabilities

**Categories (20+)**: apps, volume, brightness, display, system, power, network, bluetooth, window, keyboard, media, finder, clipboard, speech, notifications, urls, files, apps_apple, appearance, info, git, docker, npm, yarn, python, homebrew, mas, process, network_tools, archive, text, permissions, disk, services, database, xcode, flutter, rust, go, aws, misc

**Operations (200+)**: See `macos_operations.json` for complete list

## Limitations

- Single-step commands only
- Cannot do dynamic scripting (batch operations)
- Parameters must match trained patterns
- 0.5B model - pattern matching, not reasoning
