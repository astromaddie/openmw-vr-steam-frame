# Technical notes

What we learned about the Steam Frame while getting OpenMW-VR to run on it, why the build looks the way it
does, and every problem we hit with its cause and fix. Facts are from our headset unless marked otherwise.

## The platform

| | |
|---|---|
| SoC | Qualcomm Snapdragon 8 Gen 3 (SM8650): 8 cores (1 Cortex-X4, 5 Cortex-A720, 2 Cortex-A520), Adreno 750 GPU |
| Memory | 16 GB (15 GiB usable) plus 7.6 GiB zram swap |
| OS | SteamOS, `VARIANT_ID=vr`; tested 0.4.2 (build 20260928.6175029) and 0.4.3 (build 20260930.6234839); Linux 6.18; glibc 2.39 |
| Storage | Read-only btrfs root (10 GB, replaced by updates); `/home` is its own ext4 partition (~929 GB), which survives updates |
| User | `steamos` (Steam library under `~/.local/share/Steam`) |
| Preinstalled tools | GCC 15.1.1, CMake 3.29.2, Ninja 1.12.0, Git, Python 3, podman, flatpak, `steamos-add-to-steam`, `steamosctl` |
| Session | `gamescope` runs with `--backend openvr`: Steam's UI and flat games appear as SteamVR overlays. Steam launches games on Xwayland display `:0`; Desktop Mode adds a nested Plasma session on `:2`. |

## The VR stack

SteamVR runs **natively on ARM64** from `/opt/steamvr`: `bin/linuxarm64/` has `vrserver`, `vrcompositor`
and `vrclient.so`. `bin/linux64/` (x86-64) and `bin/androidarm64/` client libraries and the Windows
manifests (for Proton) ship alongside.

The OpenXR runtime is SteamVR's ARM64 client:

```
~/.config/openxr/1/active_runtime.json -> /opt/steamvr/steamxr_linuxarm64.json
  "library_path" : "bin/linuxarm64/vrclient.so"
```

The runtime offers, among others: `XR_KHR_opengl_enable`, `XR_KHR_opengl_es_enable`, `XR_MNDX_egl_enable`,
`XR_KHR_vulkan_enable(2)`, `XR_KHR_composition_layer_depth`, `XR_KHR_visibility_mask`,
`XR_VALVE_frame_controller_interaction`, `XR_EXT_eye_gaze_interaction`, `XR_EXT_hand_tracking`,
`XR_FB_display_refresh_rate`, `XR_FB_foveation`, `XR_META_performance_metrics`. Its system name is
"SteamVR/OpenXR : cv". It recommends 1728×1728 per eye (maximum 8192) and offers five OpenGL swapchain
formats and the VIEW, LOCAL and STAGE reference spaces. OpenMW-VR sessions ran at 72 Hz.

SteamVR identifies an app by an *app key*. Launched from the Steam library, OpenMW-VR is
`steam.app.<shortcut id>` (ours: `steam.app.3741769447`). Launched from a shell it's
`system.generated.openxr.openmw_vr.openmw_vr`. Per-app SteamVR settings live under that key in
`~/.config/openvr/config/steamvr.vrsettings`; an entry there looks like
`"steam.app.<id>": {"preferredRefreshRate": 120, "resolutionOverride": 2064}`.

## Graphics

- OpenGL is **Mesa's Zink** (OpenGL on Vulkan) over **Turnip**, the Adreno 750 Vulkan driver, from Valve's
  `deckard-mesa` 26.3.0-devel. GLX on gamescope's Xwayland reports OpenGL 4.6 in both core and
  compatibility profiles. EGL and OpenGL ES 3.2 work too.
