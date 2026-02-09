#!/usr/bin/env python3
"""
Enhanced config-driven dataset generator for Whispera voice commands.
Includes typo tolerance, casual speech patterns, compound commands, and semantic variations.

Usage:
    python generate_dataset.py

To add new commands:
    1. Edit macos_operations.json - add category/operation and nlp_patterns
    2. Run: python generate_dataset.py
    3. Retrain: mlx_lm.lora --model ./qwen-base --data . --train --iters 2000 --batch-size 4 --num-layers 12
"""

import json
import random
import re
import os
from difflib import get_close_matches

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "macos_operations.json")

# Common typos and variations for robustness
TYPO_PATTERNS = {
    "chrome": ["chrme", "chrom", "crome", "chrrome", "chome"],
    "safari": ["saari", "safri", "sfari", "safary"],
    "terminal": ["termial", "termnl", "trminal", "terminl"],
    "vscode": ["vscod", "vscoode", "vcode", "code"],
    "slack": ["slck", "slak", "sack"],
    "spotify": ["spotfy", "spotifi", "spootify"],
    "discord": ["dscord", "discrd", "discor"],
    "firefox": ["firefo", "firfox", "firefx"],
    "finder": ["fnder", "findr", "fider"],
    "xcode": ["xcd", "xcde", "xcod"],
    "docker": ["dcker", "docer", "dockr"],
    "git": ["gt", "gir", "igt"],
    "npm": ["nmp", "pnm"],
    "python": ["pthon", "pyton", "pythn"],
    "commit": ["comit", "commt", "comitt"],
    "install": ["instal", "intall", "instll"],
    "update": ["updat", "upate", "updte"],
    "volume": ["volme", "volum", "vol"],
    "brightness": ["brightnes", "brigthness", "bright"],
    "screenshot": ["screnshot", "screensht", "screshot"],
    "restart": ["restar", "restert", "restrt"],
    "shutdown": ["shutdow", "shutdon", "shutdwn"],
    "mute": ["mut", "mte", "mutee"],
}

# Casual speech fillers and variations
CASUAL_PREFIXES = [
    "",
    "hey ",
    "yo ",
    "okay ",
    "please ",
    "can you ",
    "could you ",
    "would you ",
]
CASUAL_SUFFIXES = ["", " please", " now", " immediately", " quickly", " for me"]
CASUAL_CONNECTORS = ["and", "then", "also", "plus", "after that"]

# Semantic keyword mappings for fallback
SEMANTIC_KEYWORDS = {
    "volume": ["sound", "loud", "quiet", "audio", "noise", "speaker"],
    "brightness": ["screen", "display", "light", "dim", "bright"],
    "apps": ["application", "program", "software", "tool"],
    "display": ["screen", "monitor", "display"],
    "system": ["mac", "computer", "machine", "os"],
    "network": ["internet", "wifi", "connection", "online"],
    "git": ["version control", "repository", "repo", "commit", "branch"],
    "docker": ["container", "image"],
    "files": ["file", "folder", "directory", "path"],
    "keyboard": ["key", "shortcut", "hotkey"],
    "media": ["music", "song", "track", "video", "player"],
    "window": ["window", "tab", "pane"],
}


def load_config():
    """Load the operations config file."""
    with open(CONFIG_PATH) as f:
        return json.load(f)


def extract_params(pattern):
    """Extract parameter names from a pattern like 'open {app}' -> ['app']"""
    return re.findall(r"\{(\w+)\}", pattern)


def generate_typos(word):
    """Generate realistic typos for a word."""
    if word.lower() in TYPO_PATTERNS:
        return TYPO_PATTERNS[word.lower()]
    return []


def add_casual_variations(pattern):
    """Add casual speech variations to a pattern."""
    variations = [pattern]

    # Add prefixes
    for prefix in CASUAL_PREFIXES[:3]:  # Limit to avoid explosion
        if prefix and not pattern.startswith(prefix.strip()):
            variations.append(prefix + pattern)

    # Add suffixes
    for suffix in CASUAL_SUFFIXES[:2]:
        if suffix and not pattern.endswith(suffix.strip()):
            variations.append(pattern + suffix)

    return list(set(variations))


