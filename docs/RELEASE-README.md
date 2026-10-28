# OpenMW Frame — ARM64 Linux package

Run `./setup.sh` on the Steam Frame with Steam running, then launch **OpenMW
Frame** from the Steam library. You must own Morrowind; Steam app 22320 is detected
across its libraries. No game data is included.

For another installation: `./setup.sh --morrowind-dir "/path/to/Morrowind"`.
The path can also name the `Data Files` directory. Only installed expansions are
enabled, in Morrowind / Tribunal / Bloodmoon order.

The installer verifies SHA256SUMS, ARM64 architecture and shared-library
availability. Keep this directory installed: the persistent launcher points here.
Run setup again after moving the directory. Reinstallation preserves settings and
saves. Configuration is in `~/.config/openmw-frame`, saves in
`~/.local/share/openmw-frame/saves`, respecting XDG overrides.

Use `--import-saves PATH` to copy saves from another OpenMW profile without
replacing existing files. The original profile is preserved. Use `--no-steam`
when configuring without adding a shortcut.

The package includes engine binaries/resources, private non-driver libraries,
source patches, notices and build metadata. See BUILDINFO.txt and LIBRARIES.json.
Graphics drivers, glibc and SteamVR’s OpenXR runtime come from SteamOS. Missing
libraries or checksum failures stop installation.

Source: https://github.com/astromaddie/openmw-vr-steam-frame . The corresponding
patched engine-source archive accompanies the binary archive. Upstream engine:
https://gitlab.com/madsbuvi/openmw at the commit named in BUILDINFO.txt.

This is a development package until the published validation record satisfies the
72 rendered fps / 1728² release gate. Select the documented refresh rate in
SteamVR’s per-title settings. Compositor reprojection does not establish that gate.
