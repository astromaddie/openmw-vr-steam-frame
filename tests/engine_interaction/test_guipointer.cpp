#include <apps/openmw/mwvr/guipointer.hpp>
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>

namespace
{
    void near(float a, float b) { assert(std::abs(a-b)<.0001f); }
    struct Result { bool mHit = false; bool gui = false; float localX = 0; };
    struct Scene
    {
        float guiDistance = 0, worldDistance = 0, nativeRange = 192, units = 70;
        float guiWidth = 1, cursorWorldX = 0;
        int guiCalls = 0, occlusionCalls = 0, worldCalls = 0;
        float guiReach = 0;
        unsigned worldMask = 0;
        float query(Result& result, bool guiMode, unsigned ignoreMask, float scale)
        {
            return MWVR::Util::targetWithGui(result,guiMode,ignoreMask,scale,units,
                [&](Result& out,float reach) {
                    ++guiCalls; guiReach=reach;
                    if (guiDistance>0 && guiDistance<=reach)
                        out={true,true,cursorWorldX/guiWidth};
                    return out.mHit ? guiDistance : 0.f;
                },
                [&](Result& out,float reach,unsigned mask) {
                    ++occlusionCalls;
                    assert(mask & MWRender::Mask_3DGUI);
                    if (worldDistance>0 && worldDistance<=reach) out={true,false,0};
                    return out.mHit ? worldDistance : 0.f;
                },
                [&](Result& out,unsigned mask) {
                    ++worldCalls; worldMask=mask;
                    // Existing activation range is entirely owned by this
                    // callback, never replaced with the extended GUI length.
                    if (worldDistance>0 && worldDistance<=nativeRange) out={true,false,0};
                    return out.mHit ? worldDistance : 0.f;
                });
        }
    };
}
int main()
{
    using namespace MWVR::Util;
    for(float scale : {.25f,1.f,4.f})
    {
        Scene scene;
        scene.guiDistance=2.7f*scene.units*scale; // 2m menu + .7m hand displacement
        scene.guiWidth=.8f*scene.units*scale;
        scene.cursorWorldX=.2f*scene.units*scale;
        Result result;
        near(scene.query(result,true,MWRender::Mask_3DGUI_NonIntersectable,scale),scene.guiDistance);
        assert(result.mHit && result.gui); near(result.localX,.25f);
        assert(scene.guiCalls==1 && scene.occlusionCalls==1 && scene.worldCalls==0);
        near(scene.guiReach,3.f*scene.units*scale);
        near(pointerWidth(true,scale)/scale,.25f); near(pointerWidth(false,scale),.25f);

        Scene excluded; excluded.guiDistance=1; excluded.worldDistance=100;
        near(excluded.query(result,true,MWRender::Mask_3DGUI,scale),100);
        assert(excluded.guiCalls==0 && excluded.occlusionCalls==0 && excluded.worldCalls==1);
        assert(excluded.worldMask==MWRender::Mask_3DGUI);

        Scene gameplay; gameplay.guiDistance=1; gameplay.worldDistance=193;
        result={}; near(gameplay.query(result,false,0,scale),0);
        assert(!result.mHit && gameplay.guiCalls==0 && gameplay.occlusionCalls==0);
        assert(gameplay.worldMask==0); // no change to gameplay masks/range
        gameplay.worldDistance=191; near(gameplay.query(result,false,0,scale),191);

        Scene missing; missing.worldDistance=193;
        result={}; near(missing.query(result,true,0,scale),0);
        assert(!result.mHit && missing.worldCalls==1 && missing.occlusionCalls==0);
        assert(missing.worldMask & MWRender::Mask_3DGUI);
    }
    Scene occluded;
    occluded.guiDistance=4*occluded.units; // scale4, physical menu at1m
    occluded.worldDistance=3*occluded.units; // wall beyond native2.74m, before GUI
    Result result;
    near(occluded.query(result,true,0,4),0);
    assert(!result.mHit); // distant wall must never become a pickup/activation target
    assert(occluded.guiCalls==1 && occluded.occlusionCalls==1 && occluded.worldCalls==1);

    Scene nearWall; nearWall.guiDistance=280; nearWall.worldDistance=140;
    near(nearWall.query(result,true,0,4),140); assert(result.mHit && !result.gui);
    Scene foreground; foreground.guiDistance=140; foreground.worldDistance=180;
    near(foreground.query(result,true,0,4),140); assert(result.mHit && result.gui);
    Scene telekinesis; telekinesis.nativeRange=500; telekinesis.worldDistance=499;
    near(telekinesis.query(result,true,0,4),499); assert(!result.gui);
    Scene console; console.nativeRange=192*50; console.worldDistance=9000;
    near(console.query(result,true,0,4),9000); assert(!result.gui);
    near(guiPointerScale(std::numeric_limits<float>::quiet_NaN()),1);
    std::cout << "PASS: production GUI routing, scales .25/1/4, masks, local cursor/width, unchanged gameplay/telekinesis/console reach, foreground and distant-wall occlusion\n";
}
