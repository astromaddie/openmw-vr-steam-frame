# Building OpenMW-VR on the Steam Frame

Everything here runs **on the headset**. The Frame's SteamOS VR image already includes a full native
toolchain (GCC 15.1, CMake 3.29, Ninja 1.12, Git, Python 3), so the build needs nothing installed into the
read-only OS and no cross-compiler. Building on the headset also guarantees the result links against exactly
the system libraries it will run with.

## Getting a shell on the headset

Use either:

- **Konsole in Desktop Mode** on the headset, or
- **SSH** from another computer (what we used). The Frame's user is `steamos`. On SteamOS that generally
  means giving the user a password in Desktop Mode (`passwd`) and enabling the SSH server
  (`sudo systemctl enable --now sshd`); then from your computer:

  ```sh
  ssh steamos@<headset-ip>
  # optional: key-based login and a short alias
  ssh-keygen -t ed25519 -f ~/.ssh/frame_ed25519 -N ""
  ssh-copy-id -i ~/.ssh/frame_ed25519.pub steamos@<headset-ip>
  printf 'Host frame\n  HostName <headset-ip>\n  User steamos\n  IdentityFile ~/.ssh/frame_ed25519\n  IdentitiesOnly yes\n' >> ~/.ssh/config
  ```

Then put this repository on the headset, for example `git clone https://github.com/stephen-moskal/openmw-vr-steam-frame.git ~/openmw-vr-steam-frame`,
or `scp -r openmw-vr-steam-frame frame:` from your computer.

## Running the build

```sh
systemd-run --user --collect --unit=openmw-vr-build -p Nice=19 -p MemoryHigh=6G -p MemoryMax=8G \
    ~/openmw-vr-steam-frame/scripts/build.sh
```

- `systemd-run --user` runs the build as a background service, so it survives an SSH disconnect.
  Running `scripts/build.sh` directly in a terminal works too.