- `zink_dri.so` is the only OpenGL driver installed; there is no freedreno GL driver to try instead.
- Zink exposes `GL_OVR_multiview` and `GL_OVR_multiview2`, which matters for [performance](PERFORMANCE.md).
- On Linux, OpenMW-VR compiles with `XR_USE_GRAPHICS_API_OPENGL`, `XR_USE_PLATFORM_XLIB` and
  `XR_USE_PLATFORM_EGL`. Because it renders through SDL2 with GLX, it hands SteamVR an
  `XrGraphicsBindingOpenGLXlibKHR`. That's the same path [SteamFrameRaylibQuickstart](https://github.com/Dinsmoor/SteamFrameRaylibQuickstart)
  uses successfully, which is what made us confident it would work.
- **SteamVR on the Frame handles OpenGL image orientation correctly.** Don't flip OpenGL swapchain images;
  see [the upside-down menus](#upside-down-menus-and-a-misleading-fix) below.

## Why a native ARM64 build, and what about FEX

The Frame runs x86 software through FEX: Steam ships it as a compatibility tool (`steamapps/common/FEX-Emu`,
plus `FEXBash`), along with x86-64 Mesa drivers for emulated programs. FEX isn't registered with
`binfmt_misc`, so x86 binaries don't run transparently from a shell. None of that is needed here:

- OpenMW-VR publishes only Windows binaries. On Linux it has to be built from source anyway, and building
  for aarch64 is no harder than for x86-64.
- A native build talks to SteamVR's native OpenXR runtime in-process, with no emulation cost on a
  CPU-heavy engine.

The Windows release under Proton is a possible alternative we didn't test. Proton ARM64's OpenXR bridge
(`wineopenxr.so`) references `XR_KHR_opengl_enable`, so it might work, but the whole engine would run under
x86 emulation.

## Which OpenMW-VR source to build

OpenMW-VR's install docs say to build the `openmw-vr` branch of `gitlab.com/madsbuvi/openmw` on Linux.
**Build the `openmw-vr-0.51-rc1` tag instead.**

| | `openmw-vr` branch | `openmw-vr-0.51-rc1` tag |
|---|---|---|
| Commit | `c87d820`, 2026-05-01, "Merge tag 'openmw-51-rc2' into openmw-vr" | `56a8e01`, 2026-05-23, "Fix menu positioning" |
| Compiles on Linux | No, five merge leftovers (below) | Yes |
| VR menus | Drawn upside down and misplaced; the laser pointer misses | Correct |

The branch is the upstream OpenMW 0.51 RC2 merge before it was finished. The tag is 71 files
(+2076/−1244 lines) further along: a reworked VR menu and settings UI in Lua, OpenXR session and input
fixes, and fixes for every compile break below. Notably, it also removes a texture-matrix flip from MyGUI's
render manager. On the branch that flip draws every VR GUI panel upside down.

Compile breaks on the branch, all fixed in the tag:

1. `components/xr/interactionprofiles.cpp` and `apps/openmw/mwvr/openxrinput.cpp` include
   `<extern/oics/tinyxml.h>`, but the bundled tinyxml lives in `extern/oics/tinyxml/`.
2. `apps/openmw/mwvr/vrinputmanager.cpp` includes `<extern/oics/ICSInputControlSystem.h>` instead of
   `<oics/ICSInputControlSystem.h>`.
3. `apps/openmw/mwworld/worldimp.cpp` still uses `mDistanceToFacedObject` / `getFacedObject()`, which upstream
   renamed to `...FocusObject`.
4. `vrpointer.cpp` passes a `bool` "force shaders" argument that `SceneManager::recreateShaders()` no longer
   takes.
5. `MWWorld::World` is abstract: `getActivationDistancePlusTelekinesis()` is declared in `MWBase::World` but
   was dropped from the implementation (the source marks it `MERGETODO`).

Our fixes for the branch are kept in [`attic/`](attic) for reference only.

## Building

See [BUILDING.md](BUILDING.md). In short: build on the headset against SteamOS's libraries; let OpenMW's
CMake fetch and statically link the libraries SteamOS lacks; build Boost's two libraries ourselves; apply
three patches.

## Runtime configuration

- `~/.config/openmw/openmw.cfg` points at `~/.local/share/Steam/steamapps/common/Morrowind/Data Files` and
  lists the content files explicitly. `openmw-iniimporter -g` would sort them by modification time, and
  Steam's install timestamps make `Bloodmoon.esm` the oldest. The importer is still used without `-g` for
  the 560 `fallback=` values, the BSA list (Morrowind, Tribunal, Bloodmoon) and `encoding=win1252`.
- The build directory's own `openmw.cfg` (relative paths: `resources=./resources`,
  `data=./resources/vfs-mw`) is read first, so the engine runs in place. User settings and saves go to
  `~/.config/openmw` and `~/.local/share/openmw`.
