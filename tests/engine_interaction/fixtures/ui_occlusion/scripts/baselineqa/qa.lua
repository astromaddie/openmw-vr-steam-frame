-- QA-only addon: load with a separate validation profile.
local core = require('openmw.core')
local menu = require('openmw.menu')
local storage = require('openmw.storage')
local started, configured
return {engineHandlers={onFrame=function()
    if not configured then
        storage.playerSection('UiGroup'):set('ShowTutorials', false)
        configured=true
    end
    if menu.getState() ~= menu.STATE.Running then return end
    local now=core.getRealTime()
    if not started then started=now; print('UI_OCCLUSION_RUNNING') end
    if started and now-started>=75 then
        print('UI_OCCLUSION_QUIT'); menu.quit(); started=now+1000
    end
end}}
