# Foreground NPC / modal UI reproduction

Use this addon only in a separate validation configuration and user-data directory
with an owned Morrowind installation. Add this directory to `data` and
`baselineqa.omwscripts` to `content`; retain the normal builtin and game content.
Start with `--skip-menu --new-game`. Keep the same device pose, settings and
addon for before/after captures. No save is requested.

1. Skip the intro movie, enter a temporary character name and confirm it.
2. Wait for the movement tutorial. The player script waits at least 25 seconds
   and a paused world, then samples the actual View and DefaultWindow poses.
3. The global script places an additional `chargen boat guard 1` between those
   poses. The paused model deliberately covers the panel's line of sight.
4. Use native F12 captures: the old build hides the tutorial/OK; the corrected
   build draws the complete panel over the same model. Confirm OK and capture
   its dismissal and the resumed world. The menu script quits after 75 seconds.

The automated run used Return to dismiss the tutorial. Controller aiming and
clicking exercise the separate native PointerActivate/MyGUI path. The C++ routing
regression covers GUI priority, masks, coordinates and unchanged gameplay range;
the real OSG fixture covers both-eye cull/bin/depth policy.

The scripts use supported menu/player/global Lua APIs. Runtime poses are sampled
only in `onVRFrame`; no forced rendering or synthetic tracking is required.
The nonblocking OpenMW tutorial popups are disabled only in the private profile;
the legacy Morrowind movement message remains enabled.
