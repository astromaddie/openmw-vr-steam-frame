#!/bin/sh
# Run installer checks and, when supplied, checks against the patched engine tree.
set -eu
repo=$(CDPATH='' cd -- "$(dirname -- "$0")/.." && pwd)
cd "$repo"
python3 -m unittest discover -s tests -p 'test_*.py' -v
bash -n scripts/build.sh scripts/build_container.sh scripts/package.sh
sh -n scripts/setup.sh scripts/diag.sh
# Unified-diff context lines carry a required space prefix. Check the
# resulting engine source below rather than treating patch syntax as code style.
git diff --check -- . ':!patches/*.patch'
if [ "$#" -gt 0 ]; then
    OPENMW_SOURCE=$(cd "$1" && pwd)
    export OPENMW_SOURCE
    git -C "$OPENMW_SOURCE" diff --check
    for suite in tests/engine*; do
        if [ -d "$suite" ]; then
            python3 -m unittest discover -s "$suite" -p 'test_*.py' -v
        fi
    done
fi
