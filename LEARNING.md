# How This Project Works: A Learning Guide

This document explains the machine learning concepts behind Whispera's voice command system.

## Table of Contents

1. [The Big Picture](#the-big-picture)
2. [What is Fine-Tuning?](#what-is-fine-tuning)
3. [LoRA: Efficient Fine-Tuning](#lora-efficient-fine-tuning)
4. [Training Data Format](#training-data-format)
5. [Pattern-Based Learning](#pattern-based-learning)
6. [The Full Pipeline](#the-full-pipeline)
7. [Key Decisions We Made](#key-decisions-we-made)

---

## The Big Picture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         WHISPERA ARCHITECTURE                          │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                         │
│   "open chrome"                                                         │
│        │                                                                │
│        ▼                                                                │
│   ┌─────────────────────────────────────────┐                          │
│   │  Fine-tuned LLM (Qwen 0.5B + LoRA)      │                          │
│   │  - Learned to extract INTENT            │                          │
│   │  - Outputs structured JSON              │                          │
│   └─────────────────────────────────────────┘                          │
│        │                                                                │
│        ▼                                                                │
│   {"action": "open_app", "target": "chrome"}                           │
│        │                                                                │
│        ▼                                                                │
│   ┌─────────────────────────────────────────┐                          │
│   │  Config Lookup (whispera_config.json)   │                          │
│   │  - Maps "chrome" → "Google Chrome"      │                          │
│   │  - No ML needed, just a lookup table    │                          │
│   └─────────────────────────────────────────┘                          │
│        │                                                                │
│        ▼                                                                │
│   open -a "Google Chrome"                                               │
│                                                                         │
└─────────────────────────────────────────────────────────────────────────┘
```

## What is Fine-Tuning?

### Pre-trained vs Fine-tuned Models

**Pre-trained model** (Qwen 0.5B):
- Trained on billions of words from the internet
- Knows general language patterns, facts, how to write code
- Like a fresh college graduate - broad knowledge, no specialization

**Fine-tuned model** (our model):
- Starts from the pre-trained model
- Trained on our specific examples
- Like that graduate after 3 months at a job - specialized skills

### What Fine-Tuning Does

It adjusts the model's weights to make certain input→output patterns more likely:

```
Before fine-tuning:
  Input: "open chrome"
  Output: "Chrome is a web browser developed by Google..."

After fine-tuning:
  Input: "open chrome"
  Output: {"action": "open_app", "target": "chrome"}
```

The model learns: "When someone says 'open X', I should output JSON with action=open_app"

## LoRA: Efficient Fine-Tuning

### The Problem

Qwen 0.5B has **494 million parameters** (numbers that define the model's behavior). Updating all of them:
- Takes massive amounts of memory
- Takes hours/days of training
- Risks "forgetting" what the model already knew

### The Solution: LoRA (Low-Rank Adaptation)

Instead of changing all 494M parameters, LoRA:
1. Freezes the original model (keeps it unchanged)
2. Adds tiny "adapter" layers (~1.5M parameters, 0.3% of total)
3. Only trains the adapters

```
┌────────────────────────────────────────────┐
│           Original Model (Frozen)          │
│           494M parameters                  │
│           ❄️ Not changed during training   │
├────────────────────────────────────────────┤
│           LoRA Adapters (Trained)          │
│           ~1.5M parameters                 │
│           🔥 Updated during training       │
└────────────────────────────────────────────┘
```

Benefits:
- Trains in ~3 minutes instead of hours
- Uses ~8GB RAM instead of 40GB+
- Can have multiple adapters for different tasks
- Original model preserved (can always go back)

### How LoRA Math Works (Simplified)

A neural network layer is basically a matrix multiplication:
```
output = input × W    (W is a huge matrix)
```

LoRA adds a small "correction":
```
output = input × W + input × A × B
                     └───────────┘
                     tiny matrices
```

Instead of modifying W (huge), we learn A and B (tiny). The result is nearly as good.

## Training Data Format

### JSONL Format

Our training data is in `train.jsonl`. Each line is one training example:

```json
{
  "messages": [
    {"role": "user", "content": "open safari"},
    {"role": "assistant", "content": "{\"action\":\"open_app\",\"target\":\"safari\"}"}
  ]
}
```

This teaches: "When user says X, assistant should respond with Y"

### Why JSON Output?

We chose JSON output (instead of raw bash) for extensibility:

```
                    JSON Approach
                    ─────────────
Model outputs:      {"action": "open_app", "target": "chrome"}
                           │
                           ▼
Config maps:        "chrome" → "Google Chrome"  (configurable!)
                           │
                           ▼
Final command:      open -a "Google Chrome"


                    Bash Approach (what we tried first)
                    ──────────────
Model outputs:      open -a "Google Chrome"
                           │
                           ▼
Problem:            What if user installs new app?
                    Model has never seen it!
                    Would need to RETRAIN.
```

JSON lets users add new apps by editing a config file, no retraining needed.

## Pattern-Based Learning

### The Key Insight

We don't teach the model every possible command. We teach **patterns**:

```python
# Training examples include variations like:
"open chrome"           → {"action": "open_app", "target": "chrome"}
"launch safari"         → {"action": "open_app", "target": "safari"}
"start firefox"         → {"action": "open_app", "target": "firefox"}
"open the calculator"   → {"action": "open_app", "target": "calculator"}
```

The model learns: **"open/launch/start [app]" → open_app action**

Then it **generalizes** to apps it's never seen:
```
"open spotify"  → {"action": "open_app", "target": "spotify"}  ✓ Works!
```

### Why This Works

Neural networks are pattern matchers. Given enough examples, they learn:
- Word positions (verbs like "open" come first)
- Synonyms ("launch" ≈ "start" ≈ "open")
- Sentence structure ("open the X" vs "open X")

### Dataset Balance Matters

We learned this the hard way. Our first dataset had:
- 500 "open app" examples
- 50 "copy" examples

Result: Model was great at "open app", terrible at everything else.

Solution: Balance the dataset. Critical commands get **duplicated 3x**.

## The Full Pipeline

### 1. Generate Training Data

```bash
python generate_dataset.py
```

This script:
- Defines action patterns (open app, volume, screenshot, etc.)
- Generates variations ("open X", "launch X", "start X")
- Outputs `train.jsonl` with ~2000 examples

### 2. Train the Model

```bash
mlx_lm.lora \
  --model ./qwen-base \
  --data . \
  --train \
  --iters 1500 \
  --batch-size 4 \
  --num-layers 8
```

This:
- Loads base Qwen model
- Reads train.jsonl
- Updates LoRA adapters for 1500 iterations
- Saves adapters to `adapters/` folder

### 3. Inference (Using the Model)

```bash
./w "open chrome"
```

This:
1. Formats input as a chat message
2. Runs through model + adapters
3. Gets JSON output
4. Looks up actual app name in config
5. Generates bash command

## Key Decisions We Made

### 1. Small Model (0.5B) vs Large Model (7B+)

| Aspect | Small (0.5B) | Large (7B) |
|--------|-------------|------------|
| Speed | ~0.1s inference | ~1-2s inference |
| Memory | ~2GB | ~14GB |
| Accuracy | Good for narrow tasks | Better generalization |
| Training | 3 minutes | 30+ minutes |

We chose small because:
- Voice commands need instant response
- Task is narrow (not open-ended chat)
- Can retrain quickly when adding features

### 2. LoRA Layers

We use `--num-layers 8` (only adapt 8 layers out of 24).

More layers = more capacity but slower training. 8 was enough for our task.

### 3. Training Iterations

We use 1500 iterations. Found empirically:
- 500: Underfitting (model doesn't learn patterns)
- 1500: Good accuracy
- 3000: Overfitting (memorizes training data, fails on variations)

### 4. Batch Size

We use batch-size 4. Higher batch = faster training but more memory. 4 works well on M4 48GB.

## Extending the System

### Adding New Simple Commands

1. Edit `generate_dataset.py`:
```python
ACTIONS["my_action"] = '{{"action":"my_action","param":"{value}"}}'
SIMPLE_PATTERNS["my_action"] = ["trigger phrase {value}", ...]
```

2. Edit `whispera.py` to handle the new action
3. Regenerate dataset: `python generate_dataset.py`
4. Retrain: `mlx_lm.lora --model ./qwen-base --data . --train --iters 1500`

### Adding New Apps (No Retraining)

Just edit `whispera_config.json`:
```json
{
  "apps": {
    "myapp": "My Application"
  }
}
```

The model already knows "open [app]" pattern, it will work.

## What We Learned

1. **Dataset balance is crucial** - Underrepresented commands fail
2. **JSON output enables extensibility** - Users can configure without retraining
3. **Small models can be specialists** - 0.5B is enough for narrow tasks
4. **LoRA makes fine-tuning accessible** - 3 minutes on a laptop!
5. **Patterns > memorization** - Teach the structure, not every example

## Further Reading

- [LoRA Paper](https://arxiv.org/abs/2106.09685) - The original research
- [MLX Documentation](https://ml-explore.github.io/mlx/) - Apple's ML framework
- [Qwen Models](https://github.com/QwenLM/Qwen2.5) - The base model family
