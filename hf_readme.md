---
license: apache-2.0
base_model: Qwen/Qwen2.5-0.5B-Instruct
tags:
  - mlx
  - voice-commands
  - macos
  - bash
  - fine-tuned
language:
  - en
pipeline_tag: text-generation
library_name: mlx
---

# Whispera Voice Commands

A fine-tuned LLM that converts natural language voice commands into executable macOS bash commands.

## Model Details

- **Base Model**: [Qwen/Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
- **Fine-tuning Method**: LoRA (Low-Rank Adaptation)
- **Framework**: MLX
- **Parameters**: 494M (base) + 1.5M (LoRA adapters, merged)
- **Training Examples**: ~1,300
- **Categories**: 28 command categories
- **Operations**: 250+ supported commands

## Usage

### With MLX (Python)

```python
from mlx_lm import load, generate

model, tokenizer = load("sapoepsilon/whispera-voice-commands")
response = generate(model, tokenizer, prompt="open chrome", max_tokens=100)
print(response)
# {"category": "apps", "operation": "open", "app": "chrome"}
```

### With WhisperaKit (Swift)

```swift
import WhisperaKit

let whispera = Whispera()
try await whispera.loadModel()
let command = try await whispera.process("open chrome")
print(command)  // open -a "Google Chrome"
```

## Output Format

The model outputs structured JSON:

```json
{"category": "apps", "operation": "open", "app": "chrome"}
```

This JSON is then mapped to actual bash commands using a config file.

## Supported Commands

| Category | Examples |
|----------|----------|
| **Apps** | open, quit, hide, show |
| **Volume** | set level, mute, unmute |
| **Git** | status, commit, push, pull, branch |
| **Docker** | ps, images, run, stop, logs |
| **Files** | ls, mkdir, rm, mv, cp, find |
| **System** | screenshot, lock, sleep, restart |
| **Network** | ping, curl, ssh, wifi |
| **Clipboard** | pbcopy, pbpaste |

## Training

Trained on Apple Silicon (M4) using MLX with LoRA:

```bash
mlx_lm.lora \
  --model Qwen/Qwen2.5-0.5B-Instruct \
  --data . \
  --train \
  --iters 1500 \
  --batch-size 4 \
  --num-layers 8
```

## License

This model is released under the Apache 2.0 license, same as the base Qwen model.

## Citation

If you use this model, please cite the base model:

```bibtex
@article{qwen2.5,
  title={Qwen2.5: A Party of Foundation Models},
  author={Qwen Team},
  year={2024},
  url={https://qwenlm.github.io/blog/qwen2.5/}
}
```

## Links

- **Swift Package**: [WhisperaKit](https://github.com/sapoepsilon/WhisperaKit)
- **Training Code**: [whisperaModel](https://github.com/sapoepsilon/whisperaModel)
- **Base Model**: [Qwen/Qwen2.5-0.5B-Instruct](https://huggingface.co/Qwen/Qwen2.5-0.5B-Instruct)
