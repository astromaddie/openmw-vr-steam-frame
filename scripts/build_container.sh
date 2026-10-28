#!/bin/bash
# Build ARM64 Linux from macOS, Linux or Windows/WSL2 with Docker.
set -euo pipefail
repo=$(cd "$(dirname "$0")/.." && pwd)
work=${OPENMW_FRAME_BUILD_ROOT:-$repo/.build}
image=${OPENMW_FRAME_BUILD_IMAGE:-openmw-frame-builder}
mkdir -p "$work"
docker build --platform linux/arm64 -t "$image" -f "$repo/tools/docker/Dockerfile" "$repo/tools/docker"
image_id=$(docker image inspect --format '{{.Id}}' "$image")
docker run --rm --platform linux/arm64 --memory=4g --cpus=2 \
    -v "$repo:/repo:ro" -v "$work:/work" -e ROOT=/work -e JOBS="${JOBS:-2}" \
    -e OPENMW_FRAME_BUILD_IMAGE_ID="$image_id" "$image_id" bash /repo/scripts/build.sh
