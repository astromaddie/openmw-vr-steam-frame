#!/bin/bash
# One-time setup of OpenMW-VR on a Steam Frame, after building it (scripts/build.sh) or unpacking a
# binary release. Run it on the headset; Steam must be running.
#   - checks that every shared library resolves (binary releases use SteamOS's own libraries)
#   - points OpenMW at Steam's Morrowind install  -> ~/.config/openmw/openmw.cfg  (kept if it exists)
#   - writes recommended settings                 -> ~/.config/openmw/settings.cfg (kept if it exists)
#   - writes the launcher ~/openmw-vr/OpenMW-VR and adds it to Steam as a non-Steam game (once)
#
# Usage: setup.sh [OPENMW_DIR]
#   OPENMW_DIR is the directory containing openmw_vr. Default: this script's directory when openmw_vr is
#   next to it (binary release), otherwise ~/openmw-vr/build (source build).
# Environment overrides: MORROWIND_DIR, LAUNCHER, ADD_TO_STEAM=0 (don't touch the Steam library).
set -euo pipefail

SCRIPT_DIR=$(cd "$(dirname "$0")" && pwd)
if [ -n "${1:-}" ]; then
    OPENMW_DIR=$(cd "$1" && pwd)
elif [ -x "$SCRIPT_DIR/openmw_vr" ]; then
    OPENMW_DIR=$SCRIPT_DIR
else
    OPENMW_DIR=$HOME/openmw-vr/build
fi
LAUNCHER=${LAUNCHER:-$HOME/openmw-vr/OpenMW-VR}
MW=${MORROWIND_DIR:-$HOME/.local/share/Steam/steamapps/common/Morrowind}
CFG_DIR=$HOME/.config/openmw

[ -x "$OPENMW_DIR/openmw_vr" ] || { echo "openmw_vr not found in $OPENMW_DIR" >&2; exit 1; }
[ -f "$MW/Data Files/Morrowind.esm" ] \
    || { echo "Morrowind not found in $MW (install it from Steam, or set MORROWIND_DIR)" >&2; exit 1; }

missing=$(ldd "$OPENMW_DIR/openmw_vr" | awk '/not found/ {print $1}')
if [ -n "$missing" ]; then
    echo "openmw_vr needs libraries this SteamOS doesn't have:" $missing >&2
    echo "The binary release was built for a different SteamOS version; build from source instead." >&2
    exit 1
fi

mkdir -p "$CFG_DIR"
if [ -e "$CFG_DIR/openmw.cfg" ]; then
    echo "$CFG_DIR/openmw.cfg already exists; leaving it alone"
else
    # Content order is written explicitly: the importer's -g sorts by file time, and Steam's install
    # timestamps make Bloodmoon.esm older than Morrowind.esm.
    cat >"$CFG_DIR/openmw.cfg" <<EOF
data="$MW/Data Files"
content=Morrowind.esm
content=Tribunal.esm
content=Bloodmoon.esm
EOF
    # Adds the fallback= values, the BSA archive list and the text encoding from Morrowind.ini.
    "$OPENMW_DIR/openmw-iniimporter" -i "$MW/morrowind.ini" -c "$CFG_DIR/openmw.cfg"
    echo "wrote $CFG_DIR/openmw.cfg"
fi

if [ -e "$CFG_DIR/settings.cfg" ]; then
    echo "$CFG_DIR/settings.cfg already exists; leaving it alone (recommended values: config/settings.cfg)"
else
    cat >"$CFG_DIR/settings.cfg" <<'EOF'
# Recommended for the Steam Frame (openmw-vr-steam-frame).

[GUI]
# Largest font OpenMW allows (12-18); VR text is small at the default 16.
font size = 18

[VR]
# The desktop mirror window only feeds Steam's 2D preview; skip copying both eyes into it every frame.
mirror texture = false
EOF
    echo "wrote $CFG_DIR/settings.cfg"
fi

mkdir -p "$(dirname "$LAUNCHER")"
cat >"$LAUNCHER" <<EOF
#!/bin/bash
# OpenMW-VR launcher for the Steam Frame; the Steam shortcut runs this.
# OpenMW-VR can crash while shutting down, and OpenMW's crash catcher then hangs with the game stuck
# in the headset. Without it a shutdown crash just ends the process.
export OPENMW_DISABLE_CRASH_CATCHER=1
exec "$OPENMW_DIR/openmw_vr" "\$@"
EOF
chmod +x "$LAUNCHER"
echo "launcher: $LAUNCHER -> $OPENMW_DIR/openmw_vr"

if [ "${ADD_TO_STEAM:-1}" = 0 ]; then
    echo "ADD_TO_STEAM=0: not adding a Steam shortcut"
elif grep -q -a -F "\"$LAUNCHER\"" "$HOME"/.local/share/Steam/userdata/*/config/shortcuts.vdf 2>/dev/null; then
    echo "Steam already has a shortcut for $LAUNCHER"
else
    # Same as Desktop Mode's "Add to Steam"; it shows up in the library as "OpenMW-VR".
    steamos-add-to-steam "$LAUNCHER"
    echo "added $LAUNCHER to Steam"
fi
