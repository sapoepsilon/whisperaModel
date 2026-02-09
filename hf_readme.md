---
language: en
tags:
  - mlx
  - text-generation
  - command-parsing
  - macos
license: mit
---

# Whispera Voice Commands (MLX)

This repo hosts a small MLX-compatible model fine-tuned to convert natural-language (voice-like) macOS commands into structured JSON:

```json
{"category":"apps","operation":"open","app":"chrome"}
```

That JSON is intended to be mapped to real shell commands using the templates/patterns in `macos_operations.json` from the main project repo.

Project: https://github.com/sapoepsilon/whisperaModel

## Usage (mlx_lm)

```bash
mlx_lm.generate --model sapoepsilon/whispera-voice-commands --prompt "open safari" --max-tokens 100 --temp 0.1
```

## Notes

- This is a fused (merged) model for convenience (base + LoRA adapters).
- Outputs are JSON only; you should parse the first `{...}` block and then apply your own command templates.
