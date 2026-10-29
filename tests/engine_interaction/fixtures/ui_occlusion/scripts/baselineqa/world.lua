-- QA-only addon: load with a separate validation profile.
local world = require('openmw.world')
local util = require('openmw.util')
return {eventHandlers={UIOcclusionPlaceActor=function(data)
    local player=world.players[1]
    local actor=world.createObject('chargen boat guard 1')
    local center=data.head+(data.panel-data.head)*0.45
    local feet=center-util.vector3(0,0,45)
    actor:teleport(player.cell,feet,{onGround=false})
    print('UI_OCCLUSION_ACTOR',actor.recordId,feet)
end}}
