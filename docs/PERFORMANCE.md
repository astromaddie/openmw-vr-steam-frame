# Performance

OpenMW-VR is playable on the Frame, but it doesn't reach the headset's refresh rate. These are the
measurements so far, what they mean, and the plan for improving them.

## Measurements

SteamVR logs a summary for each app session. After quitting, `journalctl --user | grep -A6 "Process openmw_vr"`
shows how many frames the compositor *presented* (72 per second), how many of those were *reprojected*
because the game didn't deliver a new frame in time, and the game's average CPU and GPU time per frame.

| Session (2026-10-01) | Clocks | Eye resolution | CPU per frame | GPU per frame | Reprojected | Game's own rate |
|---|---|---|---|---|---|---|
| 11.6 min of play | SteamOS default | 1440×1440 | 15.3 ms | 28.6 ms | 57% | ~31 fps |
| 10.7 min of play, bigger UI, mirror off | SteamOS default | 1440×1440 | 16.1 ms | 28.4 ms | 55% | ~33 fps |
| 2.6 min of play | **Performance mode** | **1728×1728** | 15.4 ms | **23.1 ms** | 44% | ~40 fps |
| Main menu only, headset not worn | default | — | 6.7 ms | 29.1 ms | 51% | ~35 fps |

The budget at 72 Hz is **13.9 ms** of CPU and of GPU time per frame. "Game's own rate" is presents minus
reprojected frames, divided by the session length.

## What the numbers say

- **The game runs at about a third to half of 72 fps, and SteamVR fills the gaps.** Reprojection re-presents
  the last frame warped to the newest head pose. That's why it feels smooth enough to play.
- **SteamVR picks the resolution.** With "Auto" render resolution it recommended 1728×1728 at first, dropped
  to 1440×1440 after measuring the game at default clocks, and went back to 1728×1728 in Performance mode.
  The panels are 2160×2160, so 1440 shows less than half the pixels the display has.
- **Frame time doesn't scale with clock speed.** CPU time stayed at 15–16 ms whether the CPU was capped at
  2.0 GHz or running at up to 3.1 GHz, and the GPU reported about 29 ms at the nearly empty main menu while
  its clock sat at 310–500 MHz. So a large part of each frame is waiting and per-frame overhead, not raw
  computation. That makes [profiling](#next-steps) the next step rather than more tweaking.
- **About 40 fps can feel worse than 36.** Between half rate (36) and full rate (72), SteamVR keeps switching
  between presenting new frames and reprojecting, so the motion cadence is uneven. That matches how
  Performance mode felt: sharper, but not smoother, maybe more stuttery.

## SteamOS clock caps

By default SteamOS limits the Frame well below what the chip can do:

| | Hardware maximum | SteamOS default | Performance mode |
|---|---|---|---|
| CPU prime core (cpu7) | 3052 MHz | 2035 MHz | 3052 MHz |
| CPU big cores (cpu2–4) | 3148 MHz | 2035 MHz | 3148 MHz |
| CPU mid cores (cpu5–6) | 2956 MHz | 2035 MHz | 2956 MHz |
| CPU little cores (cpu0–1) | 2265 MHz | 2035 MHz | 2265 MHz |
| GPU (Adreno 750) | 903 MHz | 629 MHz ("auto") | 903 MHz |

`steamosctl` reports it: in the default state `get-cpu-boost-state` is `disabled` and
`get-gpu-performance-level` is `auto` with a 629 MHz ceiling. Nothing was thermally throttled during our
tests (all cooling devices at 0, CPU around 64–71 °C). Choosing **Performance** in Steam's quick-menu
performance settings lifted both caps. It's worth using for OpenMW-VR, at the cost of more heat, fan noise
and battery drain.

## Current settings

The recommended [`settings.cfg`](../config/settings.cfg) changes only the font size and turns off the mirror
window. OpenMW's defaults were already light: shadows, water shader and refraction, distant terrain,
groundcover, post-processing and anti-aliasing are all off; view distance is 7168 units; up to 8 lights per
object; anisotropic filtering 4×. Turning the mirror window off made no measurable difference.

## Next steps

In rough order of effort:

1. **Lock the frame rate to a steady 36 fps** and pin the resolution, using SteamVR's per-app video settings
   for OpenMW-VR (app key `steam.app.<shortcut id>`; see [TECHNICAL-NOTES.md](TECHNICAL-NOTES.md#the-vr-stack)).
   At 36 fps the GPU has 27.8 ms per frame, so 1728×1728 (about 23 ms in Performance mode) fits with room to
   spare. This trades the uneven cadence for a steady one.
2. **Profile a session.** OpenMW writes per-frame timings when started with
   `OPENMW_OSG_STATS_FILE=<file>` (and optionally `OPENMW_OSG_STATS_LIST=<stats>`): event, update, physics,
   Lua, cull, draw and GPU time. That shows where the 15 ms of CPU time goes.
3. **Multiview.** Each eye is currently culled and drawn separately ("Disabling Multiview (OSG does not
   support multiview)"). Zink supports `GL_OVR_multiview2`, but OpenMW's multiview path needs an
   OpenSceneGraph with `OSG_HAS_MULTIVIEW` (3.7 / master); the 3.6.5 fork doesn't have it. Switching OSG
   means a full rebuild and some compatibility risk. In return it should roughly halve the per-eye CPU work,
   which matters doubly because Zink adds CPU cost to every GL call.
4. **Cheaper VR GUI.** Every visible VR GUI layer renders the GUI into its own 1024×1024 texture and
   regenerates its mipmaps every frame, even when nothing changed. Rendering a layer only when it changes,
   and giving the small HUD layers smaller textures, would save GPU time. The depth-texture mipmap call that
   Mesa rejects ~60 times a second (see [TECHNICAL-NOTES.md](TECHNICAL-NOTES.md#log-messages-you-can-ignore))
   is part of the same render-texture code.
5. **Settings trade-offs** if still needed: a shorter view distance and fewer lights per object reduce both
   CPU and GPU work.
