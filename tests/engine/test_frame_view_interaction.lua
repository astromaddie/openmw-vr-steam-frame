local source = assert(os.getenv('OPENMW_SOURCE'), 'OPENMW_SOURCE must point to OpenMW source')
package.path = source .. '/files/data/?.lua;' .. package.path

local left = '/user/hand/left'
local right = '/user/hand/right'
local frameProfile = '/interaction_profiles/valve/frame_controller_valve'
local viveProfile = '/interaction_profiles/htc/vive_controller'
local viewPath = left .. '/input/view/click'
local menuPath = right .. '/input/menu/click'
local menuSelectPath = right .. '/input/a/click'
local menuPaths = {
    [left .. '/input/dpad_up/click'] = 'MenuUp',
    [left .. '/input/dpad_down/click'] = 'MenuDown',
    [left .. '/input/dpad_left/click'] = 'MenuLeft',
    [left .. '/input/dpad_right/click'] = 'MenuRight',
}

local profiles = { [left] = frameProfile, [right] = frameProfile }
local values = { [viewPath] = false, [menuPath] = false, [menuSelectPath] = false }
for path in pairs(menuPaths) do values[path] = false end
local focused = true
local now = 0
local paused = true
local recenteredXY = 0
local recenteredZ = 0
local manualMenuBack = 0
local activated = {}
local groups = {}
local sectionData = {}

local vr = {
    INTERACTION_VALUE_TYPES = { Boolean = 1, Float = 2, Axis = 3, Pose = 4 },
    availableInteractions = {
        [frameProfile] = {
            [left] = {
                ['/input/view/click'] = 1,
                ['/input/dpad_up/click'] = 1,
                ['/input/dpad_down/click'] = 1,
                ['/input/dpad_left/click'] = 1,
                ['/input/dpad_right/click'] = 1,
            },
            [right] = { ['/input/a/click'] = 1 },
        },
        [viveProfile] = { [right] = { ['/input/menu/click'] = 1 } },
    },
    isLeftHandedMode = function() return false end,
    isFocused = function() return focused end,
    isControllerActive = function() return true end,
    _getInteractionProfileOfController = function(path) return profiles[path] end,
    _recenterXY = function() recenteredXY = recenteredXY + 1 end,
    _recenterZ = function() recenteredZ = recenteredZ + 1 end,
}