- Morrowind's Proton prefix (`steamapps/compatdata/22320`) isn't used.
- The Steam shortcut targets `~/openmw-vr/OpenMW-VR`, a shell script that sets
  `OPENMW_DISABLE_CRASH_CATCHER=1` (see below) and `exec`s `openmw_vr`. `steamos-add-to-steam` adds it,
  the same way Desktop Mode's "Add to Steam" does. Steam then runs it natively, not in a Steam Linux
  Runtime container, which matters because the binary links against SteamOS's own libraries.

## Problems we hit, in order

| Symptom | Cause | Fix |
|---|---|---|
| CMake: `Target "osgdb_dae" not found` | No COLLADA DOM on SteamOS, so no `.dae` plugin | [Patch 01](../patches/01-skip-osgdb-dae-without-collada.patch) |
| Compile errors in VR sources | Building the unfinished `openmw-vr` branch | Build the `openmw-vr-0.51-rc1` tag |
| Error box "No ShadowManager exists yet" right after the session starts | The VR GUI and pointer call `ShadowManager::instance()` before the RenderingManager creates it | [Patch 02](../patches/02-shadowmanager-guard.patch) |
| Main menu upside down and mirrored; buttons in the wrong place; pointer misses | Branch only: an extra texture-matrix flip in the MyGUI render manager flips every GUI panel inside the eye images | Build the tag. *Not* a swapchain flip; see below |
| Game won't close from the headset; `openmw_vr` ignores SIGTERM | A crash during shutdown (`xrDestroySpace` on an invalid handle, then glibc's "corrupted size vs. prev_size") after which OpenMW's crash catcher hangs | `OPENMW_DISABLE_CRASH_CATCHER=1` in the launcher; `pkill -KILL -x openmw_vr` if one is stuck |
| UI text small and soft | Each VR panel samples the 1280×720 GUI from a 1024×1024 render texture, and auto-sized panels use 1024 px per meter | Font size 18 and [patch 03](../patches/03-larger-vr-ui.patch); see [PERFORMANCE.md](PERFORMANCE.md) for why the render texture wasn't enlarged |
| Soft image, 33–40 fps | GPU and CPU time per frame are over the 13.9 ms budget at 72 Hz | [PERFORMANCE.md](PERFORMANCE.md) |
| Headset rebooted during a build | Kernel bug on SteamOS 0.4.3 (`6.18.0-ge66bc2ca6f8c`): NULL-pointer dereference in `kswapd0` under memory pressure (build with 6 jobs, SteamVR, and a Steam game install at once) | Build with 4 jobs and downloads paused ([BUILDING.md](BUILDING.md#memory-pressure-can-crash-the-headset)); `journalctl -b -1` shows the oops |

### Upside-down menus and a misleading fix

On the branch build, the main menu showed up upside down and mirrored in the headset. Our first theory was
that SteamVR reads OpenGL swapchain images top row first. We added an opt-in vertical flip when copying the
eye images into the swapchain ([`attic/03-gl-swapchain-flip.patch`](attic/03-gl-swapchain-flip.patch)).
That turned the menu upright but turned the 3D world upside down. Meanwhile Steam's 2D preview, which shows
the unflipped eye images, showed the world upright. A screenshot of the desktop mirror window (which shows
the eye images) settled it: the menu text was vertically flipped *inside* the eye image, while the world was
correct. So the GUI pipeline was at fault, not SteamVR. The release tag fixes it.

## Log messages you can ignore

| Message | Meaning |
|---|---|
| `Mesa: error: GL_INVALID_OPERATION in glGenerateMipmap(invalid internal format GL_DEPTH32F_STENCIL8)` (with `MESA_DEBUG=1`), or OSG's `detected OpenGL error 'invalid operation' at after RenderBin::draw(..)`, about 60 per second | A mipmap generation request on a depth/stencil texture each frame; Mesa rejects it, other drivers may silently accept it. Nothing is drawn wrong. |
| `Failed to open shader .../gui_vertex.glsl` / `gui_fragment.glsl` | Unused leftovers in an OpenMW-VR change to the MyGUI render manager; the GUI uses `gui.vert` / `gui.frag` |
| `xrSuggestInteractionProfileBindings ... XR_ERROR_PATH_UNSUPPORTED`; SteamVR log: `Invalid Interaction Profile suggested: /interaction_profiles/htc/cosmos_controller` | SteamVR on the Frame rejects OpenMW-VR's HTC Cosmos controller bindings; the other profiles are accepted |
| `Layer HUD_3D unable to track space: -3`, `Layer Tooltip ...` | A few warnings while the VR spaces initialise |
| `Failed to create message #{OMWEngine:...} (%s) ... U_PATTERN_SYNTAX_ERROR` | Localisation formatting of a few settings labels |
| `Disabling Multiview (OSG does not support multiview)` | The OpenSceneGraph 3.6.5 fork lacks `OSG_HAS_MULTIVIEW`; see [PERFORMANCE.md](PERFORMANCE.md) |

## Diagnostics toolbox

| What | How |
|---|---|
| Game log | `~/.config/openmw/openmw.log` (recreated on every launch) |
| SteamVR's per-session frame stats | SteamVR logs to journald. After quitting: `journalctl --user \| grep -A6 "Process openmw_vr"` shows presents, dropped and reprojected frames, and the average CPU and GPU time per frame |
| SteamVR client log for the app | `journalctl --user \| grep xrclient_openmw_vr`: chosen resolution, app key, rejected bindings |
| Exact GL errors | Run with `MESA_DEBUG=1`; Mesa prints the failing call and the reason ([`scripts/diag.sh`](../scripts/diag.sh)) |
| What the game renders | With `[VR] mirror texture = true`, the desktop window shows the eye images; `xwininfo -display :0 -root -tree` finds it, `xwd -display :0 -id <id>` grabs it, and `ffmpeg` turns the `.xwd` into PNG ([`scripts/diag.sh`](../scripts/diag.sh)). SteamVR only requests frames while the headset is worn. |
| SteamVR tool | `/opt/steamvr/bin/linuxarm64/vrcmd` has `--stats`, `--statsLoop`, `--screenshot` and settings get/set options (we didn't need them) |
| Clocks | `/sys/class/devfreq/3d00000.gpu/{cur_freq,max_freq,trans_stat}`; `/sys/devices/system/cpu/cpufreq/policy*/scaling_{cur,max}_freq` |
| Power settings | `steamosctl get-performance-profile`, `get-cpu-boost-state`, `get-gpu-performance-level`, … |
| Thermal throttling | `/sys/class/thermal/cooling_device*/{type,cur_state}` (non-zero means throttling) |

### Recordings

Steam's background recording captures the **headset view** (1920×1080, 60 fps, H.264 plus AAC audio). Each
session is a DASH stream under
`~/.local/share/Steam/userdata/<account id>/gamerecordings/video/bg_<game id>_<UTC date>_<UTC time>/`.
For non-Steam shortcuts the game id is `(shortcut app id << 32) | 0x02000000`; for ours that is
`16070777404070559744`. To get one MP4 without re-encoding:

```sh
cd ~/.local/share/Steam/userdata/*/gamerecordings/video/bg_<game id>_<date>_<time>/
ffmpeg -i session.mpd -c copy ~/openmw-vr-session.mp4
```

(ffmpeg warns "Error when loading first fragment of playlist"; the result is complete.)
