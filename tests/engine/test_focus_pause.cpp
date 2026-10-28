#include "mwvr/focuspause.hpp"

#include <iostream>

namespace
{
    bool expect(bool condition, const char* message)
    {
        if (!condition)
            std::cerr << message << '\n';
        return condition;
    }
}

int main()
{
    MWVR::FocusPauseController controller;
    using Transition = MWVR::FocusPauseController::Transition;

    if (!expect(controller.update(false, false, false) == Transition::None, "No XR session must not pause")
        || !expect(controller.update(true, false, true) == Transition::None, "Focused XR must not pause")
        || !expect(!controller.isPaused(), "Controller should start and remain unpaused"))
        return 1;

    if (!expect(controller.update(true, false, false) == Transition::Pause, "Focus loss must pause once")
        || !expect(controller.isPaused(), "Controller must remember focus-owned pause")
        || !expect(controller.update(true, false, false) == Transition::None, "Repeated focus loss is not a new transition"))
        return 1;

    if (!expect(controller.update(true, false, true) == Transition::Resume, "Focus regain must resume once")
        || !expect(!controller.isPaused(), "Focus regain must clear the focus-owned pause")
        || !expect(controller.update(true, false, true) == Transition::None, "Repeated focus regain is not a new transition"))
        return 1;

    if (!expect(controller.update(true, false, false) == Transition::Pause, "Unfocused runtime must pause again")
        || !expect(controller.update(true, true, false) == Transition::Resume,
            "Offscreen diagnostics must remove a previously active focus pause")
        || !expect(!controller.isPaused(), "Offscreen diagnostics must remain unpaused")
        || !expect(controller.update(true, true, true) == Transition::None,
            "Diagnostic focus changes must not affect pause state")
        || !expect(controller.update(true, false, false) == Transition::Pause,
            "Returning to normal unfocused mode must pause again")
        || !expect(controller.update(false, false, false) == Transition::Resume,
            "Removing the XR session must clear only its focus-owned pause"))
        return 1;

    return 0;
}
