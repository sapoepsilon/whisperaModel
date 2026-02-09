#!/usr/bin/env python3
"""
Whispera CLI - Enhanced config-driven natural language to bash commands.
Includes fuzzy matching, semantic fallback, confidence scoring, typo correction,
and compound command support.

Usage:
    python whispera.py "open chrome"
    python whispera.py --execute "open chrome"
    python whispera.py -i  # interactive mode
    python whispera.py --confidence-threshold 0.6 "some command"
"""

import subprocess
import json
import sys
import os
import re
from difflib import get_close_matches, SequenceMatcher
from typing import Dict, List, Tuple, Optional, Any

SCRIPT_DIR = os.path.dirname(__file__)
OPERATIONS_CONFIG = os.path.join(SCRIPT_DIR, "macos_operations.json")
APP_CONFIG_PATH = os.path.join(SCRIPT_DIR, "whispera_config.json")
CORRECTIONS_PATH = os.path.join(SCRIPT_DIR, "corrections.json")
SEMANTIC_KEYWORDS_PATH = os.path.join(SCRIPT_DIR, "semantic_keywords.json")
TYPO_PATTERNS_PATH = os.path.join(SCRIPT_DIR, "typo_patterns.json")
MODEL_PATH = os.path.join(SCRIPT_DIR, "qwen-base")
ADAPTER_PATH = os.path.join(SCRIPT_DIR, "adapters")


# Context tracking for ambiguous commands
class SessionContext:
    """Track conversation context for resolving ambiguous commands."""

    def __init__(self):
        self.last_category: Optional[str] = None
        self.last_operation: Optional[str] = None
        self.last_params: Dict[str, Any] = {}
        self.command_history: List[str] = []

    def update(self, category: str, operation: str, params: Dict):
        self.last_category = category
        self.last_operation = operation
        self.last_params = params
        self.command_history.append(f"{category}.{operation}")
        if len(self.command_history) > 10:
            self.command_history.pop(0)

    def get_likely_category(self) -> Optional[str]:
        if not self.command_history:
            return None
        # Return most common recent category
        categories = [cmd.split(".")[0] for cmd in self.command_history[-3:]]
        return max(set(categories), key=categories.count) if categories else None


# Global session context
session = SessionContext()


def load_operations_config() -> dict:
    """Load the operations config with command templates."""
    with open(OPERATIONS_CONFIG) as f:
        return json.load(f)


def load_app_config() -> dict:
    """Load the app mappings config (for app name lookups)."""
    if os.path.exists(APP_CONFIG_PATH):
        with open(APP_CONFIG_PATH) as f:
            return json.load(f)
    return {"apps": {}, "folders": {}, "urls": {}}


def load_corrections() -> dict:
    """Load learned corrections from previous failures."""
    if os.path.exists(CORRECTIONS_PATH):
        with open(CORRECTIONS_PATH) as f:
            return json.load(f)
    return {
        "mappings": {},
        "common_failures": {},
        "stats": {"total": 0, "corrected": 0},
    }


def save_corrections(corrections: dict):
    """Save corrections to file."""
    with open(CORRECTIONS_PATH, "w") as f:
        json.dump(corrections, f, indent=2)


def load_semantic_keywords() -> dict:
    """Load semantic keyword mappings."""
    if os.path.exists(SEMANTIC_KEYWORDS_PATH):
        with open(SEMANTIC_KEYWORDS_PATH) as f:
            return json.load(f)
    return {}


def load_typo_patterns() -> dict:
    """Load common typo patterns."""
    if os.path.exists(TYPO_PATTERNS_PATH):
        with open(TYPO_PATTERNS_PATH) as f:
            return json.load(f)
    return {}


def correct_typos(input_text: str, typo_patterns: dict) -> str:
    """Correct common typos in input."""
    words = input_text.split()
    corrected = []

    for word in words:
        word_lower = word.lower()
        # Check if this word is a known typo
        for correct, typos in typo_patterns.items():
            if word_lower in [t.lower() for t in typos]:
                # Preserve capitalization
                if word[0].isupper():
                    corrected.append(correct.capitalize())
                else:
                    corrected.append(correct)
                break
        else:
            corrected.append(word)

    return " ".join(corrected)


