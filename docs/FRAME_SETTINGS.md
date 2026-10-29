# Native Frame VR settings

Patch 10 adds a paused native MWUI panel using the engine's existing dark/gold
MyGUI-backed templates, fonts and VR pointer layer. Open it from **VR Settings**
in the actual pause menu or legacy VR meta menu. Back returns to the originating
menu. No bitmap assets or browser runtime are used.

Six tabs: Comfort, Controls, HUD & Menus, Display, Accessibility, Room.
Numeric rows use bounded minus/plus steppers; the existing Lua settings renderer
provides numeric text entry, not a stable slider primitive. This is not exact
slider parity with the approved mockup. Display and audio buttons open the real
native Options window, without pretending unsupported features exist.

## Setting map

| Control | Native backing and consumer |
| --- | --- |
| Turning | `OMWVRInputControls` storage `SmoothTurn`, `SnapTurnRate`, `SmoothTurnSensitivity`; existing `inputs/player.lua` turning; speed stored in radians/second |
| Dominant hand | `[VR] left handed mode`, `VR::setLeftHandedMode` |
| Movement direction | `[VR] hand directed movement`; animation/physics consumers |
| Haptics | `[VR] haptics enabled`; `_setOutputValue` now sends zero amplitude while disabled |
| Crosshairs | `[VR] show 3D crosshairs`; world's `processChangedSettings` updates rendering |
| Physical sneak | Existing controls storage `PhysicalSneak` and player.lua consumer |
| HUD location | Existing `SpacesGroup.HUDSpace` subscription |
| Menu/HUD scale | Persistent `SettingsFrameVR.menu_scale` / `hud_scale`; existing VR layer pixels-per-metre configuration, bounded 0.7–1.5 |
| Menu distance | `SettingsFrameVR.menu_distance`, bounded 0.6–2m; existing `DefaultWindow` derived-space offset; preserves X/Z and rotation |
| Recenter/calibrate | Existing `_recenterXY` / `_recenterZ` reference-space path |
| Profile | Persistent `SettingsFrameVR.defaults_profile`: `standard` or `frame_personal` |

Fresh profile selection is Standard, snap 30. Selecting a defaults profile preserves explicit current settings. Comfort Tab
Defaults applies Standard snap 30 or Personal smooth 120 degrees/second. Merely opening the panel does not overwrite saved
turning or unknown fields. Tab Defaults resets only that tab; Comfort uses the
selected profile. Display and Room have no meaningless Defaults control.
Native C++ values use normal Settings persistence; Lua values use persistent
player storage. No section-wide reset occurs.

The existing DefaultWindow base is 1 metre forward, 0.25m below view; an unset
menu-distance value leaves existing space offsets untouched. Explicit distance
changes/defaults use that actual native base. Stored scale/distance values are
checked for type, finiteness and bounds before geometry or division.

XR navigation consumes the MenuOnly `MenuUp/Down/Left/Right/MenuSelect` triggers
from patch 04 and re-registers after the existing menu heartbeat. A while a
control has pointer focus belongs exclusively to existing PointerActivate;
otherwise MenuSelect activates the selected control. Native MenuBack reaches
WindowBase::exit and preserves the originating menu. SDL fallback remains.

## World size and posture (patch 11)

World Size is apparent size, 25–400%, backed by native `[VR] world scale`
(default 1, physical-to-game multiplier = 100 / displayed percent). The shared
world adapter scales tracked head/hand translations before world-anchor
composition, rendered eye translations, derived-space offsets, physical hand
adjustment and scene GUI geometry. Absolute Lua menu positions scale their
physical displacement from the anchor. Scene inverse-model picking uses the
same scaled quad, preserving angular size and pointer coordinates. Raw
`locateSpace`, `fromXR`/`toXR`, physical combat velocity and submitted `localViews`
retain runtime units; compile-time `UnitsPerMeter` is unchanged. The dormant
compositor-GUI branch remains unused by this port.