local input
input = {
    ACTION_TYPE = { Boolean = 1, Number = 2, Range = 3 },
    actions = {},
    triggers = {},
    registerAction = function(definition) input.actions[definition.key] = definition end,
    registerTrigger = function(definition) input.triggers[definition.key] = definition end,
    bindAction = function() end,
    activateTrigger = function(key) activated[#activated + 1] = key end,
    getBooleanActionValue = function() return false end,
}

local function playerSection(key)
    if not sectionData[key] then
        local section = { data = {}, subscribers = {} }
        function section:subscribe(callback) self.subscribers[#self.subscribers + 1] = callback end
        function section:asTable() return self.data end
        function section:get(id) return self.data[id] end
        sectionData[key] = section
    end
    return sectionData[key]
end

package.preload['openmw.vr'] = function() return vr end
package.preload['openmw.ui'] = function() return {} end
package.preload['openmw.util'] = function() return {} end
package.preload['openmw.storage'] = function() return { playerSection = playerSection } end
package.preload['openmw.input'] = function() return input end
package.preload['openmw.core'] = function()
    return {
        getRealTime = function() return now end,
        isWorldPaused = function() return paused end,
        l10n = function() return function(key) return key end end,
    }
end
package.preload['openmw.async'] = function()
    return { callback = function(_, callback) return callback end }
end
package.preload['openmw.interfaces'] = function()
    return {
        vrinputs = {
            getInteractionProfileOfController = function(path) return profiles[path] end,
            getInputValue = function(path) return values[path] end,
        },
        Settings = { registerGroup = function(group) groups[group.key] = group end },
        UI = { getMode = function() return nil end },
    }
end

local common = require('scripts.omw.vr.inputs.common')
common.registerSettingsGroup()

local bindingSection = common.bindingSection
for _, setting in ipairs(groups[common.userBindingsGroupKey].settings) do
    local binding = setting.default
    bindingSection.data[binding.id] = binding
end

common.registerTriggerHandlerForMainMenu('MenuBack', function()
    manualMenuBack = manualMenuBack + 1
end)
common.onFrame()

local function resetObserved()
    activated = {}
    manualMenuBack = 0
end

local function countTrigger(key)
    local count = 0
    for _, value in ipairs(activated) do
        if value == key then count = count + 1 end
    end
    return count
end

local function tap(path)
    values[path] = true
    common.updateInputs(0)
    values[path] = false
    common.updateInputs(0)
end

local function expect(condition, message)
    if not condition then error(message, 2) end
end

-- Frame D-pad and A reach the existing menu-only trigger channel.
for path, trigger in pairs(menuPaths) do
    resetObserved()
    tap(path)
    expect(countTrigger(trigger) == 1, 'Frame D-pad did not invoke ' .. trigger)
end
resetObserved()
tap(menuSelectPath)
expect(countTrigger('MenuSelect') == 1, 'Frame A did not invoke MenuSelect in menus')

-- The same controls cannot navigate or select while the gameplay action set is active.
paused = false
common.onFrame()
resetObserved()
tap(left .. '/input/dpad_up/click')
tap(menuSelectPath)
expect(countTrigger('MenuUp') == 0, 'Frame D-pad navigation leaked into gameplay')
expect(countTrigger('MenuSelect') == 0, 'Frame A menu selection leaked into gameplay')
paused = true
common.onFrame()

-- A short Frame View tap invokes the existing menu back trigger once.
values[viewPath] = true
now = 0
common.updateInputs(0)
now = 0.45
common.updateInputs(0.45)
values[viewPath] = false
common.updateInputs(0)
expect(countTrigger('MenuBack') == 1, 'short Frame View did not invoke MenuBack')
expect(countTrigger('Recenter') == 0, 'short Frame View invoked Recenter')

-- A one second Frame View hold recenters, then release must not also go back.
resetObserved()
values[viewPath] = true
now = 10
common.updateInputs(0)
now = 11.1
common.updateInputs(1.1)
expect(countTrigger('Recenter') == 1, 'one second Frame View hold did not invoke Recenter')
expect(manualMenuBack == 0, 'long Frame View hold invoked the manual MenuBack callback')
now = 13.1
common.updateInputs(2)
expect(recenteredXY == 1 and recenteredZ == 1, 'three second Frame View hold did not calibrate XY and height')
now = 13.2
common.updateInputs(0.1)
values[viewPath] = false
common.updateInputs(0)
expect(countTrigger('MenuBack') == 0, 'Frame View hold release invoked MenuBack')
expect(recenteredXY == 1 and recenteredZ == 1, 'height calibration repeated during one hold')

-- Losing focus while held clears the timer; refocusing after physical release is neutral.
resetObserved()
values[viewPath] = true
now = 20
common.updateInputs(0)
focused = false
values[viewPath] = false
now = 20.5
common.updateInputs(0.5)
focused = true
now = 21
common.updateInputs(0.5)
expect(#activated == 0 and manualMenuBack == 0, 'focus loss/refocus synthesized a Frame View action')
expect(recenteredXY == 1 and recenteredZ == 1, 'focus loss/refocus retained the calibration hold')

-- Other profiles keep the existing generic long-press/manual-trigger behavior.
profiles[left] = nil
profiles[right] = viveProfile
common.onFrame()
resetObserved()
values[menuPath] = true
now = 30
common.updateInputs(0)
now = 30.8
common.updateInputs(0.8)
expect(countTrigger('Recenter') == 1, 'legacy long-press threshold changed for a non-Frame profile')
expect(manualMenuBack == 1, 'legacy manual long-press callback changed for a non-Frame profile')

print('Frame View and legacy long-press interaction tests passed')
