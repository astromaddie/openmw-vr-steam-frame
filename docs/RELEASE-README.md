# OpenMW-VR for the Steam Frame — prebuilt aarch64 release

A native ARM64 build of [OpenMW-VR](https://gitlab.com/madsbuvi/openmw) (OpenMW with OpenXR VR support,
by Mads Buvik Sandvei) that runs standalone on Valve's Steam Frame under SteamOS. It talks to SteamVR's
native ARM64 OpenXR runtime directly: no PC, no streaming, no x86 emulation.

You need:

- a Steam Frame on SteamOS 0.4.x (`BUILDINFO.txt` names the exact build this was made on)
- The Elder Scrolls III: Morrowind from Steam (app 22320) installed on the headset
- a terminal on the headset (SSH, or Konsole in Desktop Mode)

## Install

1. Copy the tarball to the headset and unpack it into `~/openmw-vr`:

   ```sh
   mkdir -p ~/openmw-vr
   tar -C ~/openmw-vr -xJf openmw-vr-0.51-rc1-steamframe-aarch64.tar.xz
   ```

2. With Steam running on the headset, run the setup script:

   ```sh
   ~/openmw-vr/openmw-vr-0.51-rc1-steamframe-aarch64/setup.sh
   ```

   It checks that every library resolves, points OpenMW at Steam's Morrowind install
   (`~/.config/openmw/openmw.cfg`), writes recommended settings (`~/.config/openmw/settings.cfg`), creates
   the launcher `~/openmw-vr/OpenMW-VR` and adds it to your Steam library. Files that already exist are
   left alone.

3. In the headset, launch **OpenMW-VR** from the Steam library (it is listed with non-Steam games).

## If setup.sh reports missing libraries

This release uses SteamOS's own libraries (FFmpeg, ICU, LuaJIT, SDL2, OpenAL and others). A SteamOS update
can replace them with versions this build was not linked against. In that case build from source with the
[openmw-vr-steam-frame](https://github.com/stephen-moskal/openmw-vr-steam-frame) scripts (about 45 minutes on the headset).

## Contents

| Path | What it is |
|---|---|
| `openmw_vr` | OpenMW-VR, the VR game |
| `openmw` | the same engine without VR (flat screen) |
| `openmw-iniimporter` | imports Morrowind.ini settings; setup.sh uses it |
| `openmw.cfg`, `defaults.bin`, `resources/`, ... | engine data; the release runs in place |
| `setup.sh` | the one-time setup described above |
| `patches/` | the changes made to the upstream source for the Frame |
| `licenses/` | OpenMW (GPL-3.0) and the libraries linked in statically |
| `BUILDINFO.txt` | exact source revision and build environment |

## Source

OpenMW-VR is licensed under the GPL-3.0. This build is the upstream tag named in `BUILDINFO.txt` with the
patches in `patches/` applied. The build scripts and full documentation are at
https://github.com/stephen-moskal/openmw-vr-steam-frame. Morrowind's game data is not included; you need
your own copy.