def expand_single_token_intents(
    input_text: str, app_config: dict, typo_patterns: dict
) -> str:
    """Expand single-token inputs into more explicit intents.

    Voice input often arrives as a single word (app name or a shortened command).
    Making intent explicit reduces drift into unrelated categories.
    """

    parts = input_text.strip().split()
    if len(parts) != 1:
        return input_text

    token = parts[0]
    token_lower = token.lower()

    # App name alone => open app
    apps = app_config.get("apps", {})
    if token_lower in apps:
        return f"open {token_lower}"

    # Known app typos => open corrected app
    for correct, typos in (typo_patterns or {}).items():
        if correct in apps and token_lower in {t.lower() for t in typos}:
            return f"open {correct}"

    # Common action typos that should remain single intent
    if token_lower in ("mute", "unmute"):
        return token_lower

    return input_text


def fuzzy_match_app(app_name: str, app_config: dict) -> str:
    """Fuzzy match app name against known apps."""
    apps = app_config.get("apps", {})
    if not apps:
        return app_name

    app_lower = app_name.lower()

    # Direct match
    if app_lower in apps:
        return apps[app_lower]

    # Check for partial matches
    for known, full_name in apps.items():
        if app_lower in known or known in app_lower:
            return full_name

    # Fuzzy matching
    matches = get_close_matches(app_lower, apps.keys(), n=1, cutoff=0.6)
    if matches:
        return apps[matches[0]]

    return app_name.title()


def semantic_fallback_search(
    input_text: str, ops_config: dict, semantic_keywords: dict
) -> Tuple[Optional[str], Optional[str], dict]:
    """Use semantic keyword matching when exact match fails."""
    input_lower = input_text.lower()
    input_words = set(re.findall(r"\b\w+\b", input_lower))

    best_category = None
    best_score = 0

    # Find best matching category by semantic keywords
    for category, keywords in semantic_keywords.items():
        score = len(input_words & set(keywords))
        if score > best_score:
            best_score = score
            best_category = category

    if not best_category:
        return None, None, {}

    # Now find best operation within that category
    categories = ops_config.get("categories", {})
    if best_category not in categories:
        return best_category, None, {}

    operations = categories[best_category]

    # Check for operation keywords in input
    best_operation = None
    best_op_score = 0

    op_keywords = {
        "open": ["open", "launch", "start", "run", "fire up"],
        "quit": ["quit", "close", "exit", "kill", "stop", "shut down"],
        "up": ["up", "increase", "higher", "louder", "brighter", "raise"],
        "down": ["down", "decrease", "lower", "quieter", "dimmer", "reduce"],
        "mute": ["mute", "silence", "quiet", "shut up", "off"],
        "unmute": ["unmute", "sound on", "audio on"],
        "play": ["play", "resume", "start"],
        "pause": ["pause", "stop"],
        "next": ["next", "skip", "forward"],
        "previous": ["previous", "back", "rewind"],
        "screenshot": ["screenshot", "capture", "screen shot"],
        "sleep": ["sleep", "suspend", "hibernate"],
        "restart": ["restart", "reboot"],
        "shutdown": ["shutdown", "shut down", "power off", "turn off"],
        "copy": ["copy", "duplicate"],
        "paste": ["paste", "insert"],
        "undo": ["undo", "revert"],
        "save": ["save", "store"],
    }

    for operation in operations.keys():
        op_lower = operation.lower()
        keywords = op_keywords.get(op_lower, [op_lower])
        score = sum(1 for kw in keywords if kw in input_lower)
        if score > best_op_score:
            best_op_score = score
            best_operation = operation

    # Extract parameters
    params = {}
    # Look for app names
    apps = list(load_app_config().get("apps", {}).keys())
    for app in apps:
        if app in input_lower:
            params["app"] = app
            break

    # Look for numeric values (volume, brightness)
    numbers = re.findall(r"\b(\d+)(?:\s*%?)?\b", input_text)
    if numbers:
        params["level"] = numbers[0]

    return best_category, best_operation, params


