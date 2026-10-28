#!/bin/sh
# Run on the Frame after unpacking a release or finishing a source build.
set -eu
script_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
if [ -f "$script_dir/SHA256SUMS" ]; then
    (cd "$script_dir" && sha256sum -c SHA256SUMS >/dev/null)
fi
exec python3 "$script_dir/frame_setup.py" "$@"