Seated Mode uses native `[VR] seated` (default false); Height Offset uses native
`[VR] height offset` (default 0m, -1..1m). Settings persist through OpenMW's normal
Settings store. Non-finite writes are rejected; loaded scale/height values are
bounded with finite fallbacks before use. Scale and height are latched at the
XR update boundary. The offset is applied once to the shared world anchor in
physical metres, so camera and hands move together without changing scale.

The first valid tracked head sample in standing mode establishes a session-local
standing center. Enabling Seated captures a separate active center; returning to
standing restores the retained standing center. Calibrate Standing replaces the
standing center; Calibrate Seated replaces only the seated center. XY Recenter
and focus regain preserve height. Physical sneak compares head height against
the active posture center in metres, retaining its physical threshold at every
world scale. No roomscale locomotion is enabled by this change.

A fresh session saved as seated has no standing calibration. It safely centers
on the seated pose and shows the instruction to stand, disable Seated Mode,
then Calibrate Standing. No guessed standing height is used. A LOCAL reference
space change invalidates calibration at the runtime's change time; current-pose
centering is recovered only from valid tracking, and standing calibration is
requested again. Absolute LOCAL coordinates are never persisted. Invalid or
orientation-only tracking cannot calibrate height; a pending capture waits for
valid position and orientation tracking. Synthetic diagnostic poses cannot
establish a standing calibration.

Native private API map (`openmw.vr._frameSettingGet/Set`):

| Key | Access | Meaning |
| --- | --- | --- |
| `world scale` | Read/write | Requested `[VR] world scale`, finite 0.25–4 multiplier |
| `height offset` | Read/write | Requested `[VR] height offset`, finite -1..1 metres |
| `seated` | Read/write | Requested `[VR] seated`, 0/1 |
| `applied world scale` | Read | Frame-boundary world multiplier used by Lua physical menu offsets |
| `applied height offset` | Read | Frame-boundary height, used to refresh menu anchors |
| `applied seated` | Read | Active posture, used to refresh menu anchors |
| `standing calibrated` | Read | Session-local valid standing baseline exists, 0/1 |
| `posture center` | Read | Session-local active LOCAL vertical center in metres, used by physical sneak |

`_recenterXY()` requests horizontal recenter; `_recenterZ()` requests active
posture calibration without changing world scale. These APIs predate patch 11.
No vignette, fabricated telemetry or unsupported render scale is introduced.

## Reproduction and evidence

Apply the complete ordered patch series to the pinned OpenMW source using
`scripts/build.sh`. The UI preserves patch 04's `isFocused` binding. Integrated
build and runtime results are recorded in [validation](VALIDATION.md).

Reproducible script tests (Python 3, pinned embedded Lua dependency):

```sh
python3 -m venv /tmp/openmw-ui-tests
/tmp/openmw-ui-tests/bin/pip install -r tests/engine_ui/requirements.txt
OPENMW_SOURCE=/path/to/patched/openmw /tmp/openmw-ui-tests/bin/python -m unittest discover -s tests/engine_ui -v
```

Eleven tests pass against the shipped Lua script: preservation, profiles, tab-scoped
defaults, controls/calibration, native options, XR registration/heartbeat,
A/pointer ownership, syntax, and source-level haptic dispatch wiring. The harness
stubs native APIs; it does not establish rendered geometry, physical pointer or
controller operation, audio/haptic output, or C++ build success.

`OPENMW_FRAME_SETTINGS_PREVIEW=1` opens the panel once a real game is running,
through the same production entrypoint as the pause button. It is off by default
and does not synthesize input or change settings. The normal-runtime idle-device
method in [validation](VALIDATION.md) supports native F12 captures without forced
rendering. Final native captures cover all six tabs and MenuBack; the tab row uses
the existing horizontal layout so selected and active labels fit their actual
font widths. Physical pointer operation and headset readability remain separate
interaction checks.

Scale/posture checks (Python 3 and clang++; no extra package dependency):

```sh
OPENMW_SOURCE=/path/to/patched/openmw python3 -m unittest discover -s tests/engine_scale -v
```