def calculate_confidence(
    model_output: str, action_json: dict, ops_config: dict, input_text: str
) -> float:
    """Calculate confidence score for the prediction."""
    confidence = 1.0

    # Penalize if JSON parsing had issues
    try:
        json.loads(model_output)
    except json.JSONDecodeError:
        confidence -= 0.3

    category = action_json.get("category", "")
    operation = action_json.get("operation", "")

    # Check if category exists
    categories = ops_config.get("categories", {})
    if category not in categories:
        confidence -= 0.4
        # Try fuzzy matching
        cat_matches = get_close_matches(category, categories.keys(), n=1, cutoff=0.6)
        if cat_matches:
            confidence += 0.2

    # Check if operation exists in category
    if category in categories:
        operations = categories[category]
        if operation not in operations:
            confidence -= 0.4
            # Try fuzzy matching
            op_matches = get_close_matches(
                operation, operations.keys(), n=1, cutoff=0.6
            )
            if op_matches:
                confidence += 0.2

    # Check semantic coherence with input
    input_lower = input_text.lower()
    if category.lower() not in input_lower and operation.lower() not in input_lower:
        # Check if any related words exist
        semantic_keywords = load_semantic_keywords()
        if category in semantic_keywords:
            if any(kw in input_lower for kw in semantic_keywords[category]):
                confidence += 0.1

    # Check for missing required parameters
    if category in categories and operation in categories[category]:
        template = categories[category][operation]
        required_params = re.findall(r"\{(\w+)\}", template)
        for param in required_params:
            if param not in action_json:
                confidence -= 0.2

    return max(0.0, min(1.0, confidence))


def find_best_category(cat: str, ops_config: dict) -> str:
    """Find the best matching category in config."""
    categories = ops_config.get("categories", {})
    if cat in categories:
        return cat

    # Try fuzzy matching
    cat_lower = cat.lower()
    for c in categories:
        if cat_lower in c.lower() or c.lower() in cat_lower:
            return c

    # Try close matches
    matches = get_close_matches(cat, categories.keys(), n=1, cutoff=0.6)
    if matches:
        return matches[0]

    return cat


def find_best_operation(op: str, category: str, ops_config: dict) -> str:
    """Find the best matching operation in category."""
    categories = ops_config.get("categories", {})
    if category not in categories:
        return op

    operations = categories[category]
    if op in operations:
        return op

    # Normalize and try matching
    op_lower = op.lower().replace("_", "").replace("-", "")
    for o in operations:
        o_norm = o.lower().replace("_", "").replace("-", "")
        if op_lower == o_norm:
            return o
        if op_lower in o_norm or o_norm in op_lower:
            return o

    # Try close matches
    matches = get_close_matches(op, operations.keys(), n=1, cutoff=0.6)
    if matches:
        return matches[0]

    return op


def resolve_ambiguity(
    input_text: str, possible_categories: List[str], ops_config: dict
) -> str:
    """Resolve ambiguous commands using context."""
    # Use session context
    likely_category = session.get_likely_category()

    if likely_category and likely_category in possible_categories:
        return likely_category

    # Check recent command history
    if session.command_history:
        recent_categories = [cmd.split(".")[0] for cmd in session.command_history[-3:]]
        for cat in recent_categories:
            if cat in possible_categories:
                return cat

    # Default to first option (could be smarter)
    return possible_categories[0]


def parse_compound_command(input_text: str) -> List[dict]:
    """Parse compound commands like 'open chrome and safari'."""
    compounds = []

    # Split by common conjunctions
    parts = re.split(r"\s+(?:and|then|also|plus|after that)\s+", input_text.lower())

    if len(parts) > 1:
        # Extract common verb from first part if present
        first_part = parts[0]
        common_verbs = ["open", "launch", "start", "close", "quit", "kill"]

        verb = None
        for v in common_verbs:
            if v in first_part:
                verb = v
                break

        if verb:
            for part in parts:
                if verb not in part and part.strip():
                    # Prepend the verb to subsequent parts
                    compounds.append(f"{verb} {part.strip()}")
                else:
                    compounds.append(part.strip())
        else:
            compounds = parts

    return (
        [{"type": "command", "text": cmd} for cmd in compounds]
        if len(compounds) > 1
        else []
    )


