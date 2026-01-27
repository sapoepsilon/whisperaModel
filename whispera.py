#!/usr/bin/env python3
"""
Whispera CLI - Config-driven natural language to bash commands.

Usage:
    python whispera.py "open chrome"
    python whispera.py --execute "open chrome"
    python whispera.py -i  # interactive mode
"""

import subprocess
import json
import sys
import os
import re

SCRIPT_DIR = os.path.dirname(__file__)
OPERATIONS_CONFIG = os.path.join(SCRIPT_DIR, "macos_operations.json")
APP_CONFIG_PATH = os.path.join(SCRIPT_DIR, "whispera_config.json")
MODEL_PATH = os.path.join(SCRIPT_DIR, "qwen-base")
ADAPTER_PATH = os.path.join(SCRIPT_DIR, "adapters")


def load_operations_config():
    """Load the operations config with command templates."""
    with open(OPERATIONS_CONFIG) as f:
        return json.load(f)


def load_app_config():
    """Load the app mappings config (for app name lookups)."""
    if os.path.exists(APP_CONFIG_PATH):
        with open(APP_CONFIG_PATH) as f:
            return json.load(f)
    return {"apps": {}, "folders": {}, "urls": {}}


def run_model(prompt: str) -> str:
    """Run the fine-tuned model and get JSON output."""
    cmd = [
        "mlx_lm.generate",
        "--model", MODEL_PATH,
        "--adapter-path", ADAPTER_PATH,
        "--prompt", prompt,
        "--max-tokens", "100",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout

    lines = output.strip().split('\n')
    for i, line in enumerate(lines):
        if line.startswith('='):
            if i + 1 < len(lines):
                command_lines = []
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith('='):
                        break
                    command_lines.append(lines[j])
                return '\n'.join(command_lines).strip()

    return output.strip()


def transform_param(param_name: str, value: str, app_config: dict) -> str:
    """Transform parameter values (e.g., app name lookups, level normalization)."""
    if param_name == "app":
        return app_config.get("apps", {}).get(value.lower(), value.title())

    if param_name == "level":
        level_str = str(value).replace("%", "").strip().lower()
        if level_str == "half":
            return "50"
        elif level_str in ("max", "maximum", "full"):
            return "100"
        elif level_str in ("min", "minimum"):
            return "0"
        try:
            level_int = int(level_str)
            return str(max(0, min(100, level_int)))
        except ValueError:
            return "50"

    if param_name == "folder":
        return app_config.get("folders", {}).get(value.lower(), f"~/{value}")

    return value


def json_to_bash(action_json: dict, ops_config: dict, app_config: dict) -> str:
    """Convert model JSON output to executable bash command using config templates."""
    category = action_json.get("category", "")
    operation = action_json.get("operation", "")

    categories = ops_config.get("categories", {})
    if category not in categories:
        return f"# Unknown category: {category}"

    cat_operations = categories[category]
    if operation not in cat_operations:
        return f"# Unknown operation: {operation} in category {category}"

    template = cat_operations[operation]

    params = re.findall(r'\{(\w+)\}', template)
    result = template

    for param in params:
        if param in action_json:
            value = transform_param(param, str(action_json[param]), app_config)
            result = result.replace(f"{{{param}}}", value)
        else:
            result = result.replace(f"{{{param}}}", f"<missing:{param}>")

    return result


def process(input_text: str, execute: bool = False, verbose: bool = False) -> str:
    """Process natural language input and return/execute bash command."""
    ops_config = load_operations_config()
    app_config = load_app_config()

    if verbose:
        print(f"Input: {input_text}", file=sys.stderr)

    model_output = run_model(input_text)

    if verbose:
        print(f"Model output: {model_output}", file=sys.stderr)

    try:
        action_json = json.loads(model_output)
    except json.JSONDecodeError:
        return f"# Error: Could not parse model output: {model_output}"

    bash_command = json_to_bash(action_json, ops_config, app_config)

    if execute:
        if verbose:
            print(f"Executing: {bash_command}", file=sys.stderr)
        os.system(bash_command)

    return bash_command


def interactive_mode():
    """Run in interactive mode."""
    print("Whispera CLI - Type commands or 'quit' to exit")
    print("Prefix with '!' to execute immediately\n")

    ops_config = load_operations_config()
    app_config = load_app_config()

    while True:
        try:
            user_input = input(">>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["quit", "exit", "q"]:
            print("Bye!")
            break

        execute = user_input.startswith("!")
        if execute:
            user_input = user_input[1:].strip()

        bash_cmd = process(user_input, execute=execute)
        if not execute:
            print(bash_cmd)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert natural language to bash commands (config-driven)"
    )
    parser.add_argument("command", nargs="?", help="Natural language command")
    parser.add_argument("-x", "--execute", action="store_true", help="Execute the command")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument("-i", "--interactive", action="store_true", help="Interactive mode")

    args = parser.parse_args()

    if args.interactive or not args.command:
        interactive_mode()
    else:
        result = process(args.command, execute=args.execute, verbose=args.verbose)
        print(result)


if __name__ == "__main__":
    main()
