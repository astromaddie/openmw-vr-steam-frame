# Journal

How this install came together on 2026-10-01, in order, including the dead ends. Times are the headset's
local time.

## Access

- **~15:07** Set up key-based SSH from a Mac to the headset (`steamos@<ip>`, alias `frame`) after SSH had been
  enabled on the Frame. Confirmed key-only login with `BatchMode=yes`; `sshd` is enabled, and `/home` is a
  separate partition, so both survive reboots and updates.

## Feasibility

- **~15:15** Surveyed the headset. Found SteamOS 0.4.2 "vr" variant (Snapdragon 8 Gen 3, 16 GB); SteamVR running
  natively on ARM64; the active OpenXR runtime is SteamVR's ARM64 `vrclient.so`, which lists
  `XR_KHR_opengl_enable`; OpenGL 4.6 through Zink on all of gamescope's displays; GCC, CMake and Ninja
  preinstalled. Morrowind (Steam app 22320) had been installed the evening before.
- OpenMW-VR's documentation: Windows binaries only; on Linux, build the `openmw-vr` branch from source.
  OpenMW-VR on Linux uses the OpenGL Xlib binding, the same one
  [SteamFrameRaylibQuickstart](https://github.com/Dinsmoor/SteamFrameRaylibQuickstart) uses successfully on a
  real Frame. FEX can run x86 code, but there are no x86 Linux builds to run anyway, so we chose a native
  aarch64 build on the headset. The Windows build under Proton ARM64 might also work (its OpenXR bridge
  references OpenGL support); untested.

## First build: the `openmw-vr` branch

- **15:35** Started `build.sh` as a `systemd-run --user` service (nice 19, memory capped at 6–8 GB, 6 jobs).
  Boost built in a minute.
- **15:37** Configure failed: `Target "osgdb_dae" not found`. SteamOS has no COLLADA DOM, so OpenSceneGraph
  skips its `.dae` plugin while OpenMW still asks for it. Dropped the plugin when COLLADA is missing
  (now [patch 01](../patches/01-skip-osgdb-dae-without-collada.patch)).
- **15:38–16:16** Compiled 1779 steps, stopping five times for merge leftovers in the branch: tinyxml and OICS
  include paths, the `FacedObject` → `FocusObject` rename, an obsolete `recreateShaders()` argument, and a
  missing `getActivationDistancePlusTelekinesis()` (marked `MERGETODO` in the source). Switched Ninja to
  `-k 0` so later failures would all show up in one pass. The fixes are in [`attic/`](attic).
- **16:17** First launch over SSH: SteamVR's OpenXR instance and an OpenGL session came up at 1728×1728 per
  eye and the game data loaded. Then an error box: "No ShadowManager exists yet". The VR GUI and pointer
  touch the ShadowManager before the renderer creates it. Fixed with a guard (now
  [patch 02](../patches/02-shadowmanager-guard.patch)).
- **16:24** Second launch: the main menu appeared in the headset with music playing, but upside down and
  mirrored. Quitting hung: a crash during shutdown left OpenMW's crash catcher stuck, and the process
  ignored SIGTERM. Killed it with SIGKILL.
- **16:29** Assumed SteamVR was reading OpenGL images top row first, and added an opt-in vertical flip for
  the swapchain copy. Also made the launcher disable the crash catcher, and added **OpenMW-VR** to Steam with
  `steamos-add-to-steam`.

## The wrong fix, and the right source

- **~19:00** Tested from the Steam library. The title screen was now upright, but the 3D world was upside down,
  the menu buttons sat at the top and the laser pointer missed them. Steam's 2D preview showed the world
  upright. So the flip was wrong: SteamVR handles OpenGL orientation correctly.
- **19:07** Diagnostic run with `MESA_DEBUG=1` and a screenshot of the desktop mirror window. The only GL error
  was a `glGenerateMipmap` on a depth texture (harmless). The screenshot showed the copyright text
  vertically flipped *inside* the eye image, so the GUI pipeline itself was flipping.
- **19:10** Found the release tag `openmw-vr-0.51-rc1` (2026-05-23, "Fix menu positioning"), three weeks newer
  than the branch tip the docs point to. It fixes all five compile breaks, and among 71 changed files it
  removes a texture-matrix flip from MyGUI's render manager: the GUI bug. Switched the build to the tag and
  dropped the swapchain flip, the telekinesis fix (the tag solves it differently) and the include fixes.
  The COLLADA patch and the ShadowManager guard are still needed.
- **19:13–19:29** Incremental rebuild on the tag (323 steps, 16 minutes).

## Playable

- **19:35–19:47** First real session: into the game and playing. Remarks: low rendering resolution, small and
  hard-to-read text. SteamVR's summary: 1440×1440 per eye, CPU 15.3 ms and GPU 28.6 ms per frame, 57% of
  frames reprojected (the game ran at about 31 fps).
- **19:58** Readability: VR panels a third larger (now [patch 03](../patches/03-larger-vr-ui.patch)), font size 18
  (OpenMW's maximum), desktop mirror window off.
- **19:59–20:10** Second session: frame numbers essentially unchanged. Pulled Steam's background recording
  (it captures the headset view) and converted it to MP4; the stills show the world upright and the VR quick
  menu readable.
- **~20:15** Found SteamOS's default clock caps: CPU boost off (every core at most 2.0 GHz; the prime core can
  reach 3.05) and GPU "auto" at most 629 MHz (the chip can reach 903). There was no thermal throttling.
- **20:23–20:26** Session in Performance mode: caps lifted, SteamVR raised the resolution to 1728×1728, GPU time
  fell to 23.1 ms and the game reached about 40 fps. It looked sharper but felt no smoother, maybe more
  stuttery, which fits a frame rate stuck between SteamVR's 36 and 72 fps cadences.
  Also noticed SteamOS had updated itself to 0.4.3 (build 20260930.6234839) during the day; the build kept
  working.

## Documentation

- **21:00** Wrote this repository: the scripts and patches in their final form plus these docs.
- **21:03** Started a from-scratch build with the final scripts in a separate directory
  (`ROOT=~/openmw-vr-cleantest`) to confirm the instructions reproduce the build. A fresh clone of the release
  tag took all three patches and configured cleanly.
- **21:08** The headset's kernel crashed and the headset rebooted: a NULL-pointer dereference in `kswapd0`
  (memory reclaim) on SteamOS 0.4.3's new kernel. At the time the clean build was at step 258 of 1777
  (OpenSceneGraph, 6 jobs), SteamVR was running and Steam was installing a large game. Nothing was lost.
  Lowered `build.sh`'s default to 4 jobs and documented the risk.
- **21:11–21:13** Packaged the binary release (24 MB) from the working build, which has the same tag and
  patches. Verified it by unpacking it into a fresh directory, running its `setup.sh` (library check, launcher)
  and launching it: it loaded its own config and resources, created the OpenXR session at 1728×1728 and loaded
  Morrowind, Tribunal and Bloodmoon. The from-scratch build test still needs a complete run.

Next: a steady 36 fps per-app frame-rate lock with a pinned resolution, then profiling and multiview
([PERFORMANCE.md](PERFORMANCE.md#next-steps)).
