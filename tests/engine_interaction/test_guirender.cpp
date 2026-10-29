// Native OSG regression for the exact StateSet policy used by VRGUILayer::cull
// and Crosshair. This exercises cull/bin/state inheritance without a GL context;
// actual eye pixels and input still require the engine/headset acceptance run.
#include <apps/openmw/mwvr/guirender.hpp>

#include <osg/Camera>
#include <osg/Geode>
#include <osg/Geometry>
#include <osg/State>
#include <osgUtil/SceneView>

#include <algorithm>
#include <cassert>
#include <iostream>
#include <vector>

namespace
{
    struct WorldDepthPostpass : osgUtil::RenderBin::DrawCallback
    {
        void drawImplementation(osgUtil::RenderBin*, osg::RenderInfo&, osgUtil::RenderLeaf*&) override {}
    };

    osg::ref_ptr<osg::Geode> quad(const char* name, float distance)
    {
        osg::ref_ptr<osg::Geometry> geometry = osg::createTexturedQuadGeometry(
            osg::Vec3(-1, distance, -1), osg::Vec3(2, 0, 0), osg::Vec3(0, 0, 2));
        geometry->setName(name);
        geometry->setCullingActive(false);
        osg::ref_ptr<osg::Geode> geode = new osg::Geode;
        geode->setCullingActive(false);
        geode->addDrawable(geometry);
        return geode;
    }

    // Reproduce the production push/pop policy at cull time, rather than only
    // inspecting constants. The root and leaf both try to override depth/bin.
    struct OverlayCull : osg::NodeCallback
    {
        osg::ref_ptr<osg::StateSet> policy;
        explicit OverlayCull(osg::StateSet* state) : policy(state) {}
        void operator()(osg::Node* node, osg::NodeVisitor* nv) override
        {
            auto* cv = dynamic_cast<osgUtil::CullVisitor*>(nv);
            assert(cv);
            cv->pushStateSet(policy);
            traverse(node, nv);
            cv->popStateSet();
        }
    };

    osg::ref_ptr<osg::StateSet> effectiveState(const osgUtil::RenderLeaf& leaf)
    {
        std::vector<const osg::StateSet*> path;
        for (auto* graph = leaf._parent; graph; graph = graph->_parent)
            if (graph->getStateSet()) path.push_back(graph->getStateSet());
        osg::ref_ptr<osg::State> state = new osg::State;
        for (auto it = path.rbegin(); it != path.rend(); ++it) state->pushStateSet(*it);
        osg::ref_ptr<osg::StateSet> effective = new osg::StateSet;
        state->captureCurrentState(*effective);
        return effective;
    }

    osg::ref_ptr<osg::Group> overlay(const char* name, float distance, bool pointer = false)
    {
        osg::ref_ptr<osg::Group> group = new osg::Group;
        group->setCullingActive(false);
        group->setCullCallback(new OverlayCull(MWVR::createGuiOverlayState(pointer)));
        auto leaf = quad(name, distance);
        auto* state = leaf->getDrawable(0)->getOrCreateStateSet();
        state->setAttributeAndModes(new osg::Depth(osg::Depth::LESS, 0, 1, true), osg::StateAttribute::ON);
        state->setRenderingHint(osg::StateSet::TRANSPARENT_BIN);
        group->addChild(leaf);
        return group;
    }

    void assertOverlay(const osgUtil::RenderLeaf& leaf)
    {
        auto state = effectiveState(leaf);
        assert(!(state->getMode(GL_DEPTH_TEST) & osg::StateAttribute::ON));
        auto* depth = dynamic_cast<const osg::Depth*>(state->getAttribute(osg::StateAttribute::DEPTH));
        assert(depth && !depth->getWriteMask() && depth->getFunction() == osg::Depth::ALWAYS);
    }
}

