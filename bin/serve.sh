#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")/.."

if [ ! -f build/dist/index.html ]; then
    echo "No build/dist/index.html: build the site first" >&2
    echo "    python bin/mkbuild.py && ninja -C build" >&2
    exit 1
fi

# python3, not python: only the standard library is needed, and python is
# only on the PATH when .venv is activated
python3 -m http.server -d build/dist