- `Nice=19` keeps the build from competing with SteamVR, and the memory limits keep the compiler from
  pushing the rest of the system into swap. With 6 parallel jobs the build peaked at about 6 GB; the
  default is 4. Read [Memory pressure can crash the headset](#memory-pressure-can-crash-the-headset) first.
- Watch it with `tail -f ~/openmw-vr/logs/build.log`. `~/openmw-vr/logs/status` reads `RUNNING`, then `OK`
  or `FAILED <exit code>`.
- The script is resumable: run it again after a failure or an interruption and it skips finished steps,
  re-applies only missing patches and lets Ninja continue where it stopped.
- Overrides: `JOBS=<n>` sets the number of parallel compile jobs (default 4; 6 is faster when nothing else
  is running, fewer if a compiler gets `Killed`), `ROOT=<dir>` builds somewhere other than `~/openmw-vr`,
  and `REF=<tag>` builds a different OpenMW-VR tag.

Pass overrides to `systemd-run` with `-E`, for example `-E JOBS=4`.

## What build.sh does

| Step | Details |
|---|---|
| Boost 1.83.0 | SteamOS ships Boost's runtime libraries but no headers or CMake files. OpenMW needs `program_options` and `iostreams`, so they're built as static libraries into `~/openmw-vr/deps`. Only `stream.hpp` is used from iostreams, so it's built without compression filters. |
| Source | Shallow clone of the **`openmw-vr-0.51-rc1`** tag from `https://gitlab.com/madsbuvi/openmw` into `~/openmw-vr/src`. Not the `openmw-vr` branch: see [TECHNICAL-NOTES.md](TECHNICAL-NOTES.md#which-openmw-vr-source-to-build). |
| Patches | Applies each file in [`patches/`](../patches) unless it's already applied. |
| Configure | CMake with Ninja, `Release`. OpenMW's options are set to download and statically link the libraries SteamOS doesn't have (table below). The launcher, editor and wizard (Qt tools) aren't built. |
| Build | `cmake --build -- -k 0`: Ninja keeps compiling past a failure so one run shows every broken file. |

### Where each dependency comes from

| From SteamOS (dynamically linked) | Downloaded and linked statically by OpenMW's CMake | Built by build.sh |
|---|---|---|
| SDL2 2.30, FFmpeg 7.0, OpenAL Soft 1.23, LuaJIT 2.1, ICU 74, SQLite 3.45, LZ4, zlib, FreeType, libpng, libjpeg, X11, OpenGL (libglvnd → Mesa Zink) | OpenSceneGraph 3.6.5 (OpenMW's fork, commit `01cc2b58`), Bullet 3.17 (double precision), MyGUI 3.4.3, recastnavigation (OpenMW's fork, `03259f32`), yaml-cpp (`c2680200`), OpenXR SDK `release-1.0.24` (static loader with bundled jsoncpp) | Boost 1.83.0 (`program_options`, `iostreams`) |

The OpenXR loader is built into the binary, so nothing needs installing for OpenXR either. At runtime it
reads `~/.config/openxr/1/active_runtime.json`, which on the Frame points at SteamVR's ARM64 runtime.

### CMake options and why

| Option | Why |
|---|---|
| `OPENMW_USE_SYSTEM_OSG/BULLET/MYGUI/YAML_CPP=OFF` | Not packaged on SteamOS; OpenMW fetches pinned versions |
| `OPENMW_USE_SYSTEM_RECASTNAVIGATION=OFF` | Same (this is OpenMW's default) |
| `CMAKE_PREFIX_PATH=~/openmw-vr/deps`, `Boost_USE_STATIC_LIBS=ON` | Use the Boost built above |
| `CMAKE_CXX_FLAGS="-include cstdint"` | Some pinned dependencies predate GCC 13, which stopped including `<cstdint>` transitively; a precaution for GCC 15 |
| `BUILD_OPENMW_VR=ON`, `BUILD_OPENMW=ON`, `BUILD_MWINIIMPORTER=ON` | The VR game, the same engine without VR, and the Morrowind.ini importer `setup.sh` uses |
| `BUILD_LAUNCHER/OPENCS/WIZARD=OFF` | Qt tools aren't needed and would pull in more of Qt |
| Other `BUILD_*` tools `OFF` | Not needed to play; saves build time |

## Patches

| Patch | Why the Frame needs it |
|---|---|
| [`01-skip-osgdb-dae-without-collada.patch`](../patches/01-skip-osgdb-dae-without-collada.patch) | SteamOS has no COLLADA DOM, so the fetched OpenSceneGraph never builds its `.dae` plugin, and OpenMW's configure step fails on the missing `osgdb_dae` target. The patch drops the plugin when COLLADA is missing. Vanilla Morrowind models are NIF, so only some mods notice. |
| [`02-shadowmanager-guard.patch`](../patches/02-shadowmanager-guard.patch) | OpenMW-VR's VR GUI and laser pointer set up their render state before OpenMW has created its ShadowManager, which aborts startup with "No ShadowManager exists yet". The patch only disables shadows on them once a ShadowManager exists. The upstream source already comments out a third such call for the same reason. |
| [`03-larger-vr-ui.patch`](../patches/03-larger-vr-ui.patch) | Makes every auto-sized VR menu and HUD panel about a third larger (768 instead of 1024 pixels per meter), so Morrowind's small text is easier to read. The panels' render textures keep their size, so it costs no GPU time. Optional. |

## Build output

`~/openmw-vr/build` is also the install: the engine runs in place, with its local `openmw.cfg` pointing at
`./resources`. The files that matter are `openmw_vr`, `openmw`, `openmw-iniimporter`, `openmw.cfg`,
`defaults.bin`, `overrides.bin`, `gamecontrollerdb.txt`, `openxrinteractionprofiles.xml` and `resources/`.
`scripts/package.sh` copies exactly those into the binary release.

## Timing and resources

Measured on the Frame (Snapdragon 8 Gen 3, 8 cores; SteamVR running), 6 parallel jobs, nice 19:

| Phase | Time |
|---|---|
| Boost download and build | about 1 minute |
| Clone, patch, configure (includes downloading the dependencies) | under 1 minute |
| Compile and link (from scratch, 1777 steps) | about 35 minutes with 6 jobs; expect longer with the default 4 |
| Rebuild after switching from the branch to the release tag | 16 minutes (323 steps) |

Disk: about 5 GB under `~/openmw-vr`. Memory: the Lua-binding sources need about 1.2 GB per compiler, and
with 6 jobs the build peaked just under the 6 GB `MemoryHigh` limit without any compiler being killed.

## Memory pressure can crash the headset

On SteamOS 0.4.3 (kernel `6.18.0-ge66bc2ca6f8c`) the headset **crashed and rebooted** during a build: a
kernel NULL-pointer dereference in `kswapd0`, the kernel thread that reclaims memory when it runs low. At
the time the build was compiling OpenSceneGraph with 6 jobs while SteamVR was running and Steam was
installing a large game. Three earlier builds with the same settings on SteamOS 0.4.2 were fine. To make it
less likely:

- pause Steam downloads and installs, and close games, before building
- keep the default `JOBS=4` (or lower) and the `MemoryHigh`/`MemoryMax` limits
- don't wear the headset during the build. A crash only costs a reboot: `/home` is journaled ext4 and
  `build.sh` resumes where it stopped.

## Updating

- **A new OpenMW-VR release:** `REF=<new tag> scripts/build.sh`. The script switches the checkout,
  re-applies the patches and rebuilds what changed. A patch that no longer applies stops the build;
  check whether upstream fixed that issue and drop or refresh the patch.
- **A SteamOS update:** the build keeps working as long as SteamOS still ships the same library versions.
  It survived the 0.4.2 → 0.4.3 update. If `ldd ~/openmw-vr/build/openmw_vr | grep "not found"` prints
  anything, delete `~/openmw-vr/build` and run `build.sh` again.

## Uninstalling

```sh
rm -rf ~/openmw-vr ~/openmw-vr-steam-frame      # build, binaries, launcher, scripts
rm -rf ~/.config/openmw ~/.local/share/openmw   # OpenMW settings, logs and saved games
```

Then remove **OpenMW-VR** from the Steam library (Manage → Remove non-Steam game from your library).
Your Morrowind installation isn't touched by any of this.