def run_model(prompt: str) -> Tuple[str, float]:
    """Run the fine-tuned model and get JSON output with confidence."""
    cmd = [
        "mlx_lm.generate",
        "--model",
        MODEL_PATH,
        "--adapter-path",
        ADAPTER_PATH,
        "--prompt",
        prompt,
        "--max-tokens",
        "100",
        "--temp",
        "0.1",  # Lower temperature for more deterministic output
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


def transform_param(param_name: str, value: str, app_config: dict) -> str:
    """Transform parameter values (e.g., app name lookups, level normalization)."""
    if param_name == "app":
        return fuzzy_match_app(value, app_config)

    if param_name == "level":
        level_str = str(value).replace("%", "").strip().lower()
        if level_str == "half":
            return "50"
        elif level_str in ("max", "maximum", "full"):
            return "100"
        elif level_str in ("min", "minimum"):
            return "0"
        elif level_str in ("low", "quiet"):
            return "25"
        elif level_str in ("high", "loud"):
            return "75"
        try:
            level_int = int(level_str)
            return str(max(0, min(100, level_int)))
        except ValueError:
            return "50"

    if param_name == "folder":
        return app_config.get("folders", {}).get(value.lower(), f"~/{value}")

    return value


STOP_WORDS = {
    "a",
    "an",
    "the",
    "to",
    "for",
    "of",
    "in",
    "on",
    "at",
    "by",
    "my",
    "me",
    "i",
    "is",
    "it",
    "and",
    "or",
}


def search_nlp_patterns(
    input_text: str, ops_config: dict
) -> Tuple[Optional[str], Optional[str], dict]:
    """Search config for best matching category/operation and extract params."""
    input_lower = input_text.lower()
    input_words = set(input_lower.split()) - STOP_WORDS

    best_cat, best_op, best_score, best_pattern = None, None, 0, None

    # First: check category + operation names (more reliable)
    categories = ops_config.get("categories", {})
    for category, operations in categories.items():
        cat_words = set(category.replace("_", " ").lower().split()) - STOP_WORDS
        for operation in operations.keys():
            op_words = set(operation.replace("_", " ").lower().split()) - STOP_WORDS
            all_words = op_words | cat_words
            overlap = input_words & all_words
            if overlap:
                cat_match = bool(input_words & cat_words)
                op_match = bool(input_words & op_words)
                bonus = 0.3 if (cat_match and op_match) else 0
                score = len(overlap) / max(len(input_words), len(all_words)) + bonus
                if score > best_score:
                    best_score = score
                    best_cat, best_op, best_pattern = category, operation, None

    # Second: check NLP patterns
    nlp_patterns = ops_config.get("nlp_patterns", {})
    for category, operations in nlp_patterns.items():
        for operation, patterns in operations.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                pattern_base = re.sub(r"\{[^}]+\}", "", pattern_lower).strip()

                if (
                    pattern_base
                    and len(pattern_base) > 3
                    and re.search(r"\b" + re.escape(pattern_base) + r"\b", input_lower)
                ):
                    score = len(pattern_base) / len(input_lower) + 0.5
                    if score > best_score:
                        best_score = score
                        best_cat, best_op, best_pattern = category, operation, pattern

                pattern_words = set(pattern_base.split()) - STOP_WORDS
                overlap = input_words & pattern_words
                if len(overlap) >= 2 or (len(overlap) == 1 and len(pattern_words) == 1):
                    score = len(overlap) / max(len(input_words), len(pattern_words))
                    if score > best_score:
                        best_score = score
                        best_cat, best_op, best_pattern = category, operation, pattern

    # Extract parameters from input using best matching pattern
    params = {}
    if best_pattern:
        param_names = re.findall(r"\{(\w+)\}", best_pattern)
        if param_names:
            pattern_regex = re.escape(best_pattern)
            for param in param_names:
                pattern_regex = pattern_regex.replace(r"\{" + param + r"\}", r"(.+)")
            match = re.search(pattern_regex, input_lower, re.IGNORECASE)
            if match:
                for i, param in enumerate(param_names):
                    if i < len(match.groups()):
                        params[param] = match.group(i + 1).strip()
            else:
                # Fallback: take the last word as the parameter value
                words = input_text.split()
                if words and param_names:
                    params[param_names[-1]] = words[-1]

    return best_cat, best_op, params


def generate_bash_directly(prompt: str) -> str:
    """Fallback: ask base model (without adapters) to generate bash command directly."""
    cmd = [
        "mlx_lm.generate",
        "--model",
        MODEL_PATH,
        "--prompt",
        f"<|im_start|>user\nWhat is the macOS terminal command to: {prompt}? Reply with only the bash command.\n<|im_start|>assistant\n```bash\n",
        "--max-tokens",
        "50",
        "--temp",
        "0.1",
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    output = result.stdout.strip()

    lines = output.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("="):
            for j in range(i + 1, len(lines)):
                l = lines[j].strip()
                if l.startswith("=") or l.startswith("```"):
                    break
                if l and not l.startswith("#"):
                    return l
            break

    return f"# No template for this command. Try adding it to macos_operations.json"


def json_to_bash(
    action_json: dict,
    ops_config: dict,
    app_config: dict,
    original_input: str = "",
    semantic_keywords: dict = None,
) -> Tuple[str, float]:
    """Convert model JSON output to executable bash command using config templates."""
    category = action_json.get("category", "")
    operation = action_json.get("operation", "")

    category = find_best_category(category, ops_config)
    categories = ops_config.get("categories", {})

    extracted_params = {}
    confidence = 1.0

    if category not in categories:
        # Try semantic fallback
        if semantic_keywords:
            found_cat, found_op, extracted_params = semantic_fallback_search(
                original_input, ops_config, semantic_keywords
            )
            if found_cat:
                category, operation = found_cat, found_op
                confidence = 0.7

        if category not in categories and original_input:
            found_cat, found_op, extracted_params = search_nlp_patterns(
                original_input, ops_config
            )
            if found_cat and found_op:
                category, operation = found_cat, found_op
                confidence = 0.7
            else:
                return (
                    f"# No template for this command. Try adding it to macos_operations.json",
                    0.0,
                )
        elif category not in categories:
            return f"# Unknown category: {category}", 0.0

    operation = find_best_operation(operation, category, ops_config)

    cat_operations = categories.get(category, {})
    if operation not in cat_operations:
        if original_input:
            found_cat, found_op, extracted_params = search_nlp_patterns(
                original_input, ops_config
            )
            if found_cat and found_op:
                category, operation = found_cat, found_op
                cat_operations = categories.get(category, {})
                confidence = 0.7
            else:
                return (
                    f"# No template for this command. Try adding it to macos_operations.json",
                    0.0,
                )
        else:
            return f"# Unknown operation: {operation} in category {category}", 0.0

    template = cat_operations.get(operation)
    if not template:
        return f"# No template for {category}.{operation}", 0.0

    params = re.findall(r"\{(\w+)\}", template)
    result = template

    for param in params:
        if param in action_json:
            value = transform_param(param, str(action_json[param]), app_config)
            result = result.replace(f"{{{param}}}", value)
        elif param in extracted_params:
            value = transform_param(param, str(extracted_params[param]), app_config)
            result = result.replace(f"{{{param}}}", value)
        else:
            result = result.replace(f"{{{param}}}", f"<missing:{param}>")
            confidence -= 0.2

    return result, max(0.0, confidence)


def learn_from_failure(
    input_text: str, intended_category: str, intended_operation: str
):
    """Learn from user correction to improve future predictions."""
    corrections = load_corrections()

    # Store mapping
    corrections["mappings"][input_text.lower()] = {
        "category": intended_category,
        "operation": intended_operation,
    }

    corrections["stats"]["total"] += 1
    corrections["stats"]["corrected"] += 1

    save_corrections(corrections)
    print(f"✓ Learned: '{input_text}' → {intended_category}.{intended_operation}")


def process(
    input_text: str,
    execute: bool = False,
    verbose: bool = False,
    confidence_threshold: float = 0.5,
) -> str:
    """Process natural language input and return/execute bash command."""
    ops_config = load_operations_config()
    app_config = load_app_config()
    corrections = load_corrections()
    semantic_keywords = load_semantic_keywords()
    typo_patterns = load_typo_patterns()

    # Apply typo correction
    input_text = correct_typos(input_text, typo_patterns)

    # Expand ambiguous single-token inputs (e.g. "chrome" => "open chrome")
    input_text = expand_single_token_intents(input_text, app_config, typo_patterns)

    # Check for learned corrections first
    if input_text.lower() in corrections.get("mappings", {}):
        mapping = corrections["mappings"][input_text.lower()]
        bash_command, _ = json_to_bash(mapping, ops_config, app_config)
        if execute:
            os.system(bash_command)
        return bash_command

    if verbose:
        print(f"Input: {input_text}", file=sys.stderr)

    # Check for compound commands
    compound_parts = parse_compound_command(input_text)
    if compound_parts and len(compound_parts) > 1:
        if verbose:
            print(
                f"Compound command detected: {len(compound_parts)} parts",
                file=sys.stderr,
            )

        commands = []
        for part in compound_parts:
            model_output, _ = run_model(part["text"])
            try:
                action_json = json.loads(model_output)
                bash_cmd, conf = json_to_bash(
                    action_json, ops_config, app_config, part["text"], semantic_keywords
                )
                if conf >= confidence_threshold:
                    commands.append(bash_cmd)
            except json.JSONDecodeError:
                continue

        if commands:
            final_command = "; ".join(commands)
            if execute:
                os.system(final_command)
            return final_command

    # Single command processing
    model_output, model_confidence = run_model(input_text)

    if verbose:
        print(f"Model output: {model_output}", file=sys.stderr)
        print(f"Model confidence: {model_confidence:.2f}", file=sys.stderr)

    try:
        action_json = json.loads(model_output)
    except json.JSONDecodeError:
        if verbose:
            print("JSON parse failed, trying direct bash generation", file=sys.stderr)
        return generate_bash_directly(input_text)

    # Calculate overall confidence
    prediction_confidence = calculate_confidence(
        model_output, action_json, ops_config, input_text
    )
    overall_confidence = (model_confidence + prediction_confidence) / 2

    bash_command, template_confidence = json_to_bash(
        action_json, ops_config, app_config, input_text, semantic_keywords
    )

    overall_confidence = (overall_confidence + template_confidence) / 2

    if verbose:
        print(f"Overall confidence: {overall_confidence:.2f}", file=sys.stderr)

    # Handle low confidence
    if overall_confidence < confidence_threshold:
        # Try semantic fallback
        found_cat, found_op, extracted_params = semantic_fallback_search(
            input_text, ops_config, semantic_keywords
        )
        if found_cat and found_op:
            fallback_json = {
                "category": found_cat,
                "operation": found_op,
                **extracted_params,
            }
            bash_command, _ = json_to_bash(
                fallback_json, ops_config, app_config, input_text
            )
            if verbose:
                print(
                    f"Using semantic fallback: {found_cat}.{found_op}", file=sys.stderr
                )
        else:
            print(
                f"⚠ Low confidence ({overall_confidence:.2f}). Did you mean: {bash_command}"
            )
            print(
                f"   If this is wrong, run: python whispera.py --learn '{input_text}' --category <cat> --operation <op>"
            )

    # Update session context
    session.update(
        action_json.get("category", ""),
        action_json.get("operation", ""),
        {k: v for k, v in action_json.items() if k not in ("category", "operation")},
    )

    if execute:
        if verbose:
            print(f"Executing: {bash_command}", file=sys.stderr)
        os.system(bash_command)

    return bash_command


def interactive_mode(confidence_threshold: float = 0.5):
    """Run in interactive mode."""
    print("Whispera CLI - Enhanced Natural Language to Bash")
    print("Type commands or 'quit' to exit")
    print("Prefix with '!' to execute immediately")
    print("Type 'learn: <correct category> <correct operation>' to teach the system")
    print()

    ops_config = load_operations_config()
    app_config = load_app_config()
    last_input = ""
    last_output = ""

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

        # Handle learning from mistakes
        if user_input.startswith("learn:"):
            parts = user_input[6:].strip().split()
            if len(parts) >= 2 and last_input:
                learn_from_failure(last_input, parts[0], parts[1])
            else:
                print("Usage: learn: <category> <operation>")
            continue

        execute = user_input.startswith("!")
        if execute:
            user_input = user_input[1:].strip()

        last_input = user_input
        bash_cmd = process(
            user_input, execute=execute, confidence_threshold=confidence_threshold
        )
        last_output = bash_cmd

        if not execute:
            print(bash_cmd)


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert natural language to bash commands (config-driven with robustness features)"
    )
    parser.add_argument("command", nargs="?", help="Natural language command")
    parser.add_argument(
        "-x", "--execute", action="store_true", help="Execute the command"
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose output")
    parser.add_argument(
        "-i", "--interactive", action="store_true", help="Interactive mode"
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Minimum confidence threshold (0.0-1.0)",
    )
    parser.add_argument("--learn", help="Learn from this input")
    parser.add_argument("--category", help="Category for learning")
    parser.add_argument("--operation", help="Operation for learning")

    args = parser.parse_args()

    # Handle learning mode
    if args.learn and args.category and args.operation:
        learn_from_failure(args.learn, args.category, args.operation)
        return

    if args.interactive or not args.command:
        interactive_mode(confidence_threshold=args.confidence_threshold)
    else:
        result = process(
            args.command,
            execute=args.execute,
            verbose=args.verbose,
            confidence_threshold=args.confidence_threshold,
        )
        print(result)


if __name__ == "__main__":
    main()
