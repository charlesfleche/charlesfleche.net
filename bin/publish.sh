#!/bin/bash

# Forcing ipv4 for now, at the time of writing the ipv6 address
# is not propagated to all DNS yet
rsync \
    -e "ssh -4" \
    --archive \
    --progress \
    --human-readable \
    --delete \
    build/dist/ \
    cf:/srv/www/charlesfleche.net/
