--[[
rotate_hotkey.lua — cycle video rotation in 90° steps with a hotkey.

VLC's hotkey system cannot trigger video filters, and VLC 3.x removed the
lua var.add_callback API, so this script polls the libvlc "key-pressed"
variable instead.

Install:   ~/.local/share/vlc/lua/intf/rotate_hotkey.lua
Enable:    Tools > Preferences > (Show settings: All) > Interface > Main interfaces
             - check "Lua interpreter"  (adds extraintf "luaintf")
           then under Main interfaces > Lua:
             - Lua interface: rotate_hotkey
           ...or run:  vlc --extraintf luaintf --lua-intf rotate_hotkey
Key:       press  y  in the VLC window to rotate +90° (cycles back to 0°).
           Change KEY below to any plain character to rebind.
]]

local KEY = string.byte("y")  -- VLC keycode of a plain ASCII key == its codepoint
local STEP = 90

local function msleep(ms) vlc.misc.mwait(vlc.misc.mdate() + ms * 1000) end

local angle = 0
local osd_channel = nil

local function apply_rotation()
  local vout = vlc.object.vout()
  if not vout then return end
  local filter = (angle == 0) and "" or ("rotate{angle=" .. angle .. "}")
  vlc.var.set(vout, "video-filter", filter)
  pcall(function()
    osd_channel = osd_channel or vlc.osd.channel_register()
    vlc.osd.message("Rotation: " .. angle .. "\xc2\xb0", osd_channel, "top-right", 1200000)
  end)
  vlc.msg.info("[rotate_hotkey] rotation set to " .. angle)
end

local libvlc = vlc.object.libvlc()
pcall(vlc.var.set, libvlc, "key-pressed", 0)
vlc.msg.info("[rotate_hotkey] active, key code " .. KEY)

while true do
  local ok, key = pcall(vlc.var.get, libvlc, "key-pressed")
  if ok and key == KEY then
    -- clear so an immediate repeat press of the same key is detected
    pcall(vlc.var.set, libvlc, "key-pressed", 0)
    angle = (angle + STEP) % 360
    apply_rotation()
  end
  msleep(50)
end
