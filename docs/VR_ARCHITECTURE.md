# OpenMW Frame

## Target and source

Native Linux ARM64 on Steam Frame, SteamVR OpenXR, desktop OpenGL through Zink.
Engine: `https://gitlab.com/madsbuvi/openmw`, tag `openmw-vr-0.51-rc1`, commit
`56a8e01390507375c9c2f2593e1c09e0df88c505`. Build-kit ancestor: Stephen Moskal's
`3bb39fc1f6fc2e07fde14b8f8765b727f51f1d80`. Keep engine adaptations as ordered
patches and keep the flat `openmw` target buildable.

## Frame protocol and draw inventory

Retain the upstream OpenXR frame loop: wait/begin/end once per frame, locate views
at predicted display time, update game state once, and render both eyes from the
same frame state. Standby is a normal runtime state. Suppress gameplay input when
focus is absent; teardown must release child XR objects before the session.

| Content | Existing path and validation requirement |
| --- | --- |
| World, terrain, water, shadows | OSG stereo cameras; compare both eyes at several yaw angles |
| Weapon and tracked hands | Upstream VR animation/combat; check aim versus visible weapon |
| Sky, fog, particles, billboards | Existing stereo rendering; check translation, roll, depth and culling |
| Inventory, dialogue, journal, map | Existing MyGUI VR surfaces; modal layers and their pointer take priority over world geometry |
| HUD and radial menu | Existing VR surfaces; verify readable angular size and stable anchoring |
| Intro/video/loading | Existing VR presentation; verify transitions and no forced camera motion |

This inventory identifies inspection targets; it is not a claim that all paths
have passed device validation.

## Installation interfaces

`setup.sh [BUILD_DIR] [--morrowind-dir PATH] [--no-steam] [--import-saves PATH]`
verifies a packaged build's checksums and ARM64 ELF before installation. It finds
Steam app 22320 through Steam library manifests, including removable libraries.
An explicit path can name either the installation or its `Data Files` directory.
Only present expansion masters are enabled, in Morrowind/Tribunal/Bloodmoon order.

Frame configuration: `$XDG_CONFIG_HOME/openmw-frame` (default
`~/.config/openmw-frame`). Save/data root: `$XDG_DATA_HOME/openmw-frame` (default
`~/.local/share/openmw-frame`). The stable `OpenMW Frame` launcher lives in that
data root. It selects the Frame profile with native `--replace config --config`
and `--user-data` options, leaving other OpenMW profiles independent.

Reinstallation keeps configuration and saves. Optional save import copies missing
files and never overwrites existing destination saves. `frame-install.json`
records the installed build and data locations. Package libraries are private to
the launcher; graphics drivers, window-system libraries, glibc, the system C++ runtime and the active OpenXR runtime stay external. Bundling an older C++ runtime can break newer SteamVR/driver modules; the supported SteamOS ABI is checked on the device.

## Release gates

The performance floor is 72 rendered fps at 1728² per eye in repeatable outdoor,
town and interior routes. Display refresh is selected through SteamVR's per-title
setting. Higher refresh and resolution require separate measurements. Never count
reprojected compositor frames as newly rendered application frames.

Retain compact build, patch, timing and image-comparison evidence in
`docs/VALIDATION.md`. A source test, successful build, installed package, rendered
device session and user acceptance establish different facts.
