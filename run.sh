#!/usr/bin/env bash
set -e

cd "$(dirname "$0")"

if [[ "${1:-}" == "--tests" ]]; then
    python -m unittest discover -s tests -v
else
    python main.py "$@"
fi
