#include <components/vr/frameworld.hpp>
#include <cassert>
#include <cmath>
#include <iostream>
#include <limits>

namespace
{
    void near(float a, float b) { assert(std::abs(a-b) < 0.00001f); }
    struct Vector
    {
        float x, y, z;
        Vector operator*(float s) const { return {x*s,y*s,z*s}; }
    };
}
int main()
{
    using namespace VR;
    near(validWorldScale(std::numeric_limits<float>::quiet_NaN()), 1);
    near(validWorldScale(std::numeric_limits<float>::infinity()), 1);
    near(validWorldScale(0), .25); near(validWorldScale(9), 4);
    near(validHeightOffset(-9), -1); near(validHeightOffset(9), 1);
    near(validHeightOffset(std::numeric_limits<float>::quiet_NaN()), 0);
    // The same production adapter is used by the world head/hands, rendered
    // eye offsets, derived physical offsets and GUI scene geometry.
    const Vector rawHand{.3f,.6f,-.4f}, rawEye{.032f,0,0}, rawPanel{.8f,1.f,0};
    for (float scale : {.5f,1.f,2.f})
    {
        auto hand = physicalToWorld(rawHand,scale);
        auto eye = physicalToWorld(rawEye,scale);
        near(hand.x,.3f*scale); near(hand.y,.6f*scale); near(hand.z,-.4f*scale);
        near(eye.x,.032f*scale); near(eye.x*2,.064f*scale);
        auto panel = physicalToWorld(rawPanel,scale);
        near(panel.x/panel.y,.8f); // angular width unchanged
        // Inverse-model picking returns identical quad-local coordinates.
        float cursorX = physicalToWorld(.2f,scale)/panel.x;
        near(cursorX,.25f);
        near(physicalToWorld(.09f,scale),.09f*scale); // wrist offset
        near(rawHand.x,.3f); near(rawEye.x,.032f); // adapter does not mutate raw samples
        const Vector nextRawHand{.3f,.9f,-.4f};
        auto nextWorldHand = physicalToWorld(nextRawHand,scale);
        near((nextWorldHand.y-hand.y)/.1f,3.f*scale);
        near((nextRawHand.y-rawHand.y)/.1f,3.f); // physical velocity remains raw
    }
    auto identity = physicalToWorld(rawHand,1);
    near(identity.x,rawHand.x); near(identity.y,rawHand.y); near(identity.z,rawHand.z);
    PostureCalibration posture;
    assert(!posture.sample(1.7f,false)); assert(posture.pending()); assert(!posture.hasStanding());
    assert(!posture.sample(std::numeric_limits<float>::quiet_NaN(),true));
    assert(posture.sample(1.7f,true)); assert(posture.hasStanding()); near(posture.center(),1.7f);
    // XY and focus recenter do not request vertical calibration.
    assert(!posture.sample(1.4f,true)); near(posture.center(),1.7f);
    posture.setSeated(true); assert(posture.pending());
    assert(!posture.sample(1.1f,false)); near(posture.center(),1.7f);
    assert(posture.sample(1.1f,true)); near(posture.center(),1.1f); assert(posture.hasStanding());
    posture.requestCalibration(); assert(posture.sample(1.2f,true));
    posture.setSeated(false); near(posture.center(),1.7f); assert(!posture.pending());
    posture.requestCalibration(); assert(posture.sample(1.8f,true)); near(posture.center(),1.8f);
    // Shared anchor moves camera and both hands exactly once; deltas and physical
    // velocity are unaffected by posture/height adjustment.
    for(float scale : {.5f,1.f,2.f})
    {
        float shift=postureTranslation(posture.center(),.1f,scale);
        near(physicalToWorld(1.8f,scale)+shift,.1f*scale);
        near((physicalToWorld(1.4f,scale)+shift)-(physicalToWorld(1.8f,scale)+shift),-.4f*scale);
    }
    posture.invalidate(); assert(!posture.hasStanding()); assert(posture.pending());
    assert(posture.sample(-.3f,true)); assert(!posture.hasStanding()); // no stale origin baseline
    posture.requestCalibration(); assert(posture.sample(-.3f,true)); assert(posture.hasStanding());
    PostureCalibration freshSeated;
    freshSeated.setSeated(true); assert(freshSeated.sample(.9f,true)); assert(!freshSeated.hasStanding());
    freshSeated.setSeated(false); assert(!freshSeated.pending()); near(freshSeated.center(),.9f);
    freshSeated.requestCalibration(); assert(freshSeated.sample(1.7f,true)); assert(freshSeated.hasStanding());
    std::cout << "PASS: validation, scale .5/1/2, identity, physical raw values, GUI angular/pick math, posture transitions, invalid tracking and origin change\n";
}
