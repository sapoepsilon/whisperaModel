#!/bin/bash
# Whispera CLI wrapper
# Usage: ./w "open chrome"
#        ./w -x "open chrome"  (execute)

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/venv/bin/activate"
python "$SCRIPT_DIR/whispera.py" "$@"
