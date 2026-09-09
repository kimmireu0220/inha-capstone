#!/bin/sh
set -eu
cd "$(dirname "$0")/.."
exec .venv-metrics/bin/python local-studio/server.py