def generate_compound_examples(category, operations, sample_values):
    """Generate compound command examples.

    NOTE: The runtime (whispera.py) supports compound commands by splitting the
    input and running the model on each part. Training the model to emit a
    different JSON schema (e.g. category=compound) increases error risk for
    single-step commands.
    """

    return []


def generate_semantic_fallback_examples():
    """Generate examples for semantic fallback matching."""
    examples = []

    # Map semantically similar phrases to correct categories
    semantic_mappings = [
        ("make it louder", {"category": "volume", "operation": "up"}),
        ("make it quieter", {"category": "volume", "operation": "down"}),
        ("turn up the sound", {"category": "volume", "operation": "up"}),
        ("turn down the sound", {"category": "volume", "operation": "down"}),
        ("screen darker", {"category": "brightness", "operation": "down"}),
        ("screen brighter", {"category": "brightness", "operation": "up"}),
        ("dim the screen", {"category": "brightness", "operation": "down"}),
        ("brighten the screen", {"category": "brightness", "operation": "up"}),
        ("shut down", {"category": "system", "operation": "shutdown"}),
        ("turn off computer", {"category": "system", "operation": "shutdown"}),
        ("restart computer", {"category": "system", "operation": "restart"}),
        ("reboot", {"category": "system", "operation": "restart"}),
        ("put to sleep", {"category": "system", "operation": "sleep"}),
        ("internet off", {"category": "network", "operation": "wifi_off"}),
        ("internet on", {"category": "network", "operation": "wifi_on"}),
        ("wifi status", {"category": "network", "operation": "wifi_status"}),
        ("bluetooth on", {"category": "bluetooth", "operation": "on"}),
        ("bluetooth off", {"category": "bluetooth", "operation": "off"}),
        ("kill app", {"category": "apps", "operation": "quit"}),
        ("close application", {"category": "apps", "operation": "quit"}),
        ("start app", {"category": "apps", "operation": "open"}),
        ("launch application", {"category": "apps", "operation": "open"}),
        ("copy that", {"category": "keyboard", "operation": "copy"}),
        ("paste that", {"category": "keyboard", "operation": "paste"}),
        ("undo that", {"category": "keyboard", "operation": "undo"}),
        ("play music", {"category": "media", "operation": "play"}),
        ("pause music", {"category": "media", "operation": "pause"}),
        ("stop music", {"category": "media", "operation": "pause"}),
        ("next song", {"category": "media", "operation": "next"}),
        ("previous song", {"category": "media", "operation": "previous"}),
        ("skip track", {"category": "media", "operation": "next"}),
        ("go back song", {"category": "media", "operation": "previous"}),
    ]

    for phrase, output in semantic_mappings:
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": phrase},
                    {"role": "assistant", "content": json.dumps(output)},
                ]
            }
        )

        # Add variations with prefixes/suffixes
        for prefix in ["hey ", "please ", "can you "]:
            examples.append(
                {
                    "messages": [
                        {"role": "user", "content": prefix + phrase},
                        {"role": "assistant", "content": json.dumps(output)},
                    ]
                }
            )

    return examples


