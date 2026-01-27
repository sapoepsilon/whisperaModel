#!/usr/bin/env python3
"""
Test script for the pattern-based voice command model.
Validates that the model outputs correct JSON for given inputs.
"""

import subprocess
import json
import sys
from dataclasses import dataclass


@dataclass
class TestCase:
    input: str
    expected_json: dict
    description: str


TEST_CASES = [
    # Open app - tests pattern extraction
    TestCase(
        input="open safari",
        expected_json={"action": "open_app", "target": "safari"},
        description="Open app - Safari"
    ),
    TestCase(
        input="launch terminal",
        expected_json={"action": "open_app", "target": "terminal"},
        description="Open app - Terminal"
    ),
    TestCase(
        input="open vscode",
        expected_json={"action": "open_app", "target": "vscode"},
        description="Open app - VS Code"
    ),
    # Quit app
    TestCase(
        input="quit chrome",
        expected_json={"action": "quit_app", "target": "chrome"},
        description="Quit app - Chrome"
    ),
    # Volume
    TestCase(
        input="volume up",
        expected_json={"action": "volume", "direction": "up"},
        description="Volume up"
    ),
    TestCase(
        input="mute",
        expected_json={"action": "volume", "direction": "mute"},
        description="Mute volume"
    ),
    # Screenshot
    TestCase(
        input="take a screenshot",
        expected_json={"action": "screenshot"},
        description="Screenshot"
    ),
    # Folder
    TestCase(
        input="open downloads",
        expected_json={"action": "open_folder", "folder": "downloads"},
        description="Open folder - Downloads"
    ),
    # Web search
    TestCase(
        input="search for weather",
        expected_json={"action": "web_search", "query": "weather"},
        description="Web search"
    ),
    # Open URL
    TestCase(
        input="go to github",
        expected_json={"action": "open_url", "site": "github"},
        description="Open URL - GitHub"
    ),
    # Window management
    TestCase(
        input="close window",
        expected_json={"action": "window", "operation": "close"},
        description="Close window"
    ),
    TestCase(
        input="minimize",
        expected_json={"action": "window", "operation": "minimize"},
        description="Minimize window"
    ),
    TestCase(
        input="full screen",
        expected_json={"action": "window", "operation": "fullscreen"},
        description="Full screen"
    ),
    # System
    TestCase(
        input="sleep",
        expected_json={"action": "system", "operation": "sleep"},
        description="Sleep computer"
    ),
    TestCase(
        input="lock screen",
        expected_json={"action": "system", "operation": "lock"},
        description="Lock screen"
    ),
    TestCase(
        input="empty trash",
        expected_json={"action": "system", "operation": "empty_trash"},
        description="Empty trash"
    ),
    # Media
    TestCase(
        input="play music",
        expected_json={"action": "media", "operation": "play"},
        description="Play music"
    ),
    TestCase(
        input="next track",
        expected_json={"action": "media", "operation": "next"},
        description="Next track"
    ),
    # Keyboard shortcuts
    TestCase(
        input="copy",
        expected_json={"action": "keyboard", "shortcut": "copy"},
        description="Copy"
    ),
    TestCase(
        input="paste",
        expected_json={"action": "keyboard", "shortcut": "paste"},
        description="Paste"
    ),
    TestCase(
        input="undo",
        expected_json={"action": "keyboard", "shortcut": "undo"},
        description="Undo"
    ),
    # Info
    TestCase(
        input="what time is it",
        expected_json={"action": "info", "type": "time"},
        description="Show time"
    ),
    TestCase(
        input="show battery",
        expected_json={"action": "info", "type": "battery"},
        description="Battery status"
    ),
    # Dark mode
    TestCase(
        input="dark mode",
        expected_json={"action": "dark_mode"},
        description="Toggle dark mode"
    ),
    # Test generalization - apps NOT in training set
    TestCase(
        input="open photoshop",
        expected_json={"action": "open_app", "target": "photoshop"},
        description="Open app - Photoshop (not in training)"
    ),
    TestCase(
        input="search for best tacos in austin",
        expected_json={"action": "web_search", "query": "best tacos in austin"},
        description="Web search - novel query"
    ),
]


def run_inference(prompt: str, model_path: str = "./qwen-base", adapter_path: str = "./adapters") -> str:
    """Run model inference and return the output."""
    cmd = [
        "mlx_lm.generate",
        "--model", model_path,
        "--adapter-path", adapter_path,
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


def check_output(output: str, expected_json: dict) -> tuple[bool, str]:
    """Check if output JSON matches expected JSON."""
    try:
        parsed = json.loads(output)

        # Check all expected keys are present and match
        for key, value in expected_json.items():
            if key not in parsed:
                return False, f"Missing key: {key}"
            # Case-insensitive comparison for string values (queries, targets, etc.)
            parsed_val = parsed[key]
            if isinstance(value, str) and isinstance(parsed_val, str):
                if parsed_val.lower() != value.lower():
                    return False, f"Key '{key}': expected '{value}', got '{parsed_val}'"
            elif parsed_val != value:
                return False, f"Key '{key}': expected '{value}', got '{parsed_val}'"

        return True, "OK"
    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}"


def run_tests(model_path: str = "./qwen-base", adapter_path: str = "./adapters", verbose: bool = True):
    """Run all test cases and report results."""
    passed = 0
    failed = 0
    results = []

    print("\n" + "=" * 60)
    print("PATTERN-BASED VOICE COMMAND MODEL TEST SUITE")
    print("=" * 60 + "\n")

    for i, test in enumerate(TEST_CASES, 1):
        print(f"Test {i}/{len(TEST_CASES)}: {test.description}")
        print(f"  Input: \"{test.input}\"")

        try:
            output = run_inference(test.input, model_path, adapter_path)
            success, message = check_output(output, test.expected_json)

            if success:
                passed += 1
                status = "✓ PASS"
            else:
                failed += 1
                status = f"✗ FAIL - {message}"

            if verbose:
                print(f"  Output: {output[:80]}{'...' if len(output) > 80 else ''}")
                print(f"  Expected: {json.dumps(test.expected_json)}")
            print(f"  Status: {status}")

            results.append({
                "test": test.description,
                "input": test.input,
                "output": output,
                "expected": test.expected_json,
                "passed": success
            })

        except Exception as e:
            failed += 1
            print(f"  Status: ✗ ERROR - {str(e)}")
            results.append({
                "test": test.description,
                "input": test.input,
                "output": str(e),
                "expected": test.expected_json,
                "passed": False
            })

        print()

    print("=" * 60)
    print(f"RESULTS: {passed}/{len(TEST_CASES)} passed ({100*passed/len(TEST_CASES):.1f}%)")
    print("=" * 60)

    if failed > 0:
        print("\nFailed tests:")
        for r in results:
            if not r["passed"]:
                print(f"  - {r['test']}: \"{r['input']}\"")
                print(f"    Got: {r['output'][:80]}...")

    with open("test_results.json", "w") as f:
        json.dump({
            "total": len(TEST_CASES),
            "passed": passed,
            "failed": failed,
            "results": results
        }, f, indent=2)

    print("\nDetailed results saved to test_results.json")

    return passed == len(TEST_CASES)


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "./qwen-base"
    adapter = sys.argv[2] if len(sys.argv) > 2 else "./adapters"

    success = run_tests(model, adapter)
    sys.exit(0 if success else 1)
