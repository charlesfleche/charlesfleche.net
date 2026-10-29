#!/bin/bash

set -euo pipefail

cd "$(dirname "$0")/.."

python -m http.server -d build/dist
