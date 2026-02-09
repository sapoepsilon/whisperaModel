#!/usr/bin/env python3
"""
Enhanced test suite for Whispera robust voice command model.
Tests pattern matching, typo correction, semantic fallback, and compound commands.
"""

import subprocess
import json
import sys
from dataclasses import dataclass
from typing import Dict, Any, Optional
import os
import shutil


@dataclass
class TestCase:
    input: str
    expected_category: str
    expected_operation: str
    expected_params: Dict[str, Any]
    description: str
    test_type: str = "basic"  # basic, typo, casual, compound, edge


# Comprehensive test cases covering robustness features
TEST_CASES = [
    # === BASIC COMMANDS (should work with original model) ===
    TestCase(
        "open safari", "apps", "open", {"app": "safari"}, "Open app - Safari", "basic"
    ),
    TestCase(
        "open chrome", "apps", "open", {"app": "chrome"}, "Open app - Chrome", "basic"
    ),
    TestCase(
        "launch terminal",
        "apps",
        "open",
        {"app": "terminal"},
        "Open app - Terminal (launch)",
        "basic",
    ),
    TestCase(
        "start vscode",
        "apps",
        "open",
        {"app": "vscode"},
        "Open app - VS Code (start)",
        "basic",
    ),
    TestCase(
        "quit chrome", "apps", "quit", {"app": "chrome"}, "Quit app - Chrome", "basic"
    ),
    TestCase(
        "close safari",
        "apps",
        "quit",
        {"app": "safari"},
        "Quit app - Safari (close)",
        "basic",
    ),
    # Volume commands
    TestCase("volume up", "volume", "up", {}, "Volume up", "basic"),
    TestCase("volume down", "volume", "down", {}, "Volume down", "basic"),
    TestCase("mute", "volume", "mute", {}, "Mute", "basic"),
    TestCase("unmute", "volume", "unmute", {}, "Unmute", "basic"),
    TestCase(
        "set volume to 50", "volume", "set", {"level": "50"}, "Set volume 50%", "basic"
    ),
    TestCase(
        "volume 75", "volume", "set", {"level": "75"}, "Volume 75% shorthand", "basic"
    ),
    # System commands
    TestCase("sleep", "system", "sleep", {}, "Sleep computer", "basic"),
    TestCase("restart", "system", "restart", {}, "Restart computer", "basic"),
    TestCase("shutdown", "system", "shutdown", {}, "Shutdown computer", "basic"),
    TestCase("empty trash", "system", "empty_trash", {}, "Empty trash", "basic"),
    TestCase("lock screen", "display", "lock", {}, "Lock screen", "basic"),
    # Display
    TestCase("screenshot", "display", "screenshot", {}, "Screenshot", "basic"),
    # Keyboard
    TestCase("copy", "keyboard", "copy", {}, "Copy", "basic"),
    TestCase("paste", "keyboard", "paste", {}, "Paste", "basic"),
    TestCase("undo", "keyboard", "undo", {}, "Undo", "basic"),
    TestCase("save", "keyboard", "save", {}, "Save", "basic"),
    # Window management
    TestCase("close window", "window", "close", {}, "Close window", "basic"),
    TestCase("minimize", "window", "minimize", {}, "Minimize window", "basic"),
    TestCase("fullscreen", "window", "fullscreen", {}, "Fullscreen", "basic"),
    # Media
    TestCase("play", "media", "play", {}, "Play media", "basic"),
    TestCase("pause", "media", "pause", {}, "Pause media", "basic"),
    TestCase("next", "media", "next", {}, "Next track", "basic"),
    TestCase("previous", "media", "previous", {}, "Previous track", "basic"),
    # Info
    TestCase("what time is it", "info", "time", {}, "Show time", "basic"),
    TestCase("show date", "info", "date", {}, "Show date", "basic"),
    # === TYPO TESTS (new robustness feature) ===
    TestCase(
        "opn chrome", "apps", "open", {"app": "chrome"}, "Typo: opn chrome", "typo"
    ),
    TestCase(
        "oepn safari", "apps", "open", {"app": "safari"}, "Typo: oepn safari", "typo"
    ),
    TestCase(
        "chrme", "apps", "open", {"app": "chrome"}, "Typo: chrme (app name)", "typo"
    ),
    TestCase(
        "termial",
        "apps",
        "open",
        {"app": "terminal"},
        "Typo: termial (app name)",
        "typo",
    ),
    TestCase("volme up", "volume", "up", {}, "Typo: volme up", "typo"),
    TestCase("screnshot", "display", "screenshot", {}, "Typo: screnshot", "typo"),
    TestCase("mut", "volume", "mute", {}, "Typo: mut", "typo"),
    TestCase(
        "mutee",
        "volume",
        "mute",
        {},
        "Typo: mutee",
        "typo",
    ),
    TestCase("cop", "keyboard", "copy", {}, "Typo: cop", "typo"),
    TestCase("pst", "keyboard", "paste", {}, "Typo: pst", "typo"),
    TestCase("und", "keyboard", "undo", {}, "Typo: und", "typo"),
    TestCase("sllep", "system", "sleep", {}, "Typo: sllep", "typo"),
    TestCase("restar", "system", "restart", {}, "Typo: restar", "typo"),
    # === CASUAL SPEECH TESTS (new robustness feature) ===
    TestCase(
        "hey open chrome",
        "apps",
        "open",
        {"app": "chrome"},
        "Casual: hey open chrome",
        "casual",
    ),
    TestCase("yo volume up", "volume", "up", {}, "Casual: yo volume up", "casual"),
    TestCase("please mute", "volume", "mute", {}, "Casual: please mute", "casual"),
    TestCase(
        "can you open safari",
        "apps",
        "open",
        {"app": "safari"},
        "Casual: can you open safari",
        "casual",
    ),
    TestCase(
        "make it louder", "volume", "up", {}, "Semantic: make it louder", "casual"
    ),
    TestCase(
        "make it quieter", "volume", "down", {}, "Semantic: make it quieter", "casual"
    ),
    TestCase("shut up", "volume", "mute", {}, "Semantic: shut up", "casual"),
    TestCase(
        "turn off sound", "volume", "mute", {}, "Semantic: turn off sound", "casual"
    ),
    TestCase(
        "dim the screen", "brightness", "down", {}, "Semantic: dim the screen", "casual"
    ),
    # === GIT COMMANDS ===
    TestCase("git status", "git", "status", {}, "Git status", "basic"),
    TestCase("git fetch", "git", "fetch", {}, "Git fetch", "basic"),
    TestCase("git branch", "git", "branch", {}, "Git branch", "basic"),
    TestCase(
        "merge main",
        "git",
        "merge",
        {"branch": "main"},
        "Git merge main",
        "basic",
    ),
    TestCase(
        "commit changes", "git", "commit", {"message": "update"}, "Git commit", "basic"
    ),
    TestCase("push", "git", "push", {}, "Git push", "basic"),
    TestCase("pull", "git", "pull", {}, "Git pull", "basic"),
    # === DOCKER COMMANDS ===
    TestCase("docker ps", "docker", "ps", {}, "Docker ps", "basic"),
    TestCase(
        "docker stop container",
        "docker",
        "stop",
        {"container": "container"},
        "Docker stop",
        "basic",
    ),
    # === NPM COMMANDS ===
    TestCase("npm install", "npm", "install", {}, "NPM install", "basic"),
    TestCase("npm start", "npm", "start", {}, "NPM start", "basic"),
    TestCase("npm test", "npm", "test", {}, "NPM test", "basic"),
    # === NETWORK COMMANDS ===
    TestCase("wifi on", "network", "wifi_on", {}, "WiFi on", "basic"),
    TestCase("wifi off", "network", "wifi_off", {}, "WiFi off", "basic"),
    # === AUDIO COMMANDS ===
    TestCase(
        "list audio devices",
        "audio",
        "list_devices",
        {},
        "Audio: list devices",
        "basic",
    ),
    TestCase(
        "switch output to AirPods",
        "audio",
        "switch_output",
        {"device": "AirPods"},
        "Audio: switch output",
        "basic",
    ),
    # === EDGE CASES ===
    TestCase(
        "open photoshop",
        "apps",
        "open",
        {"app": "photoshop"},
        "Edge: App not in training",
        "edge",
    ),
    TestCase(
        "start unknownapp",
        "apps",
        "open",
        {"app": "unknownapp"},
        "Edge: Unknown app",
        "edge",
    ),
    TestCase(
        "git comit",
        "git",
        "commit",
        {"message": "update"},
        "Edge: Typo in command",
        "edge",
    ),
]


