#!/bin/bash

set -euo pipefail

# Paths below are relative to the repository root
cd "$(dirname "$0")/.."

# Publishes exactly what the repository builds
uv run bin/mkbuild.py
uv run ninja -C build

# ninja never deletes the outputs of removed build edges (renamed images,
# deleted static files...): prune what the build graph doesn't produce, so
# rsync --delete removes it from the server too. Paths are compared relative
# to build/dist: absolute ones may differ through symlinks.
# Assignments, not <(...): set -e and pipefail stop the script if ninja fails
targets=$(uv run ninja -C build -t targets all | sed -n 's|^.*/build/dist/\(.*\): [a-z_]*$|\1|p' | sort)
files=$(cd build/dist && find . -type f | sed 's|^\./||' | sort)
if [ -z "$targets" ]; then
    echo "No build target in build/dist: not pruning, not publishing" >&2
    exit 1
fi
stale=$(comm -23 <(echo "$files") <(echo "$targets"))
if [ -n "$stale" ]; then
    # A bug here would empty the site: rsync --delete would mirror that
    if [ "$(wc -l <<<"$stale")" -gt "$(( $(wc -l <<<"$files") / 2 ))" ]; then
        echo "More than half of build/dist is stale: not pruning, not publishing" >&2
        exit 1
    fi
    (cd build/dist && xargs --delimiter='\n' rm --verbose -- <<<"$stale")
fi
find build/dist -mindepth 1 -type d -empty -delete

# Forcing ipv4 for now, at the time of writing the ipv6 address
# is not propagated to all DNS yet
rsync \
    -e "ssh -4" \
    --archive \
    --progress \
    --human-readable \
    --delete \
    build/dist/ \
    pi:/srv/www/charlesfleche.net/
