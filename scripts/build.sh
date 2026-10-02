#!/bin/bash
# Native aarch64 build of OpenMW-VR (gitlab.com/madsbuvi/openmw) on the Steam Frame, run on the headset.
#
# Everything is built under $ROOT (default ~/openmw-vr); nothing outside /home is touched. Safe to re-run:
# finished steps are skipped and ninja resumes where it stopped.
#   progress: tail -f $ROOT/logs/build.log
#   result:   $ROOT/logs/status  (RUNNING, OK, or FAILED <exit code>)
#
# Environment overrides: ROOT, JOBS (parallel compile jobs, default 4), REF (git tag to build).
set -euo pipefail

REPO_DIR=$(cd "$(dirname "$0")/.." && pwd)
PATCHES=$REPO_DIR/patches
ROOT=${ROOT:-$HOME/openmw-vr}
DEPS=$ROOT/deps    # Boost install prefix
SRC=$ROOT/src      # OpenMW-VR checkout
BUILD=$ROOT/build
JOBS=${JOBS:-4}   # 6 is faster, but see docs/BUILDING.md on memory pressure
# Latest OpenMW-VR release. The openmw-vr branch the install docs point at stops at the upstream 0.51
# merge and lacks the fixes made for this release (e.g. upside-down, misplaced VR menus).
REF=${REF:-openmw-vr-0.51-rc1}
BOOST_VER=1.83.0   # matches SteamOS's boost-libs runtime
BOOST_DIR=boost_${BOOST_VER//./_}

mkdir -p "$ROOT/logs" "$ROOT/dl"
exec >>"$ROOT/logs/build.log" 2>&1
step() { echo; echo "=== $(date '+%F %T') $*"; }
trap 'rc=$?; step "FAILED (exit $rc)"; echo "FAILED $rc" >"$ROOT/logs/status"' ERR
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
    rm -rf "$BOOST_DIR"
    tar xzf "$BOOST_DIR.tar.gz"
    cd "$BOOST_DIR"
    ./bootstrap.sh --with-libraries=iostreams,program_options --prefix="$DEPS"
    ./b2 -j"$JOBS" link=static variant=release threading=multi cxxflags=-fPIC -sNO_COMPRESSION=1 install
fi

if [ ! -d "$SRC/.git" ]; then
    step "Clone $REF"
    git clone --depth 1 --branch "$REF" https://gitlab.com/madsbuvi/openmw.git "$SRC"
elif [ "$(git -C "$SRC" describe --tags --exact-match 2>/dev/null || true)" != "$REF" ]; then
    # Discards local changes to the checkout; the patches below are re-applied.
    step "Switch source to $REF"
    git -C "$SRC" fetch --depth 1 origin tag "$REF"
    git -C "$SRC" checkout -f "$REF"
fi

# Source fixes for the Frame, one topic per patch (each file starts with a description), in order.
for p in "$PATCHES"/*.patch; do
    if ! git -C "$SRC" apply --reverse --check "$p" 2>/dev/null; then
        step "Patch: apply $(basename "$p")"
        git -C "$SRC" apply "$p"
    fi
done

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

step "DONE"
echo OK >"$ROOT/logs/status"