def _resolve_mlx_generate() -> str:
    """Resolve mlx_lm.generate binary path.

    Some environments run tests without activating the venv, so PATH may not include
    mlx_lm.generate.
    """

    direct = shutil.which("mlx_lm.generate")
    if direct:
        return direct

    here = os.path.dirname(os.path.abspath(__file__))
    candidate = os.path.join(here, "venv", "bin", "mlx_lm.generate")
    if os.path.exists(candidate):
        return candidate

    return "mlx_lm.generate"


def run_model(
    prompt: str, model_path: str = "./qwen-base", adapter_path: str = "./adapters"
) -> tuple[str, float]:
    """Run model inference and return the output."""
    cmd = [
        _resolve_mlx_generate(),
        "--model",
        model_path,
        "--adapter-path",
        adapter_path,
        "--prompt",
        prompt,
        "--max-tokens",
        "100",
        "--temp",
        "0.1",
    ]

    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout

    lines = output.strip().split("\n")
    for i, line in enumerate(lines):
        if line.startswith("="):
            if i + 1 < len(lines):
                command_lines = []
                for j in range(i + 1, len(lines)):
                    if lines[j].startswith("="):
                        break
                    command_lines.append(lines[j])
                return "\n".join(command_lines).strip(), 0.8

    return output.strip(), 0.5