Four groups pass: compiled production `frameworld.hpp` helper math/state tests,
raw/submission boundary source guards, production world/derived/GUI/posture
wiring guards, and native persistence/default guards. The executable checks
identity and 0.5/1/2 multipliers, eye/hand deltas, unmodified physical samples,
GUI angular and inverse-pick math, posture retention, invalid tracking and
reference-origin invalidation. The eleven Lua panel tests also execute World
Size direction/bounds and seated/height/calibration callbacks. Source guards
are distinct from runtime evidence: this suite does not run OpenXR, scene
intersection, stereo rendering, native compilation or physical controllers.

Interaction acceptance requires settled in-engine checks of
World Size, menu/wrist HUD angular size and pointer alignment at 50/100/200%,
standing-to-seated-to-standing, both calibration actions, focus regain and a
system recenter.

## Scaled GUI pointer reach and modal priority (patches 15, 26)

GUI selection casts a separate ray with a reach of three physical metres,
converted by the applied world scale. This covers the configured two-metre
menu distance with hand displacement margin. The ray traverses only
`VRGUIManager::mGeometries`, whose root and pickable layer transforms use
`Mask_3DGUI`. Non-pickable transforms use `Mask_3DGUI_NonIntersectable` and are
excluded; hidden layers are detached. RTT cameras and world subtrees are not
part of this traversal. Callers explicitly ignoring `Mask_3DGUI` bypass it.

During GUI interaction, the nearest pickable panel takes priority over world
geometry, including a nearer NPC or wall. This matches its rendered overlay and
keeps modal buttons reachable when gameplay has paused a character in front of
them. `WindowManager::isGuiMode()` includes interactive message boxes as well as
ordinary menus, dialogue and character creation. If no panel is hit, the original
native activation/telekinesis/console range runs unchanged, with GUI excluded
from that fallback. Outside GUI mode, the original ray and mask behavior remain.

Active GUI layers render in a dedicated back-to-front bin after world passes,
including transparency, first-person models and distortion. Protected depth
state disables testing and writes for these layers. The existing eye framebuffer
and postprocessor are retained. Timed Notification layers also use this policy.
A pointer targeting a GUI panel renders in a later bin. Gameplay HUD layers and
world-targeting pointers retain their normal scene depth outside menu interaction.

The GUI result preserves OSG's actual local-space intersection point for cursor
mapping. Pointer width scales only while a GUI layer is targeted, so its physical
width remains stable while gameplay pointer width retains existing behavior.
No separate hit marker exists in the current pointer implementation.

```sh
OPENMW_SOURCE=/path/to/patched/openmw python3 -m unittest discover -s tests/engine_interaction -v
```

Five native groups pass, including compilation/execution of the production MWVR
routing helper. Cases cover multipliers 0.25/1/4, menu plus hand displacement,
GUI exclusions, unchanged native/telekinesis/console distances, and panel priority
over foreground NPCs/walls. Closing the modal restores native world picking.
Source guards verify dedicated OSG traversal and local hit-coordinate forwarding.

A fifth group requires the actual OSG SDK from the native builder. Set
`OPENMW_OSG_TEST=1`, `OPENMW_OSG_CXXFLAGS` and `OPENMW_OSG_LDFLAGS` to its include
and link flags. Mark the fetched SDK includes with `-isystem`. It executes
SceneView culling and state inheritance for both eye
views, ordinary/reversed depth, hostile inherited/leaf state, GUI sorting and
pointer order. It also verifies that GUI bins escape transparent ancestors,
avoid the world's transparent-depth postpass and precede postprocessing without
changing ordinary world depth. These checks do not replace rendered pixels or
physical pointer operation; current results are in [validation](VALIDATION.md).

The optional [foreground-guard addon](../tests/engine_interaction/fixtures/ui_occlusion/README.md)
reproduces the actual tutorial obstruction in a separate profile. It uses runtime
View/DefaultWindow poses and normal game objects, then requests a native quit;
it is not part of the shipped game content.
