-- QA-only addon: load with a separate validation profile.
local core = require('openmw.core')
local I = require('openmw.interfaces')
local started, sent
return {engineHandlers={onVRFrame=function()
    local now=core.getRealTime()
    if not started then started=now end
    if sent or now-started<25 or not core.isWorldPaused() then return end
    local head=I.vrspaces.locateSpaceInWorld(I.vrspaces.referenceSpaces.View)
    local panel=I.vrspaces.locateSpaceInWorld('DefaultWindow')
    if not head or not panel then return end
    core.sendGlobalEvent('UIOcclusionPlaceActor',{head=head.position,panel=panel.position})
    sent=true
    print('UI_OCCLUSION_POSE',head.position,panel.position)
end}}
