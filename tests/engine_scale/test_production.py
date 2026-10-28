"""Production helper execution plus narrow guards on the actual engine wiring.
No native renderer/OpenXR runtime is simulated or claimed by these checks.
"""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
SOURCE=Path(os.environ['OPENMW_SOURCE'])
HERE=Path(__file__).parent

def read(path): return (SOURCE/path).read_text()

class ProductionTests(unittest.TestCase):
    def test_executable_production_helper(self):
        with tempfile.TemporaryDirectory(prefix='openmw-scale-test-') as tmp:
            binary=Path(tmp)/'frameworld-test'
            subprocess.run(['clang++','-std=c++17','-Wall','-Wextra','-Werror','-I',str(SOURCE),str(HERE/'test_frameworld.cpp'),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)
    def test_raw_and_submit_boundaries(self):
        source=read('components/xr/session.cpp')
        raw=source.split('VR::TrackingPose Session::locateSpace(XrSpace')[1].split('Session::getRecommendedSwapchainConfig')[0]
        self.assertNotIn('worldScale',raw)
        self.assertIn('pose.pose = fromXR(location.pose);',raw)
        view=read('components/vr/viewer.cpp').split('void Viewer::updateView')[1]
        self.assertIn('left.pose.position = physicalToWorld',view)
        self.assertIn('right.pose.position = physicalToWorld',view)
        self.assertIn('projectionLayer->views[i].view = localViews[i]',view)
        self.assertNotIn('localViews[i].pose.position =',view)
        combat=read('apps/openmw/mwvr/realisticcombat.cpp')
        self.assertIn('->locate(VR::ReferenceSpace::Local)',combat)
        self.assertNotIn('worldScale',combat)
        self.assertNotIn('worldScale',read('components/xr/typeconversion.hpp'))
    def test_world_derived_gui_and_posture_wiring(self):
        session=read('components/xr/session.cpp')
        world=session.split('VR::TrackingPose Session::locateSpaceInWorld')[1].split('void Session::setReferenceWorldPose')[0]
        self.assertEqual(world.count('postureTranslation'),1)
        self.assertIn('physicalToWorld(tp.pose.position, worldScale())',world)
        self.assertIn('tp.pose = mReferenceWorldPose + tp.pose',world)
        derived=read('components/vr/space.cpp').split('TrackingPose DerivedSpace::locateInWorld')[1]
        self.assertIn('physicalToWorld(offset.position',derived)
        gui=read('apps/openmw/mwvr/vrgui.cpp')
        self.assertIn('mTransform->setScale(VR::physicalToWorld(extent, scale))',gui)
        self.assertIn('pose.position = VR::physicalToWorld(pose.position',gui)
        menu=read('files/data/scripts/omw/vr/ui/menu.lua')
        self.assertEqual(menu.count("* vr._frameSettingGet('applied world scale')"),3)
        self.assertIn("vr._frameSettingGet('posture center')",read('files/data/scripts/omw/vr/inputs/player.lua'))
        self.assertIn('head.status == VR::TrackingStatus::Good',session)
        self.assertIn('mPosture.invalidate()',session)
        focus=session.split('case XR_SESSION_STATE_FOCUSED:')[1].split('default:')[0]
        self.assertNotIn('recenterZ',focus)
    def test_persisted_defaults_and_validation(self):
        defaults=read('files/settings-default.cfg')
        for setting in ['world scale = 1.0','height offset = 0.0','seated = false']:
            self.assertIn(setting,defaults)
        api=read('apps/openmw/mwlua/vrbindings.cpp')
        for name in ['mWorldScale.set(VR::validWorldScale(value))','mHeightOffset.set(VR::validHeightOffset(value))','mSeated.set(value != 0)']:
            self.assertIn(name,api)
        self.assertIn('if (!std::isfinite(value))',api)
        self.assertNotIn('mPosture',defaults)

if __name__=='__main__': unittest.main()