int main()
{
    using namespace MWVR;
    using namespace MWRender;
    // Match the native postprocessor's customization of the stock transparent
    // bin, and ensure the GUI gets neither this callback nor its depth writes.
    auto* transparent = osgUtil::RenderBin::getRenderBinPrototype("DepthSortedBin");
    osg::ref_ptr<osgUtil::RenderBin::DrawCallback> previousCallback = transparent->getDrawCallback();
    transparent->setDrawCallback(new WorldDepthPostpass);
    assert(guiOverlayRequired(true, "Modal"));
    assert(guiOverlayRequired(true, "Windows")); // chargen name entry
    assert(guiOverlayRequired(true, "DialogueWindow"));
    assert(guiOverlayRequired(true, "Settings"));
    assert(guiOverlayRequired(false, "Notification")); // timed tutorial
    assert(!guiOverlayRequired(false, "HUD"));
    assert(!guiOverlayRequired(false, "HUD_3D"));

    // Deliberately hostile inherited state catches missing PROTECTED, and the
    // leaf state above catches missing OVERRIDE. Match both normal/reversed Z.
    for (auto function : {osg::Depth::LESS, osg::Depth::GREATER})
    {
        osg::ref_ptr<osg::Group> root = new osg::Group;
        root->setCullingActive(false);
        auto* inherited = root->getOrCreateStateSet();
        inherited->setAttributeAndModes(new osg::Depth(function, 0, 1, true),
            osg::StateAttribute::ON | osg::StateAttribute::OVERRIDE);

        for (int number : {RenderBin_Default, RenderBin_Water, RenderBin_DepthSorted,
                 RenderBin_OcclusionQuery, RenderBin_FirstPerson, RenderBin_SunGlare, RenderBin_Distortion})
        {
            auto world = quad("foreground world", 1);
            world->getOrCreateStateSet()->setRenderBinDetails(number, "RenderBin");
            root->addChild(world);
            assert(number < RenderBin_VRGUI);
        }

        // Nesting under a transparent ancestor is the real GUI root topology.
        // Menus must escape that bin and run after *all* world bins.
        osg::ref_ptr<osg::Group> gui = new osg::Group;
        gui->getOrCreateStateSet()->setRenderBinDetails(RenderBin_DepthSorted, "DepthSortedBin",
            osg::StateSet::OVERRIDE_RENDERBIN_DETAILS);
        gui->addChild(overlay("far menu", 4));
        gui->addChild(overlay("near modal", 3));
        root->addChild(gui);
        root->addChild(overlay("menu pointer", 2, true));

        // The GUI remains in the scene stage, before the existing postprocessor
        // POST_RENDER resolve, rather than a camera targeting the wrong eye FBO.
        osg::ref_ptr<osg::Camera> postprocess = new osg::Camera;
        postprocess->setRenderOrder(osg::Camera::POST_RENDER);
        postprocess->setClearMask(0);
        postprocess->addChild(quad("postprocess resolve", 1));
        root->addChild(postprocess);

        for (float eye : {-.03f, .03f})
        {
            osg::ref_ptr<osgUtil::SceneView> view = new osgUtil::SceneView;
            view->setDefaults();
            view->getDisplaySettings()->setStereo(false);
            view->setViewport(0, 0, 640, 480);
            view->setProjectionMatrixAsPerspective(70, 4.0/3.0, .01, 100);
            view->setViewMatrixAsLookAt(osg::Vec3(eye, 0, 0), osg::Vec3(eye, 1, 0), osg::Vec3(0, 0, 1));
            view->setSceneData(root);
            view->cull();
            auto* stage = view->getRenderStage();
            stage->sort();
            auto& bins = stage->getRenderBinList();
            assert(bins.count(RenderBin_VRGUI) == 1);
            assert(bins.count(RenderBin_VRGUIPointer) == 1);
            assert(bins.rbegin()->first == RenderBin_VRGUIPointer);
            auto* menu = bins.at(RenderBin_VRGUI).get();
            auto* pointer = bins.at(RenderBin_VRGUIPointer).get();
            assert(menu->getStage() == stage && pointer->getStage() == stage);
            assert(menu->getSortMode() == osgUtil::RenderBin::SORT_BACK_TO_FRONT);
            assert(!menu->getDrawCallback()); // no transparent depth postpass
            assert(menu->getRenderLeafList().size() == 2);
            assert(menu->getRenderLeafList()[0]->_drawable->getName() == "far menu");
            assert(menu->getRenderLeafList()[1]->_drawable->getName() == "near modal");
            for (auto* leaf : menu->getRenderLeafList()) assertOverlay(*leaf);
            assert(pointer->getRenderLeafList().size() == 1);
            assertOverlay(*pointer->getRenderLeafList()[0]);
            assert(stage->getPostRenderList().size() == 1);

            // Ordinary world state still owns its original depth/write policy.
            const auto& worlds = bins.at(RenderBin_Water)->getStateGraphList();
            assert(!worlds.empty() && !worlds.front()->_leaves.empty());
            auto state = effectiveState(*worlds.front()->_leaves.front());
            assert(state->getMode(GL_DEPTH_TEST) & osg::StateAttribute::ON);
            auto* depth = dynamic_cast<const osg::Depth*>(state->getAttribute(osg::StateAttribute::DEPTH));
            assert(depth && depth->getWriteMask() && depth->getFunction() == function);
        }
    }
    transparent->setDrawCallback(previousCallback);
    std::cout << "PASS: native OSG cull/bin/state inheritance, both eye views and depth conventions, "
                 "modal sorting after world passes, pointer priority, postprocess stage, unchanged world depth\n";
}
