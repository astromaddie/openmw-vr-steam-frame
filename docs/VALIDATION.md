# Validation and reproduction

## Source and installer checks

Run `scripts/check.sh /path/to/patched/openmw-source` for installer, shell syntax
and production engine/Lua checks. Lua 5.4 or later is required. Installer tests use temporary
directories and do not access Steam or real saves.

Required installer scenarios: removable Steam library, alternate install name,
base game without expansions, optional expansions, spaces in paths, existing
settings, save copying without overwrite, corrupt package and wrong architecture.

## Device test protocol

Reserve the shared Frame immediately before an install/launch. Verify standby,
proximity and running scene applications before unattended work. Release as soon
as the run ends. Do not hold the device during compilation or while awaiting a
reply. Do not mute outputs for tests; if an audio change becomes necessary,
record both default and speaker-EQ sink states and register verified restoration
before changing anything.

1. Install a checksummed package and launch its Steam library entry.
2. Verify action/profile initialization and both eye images, then exit from the
   game and SteamVR separately. Repeat and inspect exit codes and XR errors.
3. Exercise focus loss, standby/resume, controller disconnect and recentre.
4. Create a character; check dialogue, inventory, journal, trade, combat and save/load.
5. Compare stereo at 0°, 90° and 180° yaw, with water, particles and weapon aim.
6. Check upgrade/reinstall persistence without removing user-owned data.

## Bounded offscreen diagnostics

For an idle-device capture, set `OPENMW_FRAME_FORCE_RENDER=1`,
`OPENMW_FRAME_DIAGNOSTIC_EXIT_SECONDS=12`,
`OPENMW_FRAME_DIAGNOSTIC_CAPTURE_FRAME=300` and
`OPENMW_FRAME_DIAGNOSTIC_DIR` to a writable directory in the Steam launcher.
Launch with `--skip-menu --start 'Seyda Neen'`. Add
`OPENMW_FRAME_SETTINGS_PREVIEW=1` for the native settings panel.
Restore the launcher after the process inherits its environment.

This mode uses synthetic poses, disables gameplay input and submits zero
composition layers. It normally exits if the session becomes FOCUSED. Only after
confirming the device is idle, `OPENMW_FRAME_CONFIRMED_IDLE=1` permits this mode
while focused, and only with a finite exit deadline of at most 60 seconds. It is
for image/startup diagnostics; it cannot establish display pacing or controller
behavior. Keep a scoped external watchdog and verify process teardown.

## Comparable performance runs

Keep the same package, save, route, resolution, refresh, quality, clock mode and
thermal starting condition for each comparison. Warm the scene before measuring.
Measure Seyda Neen outdoors, a Balmora route and an interior/combat route, followed
by a sustained session. Separate instrumented image captures from timing runs.

Use `OPENMW_OSG_STATS_FILE` with the upstream engine to record its frame-stage
statistics. Read compositor summaries after exit using `scripts/diag.sh`. Record
the actual units and elapsed measurement interval; report rendered application
fps separately from compositor refresh and reprojection. Compare full-resolution
eye images for every rendering or quality optimization.

## Results

2026-10-28 source checks: 39 tests passed against the complete patched engine:
11 installer/source-preparation, 10 XR/input/diagnostic, 3 GUI-pointer, 4 scale/posture
and 11 native Lua UI checks. Production helper executables and Lua modules are
exercised directly. Shell syntax and applied-source whitespace checks passed.

The native ARM64 Ubuntu 24.04 build passed with the complete ordered patch series through 19. Both VR and flat
engine targets compile; a separate `BUILD_OPENMW_VR=OFF` configuration also built.
ELF architecture, executable versions, shared-library resolution, source/patch
manifests and package checksums passed. The pinned engine revision is
`56a8e01390507375c9c2f2593e1c09e0df88c505`. The builder image identity is
`sha256:12e22760d3543992fa61c7f21ff1495a8692198b6d7f63a4dd2e65b754e5fe80`.

An executable OSG PNG round-trip check confirmed that the plugin preserves the
expected orientation without an extra vertical flip; the deliberately flipped
negative case failed. Render captures must still be inspected for scene correctness.

2026-10-28 author-binary startup comparison on SteamOS 0.5.6, glibc 2.39:
- Original release archive SHA256:
  `f57e246d9213d6ae0e50225953c14cc953a5f0093fa00d05d5a296f9ebd7029d`.
- Executable reports OpenMW 0.51.0, revision `56a8e01390`; all shared libraries resolve.
- New installer discovers the existing Steam installation and registers
  `OpenMW Frame`, shortcut appid `2924789393`, with the dedicated Frame profile.
- Steam launch creates a native OpenXR session and reaches SYNCHRONIZED in standby.
  The approximately 18-second session logged 1,453 invalid-operation GL warnings.
- This was a startup comparison, stopped by a scoped TERM after collection; it
  establishes neither rendered-eye correctness, clean in-game exit nor gameplay fps.
- The process was gone and the booking released after collection. Audio settings
  were not changed.
The inherited October 1 measurements remain in `PERFORMANCE.md` as historical
author evidence, not measurements of this fork.

Integrated startup diagnostics on the same device found a null VR GUI manager
access in `WindowManager` cleanup during early engine teardown (SIGSEGV at address
0x40, confirmed by GDB through a Steam launch). The patch series now guards partial
initialization cleanup and fixes the diagnostic identifier constructor reading its
own unconstructed string. Unused legacy shader lookups were also removed; the
installed GUI shaders are loaded by `getProgram("gui")`. The corrected native build
passes compilation; rendered startup and clean-exit checks remain required.
