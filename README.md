# OpenMW Frame

Native standalone **Morrowind VR on Steam Frame**, based on
[OpenMW-VR](https://gitlab.com/madsbuvi/openmw) and
[Stephen Moskal’s Frame port](https://github.com/stephen-moskal/openmw-vr-steam-frame).
The engine runs on the headset as ARM64 Linux software through SteamVR OpenXR.

This fork develops Frame controls, clean XR shutdown, persistent player profiles,
native tabbed VR settings, world-size and seated-height adjustment, and reproducible
packages. The release target is **72 rendered fps at 1728² per
eye**. The ancestor’s 33–40 fps measurements are historical; see
[validation](docs/VALIDATION.md) for this fork’s evidence and remaining gates.

You need your own Morrowind game data. No Bethesda assets are included. Vanilla
Morrowind is the initial target; Tribunal and Bloodmoon are enabled when installed.
Multiplayer and modpack certification are outside the initial release.

## Install a package

Unpack the checksummed release archive into a persistent directory on your Frame,
then run its `setup.sh` while Steam is running:

```sh
./setup.sh
# For another installation or a directory containing Morrowind.esm:
./setup.sh --morrowind-dir "/path/to/Morrowind"
```

Setup finds Steam app 22320 across Steam libraries and adds **OpenMW Frame** to
Steam. Launch that entry from the headset. Setup checks package integrity, ARM64
architecture and runtime libraries before creating the player profile.

From a Mac or Linux computer with SSH access and rsync, you can also copy an
unpacked release and install it with:

```sh
python3 scripts/install_remote.py /path/to/unpacked-release --host frame
```

Use `--no-steam` to configure without registering a shortcut. To copy existing
OpenMW saves without overwriting destination saves:

```sh
./setup.sh --import-saves "$HOME/.local/share/openmw/saves"
```

Settings live in `~/.config/openmw-frame`; saves in
`~/.local/share/openmw-frame/saves` (or the corresponding XDG paths). Reinstalling
keeps them. Other OpenMW profiles are left alone. Keep your installed release
folder: the Steam launcher points to its executable and resources.

## Build on macOS, Linux or Windows

The Docker route produces ARM64 Linux executables on all three hosts. The engine
revision, source patches and Boost checksum are pinned. Other native dependencies
are fetched by the pinned engine’s CMake files; Ubuntu package versions and
container identity belong in the build manifest.

**macOS:** install Docker Desktop from its official installer, or use an existing
ARM64 Colima installation. With Colima, select its context explicitly:

```sh
brew install colima docker git python rsync
colima start --cpu 2 --memory 6
export DOCKER_CONTEXT=colima
```

**Linux:** install Docker Engine using your distribution’s official Docker
instructions, plus Git and Python. An x86_64 host also needs Docker’s ARM64 build
emulation; Docker Desktop includes it. A native ARM64 host builds directly.

```sh
sudo apt-get update
sudo apt-get install git python3 rsync
# Confirm the Docker daemon is available before building:
docker info
```

**Windows:** install WSL2 with Ubuntu and Docker Desktop, then enable Docker’s
integration for that WSL distribution. Run the Linux commands inside WSL:

```powershell
wsl --install -d Ubuntu
```

```sh
sudo apt-get update
sudo apt-get install git python3 rsync
# Run inside WSL, with Docker Desktop running:
docker info
```

Then, on any host:

```sh
git clone https://github.com/astromaddie/openmw-vr-steam-frame.git
cd openmw-vr-steam-frame
./scripts/build_container.sh
# Build log: .build/logs/build.log
# Build status: .build/logs/status
```

The wrapper limits the build to two jobs and 4 GB of container memory. On x86_64,
ARM emulation is slower. Set `OPENMW_FRAME_BUILD_ROOT` to put artifacts on another
disk. Shared machines must reserve their build slot before running the wrapper.

To package a completed container build (same image and mounted build root):

```sh
docker run --rm --platform linux/arm64 --memory=4g --cpus=2 \
  -v "$PWD:/repo:ro" -v "$PWD/.build:/work" -e ROOT=/work \
  openmw-frame-builder bash /repo/scripts/package.sh
```

The output includes the binary archive, an engine-source archive, checksums,
licenses, private redistributable libraries and build metadata. Graphics drivers,
glibc and SteamVR remain supplied by the headset. Package installation must pass
its library checks on the supported SteamOS version.

Native builds on the Frame remain possible with `scripts/build.sh`, using the
headset’s installed development libraries. Off-device builds avoid competing with
SteamVR for CPU and memory. See the historical [build notes](docs/BUILDING.md)
for the ancestor’s native procedure; its versions and timing are dated snapshots.

## Development checks

```sh
./scripts/check.sh
# Include production engine/Lua checks after applying the patches:
./scripts/check.sh /path/to/patched/openmw-source
```

[Architecture](docs/VR_ARCHITECTURE.md) records the rendering and persistence
interfaces. [Validation](docs/VALIDATION.md) defines device and performance checks.
[Frame settings](docs/FRAME_SETTINGS.md) documents the native tabbed panel and
controller map. The approved [settings mockup](docs/mockups/vr-settings.html)
records its design; the game panel uses reusable native OpenMW controls.

Engine changes stay in `patches/`, applied to the pinned OpenMW-VR source. Preserve
`BUILD_OPENMW_VR=OFF` and the flat `openmw` target. Keep game data out of Git and
release packages. OpenMW is GPLv3; dependency notices accompany binary packages.
