# Attic: superseded fixes

Kept for reference only. **Don't apply these.** The current build uses the `openmw-vr-0.51-rc1` tag and the
patches in [`../../patches`](../../patches). See [JOURNAL.md](../JOURNAL.md) for the story.

## Fixes for the `openmw-vr` branch (`c87d820`)

The branch tip that OpenMW-VR's docs point to doesn't compile on Linux. These changes got it building; the
release tag contains equivalent or better fixes for all of them.

- [`branch-merge-fallout.patch`](branch-merge-fallout.patch) restores
  `World::getActivationDistancePlusTelekinesis()` and drops the obsolete "force shaders" argument from a
  `recreateShaders()` call.
- Include paths and a rename, applied with `sed`:

  ```sh
  sed -i 's|<extern/oics/tinyxml.h>|<extern/oics/tinyxml/tinyxml.h>|' \
      components/xr/interactionprofiles.cpp apps/openmw/mwvr/openxrinput.cpp
  sed -i 's|<extern/oics/ICSInputControlSystem.h>|<oics/ICSInputControlSystem.h>|' apps/openmw/mwvr/vrinputmanager.cpp
  sed -i 's/mDistanceToFacedObject/mDistanceToFocusObject/; s/getFacedObject()/getFocusObject()/' \
      apps/openmw/mwworld/worldimp.cpp
  ```

Even when built, the branch draws every VR GUI panel upside down (an extra texture-matrix flip in
`components/myguiplatform/myguirendermanager.cpp`), which the tag removes.

## A wrong fix

[`03-gl-swapchain-flip.patch`](03-gl-swapchain-flip.patch) adds an opt-in `OPENMW_VR_FLIP_SWAPCHAIN=1` that
flips each eye vertically when copying it into SteamVR's swapchain. We wrote it believing SteamVR on the Frame
read OpenGL images top row first. It doesn't: SteamVR handles OpenGL orientation correctly, and the flip
turns the world upside down. The real problem was the branch's GUI flip above.
