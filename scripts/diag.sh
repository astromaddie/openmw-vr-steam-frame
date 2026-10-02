#!/bin/bash
# Diagnostic run on the headset: start openmw_vr for 50 s with Mesa's GL error reporting (MESA_DEBUG),
# grab the desktop mirror window (it shows the eye images) at 15 s and 30 s, then kill the game.
#   output: $LOGS/diag.log, $LOGS/mirror_15.png, $LOGS/mirror_30.png
# SteamVR only asks for frames while the headset is worn, so wear it during the run. The mirror window
# is only drawn with "[VR] mirror texture = true" in settings.cfg (the recommended settings turn it off).
# Usage: diag.sh [OPENMW_DIR]   (default ~/openmw-vr/build; LOGS defaults to ~/openmw-vr/logs)
OPENMW_DIR=${1:-$HOME/openmw-vr/build}
LOGS=${LOGS:-$HOME/openmw-vr/logs}
cd "$OPENMW_DIR" || exit 1
mkdir -p "$LOGS"
rm -f "$LOGS"/mirror_*.png "$LOGS"/mirror_*.xwd
MESA_DEBUG=1 OPENMW_DISABLE_CRASH_CATCHER=1 DISPLAY=:0 timeout -s KILL 50 ./openmw_vr >"$LOGS/diag.log" 2>&1 &
for t in 15 30; do
    timeout $((t - SECONDS)) tail -f /dev/null
    id=$(xwininfo -display :0 -root -tree | awk 'tolower($0) ~ /"openmw/ {print $1; exit}')
    echo "t=${t}s mirror window: ${id:-not found}"
    [ -n "$id" ] && xwd -display :0 -id "$id" -silent >"$LOGS/mirror_$t.xwd" \
        && ffmpeg -loglevel error -y -i "$LOGS/mirror_$t.xwd" "$LOGS/mirror_$t.png" && echo "  saved mirror_$t.png"
done
wait
echo "== GL errors reported by Mesa"
grep -a '^Mesa' "$LOGS/diag.log" | sort | uniq -c | sort -rn | head
