# OpenMW-VR on the Steam Frame

Play **The Elder Scrolls III: Morrowind in VR, standalone on Valve's Steam Frame**: a native ARM64 build of
[OpenMW-VR](https://gitlab.com/madsbuvi/openmw) that runs on the headset itself under SteamOS and renders
through SteamVR's native OpenXR runtime. There is no PC, no streaming and no x86 emulation involved.

This repository has everything needed to reproduce it: the build script, the three source patches the Frame
needs, the one-time setup script, recommended settings, diagnostics, and the notes from getting it working.
A prebuilt binary release can be produced from it (`scripts/package.sh`) so others can skip the build.

We haven't found any earlier report of OpenMW-VR running natively on the Steam Frame; as of 2026-10-01 this
is the first install we know of.

## Status (2026-10-01)

**Playable.** You can start a new game or load a save, walk around, use the VR menus with the laser
pointer, and quit back to SteamVR. Tested on SteamOS 0.4.2 and 0.4.3 (VR variant), SteamVR 2.18.

| Works | Needs work |
|---|---|
| Native aarch64 build on the headset, about 45 minutes | Frame rate: the game renders at about 33–40 fps and SteamVR reprojects to 72 Hz ([performance notes](docs/PERFORMANCE.md)) |
| OpenXR through SteamVR's ARM64 runtime, OpenGL via Zink | Resolution: SteamVR picks 1440×1440 per eye at default clocks, 1728×1728 in Performance mode (the panels are 2160×2160) |
| Head tracking, Frame controllers (through SteamVR's binding emulation), laser pointer | No Frame-specific controller profile in OpenMW-VR yet; SteamVR maps the Index/Touch bindings |
| VR main menu, HUD, inventory, dialogue; launching from the Steam library | OpenMW-VR can crash while shutting down; the launcher makes that exit cleanly instead of hanging |
| Morrowind + Tribunal + Bloodmoon from the Steam release | |

## What you need

- A **Steam Frame** on SteamOS (tested 0.4.2 and 0.4.3, VR variant). The VR image already ships GCC, CMake,
  Ninja and Git, so nothing has to be installed into the read-only OS.
- **Morrowind from Steam** (app 22320) installed on the headset. OpenMW uses its `Data Files`; the Windows
  executable is never run.
- **A shell on the headset**: SSH from another computer (what we used), or Konsole in Desktop Mode.
  For SSH, enable `sshd` on the headset and use the `steamos` user; see
  [docs/BUILDING.md](docs/BUILDING.md#getting-a-shell-on-the-headset).
- About 6 GB free in `/home` for a source build, under 200 MB for the binary release.

## Install from the binary release (quick)

Download `openmw-vr-0.51-rc1-steamframe-aarch64.tar.xz` (24 MB) from this repository's
[Releases page](https://github.com/stephen-moskal/openmw-vr-steam-frame/releases), or make your own with
`scripts/package.sh` (see [Sharing a binary release](#sharing-a-binary-release)). Our release has SHA-256
`f57e246d9213d6ae0e50225953c14cc953a5f0093fa00d05d5a296f9ebd7029d`. It was tested by unpacking it into a
fresh directory on the headset and launching it from there.

```sh
# on the headset
mkdir -p ~/openmw-vr
tar -C ~/openmw-vr -xJf openmw-vr-0.51-rc1-steamframe-aarch64.tar.xz
~/openmw-vr/openmw-vr-0.51-rc1-steamframe-aarch64/setup.sh
```

`setup.sh` refuses to continue if the SteamOS on your headset no longer has the system libraries the release
was linked against (FFmpeg, ICU, LuaJIT, SDL2, OpenAL, …). If that happens, build from source instead.

## Install from source (about 45 minutes)

Before building, pause Steam downloads and close games: on SteamOS 0.4.3 heavy memory pressure during a
build once crashed the headset's kernel ([details](docs/BUILDING.md#memory-pressure-can-crash-the-headset)).

```sh
# on the headset
git clone https://github.com/stephen-moskal/openmw-vr-steam-frame.git ~/openmw-vr-steam-frame

# Build at low priority in the background; it keeps going if your SSH session drops.
systemd-run --user --collect --unit=openmw-vr-build -p Nice=19 -p MemoryHigh=6G -p MemoryMax=8G \
    ~/openmw-vr-steam-frame/scripts/build.sh
tail -f ~/openmw-vr/logs/build.log      # Ctrl-C stops watching, not the build
cat ~/openmw-vr/logs/status             # RUNNING, OK, or FAILED <code>

# once the status is OK (Steam must be running):
~/openmw-vr-steam-frame/scripts/setup.sh
```

`build.sh` builds Boost's two needed libraries, clones the `openmw-vr-0.51-rc1` release tag, applies the
patches in [`patches/`](patches), and lets OpenMW's CMake download and statically link OpenSceneGraph,
Bullet, MyGUI, recastnavigation, yaml-cpp and the OpenXR loader. Everything stays under `~/openmw-vr`.
Details, timings and memory use: [docs/BUILDING.md](docs/BUILDING.md).

## What setup.sh does

1. Checks that every shared library `openmw_vr` needs is present.
2. Writes `~/.config/openmw/openmw.cfg` pointing at Steam's Morrowind `Data Files`, with the load order
   Morrowind → Tribunal → Bloodmoon written explicitly, then imports the `fallback=` values, BSA list and
   text encoding from `morrowind.ini` with `openmw-iniimporter`. (Letting the importer order the content
   files would put Bloodmoon first, because Steam's install timestamps make it the oldest file.)
3. Writes the recommended `~/.config/openmw/settings.cfg` ([config/settings.cfg](config/settings.cfg)):
   font size 18 and no desktop mirror window.
4. Writes the launcher `~/openmw-vr/OpenMW-VR` and adds it to Steam as a non-Steam game named **OpenMW-VR**.

Existing `openmw.cfg` and `settings.cfg` files are left alone, so it's safe to re-run.

## Playing

- Launch **OpenMW-VR** from the Steam library in the headset (it is listed with non-Steam games).
- The VR menu, HUD and windows float in front of you; point with the controller laser and pull the trigger.
- Quit from the main menu (**Exit**) or with the Steam button → **Exit game**.
- For the smoothest result, open the Steam quick menu's performance settings and pick **Performance** mode
  before launching. It lifts SteamOS's default clock caps (CPU boost off, GPU at most 629 MHz), and SteamVR
  then renders at 1728×1728 per eye instead of 1440×1440. See [docs/PERFORMANCE.md](docs/PERFORMANCE.md).
- Steam's background recording captures the headset view; [docs/TECHNICAL-NOTES.md](docs/TECHNICAL-NOTES.md#recordings)
  shows how to turn a recording into an MP4.

## Known issues

| Issue | Effect | Status |
|---|---|---|
| The game renders at 33–40 fps | SteamVR reprojects to 72 Hz; a rate between 36 and 72 makes SteamVR switch back and forth, which can feel like stutter | Next: lock to a steady 36 fps per app, then multiview ([PERFORMANCE.md](docs/PERFORMANCE.md)) |
| Soft image | 1440 or 1728 pixels per eye on a 2160-pixel panel | Limited by GPU time; see above |
| Small, soft UI text | Morrowind's UI is small in VR | Font size 18 (OpenMW's maximum) and VR panels a third larger ([patch 03](patches/03-larger-vr-ui.patch)) |
| Shutdown crash | OpenMW-VR can crash while quitting (`xrDestroySpace` on an invalid handle, then heap corruption) | The launcher sets `OPENMW_DISABLE_CRASH_CATCHER=1`, so the game exits instead of hanging |
| `.dae` (COLLADA) models | Some mods use them; the Frame build can't load them | SteamOS has no COLLADA DOM ([patch 01](patches/01-skip-osgdb-dae-without-collada.patch)) |
| Kernel crash while building | On SteamOS 0.4.3 the kernel crashed in memory reclaim (`kswapd0`) during a build while Steam was installing a game; the headset rebooted | Build with the default 4 jobs, downloads paused ([BUILDING.md](docs/BUILDING.md#memory-pressure-can-crash-the-headset)) |
| Log noise | ~60 GL errors per second from `glGenerateMipmap` on a depth texture, two missing `gui_*.glsl` messages, HTC Cosmos controller profile rejected | Harmless; see [TECHNICAL-NOTES.md](docs/TECHNICAL-NOTES.md#log-messages-you-can-ignore) |

## Troubleshooting

| Symptom | Fix |
|---|---|
| The game is stuck in the headset and won't close | From a shell: `pkill -KILL -x openmw_vr` (a hung OpenMW-VR ignores the normal stop signal). Launch through `~/openmw-vr/OpenMW-VR`, which avoids the hang. |
| "No ShadowManager exists yet" error box | Patch 02 is missing; rebuild with `scripts/build.sh` |
| Menus upside down, buttons in the wrong place, pointer misses | You built the `openmw-vr` branch instead of the `openmw-vr-0.51-rc1` tag; `build.sh` builds the tag by default |
| `setup.sh` reports missing libraries | The binary release doesn't match your SteamOS; build from source |
| Build fails with `Killed` or runs out of memory | Rebuild with fewer jobs: `JOBS=4 scripts/build.sh` (it resumes where it stopped) |
| Need logs | Game: `~/.config/openmw/openmw.log`. SteamVR's per-session frame timing: `journalctl --user \| grep -A6 "Process openmw_vr"` |

## Sharing a binary release

After a successful build, `scripts/package.sh` creates
`~/openmw-vr/dist/openmw-vr-0.51-rc1-steamframe-aarch64.tar.xz` and its `.sha256`. Inside are stripped
binaries, the engine resources, `setup.sh`, the patches, license texts and `BUILDINFO.txt`. Morrowind's data
is never included. Publish it as a GitHub release asset rather than committing it (`dist/` is ignored).
OpenMW-VR is GPL-3.0: the release names the exact upstream tag and ships the patches, which together are
its complete source.

## Repository layout

| Path | Contents |
|---|---|
| [`scripts/build.sh`](scripts/build.sh) | Builds OpenMW-VR on the headset (idempotent, resumable) |
| [`scripts/setup.sh`](scripts/setup.sh) | One-time setup: game data, settings, launcher, Steam shortcut |
| [`scripts/package.sh`](scripts/package.sh) | Turns a finished build into a binary release tarball |
| [`scripts/diag.sh`](scripts/diag.sh) | Diagnostic run: Mesa GL error log and screenshots of the eye images |
| [`patches/`](patches) | The three source changes the Frame needs, each with a description |
| [`config/settings.cfg`](config/settings.cfg) | Recommended OpenMW settings |
| [`docs/BUILDING.md`](docs/BUILDING.md) | Building from source in detail |
| [`docs/TECHNICAL-NOTES.md`](docs/TECHNICAL-NOTES.md) | How the Frame's VR and graphics stack fit together, every problem we hit and its fix |
| [`docs/PERFORMANCE.md`](docs/PERFORMANCE.md) | Measurements, clock caps, and the plan for a higher frame rate |
| [`docs/JOURNAL.md`](docs/JOURNAL.md) | Chronological log of how this install came together |
| [`docs/RELEASE-README.md`](docs/RELEASE-README.md) | README shipped inside the binary release |
| [`docs/attic/`](docs/attic) | Superseded patches from earlier attempts, kept for reference |

## Credits

- [OpenMW](https://openmw.org) and **Mads Buvik Sandvei**'s [OpenMW-VR](https://gitlab.com/madsbuvi/openmw) did
  the heavy lifting; this repository only adapts the build for the Steam Frame.
- [SteamFrameRaylibQuickstart](https://github.com/Dinsmoor/SteamFrameRaylibQuickstart) showed that an OpenGL
  OpenXR app (`XR_KHR_opengl_enable` with the Xlib binding) renders correctly on the Frame.
- Valve's SteamOS for the Frame ships the compilers, SteamVR's ARM64 OpenXR runtime and Mesa's Zink/Turnip
  drivers that made a native build possible.

## License

The patches modify OpenMW-VR and, like it, are GPL-3.0 ([LICENSE](LICENSE)). The scripts and documentation
are released under the same license.