def check_output(output: str, test: TestCase) -> tuple[bool, str, dict]:
    """Check if output JSON matches expected values."""
    try:
        parsed = json.loads(output)

        # Check category
        if parsed.get("category") != test.expected_category:
            return (
                False,
                f"Wrong category: expected '{test.expected_category}', got '{parsed.get('category')}'",
                parsed,
            )

        # Check operation
        if parsed.get("operation") != test.expected_operation:
            return (
                False,
                f"Wrong operation: expected '{test.expected_operation}', got '{parsed.get('operation')}'",
                parsed,
            )

        # Check parameters
        for key, value in test.expected_params.items():
            if key not in parsed:
                return False, f"Missing param: {key}", parsed
            parsed_val = parsed[key]
            if isinstance(value, str) and isinstance(parsed_val, str):
                if parsed_val.lower() != value.lower():
                    return (
                        False,
                        f"Param '{key}': expected '{value}', got '{parsed_val}'",
                        parsed,
                    )
            elif parsed_val != value:
                return (
                    False,
                    f"Param '{key}': expected '{value}', got '{parsed_val}'",
                    parsed,
                )

        return True, "OK", parsed

    except json.JSONDecodeError as e:
        return False, f"Invalid JSON: {e}", {}


def run_tests(
    model_path: str = "./qwen-base",
    adapter_path: str = "./adapters",
    verbose: bool = True,
):
    """Run all test cases and report results."""
    passed = 0
    failed = 0
    results = []

    # Group by test type
    type_stats = {
        "basic": {"passed": 0, "total": 0},
        "typo": {"passed": 0, "total": 0},
        "casual": {"passed": 0, "total": 0},
        "compound": {"passed": 0, "total": 0},
        "edge": {"passed": 0, "total": 0},
    }

    print("\n" + "=" * 70)
    print("WHISPERA ROBUST VOICE COMMAND MODEL TEST SUITE")
    print("=" * 70)
    print(f"Testing {len(TEST_CASES)} cases across 5 categories")
    print("=" * 70 + "\n")

    for i, test in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] {test.description}")
        print(f'      Input: "{test.input}"')

        try:
            output, confidence = run_model(test.input, model_path, adapter_path)
            success, message, parsed = check_output(output, test)

            type_stats[test.test_type]["total"] += 1

            if success:
                passed += 1
                type_stats[test.test_type]["passed"] += 1
                status = "✓ PASS"
            else:
                failed += 1
                status = f"✗ FAIL - {message}"

            if verbose:
                output_display = output[:60] + "..." if len(output) > 60 else output
                print(f"      Output: {output_display}")
                if parsed:
                    print(
                        f"      Parsed: category={parsed.get('category')}, operation={parsed.get('operation')}"
                    )
            print(f"      Status: {status}")

            results.append(
                {
                    "test": test.description,
                    "input": test.input,
                    "type": test.test_type,
                    "output": output,
                    "parsed": parsed,
                    "expected": {
                        "category": test.expected_category,
                        "operation": test.expected_operation,
                        "params": test.expected_params,
                    },
                    "passed": success,
                    "message": message,
                }
            )

        except Exception as e:
            failed += 1
            type_stats[test.test_type]["total"] += 1
            print(f"      Status: ✗ ERROR - {str(e)}")
            results.append(
                {
                    "test": test.description,
                    "input": test.input,
                    "type": test.test_type,
                    "output": str(e),
                    "parsed": {},
                    "passed": False,
                    "message": str(e),
                }
            )

        print()

    # Print summary by type
    print("=" * 70)
    print("RESULTS BY CATEGORY")
    print("=" * 70)
    for test_type, stats in type_stats.items():
        if stats["total"] > 0:
            pct = 100 * stats["passed"] / stats["total"]
            status = "✓" if stats["passed"] == stats["total"] else "⚠"
            print(
                f"{status} {test_type.upper():12} {stats['passed']:3}/{stats['total']:<3} ({pct:5.1f}%)"
            )

    print("=" * 70)
    print(
        f"OVERALL: {passed}/{len(TEST_CASES)} passed ({100 * passed / len(TEST_CASES):.1f}%)"
    )
    print("=" * 70)

    if failed > 0:
        print("\nFAILED TESTS:")
        print("-" * 70)
        for r in results:
            if not r["passed"]:
                print(f"\n  ✗ {r['test']} [{r['type']}]")
                print(f'    Input: "{r["input"]}"')
                print(f"    Got: {r['output'][:80]}")
                print(f"    Error: {r['message']}")
        print()

    # Save results
    with open("test_results.json", "w") as f:
        json.dump(
            {
                "total": len(TEST_CASES),
                "passed": passed,
                "failed": failed,
                "by_type": type_stats,
                "results": results,
            },
            f,
            indent=2,
        )

    print("Detailed results saved to test_results.json\n")

    return passed == len(TEST_CASES)


if __name__ == "__main__":
    model = sys.argv[1] if len(sys.argv) > 1 else "./qwen-base"
    adapter = sys.argv[2] if len(sys.argv) > 2 else "./adapters"

    success = run_tests(model, adapter)
    sys.exit(0 if success else 1)
