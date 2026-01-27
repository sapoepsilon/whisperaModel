#!/usr/bin/env python3
"""
Config-driven dataset generator for Whispera voice commands.
Reads operations and NLP patterns from macos_operations.json.

Usage:
    python generate_dataset.py

To add new commands:
    1. Edit macos_operations.json - add category/operation and nlp_patterns
    2. Run: python generate_dataset.py
    3. Retrain: mlx_lm.lora --model ./qwen-base --data . --train --iters 1500 --batch-size 4 --num-layers 8
"""

import json
import random
import re
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "macos_operations.json")


def load_config():
    """Load the operations config file."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def extract_params(pattern):
    """Extract parameter names from a pattern like 'open {app}' -> ['app']"""
    return re.findall(r'\{(\w+)\}', pattern)


def generate_examples(config):
    """Generate training examples from config."""
    examples = []
    nlp_patterns = config.get("nlp_patterns", {})
    sample_values = config.get("sample_values", {})

    for category, operations in nlp_patterns.items():
        for operation, patterns in operations.items():
            for pattern in patterns:
                params = extract_params(pattern)

                if not params:
                    output = json.dumps({"category": category, "operation": operation})
                    examples.append({
                        "messages": [
                            {"role": "user", "content": pattern},
                            {"role": "assistant", "content": output}
                        ]
                    })
                else:
                    param_values = {}
                    for param in params:
                        if param in sample_values:
                            param_values[param] = sample_values[param]
                        elif param == "app":
                            param_values[param] = sample_values.get("apps", ["app"])
                        elif param == "package":
                            param_values[param] = sample_values.get("packages", ["package"])
                        elif param == "branch":
                            param_values[param] = sample_values.get("branches", ["main"])
                        elif param == "container":
                            param_values[param] = sample_values.get("containers", ["container"])
                        elif param == "host":
                            param_values[param] = sample_values.get("hosts", ["localhost"])
                        elif param == "level":
                            param_values[param] = sample_values.get("levels", ["50"])
                        elif param == "port":
                            param_values[param] = sample_values.get("ports", ["3000"])
                        elif param == "file":
                            param_values[param] = ["app.py", "index.js", "main.go", "server.ts", "config.json"]
                        elif param == "message":
                            param_values[param] = ["fix bug", "add feature", "update readme", "initial commit", "wip"]
                        elif param == "url":
                            param_values[param] = ["https://github.com", "https://google.com", "https://example.com"]
                        elif param == "query":
                            param_values[param] = ["weather", "python tutorial", "react hooks", "docker compose"]
                        elif param == "pattern":
                            param_values[param] = ["error", "TODO", "function", "import"]
                        elif param == "name":
                            param_values[param] = ["node", "python", "nginx", "redis"]
                        elif param == "pid":
                            param_values[param] = ["1234", "5678", "9999"]
                        elif param == "path":
                            param_values[param] = ["~/Downloads", "~/Documents", "/tmp", "."]
                        elif param == "script":
                            param_values[param] = ["dev", "build", "test", "lint", "start"]
                        elif param == "service":
                            param_values[param] = ["mysql", "postgresql", "redis", "nginx", "mongodb"]
                        elif param == "domain":
                            param_values[param] = sample_values.get("domains", ["example.com"])
                        elif param == "mode":
                            param_values[param] = sample_values.get("modes", ["755"])
                        elif param == "user":
                            param_values[param] = sample_values.get("users", ["root"])
                        elif param == "disk":
                            param_values[param] = sample_values.get("disks", ["disk0"])
                        elif param == "command":
                            param_values[param] = sample_values.get("commands", ["ls"])
                        elif param == "output":
                            param_values[param] = ["archive", "backup", "output", "files"]
                        elif param == "input":
                            param_values[param] = ["src", "data", "folder", "project"]
                        elif param == "source":
                            param_values[param] = ["file.txt", "data.json", "folder", "README.md"]
                        elif param == "dest":
                            param_values[param] = ["backup", "archive", "new_folder", "destination"]
                        elif param == "file1":
                            param_values[param] = ["file1.txt", "old.json", "before.md"]
                        elif param == "file2":
                            param_values[param] = ["file2.txt", "new.json", "after.md"]
                        elif param == "text":
                            param_values[param] = ["hello world", "test message", "example text"]
                        else:
                            param_values[param] = [f"example_{param}"]

                    first_param = params[0]
                    for value in param_values.get(first_param, ["example"]):
                        filled_pattern = pattern
                        output_params = {}

                        for param in params:
                            if param == first_param:
                                param_val = value
                            else:
                                vals = param_values.get(param, ["example"])
                                param_val = random.choice(vals)

                            filled_pattern = filled_pattern.replace(f"{{{param}}}", str(param_val))
                            output_params[param] = param_val

                        output = json.dumps({
                            "category": category,
                            "operation": operation,
                            **output_params
                        })

                        examples.append({
                            "messages": [
                                {"role": "user", "content": filled_pattern},
                                {"role": "assistant", "content": output}
                            ]
                        })

    critical_patterns = [
        ("volume", "mute", "mute"),
        ("volume", "mute", "silence"),
        ("volume", "up", "volume up"),
        ("volume", "down", "volume down"),
        ("keyboard", "copy", "copy"),
        ("keyboard", "paste", "paste"),
        ("keyboard", "undo", "undo"),
        ("window", "close", "close window"),
        ("window", "minimize", "minimize"),
        ("media", "play", "play"),
        ("media", "pause", "pause"),
        ("display", "screenshot", "screenshot"),
        ("system", "sleep", "sleep"),
    ]

    for _ in range(3):
        for category, operation, phrase in critical_patterns:
            output = json.dumps({"category": category, "operation": operation})
            examples.append({
                "messages": [
                    {"role": "user", "content": phrase},
                    {"role": "assistant", "content": output}
                ]
            })

    casual_variations = [
        ("opn safari", {"category": "apps", "operation": "open", "app": "safari"}),
        ("oepn chrome", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("yo open slack", {"category": "apps", "operation": "open", "app": "slack"}),
        ("plz mute", {"category": "volume", "operation": "mute"}),
        ("pls pause", {"category": "media", "operation": "pause"}),
        ("gimme terminal", {"category": "apps", "operation": "open", "app": "terminal"}),
        ("hey can u open discord", {"category": "apps", "operation": "open", "app": "discord"}),
        ("cpy this", {"category": "keyboard", "operation": "copy"}),
        ("pste", {"category": "keyboard", "operation": "paste"}),
        ("git stat", {"category": "git", "operation": "status"}),
        ("docker containers", {"category": "docker", "operation": "ps"}),
        ("npm i", {"category": "npm", "operation": "install"}),
        ("whats the time", {"category": "info", "operation": "time"}),
        ("show me the date", {"category": "info", "operation": "date"}),
    ]

    for phrase, output_dict in casual_variations:
        examples.append({
            "messages": [
                {"role": "user", "content": phrase},
                {"role": "assistant", "content": json.dumps(output_dict)}
            ]
        })

    return examples


def main():
    print("Loading config from macos_operations.json...")
    config = load_config()

    print("Generating config-driven dataset...")
    examples = generate_examples(config)

    random.seed(42)
    random.shuffle(examples)

    split_idx = int(len(examples) * 0.9)
    train_examples = examples[:split_idx]
    valid_examples = examples[split_idx:]

    with open("train.jsonl", "w") as f:
        for ex in train_examples:
            f.write(json.dumps(ex) + "\n")

    with open("valid.jsonl", "w") as f:
        for ex in valid_examples:
            f.write(json.dumps(ex) + "\n")

    categories = config.get("nlp_patterns", {})
    total_operations = sum(len(ops) for ops in categories.values())

    print(f"\nGenerated {len(train_examples)} training examples")
    print(f"Generated {len(valid_examples)} validation examples")
    print(f"Total: {len(examples)} examples")
    print(f"\nCategories: {len(categories)}")
    print(f"Operations: {total_operations}")
    print("\nModel outputs JSON like: {\"category\": \"apps\", \"operation\": \"open\", \"app\": \"chrome\"}")
    print("Then whispera.py looks up the command template from config")


if __name__ == "__main__":
    main()
