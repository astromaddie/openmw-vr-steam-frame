#!/bin/bash
# Native aarch64 build of OpenMW-VR (gitlab.com/madsbuvi/openmw) on the Steam Frame, run on the headset.
#
# Everything is built under $ROOT (default ~/openmw-vr); nothing outside /home is touched. Safe to re-run:
# finished steps are skipped and ninja resumes where it stopped.
#   progress: tail -f $ROOT/logs/build.log
#   result:   $ROOT/logs/status  (RUNNING, OK, or FAILED <exit code>)
#
# Environment overrides: ROOT, JOBS (parallel compile jobs, default 2).
set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
PATCHES=$REPO_DIR/patches
ROOT=${ROOT:-$HOME/openmw-vr}
DEPS=$ROOT/deps    # Boost install prefix
SRC=$ROOT/src      # OpenMW-VR checkout
BUILD=$ROOT/build
JOBS=${JOBS:-2}
# Latest OpenMW-VR release. The openmw-vr branch the install docs point at stops at the upstream 0.51
# merge and lacks the fixes made for this release (e.g. upside-down, misplaced VR menus).
REF=openmw-vr-0.51-rc1
SOURCE_COMMIT=56a8e01390507375c9c2f2593e1c09e0df88c505
BOOST_VER=1.83.0   # matches SteamOS's boost-libs runtime
BOOST_DIR=boost_${BOOST_VER//./_}
BOOST_SHA256=c0685b68dd44cc46574cce86c4e17c0f611b15e195be9848dfd0769a0a207628

mkdir -p "$ROOT/logs" "$ROOT/dl"
exec >>"$ROOT/logs/build.log" 2>&1
step() { echo; echo "=== $(date '+%F %T') $*"; }
failed() { local rc=$?; step "FAILED (exit $rc)"; echo "FAILED $rc" >"$ROOT/logs/status"; }
trap failed ERR
echo RUNNING >"$ROOT/logs/status"

# SteamOS ships the Boost runtime libraries but no headers or CMake config. OpenMW needs only
# iostreams (just stream.hpp, so no compression filters) and program_options; build them static.
if [ ! -f "$DEPS/lib/cmake/Boost-$BOOST_VER/BoostConfig.cmake" ]; then
    step "Boost $BOOST_VER"
    cd "$ROOT/dl"
    if [ ! -f "$BOOST_DIR.tar.gz" ]; then
        curl -fL --retry 3 -o "$BOOST_DIR.tar.gz" \
            "https://archives.boost.io/release/$BOOST_VER/source/$BOOST_DIR.tar.gz"
    fi
    printf '%s  %s\n' "$BOOST_SHA256" "$BOOST_DIR.tar.gz" | sha256sum -c -
    rm -rf "$BOOST_DIR"
    tar xzf "$BOOST_DIR.tar.gz"
    cd "$BOOST_DIR"
    ./bootstrap.sh --with-libraries=iostreams,program_options --prefix="$DEPS"
    ./b2 -j"$JOBS" link=static variant=release threading=multi cxxflags=-fPIC -sNO_COMPRESSION=1 install
fi

if [ ! -e "$SRC/.git" ]; then
    step "Clone $REF"
    git clone --depth 1 --branch "$REF" https://gitlab.com/madsbuvi/openmw.git "$SRC"
fi
if [ "$(git -C "$SRC" rev-parse HEAD)" != "$SOURCE_COMMIT" ]; then
    echo "Source is not pinned commit $SOURCE_COMMIT. Use a fresh ROOT; existing source was preserved." >&2
    exit 1
fi

# Source fixes for the Frame, one topic per patch (each file starts with a description), in order.
(cd "$REPO_DIR" && sha256sum patches/*.patch) > "$ROOT/logs/build-patches.sha256"
python3 "$REPO_DIR/scripts/prepare_source.py" "$SRC" "$PATCHES" "$SOURCE_COMMIT"

# OSG, Bullet, MyGUI, yaml-cpp, recastnavigation and the OpenXR loader aren't packaged on SteamOS,
# so OpenMW's CMake downloads and builds them statically. The Qt tools (launcher, editor, wizard)
# are skipped. "-include cstdint" guards the older bundled deps against GCC 13+ no longer pulling
# in <cstdint> transitively.
step "Configure"
cmake -S "$SRC" -B "$BUILD" -G Ninja \
    -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_CXX_FLAGS="-include cstdint" \
    -DCMAKE_PREFIX_PATH="$DEPS" \
    -DBoost_USE_STATIC_LIBS=ON \
    -DOPENMW_USE_SYSTEM_OSG=OFF -DOPENMW_USE_SYSTEM_BULLET=OFF -DOPENMW_USE_SYSTEM_MYGUI=OFF \
    -DOPENMW_USE_SYSTEM_YAML_CPP=OFF -DOPENMW_USE_SYSTEM_RECASTNAVIGATION=OFF \
    -DBUILD_OPENMW_VR=ON -DBUILD_OPENMW=ON -DBUILD_MWINIIMPORTER=ON \
    -DBUILD_LAUNCHER=OFF -DBUILD_OPENCS=OFF -DBUILD_WIZARD=OFF -DBUILD_ESSIMPORTER=OFF \
    -DBUILD_BSATOOL=OFF -DBUILD_ESMTOOL=OFF -DBUILD_NIFTEST=OFF \
    -DBUILD_NAVMESHTOOL=OFF -DBUILD_BULLETOBJECTTOOL=OFF

# -k 0: keep compiling past failures so every broken file shows up in one pass.
step "Build (-j$JOBS)"
cmake --build "$BUILD" -j "$JOBS" -- -k 0
cmp "$ROOT/logs/build-patches.sha256" <(cd "$REPO_DIR" && sha256sum patches/*.patch)

step "DONE"
git -C "$SRC" diff --binary > "$ROOT/logs/applied-source.patch"
git -C "$SRC" rev-parse HEAD > "$ROOT/logs/source-commit"
python3 "$REPO_DIR/scripts/source_manifest.py" "$SRC" "$ROOT/logs/source-sha256.json"
printf '%s\n' "${OPENMW_FRAME_BUILD_IMAGE_ID:-native-build}" > "$ROOT/logs/builder-image.txt"
echo OK >"$ROOT/logs/status"
