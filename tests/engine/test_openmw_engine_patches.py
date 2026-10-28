"""Regression checks for the patched OpenMW production sources.

Run with OPENMW_SOURCE pointing at the source checkout with the patch series applied:
    OPENMW_SOURCE=/path/to/openmw-vr-source python -m unittest discover -s tests/engine
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path


SOURCE_ENV = os.environ.get("OPENMW_SOURCE")
if not SOURCE_ENV:
    raise RuntimeError("OPENMW_SOURCE must point to the patched OpenMW checkout")
SOURCE = Path(SOURCE_ENV)
if not (SOURCE / "components/xr").is_dir():
    raise RuntimeError(f"OPENMW_SOURCE is not an OpenMW source checkout: {SOURCE}")
FRAME_PROFILE = "/interaction_profiles/valve/frame_controller_valve"
FRAME_EXTENSION = "XR_VALVE_frame_controller_interaction"
LUA = shutil.which("lua") or shutil.which("lua5.4") or shutil.which("lua5.3") or shutil.which("luajit")
CXX = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")


def brace_block(source: str, marker: str) -> str:
    start = source.index(marker)
    opening = source.index("{", start)
    depth = 0
    for index in range(opening, len(source)):
        if source[index] == "{":
            depth += 1
        elif source[index] == "}":
            depth -= 1
            if depth == 0:
                return source[opening : index + 1]
    raise AssertionError(f"Unclosed table/block after {marker!r}")


def lua_bindings(source: str, profile: str) -> dict[str, dict[str, str]]:
    profile_block = brace_block(source, f"['{profile}']")
    hands = {}
    for hand in ("left", "right"):
        hand_path = f"/user/hand/{hand}"
        hand_block = brace_block(profile_block, f"['{hand_path}']")
        hands[hand_path] = dict(
            re.findall(r"\['([^']+)'\]\s*=\s*'([^']+)'", hand_block)
        )
    return hands


def source_body(source: str, marker: str) -> str:
    return brace_block(source, marker)


class OpenMWEnginePatchTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.profiles = ET.parse(SOURCE / "files/openxrinteractionprofiles.xml").getroot()
        entries = [
            entry
            for entry in cls.profiles.findall("Entry")
            if any(
                item.get("path") == FRAME_PROFILE
                for item in entry.findall("./InteractionProfiles/InteractionProfile")
            )
        ]
        if len(entries) != 1:
            raise AssertionError(f"Expected one Frame profile entry, got {len(entries)}")
        cls.frame_entry = entries[0]
        cls.interactions = {
            controller.get("path"): {
                interaction.get("path"): interaction.get("type")
                for interaction in controller.findall("Interaction")
            }
            for controller in cls.frame_entry.findall("./InteractionsMap/Controller")
        }
        cls.bindings = {
            handedness: lua_bindings(
                (SOURCE / f"files/data/scripts/omw/vr/inputs/defaultBindings{handedness}.lua").read_text(),
                FRAME_PROFILE,
            )
            for handedness in ("RightHanded", "LeftHanded")
        }

    def test_frame_profile_is_extension_gated_and_physically_asymmetric(self) -> None:
        profile = self.frame_entry.find("./InteractionProfiles/InteractionProfile")
        self.assertEqual(profile.get("requiredExtension"), FRAME_EXTENSION)

        right = self.interactions["/user/hand/right"]
        left = self.interactions["/user/hand/left"]
        self.assertEqual(
            {f"/input/{button}/click" for button in "abxy"} | {"/input/menu/click"}
            <= right.keys(),
            True,
        )
        self.assertEqual(
            {f"/input/{button}/click" for button in "abxy"} & left.keys(),
            set(),
        )
        self.assertTrue(
            {f"/input/dpad_{direction}/click" for direction in ("up", "down", "left", "right")}
            <= left.keys()
        )
        self.assertIn("/input/view/click", left)
        self.assertNotIn("/input/view/click", right)
        self.assertNotIn("/input/menu/click", left)
        self.assertNotIn("/input/squeeze/click", right)
        self.assertNotIn("/input/squeeze/click", left)
        for hand in (right, left):
            self.assertEqual(hand["/input/squeeze/value"], "FLOAT")
            self.assertEqual(hand["/input/trigger/value"], "FLOAT")
            self.assertEqual(hand["/input/grip/pose"], "POSE")
            self.assertEqual(hand["/input/aim/pose"], "POSE")

    def test_default_maps_keep_system_and_stick_sides_fixed(self) -> None:
        right_path = "/user/hand/right"
        left_path = "/user/hand/left"
        for handedness, hands in self.bindings.items():
            right = hands[right_path]
            left = hands[left_path]

            for action in ("PointerActivate_VR", "ToggleWeapon_VR"):
                self.assertEqual(right[action], f"{right_path}/input/a/click")
            for action in ("Inventory_VR", "RadialMenu_VR"):
                self.assertEqual(right[action], f"{right_path}/input/b/click")
            self.assertEqual(right["ToggleSpell_VR"], f"{right_path}/input/x/click")
            self.assertEqual(right["MetaMenu_VR"], f"{right_path}/input/y/click")
            self.assertEqual(right["MenuSelect_VR"], f"{right_path}/input/a/click")
            self.assertEqual(right["LookLeft_VR"], f"{right_path}/input/thumbstick/left")
            self.assertEqual(left["MoveForward_VR"], f"{left_path}/input/thumbstick/up")
            self.assertEqual(left["MenuUp_VR"], f"{left_path}/input/dpad_up/click")
            self.assertEqual(left["MenuBack_VR"], f"{left_path}/input/view/click")
            self.assertEqual(left["Recenter_VR"], f"{left_path}/input/view/click")
            self.assertEqual(left["MenuDown_VR"], f"{left_path}/input/dpad_down/click")
            self.assertEqual(left["MenuLeft_VR"], f"{left_path}/input/dpad_left/click")
            self.assertEqual(left["MenuRight_VR"], f"{left_path}/input/dpad_right/click")
            self.assertFalse(any("/input/squeeze/click" in path for hand in hands.values() for path in hand.values()))
            self.assertFalse(any(re.search(r"/user/hand/left/input/[abxy]/click$", path) for path in right.values()))

            if handedness == "RightHanded":
                self.assertEqual(right["Use_VR"], f"{right_path}/input/trigger/value")
                self.assertEqual(right["PointerRight_VR"], f"{right_path}/input/squeeze/value")
                self.assertEqual(left["Jump_VR"], f"{left_path}/input/trigger/value")
                self.assertEqual(left["Sneak_VR"], f"{left_path}/input/squeeze/value")
            else:
                self.assertEqual(left["Use_VR"], f"{left_path}/input/trigger/value")
                self.assertEqual(left["PointerLeft_VR"], f"{left_path}/input/squeeze/value")
                self.assertEqual(right["Jump_VR"], f"{right_path}/input/trigger/value")
                self.assertEqual(right["Sneak_VR"], f"{right_path}/input/squeeze/value")

            for hand_path, actions in hands.items():
                for action, path in actions.items():
                    self.assertTrue(path.startswith(hand_path + "/input/"), (handedness, action, path))
                    component = path[len(hand_path) :]
                    # common.lua expands the physical thumbstick x/y components
                    # into the virtual directional action paths used by Lua.
                    if re.fullmatch(r"/input/thumbstick/(left|right|up|down)", component):
                        axis = "x" if component.endswith(("left", "right")) else "y"
                        component = f"/input/thumbstick/{axis}"
                    self.assertIn(component, self.interactions[hand_path], (handedness, action, component))

    def test_native_menu_route_and_focus_reset_are_in_production_path(self) -> None:
        openxrinput = (SOURCE / "apps/openmw/mwvr/openxrinput.cpp").read_text()
        self.assertIn('"/user/hand/right/input/menu/click"', openxrinput)
        self.assertIn("profile.first.path == FrameInteractionProfile", openxrinput)
        self.assertIn("bool OpenXRInput::frameMenuWasPressed()", openxrinput)

        manager = (SOURCE / "apps/openmw/mwvr/vrinputmanager.cpp").read_text()
        self.assertIn("executeAction(MWInput::A_GameMenu)", manager)
        self.assertIn("XR::Session::instance().shouldReadInput()", manager)
        self.assertIn("mXRInput->clearInputValues()", manager)

        common = (SOURCE / "files/data/scripts/omw/vr/inputs/common.lua").read_text()
        self.assertIn("local longPressTime = 2.0 / 3.0", common)
        self.assertIn("local holdThreshold = isFrameViewPath(path) and 1.0 or longPressTime", common)
        self.assertIn("if not long or not isFrameViewPath(path) then", common)
        self.assertIn("core.getRealTime() - frameViewHoldStartedAt >= 3.0", common)
        self.assertIn("vr._recenterZ()", common)
        self.assertIn("if focused and onInputChangedBoolean then", common)
        for trigger in ("MenuUp", "MenuDown", "MenuLeft", "MenuRight", "MenuSelect"):
            self.assertIn(f"reg('{trigger}', ActionSetTemplates.MenuOnly)", common)

    @unittest.skipUnless(CXX, "install a C++ compiler to run the production focus transition test")
    def test_focus_pause_transitions_in_production_controller(self) -> None:
        harness = Path(__file__).with_name("test_focus_pause.cpp")
        production_header = SOURCE / "apps/openmw/mwvr/focuspause.hpp"
        with tempfile.TemporaryDirectory(prefix="openmw-frame-focus-pause-") as temp_dir:
            binary = Path(temp_dir) / "test_focus_pause"
            compile_result = subprocess.run(
                [CXX, "-std=c++17", "-Wall", "-Wextra", "-Werror", "-I", str(SOURCE / "apps/openmw"),
                 str(harness), "-o", str(binary)],
                check=False,
                text=True,
                capture_output=True,
            )
            self.assertEqual(compile_result.returncode, 0, compile_result.stdout + compile_result.stderr)
            self.assertTrue(production_header.is_file())
            run_result = subprocess.run([str(binary)], check=False, text=True, capture_output=True)
            self.assertEqual(run_result.returncode, 0, run_result.stdout + run_result.stderr)

    def test_focus_pause_wiring_uses_owned_game_and_audio_pause_paths(self) -> None:
        engine_header = (SOURCE / "apps/openmw/engine.hpp").read_text()
        self.assertIn("MWVR::FocusPauseController mXrFocusPause;", engine_header)

        engine = (SOURCE / "apps/openmw/engine.cpp").read_text()
        frame = source_body(engine, "bool OMW::Engine::frame(")
        input_update = frame.index("mInputManager->update(frametime, false)")
        focus_transition = frame.index("mXrFocusPause.update(")
        transition_block = source_body(frame, "if (focusPauseTransition !=")
        simulation_update = frame.index("mStateManager->update(frametime)")
        self.assertLess(input_update, focus_transition)
        self.assertLess(focus_transition, simulation_update)
        self.assertIn("mXrSession && mXrSession->isDiagnosticMode()", frame)
        self.assertIn("mXrSession && mXrSession->shouldReadInput()", frame)
        self.assertIn("timeManager.pause(XRFocusPauseTag)", frame)
        self.assertIn("timeManager.unpause(XRFocusPauseTag)", frame)
        self.assertIn("mSoundManager->pauseSounds(MWSound::XRFocus)", frame)
        self.assertIn("mSoundManager->resumeSounds(MWSound::XRFocus)", frame)
        self.assertIn("timeManager.updateIsPaused()", frame)
        self.assertIn("VR::Session::instance().updateSpaces()", frame)
        self.assertNotIn("mSoundManager->pausePlayback()", transition_block)

        sound_header = (SOURCE / "apps/openmw/mwbase/soundmanager.hpp").read_text()
        self.assertRegex(sound_header, r"VideoPlayback,\s+XRFocus,\s+MaxCount")

    @unittest.skipUnless(LUA, "install Lua to run production common.lua interaction tests")
    def test_frame_view_hold_and_focus_behavior_in_production_lua(self) -> None:
        harness = Path(__file__).with_name("test_frame_view_interaction.lua")
        result = subprocess.run(
            [LUA, str(harness)],
            env={**os.environ, "OPENMW_SOURCE": str(SOURCE)},
            check=False,
            text=True,
            capture_output=True,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_glx_space_lifetime_and_depth_mipmap_guards(self) -> None:
        platform = (SOURCE / "components/xr/platform.cpp").read_text()
        glx = platform[platform.index("int contextFBConfigId") : platform.index("XrGraphicsBindingOpenGLXlibKHR graphicsBindings")]
        self.assertIn("glXQueryContext", glx)
        self.assertIn("glXQueryDrawable", glx)
        self.assertIn("GLX_FBCONFIG_ID", glx)
        self.assertIn("candidateId == fbConfigId", glx)

        session = (SOURCE / "components/xr/session.cpp").read_text()
        cleanup = source_body(session, "void Session::cleanup()")
        self.assertLess(cleanup.index("referenceSpace->destroy()"), cleanup.index("destroyXrSession()"))
        destroy_session = source_body(session, "void Session::destroyXrSession()")
        self.assertLess(
            destroy_session.index("std::exchange(mXrSession, XR_NULL_HANDLE)"),
            destroy_session.index("xrDestroySession(session)"),
        )

        rtt = (SOURCE / "components/sceneutil/rtt.cpp").read_text()
        self.assertIn("[osg::Camera::COLOR_BUFFER]._mipMapGeneration = mGenerateMipmaps", rtt)
        self.assertIn("[osg::Camera::PACKED_DEPTH_STENCIL_BUFFER]._mipMapGeneration\n                = false", rtt)

    def test_xr_children_are_invalidated_before_parent_handles(self) -> None:
        openxrinput = (SOURCE / "apps/openmw/mwvr/openxrinput.cpp").read_text()
        destructor = source_body(openxrinput, "OpenXRInput::~OpenXRInput()")
        self.assertIn("destroySpaces()", destructor)
        destroy_spaces = source_body(openxrinput, "void OpenXRInput::destroySpaces()")
        self.assertLess(destroy_spaces.index("xrSpace->destroy()"), destroy_spaces.index("mSpaces.clear()"))

        space = (SOURCE / "components/xr/space.cpp").read_text()
        destroy_wrapper = source_body(space, "void XrSpaceWrapper::destroy()")
        self.assertLess(destroy_wrapper.index("std::exchange(mSpace, XR_NULL_HANDLE)"), destroy_wrapper.index("xrDestroySpace"))

        engine = (SOURCE / "apps/openmw/engine.cpp").read_text()
        cleanup = source_body(engine, "OMW::Engine::~Engine()")
        self.assertLess(cleanup.index("mInputManager = nullptr"), cleanup.index("mVrViewer = nullptr"))
        self.assertLess(cleanup.index("mVrViewer = nullptr"), cleanup.index("mXrSession = nullptr"))
        self.assertLess(cleanup.index("mXrSession = nullptr"), cleanup.index("mXrInstance = nullptr"))

        instance = (SOURCE / "components/xr/instance.cpp").read_text()
        self.assertIn("Instance::~Instance()\n    {\n        cleanup();", instance)
        self.assertIn("std::exchange(mXrInstance, XR_NULL_HANDLE)", instance)

        viewer_hpp = (SOURCE / "components/vr/viewer.hpp").read_text()
        self.assertLess(viewer_hpp.index("mSession;"), viewer_hpp.index("mDepthSwapchain"))
        self.assertLess(viewer_hpp.index("mDepthSwapchain"), viewer_hpp.index("mReadyFrames"))

    def test_unfocused_diagnostic_render_capture_and_timeout_are_bounded(self) -> None:
        session = (SOURCE / "components/xr/session.cpp").read_text()
        self.assertIn('std::getenv("OPENMW_FRAME_FORCE_RENDER")', session)
        frame_update = source_body(session, "void Session::syncFrameUpdate(")
        self.assertIn("XR_SESSION_STATE_SYNCHRONIZED", frame_update)
        self.assertIn("XR_SESSION_STATE_VISIBLE", frame_update)
        focused = frame_update[frame_update.index("else if (mState == XR_SESSION_STATE_FOCUSED)") :]
        self.assertIn("shouldRender = false", focused)
        self.assertIn("mFrameDiagnosticSyntheticViewsActive = true", frame_update)
        self.assertIn("Position::fromMeters(-halfEyeSeparation, 0.f, headHeight)", session)
        self.assertIn("Position::fromMeters(halfEyeSeparation, 0.f, headHeight)", session)
        self.assertIn("IPD=0.064 m", frame_update)
        self.assertIn("locateDiagnosticFov(predictedDisplayTime)", frame_update)
        self.assertIn("xrLocateViews(mXrSession, &locateInfo", session)
        self.assertIn("performance timings are suppressed while this fallback is in use", frame_update)
        self.assertIn("mFrameDiagnosticRuntimeFov[VR::Side_Left]", session)
        self.assertIn("mFrameDiagnosticRuntimeFov[VR::Side_Right]", session)

        locate_space = source_body(session, "VR::TrackingPose Session::locateSpace(")
        self.assertIn("space == viewSpace && referenceSpace == localSpace", locate_space)
        self.assertIn("Stereo::Position::fromMeters(0.f, 0.f, 1.65f)", locate_space)
        self.assertIn("space == localSpace && referenceSpace == viewSpace", locate_space)

        header = (SOURCE / "components/xr/session.hpp").read_text()
        self.assertIn("bool shouldReadInput() const { return mAppShouldReadInput && !mFrameForceRender; }", header)
        submission = source_body(session, "bool Session::shouldSubmitFrame(")
        self.assertIn("return !mFrameForceRender && shouldRender", submission)
        end_frame = source_body(session, "void Session::syncFrameEnd(")
        self.assertIn("if (frame.shouldSubmit && !mFrameDiagnosticRefused.load()", end_frame)
        self.assertIn("frameEndInfo.layerCount = 0", end_frame)
        self.assertIn("XR_SESSION_STATE_FOCUSED", focused)
        self.assertIn("no composition ", session)
        self.assertIn("beginDiagnosticCaptureWindow", header)
        self.assertIn("diagnosticFrameNumber", header)

        viewer = (SOURCE / "components/vr/viewer.cpp").read_text()
        xr_blit = source_body(viewer, "void Viewer::blitXrFramebuffer(")
        self.assertLess(xr_blit.index("glBlitFramebuffer"), xr_blit.index("captureDiagnosticEye"))
        self.assertIn("mDrawFrame.diagnosticFrameNumber >= mDiagnosticCaptureFrame", xr_blit)
        self.assertIn("!mDiagnosticEyeCaptureAttempted[i]", xr_blit)
        capture = source_body(viewer, "void Viewer::captureDiagnosticEye(")
        self.assertIn("READ_FRAMEBUFFER", capture)
        self.assertIn('".png"', capture)
        # OSG 3.6.5's PNG writer emits rows t-i-1. A manual flip here
        # would invert GL readback twice; the PNG round-trip check covers this.
        self.assertNotIn("flipVertical()", capture)
        blit = source_body(viewer, "void Viewer::blit(osg::RenderInfo& info)")
        self.assertLess(blit.index("blitXrFramebuffer"), blit.index("mColorSwapchain[i]->endFrame"))
        for stage in ("osg_draw_callbacks", "left_swapchain_cycle", "right_swapchain_cycle"):
            self.assertIn(stage, viewer)
        self.assertIn("xr_wait_frame", session)
        self.assertIn("xr_end_frame", session)
        self.assertIn("Frame diagnostic offscreen timing (ms", viewer)
        self.assertIn("Frame diagnostic offscreen timing (ms", session)
        self.assertIn("diagnosticPerfComparable", viewer)

        vrgui = (SOURCE / "apps/openmw/mwvr/vrgui.cpp").read_text()
        ui_blit = source_body(vrgui, "void VRGUILayer::blitLayer(")
        self.assertLess(ui_blit.index("glBlitFramebuffer"), ui_blit.index("readPixels"))
        self.assertLess(ui_blit.index("readPixels"), ui_blit.index("colorSwapchain->endFrame"))
        self.assertIn("rendered UI layer texture", ui_blit)
        gui_end = source_body(vrgui, "void VRGUIManager::onFrameEnd(")
        self.assertIn("frame.diagnosticFrameNumber >= mDiagnosticCaptureFrame", gui_end)
        self.assertIn("ui-layer-", gui_end)

        engine = (SOURCE / "apps/openmw/engine.cpp").read_text()
        self.assertIn('std::getenv("OPENMW_FRAME_DIAGNOSTIC_EXIT_SECONDS")', engine)
        self.assertIn('std::getenv("OPENMW_FRAME_DIAGNOSTIC_CAPTURE_FRAME")', engine)
        self.assertIn("constexpr uint64_t defaultFrame = 300", engine)
        self.assertIn("!std::isfinite(seconds) || seconds <= 0.0", engine)
        self.assertIn("diagnosticExitDeadline", engine)
        self.assertIn("leaving the engine loop cleanly", engine)
        self.assertIn("mXrSession->diagnosticRefused()", engine)
        self.assertIn("mXrSession->beginDiagnosticCaptureWindow()", engine)
        main_loop = source_body(engine, "while (!mViewer->done()")
        self.assertNotIn("Frame diagnostic stopped after the XR runtime acquired focus", main_loop)


if __name__ == "__main__":
    unittest.main()
