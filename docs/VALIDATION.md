# Validation and reproduction

## Baseline-first verification

The starting point is the existing native Frame port, not a new VR engine:

- [Author release 1.0](https://github.com/stephen-moskal/openmw-vr-steam-frame/releases/tag/1.0), published 2026-10-02. Archive SHA256 `f57e246d9213d6ae0e50225953c14cc953a5f0093fa00d05d5a296f9ebd7029d`.
- [Author technical notes](https://github.com/stephen-moskal/openmw-vr-steam-frame/blob/main/docs/TECHNICAL-NOTES.md): unused GUI shader lookups and rejected HTC Cosmos bindings are documented nonblocking warnings. Shutdown failure and historical 33–40 fps are separate known limitations.
- [OpenMW-VR release source](https://gitlab.com/madsbuvi/openmw/-/tree/openmw-vr-0.51-rc1), pinned commit `56a8e01390507375c9c2f2593e1c09e0df88c505`, with the author's three Frame patches.

Verification order: (1) unchanged release and a separate profile, (2) normal Steam
menu/new-game/render/save/exit path, (3) one reproduced fix at a time. Native
settings and custom offscreen diagnostics remain separate from baseline evidence.
A headset display refresh or a standby process is not a rendered-gameplay result.

2026-10-29 artifact comparison: all 413 original engine/resource/license files
match the published archive. The remaining original file, `setup.sh`, had been
replaced with the isolated installer; `frame_setup.py` and `SHA256SUMS` are extra.
The installed engine SHA256 is
`8fc90cc4e6e3c0295f5b5054435b6240263cf642ddf34a8026fbd70c5fb2ae87`.
Its runtime dependencies resolve on SteamOS 0.5.6.

**OpenMW Frame Baseline**, Steam shortcut appid `3917841542`, launches that engine
without forced rendering, synthetic poses or preview flags. Its independent
profile is `~/.config/openmw-frame-baseline` and its data/save root is
`~/.local/share/openmw-frame-baseline`. The launcher retains the author's
`OPENMW_DISABLE_CRASH_CATCHER=1` shutdown workaround. The experimental
**OpenMW Frame** entry and its profile remain separate.

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

2026-10-28 source checks: 41 tests passed against the complete patched engine:
11 installer/source-preparation, 12 XR/input/diagnostic, 3 GUI-pointer, 4 scale/posture
and 11 native Lua UI checks. Production helper executables and Lua modules are
exercised directly. Shell syntax and applied-source whitespace checks passed.

The native ARM64 Ubuntu 24.04 build passed with the active ordered patch series through 20 plus 23–25. Experimental patches 21–22 are deferred. Both VR and flat
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

### 2026-10-29 normal-runtime checks

Tests use the unchanged author engine first, then the candidate, through Steam
with separate QA configuration/data. The stock compositor setting
`power.pauseCompositorOnStandby=false` allowed the original OpenXR session to
reach FOCUSED and submit 1,002 frames (1,000 presents in the collected sample).
No forced-render or synthetic-pose environment flags were used. The original
setting had no override and an effective value of true; cleanup removes the
temporary override and verifies that effective value.

The QA workload uses a supported `MENU` Lua script in a private `.omwscripts`
data directory. Its `onFrame` handler disables tutorial popups in QA player
storage, requests a save while synchronized, then requests quit using a
real-time deadline. Ordinary `--script-run` files cannot switch Lua console
contexts and immediately execute following Lua lines: those context changes
are deferred. Timer callbacks also lack the synchronization required by
`menu.saveGame`.

The original engine and candidate both reached Running and wrote QA saves.
Candidate save size was 66,524 bytes. Its built-in F12 capture contains HUD,
hands and interior geometry; the off-head view is not a stereo or interaction
acceptance check. X11 window grabs and the background screenshot API returned
blank images and are not used as scene-correctness evidence.

The original engine's native quit reproduced `GLX BadAccess` in
`X_GLXMakeCurrent`. Patch 23 stops render threads before GUI teardown and
eliminated that error in the candidate. A later SIGSEGV occurred after the
engine's peaceful-exit log. A parent-launched
GDB trace identified the retained owner: `RenderBinPrototypeList` →
`osgUtil::RenderBin` → `MWRender::DistortionCallback` →
`osg::FrameBufferObject`. Patch 24 releases the Distortion prototype's callback
alongside the existing DepthSorted callback while the rendering context still
exists. It clears only this postprocessor's callback.

Candidate `eae2fdd` passed two normal-runtime checks with the crash catcher enabled:

| Workload | Observed result | Raw engine exit status |
| --- | --- | --- |
| Direct-start interior, synchronized QA save, native quit | Save succeeded; no late graphics exception or crash-handler children | 0 |
| `--load-savegame` of the QA save, run, native quit | `Reading save file`, cell load and Running confirmed | 0 |

The direct-start interior places the player at an unsuitable location and logs
falling-into-void resets. These runs verify lifecycle and save/load, not ordinary
New Game positioning or scene correctness. The installer continues to retain the
author's crash-catcher safeguard.

The shell records the child's status after waiting for it. Restore the temporary
Steam launcher by atomic replacement: truncating that live shell script can erase
its remaining status-recording lines and create a false missing-result diagnosis.
Both runs restored the baseline launcher SHA256
`f8b5faeca1c4b14a9b4bb0bb41f80423b12c1079ee86f1650f8e6dabf1e67a99`,
removed the temporary compositor override and left no owned game/reaper/debugger
processes. Audio sinks and their volumes/mutes were unchanged.

Initial clean-exit package: `openmw-vr-0.51-rc1-frame-eae2fdd-aarch64.tar.xz`, SHA256
`20c8a1fd4acdc5b94b0c2dfddda5714dedc67022ab067b517bde42cf561bf8de`.
Engine ELF build ID: `b99052846eb94fb4faaa24e5b6ce0f8f32ccf255`.

The normal `--skip-menu --new-game` path also reached the Imperial Prison Ship,
with Jiub, the name-entry window and the native virtual keyboard visible in an
F12 capture. Escape skipped the introductory movie. The private QA save
succeeded, there were no falling-into-void resets, and native quit returned 0.

A separate `OPENMW_FRAME_SETTINGS_PREVIEW=1` run captured Comfort, Controls,
HUD & Menus, Display, Accessibility and Room. The supported Lua input-trigger API
navigated between tabs; MenuBack removed the panel, and native quit returned 0.
The capture exposed crowded active labels in the fixed-width tab spacing.
Patch 25 uses the native horizontal layout and actual font widths for the tabs.
Physical
controller pointing, stereo presentation, comfort and sustained gameplay timing
remain separate acceptance checks.

### Final package and repeat checks

`openmw-vr-0.51-rc1-frame-2d93d03-aarch64.tar.xz` is installed behind the regular
**OpenMW Frame** Steam entry. Binary archive SHA256:
`925de7a7c5af960f0e2f13d9621f173d3d6113ca09e2a19e14c8a1eddfa95a4a`.
Corresponding engine-source archive SHA256:
`6b5baf0f930dfec144e1a2dca1d54048edf9df7070f7e69075b99bfb5815b141`.

All 41 source/installer checks passed through patch 25. The package's source and
patch manifests, internal checksums, AArch64 architecture and shared-library
checks passed. The final change is Lua layout only; all three engine binaries
retain their preceding build IDs.

The final package repeated all six tab captures and MenuBack. The long active
labels have distinct borders with no neighbour overlap. Native quit returned 0.
The actual regular Steam launcher then reached OpenXR FOCUSED using its ordinary
Frame profile and closed through `WM_DELETE_WINDOW`, returning 0. That final
launcher test added only `--no-sound` for unattended quiet; it did not add the QA
addon, force rendering or enable the settings preview. It does not verify audio.
No owned game, reaper or debugger processes remained after either run.

The installed launcher SHA256 is
`755fc473114cf111de6aadfb8aae6c317517c63feb87c92d771f8de8ba6487cb`.
The original Baseline launcher hash still matches the value above. The temporary
power override was removed and its original effective value verified. Speaker
output remained unmuted at 61%; the separate speaker-EQ sink remained unmuted at
90%. Existing save-file hashes matched across the final checks.

After preserving the identities, reproduction details, useful captures and the
shutdown trace, obsolete packages, debug binaries, build caches and private QA
data were removed. This final testing pass removed approximately 3.3 GiB of
allocated files on the Mac and 1.5 GiB on the Frame. The author baseline, final
installed release, source, current binary/source archives and user profiles/game
data remain. The shared device booking and Mac build slot were released.
