"""Run private MWVR production routing; guard actual OSG traversal/wiring.
Pure callback fixtures do not claim to execute OSG intersections or headset UI.
"""
import os
import shlex
from pathlib import Path
import subprocess
import tempfile
import unittest
SOURCE=Path(os.environ['OPENMW_SOURCE'])
HERE=Path(__file__).parent

def read(path): return (SOURCE/path).read_text()

class PointerTests(unittest.TestCase):
    def test_production_routing(self):
        with tempfile.TemporaryDirectory(prefix='openmw-interaction-test-') as tmp:
            binary=Path(tmp)/'gui-pointer-test'
            subprocess.run([os.environ.get('CXX','clang++'),'-std=c++17','-Wall','-Wextra','-Werror','-I',str(SOURCE),str(HERE/'test_guipointer.cpp'),'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)
    def test_actual_gui_traversal_and_local_hit_coordinates(self):
        gui=read('apps/openmw/mwvr/vrgui.cpp')
        cast=gui.split('float VRGUIManager::castPointerRay')[1].split('void VRGUIManager::updateFocus')[0]
        self.assertIn('visitor.setTraversalMask(MWRender::Mask_3DGUI)',cast)
        self.assertIn('mGeometries->accept(visitor)',cast)
        self.assertNotIn('mRootNode->accept',cast)
        self.assertNotIn('mGUICameras->accept',cast)
        self.assertIn('dynamic_cast<VRGUILayerUserData*>',cast)
        self.assertIn('result = {}',cast)
        self.assertIn('result.mHitPointLocal = hit.getLocalIntersectPoint()',cast)
        self.assertNotIn('mHitObject =',cast)
        self.assertIn('mGeometries->setNodeMask(MWRender::VisMask::Mask_3DGUI)',gui)
        self.assertIn('mTransform->setNodeMask(MWRender::Mask_3DGUI_NonIntersectable)',gui)
        self.assertIn('mGeometryRoot->removeChild(mTransform)',gui)
    def test_native_activation_and_gui_width_wiring(self):
        util=read('apps/openmw/mwvr/vrutil.cpp')
        self.assertIn('return targetWithGui(result, wm->isGuiMode(), ignoreMask',util)
        self.assertIn('VRGUIManager::instance().castPointerRay(guiResult, pose, reach)',util)
        self.assertNotIn('world->getTargetObject(occluder,',util)
        self.assertIn('world->getMaxActivationDistance() * 50, true, worldIgnoreMask',util)
        self.assertIn('activationDistance += std::ceil(Constants::UnitsPerFoot) * telekinesisMagnitude',util)
        self.assertIn('pose.orientation, activationDistance, true, worldIgnoreMask',util)
        pointer=read('apps/openmw/mwvr/vrpointer.cpp')
        self.assertIn('Util::pointerWidth(guiHit, VR::Session::instance().worldScale())',pointer)
        self.assertIn('updateFocus(mPointerRay.mHitNode, mPointerRay.mHitPointLocal)',pointer)

    def test_render_policy_wiring(self):
        gui=read('apps/openmw/mwvr/vrgui.cpp')
        cull=gui.split('void VRGUILayer::cull')[1].split('void VRGUILayer::removeFromSceneGraph')[0]
        self.assertIn('guiOverlayRequired(', cull)
        self.assertIn('getWindowManager()->isGuiMode(), mLayerName', cull)
        self.assertLess(cull.index('cv->pushStateSet(mOverlayState)'),cull.index('geometry->accept(*cv)'))
        self.assertGreater(cull.index('cv->popStateSet()'),cull.index('geometry->accept(*cv)'))
        wm=read('apps/openmw/mwgui/windowmanagerimp.cpp')
        mode=wm.split('bool WindowManager::isGuiMode() const')[1].split('bool WindowManager::isConsoleMode')[0]
        self.assertIn('isInteractiveMessageBoxActive()',mode)
        pointer=read('apps/openmw/mwvr/vrpointer.cpp')
        self.assertIn('mCrosshair->setGuiHit(guiHit)',pointer)
        self.assertIn('mTransform->setStateSet(guiHit ? mGuiState.get() : nullptr)',pointer)
        self.assertIn('mGuiState(createGuiOverlayState(true))',pointer)

    @unittest.skipUnless(os.environ.get('OPENMW_OSG_TEST')=='1',
                         'real OSG SDK required; set OPENMW_OSG_TEST=1 and OSG compile/link flags')
    def test_native_gui_render_policy(self):
        # Use the exact fetched OSG SDK from the native builder. No fake OSG
        # classes: this runs its cull visitor, render bins and State stack.
        flags=shlex.split(os.environ.get('OPENMW_OSG_CXXFLAGS',''))
        libs=shlex.split(os.environ.get('OPENMW_OSG_LDFLAGS','-losgUtil -losg -lOpenThreads'))
        with tempfile.TemporaryDirectory(prefix='openmw-render-policy-test-') as tmp:
            binary=Path(tmp)/'gui-render-test'
            subprocess.run([os.environ.get('CXX','clang++'),'-std=c++17','-Wall','-Wextra','-Werror',
                            '-I',str(SOURCE),*flags,str(HERE/'test_guirender.cpp'),*libs,'-o',str(binary)],check=True)
            subprocess.run([str(binary)],check=True)

if __name__=='__main__': unittest.main()
