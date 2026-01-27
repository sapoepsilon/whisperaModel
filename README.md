# Whispera Voice Command Model

A fine-tuned LLM that converts natural language voice commands into executable macOS bash commands.

## Overview

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────┐
│   Voice Input   │ --> │  Fine-tuned LLM  │ --> │   Bash Command  │
│  "open chrome"  │     │  (Qwen 0.5B)     │     │ open -a "Chrome"│
└─────────────────┘     └──────────────────┘     └─────────────────┘
```

## Quick Start

```bash
# Activate environment
source venv/bin/activate

# Convert natural language to bash
./w "open safari"                    # → open -a "Safari"
./w "git status"                     # → git status
./w "set volume to 50"               # → osascript -e 'set volume output volume 50'
./w "docker ps"                      # → docker ps

# Execute immediately with -x flag
./w -x "open chrome"

# Interactive mode
./w -i
```

## Supported Commands (250+)

### macOS System
| Category | Commands |
|----------|----------|
| **Apps** | open, quit, hide, show |
| **Volume** | set level, up, down, mute, unmute |
| **Display** | screenshot, lock, sleep |
| **System** | sleep, restart, shutdown, spotlight, empty trash |
| **Window** | close, minimize, fullscreen, new tab |
| **Keyboard** | copy, paste, cut, undo, redo, save |
| **Media** | play, pause, next, previous |
| **Clipboard** | pbcopy, pbpaste, clear clipboard |
| **Speech** | say (text-to-speech), list voices |
| **macOS Tools** | spotlight/mdfind, softwareupdate, metadata |

### Developer Tools
| Category | Commands |
|----------|----------|
| **Git** | status, add, commit, push, pull, branch, checkout, clone, stash, log, diff |
| **Docker** | ps, images, run, stop, start, logs, build, compose up/down, prune |
| **npm/yarn** | install, start, test, build, run scripts |
| **Python** | run, pip install/list, venv, pytest, jupyter |
| **Homebrew** | install, uninstall, update, upgrade, search, services |

### Unix/File Commands
| Category | Commands |
|----------|----------|
| **Files** | ls, mkdir, touch, rm, mv, cp, find, ln (symlink), tree, less, stat, file |
| **Text** | cat, head, tail, grep, wc, sort, diff, nano, vim, code |
| **Archive** | zip, unzip, tar, gzip |
| **Permissions** | chmod, chown |
| **Disk** | df, du, diskutil |

### Network & Process
| Category | Commands |
|----------|----------|
| **Network** | wifi on/off, ping, curl, ssh, ifconfig, netstat, traceroute, nslookup, whois |
| **Process** | ps, top, kill, killall, lsof |
| **Info** | pwd, whoami, hostname, uptime, history, clear, env |
| **Services** | mysql, postgres, redis, nginx start/stop |

## Architecture

### Config-Driven Design

The system uses `macos_operations.json` as the single source of truth:

```
┌────────────────────────────────────────────────────────────────┐
│                    macos_operations.json                       │
├────────────────────────────────────────────────────────────────┤
│  categories:        Command templates                          │
│    apps.open:       open -a "{app}"                           │
│    git.commit:      git commit -m "{message}"                 │
│    volume.set:      osascript -e 'set volume output...'       │
│                                                                │
│  nlp_patterns:      Training patterns                          │
│    apps.open:       ["open {app}", "launch {app}", ...]       │
│    git.commit:      ["commit {message}", ...]                 │
│                                                                │
│  sample_values:     Example values for training               │
│    apps:            [safari, chrome, slack, ...]              │
│    packages:        [node, python, redis, ...]                │
└────────────────────────────────────────────────────────────────┘
            │                           │
            ▼                           ▼
┌────────────────────┐      ┌─────────────────────┐
│ generate_dataset.py │      │     whispera.py     │
│ Creates train.jsonl │      │ Looks up templates  │
└────────────────────┘      └─────────────────────┘
```

### How It Works

1. **Input**: "open chrome"
2. **Model**: Outputs `{"category": "apps", "operation": "open", "app": "chrome"}`
3. **Config Lookup**: `categories.apps.open` → `open -a "{app}"`
4. **Template Fill**: Replace `{app}` with "Google Chrome" (from app mappings)
5. **Output**: `open -a "Google Chrome"`

## Customization

### Adding New Commands (No Retraining)

For commands that use existing patterns, just add to `whispera_config.json`:

```json
{
  "apps": {
    "myapp": "My Application Name"
  }
}
```

### Adding New Operations (Requires Retraining)

1. **Edit `macos_operations.json`**:

```json
{
  "categories": {
    "myservice": {
      "start": "systemctl start {service}",
      "stop": "systemctl stop {service}"
    }
  },
  "nlp_patterns": {
    "myservice": {
      "start": ["start {service}", "run {service}", "launch {service}"],
      "stop": ["stop {service}", "kill {service}", "end {service}"]
    }
  },
  "sample_values": {
    "services": ["nginx", "mysql", "redis"]
  }
}
```

2. **Regenerate dataset**:
```bash
source venv/bin/activate
python generate_dataset.py
```

3. **Retrain model** (~3 minutes):
```bash
mlx_lm.lora \
  --model ./qwen-base \
  --data . \
  --train \
  --iters 1500 \
  --batch-size 4 \
  --num-layers 8
```

4. **Test**:
```bash
./w "start nginx"
```

## Files

| File | Purpose |
|------|---------|
| `macos_operations.json` | **Main config**: command templates + NLP patterns |
| `whispera_config.json` | App/folder name mappings (auto-generated) |
| `generate_dataset.py` | Reads config, generates training data |
| `whispera.py` | CLI that runs model + looks up templates |
| `./w` | Quick bash wrapper |
| `qwen-base/` | Base Qwen 0.5B model |
| `adapters/` | Fine-tuned LoRA weights |

## Training

### Generate Dataset
```bash
source venv/bin/activate
python generate_dataset.py
```

### Train Model
```bash
mlx_lm.lora \
  --model ./qwen-base \
  --data . \
  --train \
  --iters 1500 \
  --batch-size 4 \
  --num-layers 8
```

### Test Model
```bash
python test_model.py
# or manually:
./w "open safari"
./w "git status"
./w "volume 50"
```

## Regenerate App Config

If you install new apps, regenerate the config:

```bash
python generate_config.py
```

## Requirements

- macOS with Apple Silicon (M1/M2/M3/M4)
- Python 3.10+
- MLX (`pip install mlx-lm`)
- ~2GB disk space for model

## Training Stats

- Base model: Qwen2.5-0.5B-Instruct (494M parameters)
- Training method: LoRA (trains only 0.3% of parameters)
- Training time: ~3 minutes on M4
- Categories: 28
- Operations: 250+
- Training examples: ~1300

## Extending - Quick Reference

### Add new app (no retrain)
Edit `whispera_config.json`:
```json
{"apps": {"myapp": "My App Name"}}
```

### Add new command pattern (requires retrain)
1. Edit `macos_operations.json`:
   - Add template to `categories`
   - Add NLP patterns to `nlp_patterns`
   - Add sample values if needed
2. Run: `python generate_dataset.py`
3. Run: `mlx_lm.lora --model ./qwen-base --data . --train --iters 1500 --batch-size 4 --num-layers 8`

### Add new category (requires retrain)
Same as above, but add a new top-level key in both `categories` and `nlp_patterns`.

## Limitations

- Single-step commands only (no "open chrome and search for X")
- Cannot do dynamic scripting (batch rename with patterns)
- Parameters must match trained patterns
- For complex operations, consider larger models or API fallback
