#!/bin/sh
# Read-only diagnostics. Launch through Steam; never start or kill a game here.
set -eu
config=${OPENMW_FRAME_CONFIG:-${XDG_CONFIG_HOME:-$HOME/.config}/openmw-frame}
printf 'OS: '; uname -a
[ ! -f /etc/os-release ] || cat /etc/os-release
printf '\nOpenXR runtime: '
readlink -f "${XDG_CONFIG_HOME:-$HOME/.config}/openxr/1/active_runtime.json" || true
printf '\nInstalled build: \n'
[ ! -f "$config/frame-install.json" ] || cat "$config/frame-install.json"
printf '\nRecent OpenMW log: \n'
[ ! -f "$config/openmw.log" ] || tail -100 "$config/openmw.log"
printf '\nCompositor session statistics: \n'
journalctl --user --since '20 minutes ago' --no-pager |
    grep -A8 -E 'Process openmw_vr|reprojected|Application Performance' | tail -80 || true
