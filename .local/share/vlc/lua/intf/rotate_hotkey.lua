--[[
rotate_hotkey.lua — video rotate + mirror hotkeys.

VLC's hotkey system cannot trigger video filters, and VLC 3.x removed the
lua var.add_callback API, so this script polls the libvlc "key-pressed"
variable instead.

Only one lua interface can run at a time, so both hotkeys live in this one
script (they also share the single "video-filter" variable, which must be
written as one combined filter chain).

Install:   ~/.local/share/vlc/lua/intf/rotate_hotkey.lua
Enable:    Tools > Preferences > (Show settings: All) > Interface > Main interfaces
             - check "Lua interpreter"  (adds extraintf "luaintf")
           then under Main interfaces > Lua:
             - Lua interface: rotate_hotkey
           ...or run:  vlc --extraintf luaintf --lua-intf rotate_hotkey
Keys:      y  rotate +90° (cycles back to 0°)
           u  toggle horizontal mirror (flip left/right)
           Change ROTATE_KEY / MIRROR_KEY below to any plain character to rebind.
]]

local ROTATE_KEY = string.byte("y")  -- VLC keycode of a plain ASCII key == its codepoint
local MIRROR_KEY = string.byte("u")
local STEP = 90

local function msleep(ms) vlc.misc.mwait(vlc.misc.mdate() + ms * 1000) end

local angle = 0
local mirrored = false
local osd_channel = nil

-- transform (unlike rotate) swaps the output canvas dimensions, so the full
-- picture always fits — no cropping. transform type=90 is clockwise; the old
-- rotate{angle=90} turned counter-clockwise, so map 90→270 / 270→90 to keep
-- the same visual direction.
local TRANSFORM = { [90] = "270", [180] = "180", [270] = "90" }

local function osd(text)
  pcall(function()
    osd_channel = osd_channel or vlc.osd.channel_register()
    vlc.osd.message(text, osd_channel, "top-right", 1200000)
  end)
end

local function apply_filters()
  local vout = vlc.object.vout()
  if not vout then return end
  local chain = {}
  if angle ~= 0 then chain[#chain + 1] = "transform{type=" .. TRANSFORM[angle] .. "}" end
  -- hflip goes last so it mirrors the image as displayed, after any rotation
  if mirrored then chain[#chain + 1] = "transform{type=hflip}" end
  vlc.var.set(vout, "video-filter", table.concat(chain, ":"))
  vlc.msg.info("[rotate_hotkey] angle=" .. angle .. " mirrored=" .. tostring(mirrored))
end

local libvlc = vlc.object.libvlc()
pcall(vlc.var.set, libvlc, "key-pressed", 0)
vlc.msg.info("[rotate_hotkey] active, rotate=" .. ROTATE_KEY .. " mirror=" .. MIRROR_KEY)

while true do
  local ok, key = pcall(vlc.var.get, libvlc, "key-pressed")
  if ok and (key == ROTATE_KEY or key == MIRROR_KEY) then
    -- clear so an immediate repeat press of the same key is detected
    pcall(vlc.var.set, libvlc, "key-pressed", 0)
    if key == ROTATE_KEY then
      angle = (angle + STEP) % 360
      osd("Rotation: " .. angle .. "\xc2\xb0")
    else
      mirrored = not mirrored
      osd("Mirror: " .. (mirrored and "on" or "off"))
    end
    apply_filters()
  end
  msleep(50)
end
