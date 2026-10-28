#!/bin/bash
# Turn a finished build (scripts/build.sh) into a binary release that other Steam Frame owners can unpack
# and run without compiling. Run it in the Debian/Ubuntu build container.
#   output: $ROOT/dist/<tag>-steamframe-aarch64.tar.xz and .tar.xz.sha256
# Private redistributable dependencies are bundled; graphics drivers, glibc and
# the C++ runtime come from SteamOS. setup.sh verifies target compatibility.
# Environment override: ROOT (default ~/openmw-vr).
set -euo pipefail
command -v dpkg-query >/dev/null || { echo "Package using the documented Ubuntu build container." >&2; exit 1; }

REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
ROOT=${ROOT:-$HOME/openmw-vr}
SRC=$ROOT/src
BUILD=$ROOT/build
[ "$(cat "$ROOT/logs/status" 2>/dev/null)" = OK ] || { echo "no finished build in $ROOT" >&2; exit 1; }
python3 "$REPO_DIR/scripts/source_manifest.py" "$SRC" "$ROOT/logs/source-sha256.json" --verify
cmp "$ROOT/logs/build-patches.sha256" <(cd "$REPO_DIR" && sha256sum patches/*.patch)

REF=$(git -C "$SRC" describe --tags --exact-match)
NAME=$REF-frame-$(git -C "$REPO_DIR" rev-parse --short HEAD)-aarch64
OUT=$ROOT/dist/$NAME
rm -rf "$OUT" "$ROOT/dist/$NAME.tar.xz" "$ROOT/dist/$NAME.tar.xz.sha256"
mkdir -p "$OUT/licenses"

# Like the build tree, the release runs in place: its local openmw.cfg points at ./resources.
cp -a "$BUILD"/{openmw_vr,openmw,openmw-iniimporter,openmw.cfg,defaults.bin,gamecontrollerdb.txt} "$OUT/"
cp -a "$BUILD"/{openxrinteractionprofiles.xml,resources} "$OUT/"
[ -f "$BUILD/overrides.bin" ] && cp -a "$BUILD/overrides.bin" "$OUT/"
strip --strip-unneeded "$OUT/openmw_vr" "$OUT/openmw" "$OUT/openmw-iniimporter"
cp "$REPO_DIR/scripts/setup.sh" "$OUT/"
cp "$REPO_DIR/scripts/frame_setup.py" "$OUT/"
cp "$ROOT/logs/source-sha256.json" "$OUT/SOURCE-SHA256.json"
cp "$ROOT/logs/builder-image.txt" "$OUT/BUILDER-IMAGE.txt"
dpkg-query -W > "$OUT/BUILD-PACKAGES.txt"
cp "$REPO_DIR/docs/RELEASE-README.md" "$OUT/README.md"
# The release's source is the upstream tag plus these patches (GPL-3.0).
cp -r "$REPO_DIR/patches" "$OUT/"
(cd "$OUT" && sha256sum patches/*.patch > PATCHES.sha256)

# Licenses of OpenMW and of everything linked into the binaries statically. Libraries that come from
# SteamOS (FFmpeg, ICU, LuaJIT, SDL2, OpenAL, SQLite, ...) aren't shipped.
lic() { cp "$2" "$OUT/licenses/$1"; }
lic OpenMW-GPL-3.0.txt "$SRC/LICENSE"
lic OpenSceneGraph-OSGPL.txt "$BUILD/extern/fetched/osg/LICENSE.txt"
lic Bullet-zlib.txt "$BUILD/extern/fetched/bullet/LICENSE.txt"
lic MyGUI-MIT.txt "$BUILD/extern/fetched/mygui/COPYING.MIT"
lic recastnavigation-zlib.txt "$BUILD/extern/fetched/recastnavigation/License.txt"
lic yaml-cpp-MIT.txt "$BUILD/extern/fetched/yaml-cpp/LICENSE"
lic OpenXR-SDK-Apache-2.0.txt "$BUILD/_deps/openxr-src/LICENSE"
lic jsoncpp-MIT.txt "$BUILD/_deps/openxr-src/src/external/jsoncpp/LICENSE"
lic Boost-BSL-1.0.txt "$ROOT/dl/boost_1_83_0/LICENSE_1_0.txt"
lic osg-ffmpeg-videoplayer.txt "$SRC/extern/osg-ffmpeg-videoplayer/License.txt"
for f in "$SRC"/files/data/fonts/*License.txt; do lic "$(basename "$f")" "$f"; done

python3 "$REPO_DIR/scripts/bundle_libraries.py" "$OUT"

# Keep a corresponding engine-source archive alongside the binary package, including patches.
tar -C "$SRC" --exclude=.git -cJf "$ROOT/dist/$NAME-source.tar.xz" .

cat >"$OUT/BUILDINFO.txt" <<EOF
OpenMW-VR $REF ($(git -C "$SRC" rev-parse HEAD)) from https://gitlab.com/madsbuvi/openmw
Patches applied: $(for patch in "$REPO_DIR"/patches/*.patch; do printf '%s ' "$(basename "$patch")"; done)
Build kit: https://github.com/astromaddie/openmw-vr-steam-frame (scripts/build.sh), GCC $(gcc -dumpfullversion)
Packaged $(date -u '+%F %H:%M') UTC on $(awk -F= '/^PRETTY_NAME=/{print $2}' /etc/os-release), $(uname -m)
Graphics stack when packaged: $(pacman -Q deckard-mesa-linux-aarch64 2>/dev/null)
Build kit: $(git -C "$REPO_DIR" rev-parse HEAD)
Build kit working tree: $(if [ -z "$(git -C "$REPO_DIR" status --porcelain)" ]; then echo clean; else echo development-working-tree; fi)
EOF

python3 - "$OUT" <<'PY'
import hashlib
from pathlib import Path
import sys
root = Path(sys.argv[1])
lines = []
for path in sorted(root.rglob('*')):
    if path.is_file() and path.name != 'SHA256SUMS':
        lines.append(hashlib.sha256(path.read_bytes()).hexdigest() + '  ' + str(path.relative_to(root)))
(root / 'SHA256SUMS').write_text('\n'.join(lines) + '\n')
PY

XZ_OPT=-T4 tar -C "$ROOT/dist" -cJf "$ROOT/dist/$NAME.tar.xz" "$NAME"
(cd "$ROOT/dist" && sha256sum "$NAME.tar.xz" >"$NAME.tar.xz.sha256")
(cd "$ROOT/dist" && sha256sum "$NAME-source.tar.xz" >"$NAME-source.tar.xz.sha256")
ls -la "$ROOT/dist"
