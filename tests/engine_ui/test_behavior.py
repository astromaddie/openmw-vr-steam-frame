"""Exercise the shipped Lua panel's callbacks, storage and lifecycle.
Run with OPENMW_SOURCE set; install tests/engine_ui/requirements.txt first.
Engine rendering/native C++ dispatch still require the native build/runtime check.
"""
import os
import pathlib
import sys
import unittest
from lupa import LuaRuntime
SOURCE = pathlib.Path(os.environ['OPENMW_SOURCE'])
class PanelTests(unittest.TestCase):
    def setUp(self):
        self.lua = LuaRuntime(unpack_returned_tuples=True)
        self.lua.execute('''
sections = {}
local function section(name)
 if not sections[name] then
  local data = {}
  sections[name] = {data=data, get=function(self,k) return data[k] end,
   set=function(self,k,v) data[k]=v end}
 end
 return sections[name]
end
native = {['world scale']=1,['height offset']=0,['seated']=0,['standing calibrated']=1,['haptics enabled']=1,['left handed mode']=0,['hand directed movement']=0,['show 3D crosshairs']=1}
active, xy, z, options = true, 0, 0, 0
liveButtons = {}
triggers = {}
heartbeat = nil
package.preload['openmw.vr'] = function() return {
 isVr=function() return true end, _frameSettingsActive=function() return active end,
 _closeFrameSettings=function() active=false end,
 _frameSettingGet=function(k) assert(native[k]~=nil); return native[k] end,
 _frameSettingSet=function(k,v) assert(native[k]~=nil); native[k]=v end,
 _recenterXY=function() xy=xy+1 end, _recenterZ=function() z=z+1 end,
 _frameOpenOptions=function() options=options+1; active=false end} end
package.preload['openmw.ui'] = function() return {TYPE={Flex='Flex'},content=function(t) return t end,
 create=function(layout) return {layout=layout,destroy=function() end} end} end
package.preload['openmw.util'] = function() return {vector2=function(x,y) return {x=x,y=y} end} end
package.preload['openmw.storage'] = function() return {playerSection=section} end
package.preload['openmw.async'] = function() return {callback=function(self,f) return f end} end
package.preload['openmw.input'] = function() return {triggers={MenuUp=true,MenuDown=true,MenuLeft=true,MenuRight=true,MenuSelect=true},registerTriggerHandler=function(k,f) triggers[k]=f end,CONTROLLER_BUTTON={A=1,B=2,Back=3,DPadDown=4,DPadUp=5,DPadLeft=6,DPadRight=7},KEY={Escape=1}} end
package.preload['openmw.interfaces'] = function() return {MWUI={templates={}},vrinputs={addMenuTriggersHeartBeatListener=function(f) heartbeat=f end}} end
package.preload['scripts.omw.vr.inputs.common'] = function() return {controlsSection=section('controls')} end
package.preload['scripts.omw.vr.ui.button'] = function() return function(text,cb)
 local b={text=text,callback=cb,element={layout={props={}},update=function() end},textContent={{props={}}},buttonContent={{events={}}},update=function() end,cleanup=function() end}
 liveButtons[#liveButtons+1]=b
 return b
end end
function click(label)
 for i=#liveButtons,1,-1 do
  local b=liveButtons[i]
  if b.text:gsub('^> ','')==label then b.callback(); return end
 end
 error('Missing button '..label)
end
''')
        self.panel = self.lua.execute((SOURCE/'files/data/scripts/omw/vr/ui/framesettings.lua').read_text())
        self.frame = self.panel.engineHandlers.onFrame
        self.frame()
    def click(self, text):
        self.lua.globals().click(text)
        self.frame()
    def test_open_preserves_saved_settings_and_unknown_values(self):
        self.lua.execute("sections.controls:set('SmoothTurn',true); sections.controls:set('SnapTurnRate',45); sections.SettingsFrameVR:set('unknown',99)")
        self.frame()
        self.assertEqual(self.lua.eval("sections.controls:get('SnapTurnRate')"),45)
        self.assertTrue(self.lua.eval("sections.controls:get('SmoothTurn')"))
        self.assertEqual(self.lua.eval("sections.SettingsFrameVR:get('unknown')"),99)
    def test_selected_profile_defaults(self):
        self.lua.execute("sections.SettingsFrameVR:set('unknown',99); sections.controls:set('SmoothTurn',false); sections.controls:set('SnapTurnRate',45); sections.controls:set('SmoothTurnSensitivity',math.rad(90))")
        self.click('Defaults Profile: Standard')
        self.assertFalse(self.lua.eval("sections.controls:get('SmoothTurn')"))
        self.assertEqual(self.lua.eval("sections.controls:get('SnapTurnRate')"),45)
        self.assertAlmostEqual(self.lua.eval("math.deg(sections.controls:get('SmoothTurnSensitivity'))"),90)
        self.click('Tab Defaults')
        self.assertTrue(self.lua.eval("sections.controls:get('SmoothTurn')"))
        self.assertAlmostEqual(self.lua.eval("math.deg(sections.controls:get('SmoothTurnSensitivity'))"),120)
        self.assertEqual(self.lua.eval("sections.controls:get('SnapTurnRate')"),30)
        self.assertEqual(self.lua.eval("sections.SettingsFrameVR:get('unknown')"),99)
        self.click('Defaults Profile: Personal')
        self.assertTrue(self.lua.eval("sections.controls:get('SmoothTurn')"))
        self.click('Tab Defaults')
        self.assertFalse(self.lua.eval("sections.controls:get('SmoothTurn')"))
    def test_real_native_controls_and_calibration(self):
        self.click('Controls'); self.click('Right'); self.click('On')
        self.assertEqual(self.lua.eval("native['left handed mode']"),1)
        self.assertEqual(self.lua.eval("native['haptics enabled']"),0)
        self.click('Room'); self.click('Calibrate Standing')
        self.assertEqual(self.lua.eval('xy'),1); self.assertEqual(self.lua.eval('z'),1)
        self.click('Recenter')
        self.assertEqual(self.lua.eval('xy'),2); self.assertEqual(self.lua.eval('z'),1)
    def click_at(self, x, y):
        self.lua.execute("""
        for i=#liveButtons,1,-1 do
            local b=liveButtons[i]
            local p=b.element.layout.props.position
            if b.alive and p and p.x==... then
                local _,y=...
                if p.y==y then b.callback(); return end
            end
        end
        error('Missing live button position')
        """,x,y)
        self.frame()
    def test_world_size_inverse_direction_and_limits(self):
        self.click_at(740,320)
        self.assertAlmostEqual(self.lua.eval("native['world scale']"),0.8)
        for _ in range(20): self.click_at(740,320)
        self.assertEqual(self.lua.eval("native['world scale']"),0.25)
        for _ in range(20): self.click_at(650,320)
        self.assertEqual(self.lua.eval("native['world scale']"),4)
        self.click('Tab Defaults')
        self.assertEqual(self.lua.eval("native['world scale']"),1)
    def test_seated_height_and_calibration_preserve_world_size(self):
        self.lua.execute("native['world scale']=0.5; native['standing calibrated']=0")
        self.click('Room'); self.click('Off')
        self.assertEqual(self.lua.eval("native['seated']"),1)
        self.click('Calibrate Seated')
        self.assertEqual(self.lua.eval('z'),1)
        self.click_at(740,200)
        self.assertAlmostEqual(self.lua.eval("native['height offset']"),0.05)
        for _ in range(40): self.click_at(650,200)
        self.assertEqual(self.lua.eval("native['height offset']"),-1)
        for _ in range(80): self.click_at(740,200)
        self.assertEqual(self.lua.eval("native['height offset']"),1)
        self.click('On'); self.click('Calibrate Standing')
        self.assertEqual(self.lua.eval('z'),2)
        self.assertEqual(self.lua.eval("native['seated']"),0)
        self.assertEqual(self.lua.eval("native['world scale']"),0.5)
    def test_native_options_and_back(self):
        self.click('Display'); self.click('Open Graphics Settings')
        self.assertEqual(self.lua.eval('options'),1)
        self.assertFalse(self.lua.eval('active'))
    def test_xr_navigation_and_heartbeat(self):
        self.lua.execute("triggers.MenuRight(); triggers.MenuSelect()")
        self.frame()
        self.click('Right')
        self.assertEqual(self.lua.eval("native['left handed mode']"),1)
        self.lua.execute("triggers={}; heartbeat()")
        self.assertTrue(self.lua.eval("type(triggers.MenuSelect)=='function'"))
    def test_a_pointer_and_menu_select_do_not_double_activate(self):
        self.lua.execute("liveButtons[2].buttonContent[1].events.focusGain(); triggers.MenuSelect()")
        self.frame()
        # Pointer's control remains owner; native selection did not switch tabs.
        self.click('Snap')
        self.assertTrue(self.lua.eval("sections.controls:get('SmoothTurn')"))
    def test_tab_defaults_preserve_other_tabs(self):
        self.lua.execute("native['haptics enabled']=0; sections.SettingsFrameVR:set('hud_scale',1.3)")
        self.click('Tab Defaults')
        self.assertEqual(self.lua.eval("native['haptics enabled']"),0)
        self.assertEqual(self.lua.eval("sections.SettingsFrameVR:get('hud_scale')"),1.3)
    def test_lua_files_parse(self):
        for path in ['files/data/scripts/omw/vr/ui/menu.lua','files/data/scripts/omw/vr/ui/framesettings.lua']:
            self.lua.execute('assert(load(...))', (SOURCE/path).read_text())
    def test_haptics_production_dispatch_is_gated(self):
        source=(SOURCE/'apps/openmw/mwlua/vrbindings.cpp').read_text()
        self.assertIn('actionSet.applyHaptics(path, Settings::vr().mHapticsEnabled ? value : 0.f)',source)
        self.assertIn('Settings::vr().mHapticsEnabled.set(value != 0)',source)
        self.assertIn('getWorld()->processChangedSettings({ { "VR", key } })',source)
if __name__=='__main__': unittest.main()
