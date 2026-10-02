#!/bin/bash
# Turn a finished build (scripts/build.sh) into a binary release that other Steam Frame owners can unpack
# and run without compiling. Run it on the headset.
#   output: $ROOT/dist/<tag>-steamframe-aarch64.tar.xz and .tar.xz.sha256
# The release links against SteamOS's own libraries (FFmpeg, ICU, LuaJIT, SDL2, OpenAL, ...), so it only
# runs on SteamOS versions that still ship the same library versions; setup.sh checks this.
# Environment override: ROOT (default ~/openmw-vr).
set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
ROOT=${ROOT:-$HOME/openmw-vr}
SRC=$ROOT/src
BUILD=$ROOT/build
[ "$(cat "$ROOT/logs/status" 2>/dev/null)" = OK ] || { echo "no finished build in $ROOT" >&2; exit 1; }

REF=$(git -C "$SRC" describe --tags --exact-match)
NAME=$REF-steamframe-aarch64
OUT=$ROOT/dist/$NAME
rm -rf "$OUT" "$ROOT/dist/$NAME.tar.xz" "$ROOT/dist/$NAME.tar.xz.sha256"
mkdir -p "$OUT/licenses"

# Like the build tree, the release runs in place: its local openmw.cfg points at ./resources.
cp -a "$BUILD"/{openmw_vr,openmw,openmw-iniimporter,openmw.cfg,defaults.bin,gamecontrollerdb.txt} "$OUT/"
cp -a "$BUILD"/{openxrinteractionprofiles.xml,resources} "$OUT/"
[ -f "$BUILD/overrides.bin" ] && cp -a "$BUILD/overrides.bin" "$OUT/"
strip --strip-unneeded "$OUT/openmw_vr" "$OUT/openmw" "$OUT/openmw-iniimporter"
cp "$REPO_DIR/scripts/setup.sh" "$OUT/"
cp "$REPO_DIR/docs/RELEASE-README.md" "$OUT/README.md"
# The release's source is the upstream tag plus these patches (GPL-3.0).
cp -r "$REPO_DIR/patches" "$OUT/"

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
lic Boost-BSL-1.0.txt "$(ls "$ROOT"/dl/boost_*/LICENSE_1_0.txt | head -1)"
lic osg-ffmpeg-videoplayer.txt "$SRC/extern/osg-ffmpeg-videoplayer/License.txt"
for f in "$SRC"/files/data/fonts/*License.txt; do lic "$(basename "$f")" "$f"; done

cat >"$OUT/BUILDINFO.txt" <<EOF
OpenMW-VR $REF ($(git -C "$SRC" rev-parse HEAD)) from https://gitlab.com/madsbuvi/openmw
Patches applied: $(cd "$REPO_DIR/patches" && ls ./*.patch | xargs -n1 basename | tr '\n' ' ')
Built natively on a Steam Frame with https://github.com/stephen-moskal/openmw-vr-steam-frame (scripts/build.sh), GCC $(gcc -dumpfullversion)
Packaged $(date -u '+%F %H:%M') UTC on $(. /etc/os-release; echo "SteamOS $VERSION_ID, build $BUILD_ID, variant $VARIANT_ID"), $(uname -m)
Graphics stack when packaged: $(pacman -Q deckard-mesa-linux-aarch64 2>/dev/null)
EOF

XZ_OPT=-T4 tar -C "$ROOT/dist" -cJf "$ROOT/dist/$NAME.tar.xz" "$NAME"
(cd "$ROOT/dist" && sha256sum "$NAME.tar.xz" >"$NAME.tar.xz.sha256")
ls -la "$ROOT/dist"