def generate_confusing_examples():
    """Generate examples that differentiate between similar commands."""
    examples = []

    # Pairs that could be confused
    confusing_pairs = [
        ("open chrome", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("chrome open", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("launch chrome", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("start chrome", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("run chrome", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("fire up chrome", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("lock screen", {"category": "display", "operation": "lock"}),
        ("git commit", {"category": "git", "operation": "commit", "message": "update"}),
        ("git branch", {"category": "git", "operation": "branch"}),
        (
            "create branch feature-foo",
            {"category": "git", "operation": "branch_create", "branch": "feature-foo"},
        ),
        ("push", {"category": "git", "operation": "push"}),
        (
            "commit changes",
            {"category": "git", "operation": "commit", "message": "update"},
        ),
        (
            "commit code",
            {"category": "git", "operation": "commit", "message": "update"},
        ),
        (
            "docker stop",
            {"category": "docker", "operation": "stop", "container": "container"},
        ),
        (
            "stop docker",
            {"category": "docker", "operation": "stop", "container": "container"},
        ),
        ("npm install", {"category": "npm", "operation": "install"}),
        ("install npm", {"category": "npm", "operation": "install"}),
        ("install packages", {"category": "npm", "operation": "install"}),
    ]

    for phrase, output in confusing_pairs:
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": phrase},
                    {"role": "assistant", "content": json.dumps(output)},
                ]
            }
        )

    return examples


def generate_typo_examples(sample_values):
    """Generate examples with common typos."""
    examples = []

    typo_mappings = [
        ("opn chrome", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("oepn safari", {"category": "apps", "operation": "open", "app": "safari"}),
        ("chrme open", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("termial", {"category": "apps", "operation": "open", "app": "terminal"}),
        ("git comit", {"category": "git", "operation": "commit", "message": "update"}),
        ("gt status", {"category": "git", "operation": "status"}),
        ("npm intall", {"category": "npm", "operation": "install"}),
        ("docker ps", {"category": "docker", "operation": "ps"}),
        (
            "dcker stop",
            {"category": "docker", "operation": "stop", "container": "container"},
        ),
        ("volme up", {"category": "volume", "operation": "up"}),
        ("volme down", {"category": "volume", "operation": "down"}),
        ("screnshot", {"category": "display", "operation": "screenshot"}),
        ("mut", {"category": "volume", "operation": "mute"}),
        ("mutee", {"category": "volume", "operation": "mute"}),
        ("cop", {"category": "keyboard", "operation": "copy"}),
        ("pst", {"category": "keyboard", "operation": "paste"}),
        ("und", {"category": "keyboard", "operation": "undo"}),
        ("sllep", {"category": "system", "operation": "sleep"}),
        ("restar", {"category": "system", "operation": "restart"}),
        ("shutdon", {"category": "system", "operation": "shutdown"}),
    ]

    # Single-token intents are common in voice; heavily bias these.
    # These two are known hard cases that otherwise drift into other categories.
    hard_single_token = [
        ("chrme", {"category": "apps", "operation": "open", "app": "chrome"}),
        ("mut", {"category": "volume", "operation": "mute"}),
        ("sllep", {"category": "system", "operation": "sleep"}),
        ("restar", {"category": "system", "operation": "restart"}),
    ]

    for _ in range(40):
        for phrase, output in hard_single_token:
            typo_mappings.append((phrase, output))

    for phrase, output in typo_mappings:
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": phrase},
                    {"role": "assistant", "content": json.dumps(output)},
                ]
            }
        )

    return examples


def generate_contextual_examples():
    """Generate examples that rely on context/ambiguity resolution."""
    examples = []

    # Ambiguous phrases that need context
    context_examples = [
        ("push it", {"category": "git", "operation": "push"}, "git"),
        ("pull it", {"category": "git", "operation": "pull"}, "git"),
        (
            "commit this",
            {"category": "git", "operation": "commit", "message": "update"},
            "git",
        ),
        ("install it", {"category": "npm", "operation": "install"}, "npm"),
        ("run it", {"category": "npm", "operation": "start"}, "npm"),
        ("build it", {"category": "npm", "operation": "build"}, "npm"),
        (
            "stop it",
            {"category": "docker", "operation": "stop", "container": "container"},
            "docker",
        ),
        (
            "start it",
            {"category": "docker", "operation": "start", "container": "container"},
            "docker",
        ),
        ("open it", {"category": "apps", "operation": "open", "app": "app"}, "apps"),
        ("close it", {"category": "apps", "operation": "quit", "app": "app"}, "apps"),
    ]

    for phrase, output, context in context_examples:
        examples.append(
            {
                "messages": [
                    {"role": "user", "content": phrase},
                    {
                        "role": "assistant",
                        "content": json.dumps(output),
                    },
                ]
            }
        )

    return examples


def generate_examples(config):
    """Generate comprehensive training examples from config."""
    examples = []
    nlp_patterns = config.get("nlp_patterns", {})
    sample_values = config.get("sample_values", {})
    categories = config.get("categories", {})

    print("Generating base examples from NLP patterns...")

    # Generate base examples from config
    for category, operations in nlp_patterns.items():
        for operation, patterns in operations.items():
            for pattern in patterns:
                params = extract_params(pattern)

                if not params:
                    output = json.dumps({"category": category, "operation": operation})
                    # Add casual variations
                    for varied in add_casual_variations(pattern):
                        examples.append(
                            {
                                "messages": [
                                    {"role": "user", "content": varied},
                                    {"role": "assistant", "content": output},
                                ]
                            }
                        )
                else:
                    param_values = {}
                    for param in params:
                        if param in sample_values:
                            param_values[param] = sample_values[param]
                        elif param == "app":
                            param_values[param] = sample_values.get("apps", ["app"])
                        elif param == "package":
                            param_values[param] = sample_values.get(
                                "packages", ["package"]
                            )
                        elif param == "branch":
                            param_values[param] = sample_values.get(
                                "branches", ["main"]
                            )
                        elif param == "container":
                            param_values[param] = sample_values.get(
                                "containers", ["container"]
                            )
                        elif param == "host":
                            param_values[param] = sample_values.get(
                                "hosts", ["localhost"]
                            )
                        elif param == "level":
                            param_values[param] = sample_values.get("levels", ["50"])
                        elif param == "port":
                            param_values[param] = sample_values.get("ports", ["3000"])
                        elif param == "file":
                            param_values[param] = [
                                "app.py",
                                "index.js",
                                "main.go",
                                "server.ts",
                                "config.json",
                            ]
                        elif param == "message":
                            param_values[param] = [
                                "fix bug",
                                "add feature",
                                "update readme",
                                "initial commit",
                                "wip",
                            ]
                        elif param == "url":
                            param_values[param] = [
                                "https://github.com",
                                "https://google.com",
                                "https://example.com",
                            ]
                        elif param == "query":
                            param_values[param] = [
                                "weather",
                                "python tutorial",
                                "react hooks",
                                "docker compose",
                            ]
                        elif param == "pattern":
                            param_values[param] = [
                                "error",
                                "TODO",
                                "function",
                                "import",
                            ]
                        elif param == "name":
                            param_values[param] = ["node", "python", "nginx", "redis"]
                        elif param == "pid":
                            param_values[param] = ["1234", "5678", "9999"]
                        elif param == "path":
                            param_values[param] = [
                                "~/Downloads",
                                "~/Documents",
                                "/tmp",
                                ".",
                            ]
                        elif param == "script":
                            param_values[param] = [
                                "dev",
                                "build",
                                "test",
                                "lint",
                                "start",
                            ]
                        elif param == "service":
                            param_values[param] = [
                                "mysql",
                                "postgresql",
                                "redis",
                                "nginx",
                                "mongodb",
                            ]
                        elif param == "domain":
                            param_values[param] = sample_values.get(
                                "domains", ["example.com"]
                            )
                        elif param == "mode":
                            param_values[param] = sample_values.get("modes", ["755"])
                        elif param == "user":
                            param_values[param] = sample_values.get("users", ["root"])
                        elif param == "disk":
                            param_values[param] = sample_values.get("disks", ["disk0"])
                        elif param == "command":
                            param_values[param] = sample_values.get("commands", ["ls"])
                        elif param == "output":
                            param_values[param] = [
                                "archive",
                                "backup",
                                "output",
                                "files",
                            ]
                        elif param == "input":
                            param_values[param] = ["src", "data", "folder", "project"]
                        elif param == "source":
                            param_values[param] = [
                                "file.txt",
                                "data.json",
                                "folder",
                                "README.md",
                            ]
                        elif param == "dest":
                            param_values[param] = [
                                "backup",
                                "archive",
                                "new_folder",
                                "destination",
                            ]
                        elif param == "file1":
                            param_values[param] = ["file1.txt", "old.json", "before.md"]
                        elif param == "file2":
                            param_values[param] = ["file2.txt", "new.json", "after.md"]
                        elif param == "text":
                            param_values[param] = [
                                "hello world",
                                "test message",
                                "example text",
                            ]
                        elif param == "device":
                            param_values[param] = [
                                "MacBook Pro",
                                "AirPods",
                                "External Speakers",
                                "Built-in Microphone",
                            ]
                        elif param == "image":
                            param_values[param] = [
                                "nginx",
                                "ubuntu",
                                "redis",
                                "postgres",
                            ]
                        elif param == "tag":
                            param_values[param] = ["latest", "v1.0", "dev", "prod"]
                        elif param == "project":
                            param_values[param] = ["myapp", "project", "test", "demo"]
                        elif param == "module":
                            param_values[param] = [
                                "github.com/user/project",
                                "my-module",
                            ]
                        elif param == "var":
                            param_values[param] = ["PATH", "HOME", "USER"]
                        elif param == "value":
                            param_values[param] = [
                                "/usr/local/bin",
                                "/Users/me",
                                "true",
                            ]
                        elif param == "lines":
                            param_values[param] = ["10", "20", "50", "100"]
                        elif param == "find":
                            param_values[param] = ["old", "error", "TODO"]
                        elif param == "replace":
                            param_values[param] = ["new", "fixed", "DONE"]
                        elif param == "group":
                            param_values[param] = ["admin", "staff", "wheel"]
                        elif param == "seconds":
                            param_values[param] = ["5", "10", "60"]
                        elif param == "interval":
                            param_values[param] = ["1", "2", "5"]
                        elif param == "id":
                            param_values[param] = ["123456789", "987654321"]
                        else:
                            param_values[param] = [f"example_{param}"]

                    # Generate examples with all parameter combinations
                    first_param = params[0]
                    for value in param_values.get(first_param, ["example"])[
                        :10
                    ]:  # Limit combinations
                        filled_pattern = pattern
                        output_params = {}

                        for param in params:
                            if param == first_param:
                                param_val = value
                            else:
                                vals = param_values.get(param, ["example"])
                                param_val = random.choice(vals)

                            filled_pattern = filled_pattern.replace(
                                f"{{{param}}}", str(param_val)
                            )
                            output_params[param] = param_val

                        output = json.dumps(
                            {
                                "category": category,
                                "operation": operation,
                                **output_params,
                            }
                        )

                        # Add casual variations
                        for varied in add_casual_variations(filled_pattern)[:2]:
                            examples.append(
                                {
                                    "messages": [
                                        {"role": "user", "content": varied},
                                        {"role": "assistant", "content": output},
                                    ]
                                }
                            )

    print(f"Generated {len(examples)} base examples")

    # Add semantic fallback examples
    print("Generating semantic fallback examples...")
    examples.extend(generate_semantic_fallback_examples())
    print(f"Total after semantic: {len(examples)}")

    # Add confusing/distinguishing examples
    print("Generating distinguishing examples...")
    examples.extend(generate_confusing_examples())
    print(f"Total after distinguishing: {len(examples)}")

    # Add typo examples
    print("Generating typo examples...")
    examples.extend(generate_typo_examples(sample_values))
    print(f"Total after typos: {len(examples)}")

    # Add contextual examples
    print("Generating contextual examples...")
    examples.extend(generate_contextual_examples())
    print(f"Total after contextual: {len(examples)}")

    # Critical patterns - over-represent important commands
    print("Boosting critical patterns...")
    critical_patterns = [
        ("apps", "open", "open {app}", "chrome"),
        ("apps", "open", "launch {app}", "safari"),
        ("apps", "quit", "quit {app}", "chrome"),
        ("volume", "mute", "mute", None),
        ("volume", "unmute", "unmute", None),
        ("volume", "up", "volume up", None),
        ("volume", "down", "volume down", None),
        ("volume", "set", "volume {level}", "50"),
        ("keyboard", "copy", "copy", None),
        ("keyboard", "paste", "paste", None),
        ("keyboard", "undo", "undo", None),
        ("keyboard", "save", "save", None),
        ("window", "close", "close window", None),
        ("window", "minimize", "minimize", None),
        ("media", "play", "play", None),
        ("media", "pause", "pause", None),
        ("media", "next", "next", None),
        ("display", "screenshot", "screenshot", None),
        ("display", "lock", "lock screen", None),
        ("system", "sleep", "sleep", None),
        ("system", "restart", "restart", None),
        ("system", "shutdown", "shutdown", None),
        ("network", "wifi_on", "wifi on", None),
        ("network", "wifi_off", "wifi off", None),
        ("git", "status", "git status", None),
        ("git", "add_all", "git add all", None),
        ("git", "commit", "commit {message}", "update"),
        ("git", "fetch", "git fetch", None),
        ("git", "branch", "git branch", None),
        ("git", "push", "push", None),
        ("git", "push", "git push", None),
        ("git", "pull", "git pull", None),
        ("docker", "ps", "docker ps", None),
        ("npm", "install", "npm install", None),
        ("keyboard", "undo", "und", None),
    ]

    for _ in range(5):  # Boost 5x
        for category, operation, phrase_template, param in critical_patterns:
            if param:
                phrase = (
                    phrase_template.replace("{app}", param)
                    .replace("{level}", param)
                    .replace("{message}", param)
                )
                output = json.dumps(
                    {
                        "category": category,
                        "operation": operation,
                        "app"
                        if "{app}" in phrase_template
                        else "level"
                        if "{level}" in phrase_template
                        else "message": param,
                    }
                )
            else:
                phrase = phrase_template
                output = json.dumps({"category": category, "operation": operation})

            examples.append(
                {
                    "messages": [
                        {"role": "user", "content": phrase},
                        {"role": "assistant", "content": output},
                    ]
                }
            )

    print(f"Total after critical boost: {len(examples)}")

    return examples


def main():
    print("Loading config from macos_operations.json...")
    config = load_config()

    # Ensure dataset generation is deterministic across runs.
    random.seed(42)

    print("Generating comprehensive dataset with robustness features...")
    examples = generate_examples(config)

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

    # Generate semantic keywords file for runtime fallback
    with open("semantic_keywords.json", "w") as f:
        json.dump(SEMANTIC_KEYWORDS, f, indent=2)

    # Generate typo patterns file
    with open("typo_patterns.json", "w") as f:
        json.dump(TYPO_PATTERNS, f, indent=2)

    categories = config.get("nlp_patterns", {})
    total_operations = sum(len(ops) for ops in categories.values())

    print(f"\n{'=' * 60}")
    print(f"Dataset Generation Complete!")
    print(f"{'=' * 60}")
    print(f"Training examples: {len(train_examples)}")
    print(f"Validation examples: {len(valid_examples)}")
    print(f"Total examples: {len(examples)}")
    print(f"Categories: {len(categories)}")
    print(f"Operations: {total_operations}")
    print(f"\nRobustness features:")
    print(f"  - Typo tolerance: {len(TYPO_PATTERNS)} common typos")
    print(f"  - Casual speech variations")
    print(f"  - Semantic fallback keywords: {len(SEMANTIC_KEYWORDS)} categories")
    print(f"  - Context-aware examples")
    print(f"\nGenerated files:")
    print(f"  - train.jsonl")
    print(f"  - valid.jsonl")
    print(f"  - semantic_keywords.json")
    print(f"  - typo_patterns.json")
    print(f"\nNext steps:")
    print(f"  1. Review the generated files")
    print(
        f"  2. Train: mlx_lm.lora --model ./qwen-base --data . --train --iters 2500 --batch-size 4 --num-layers 12"
    )
    print(f"  3. Test with: python whispera.py 'your command'")


if __name__ == "__main__":
    main()
