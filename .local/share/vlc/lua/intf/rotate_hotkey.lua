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
           t  clip tagger: tags dialog
           i  clip tagger: series dialog
           Change the *_KEY constants below to any plain character to rebind.

The clip-tagger keys work in any VLC session: the root is taken from the
CLIPTAG_ROOT / CLIPTAG_DB env vars when set, otherwise discovered by walking
up from the playing clip to the nearest cliptags.json. With no db found
they just show an OSD notice.
Dialogs are external GTK windows (cliptag-dialog.py), since VLC hotkeys
can't reach lua extension dialogs.
]]

local ROTATE_KEY = string.byte("y")  -- VLC keycode of a plain ASCII key == its codepoint
local MIRROR_KEY = string.byte("u")
local TAGS_KEY   = string.byte("t")
local SERIES_KEY = string.byte("i")
local STEP = 90

local CLIPTAG_ROOT = os.getenv("CLIPTAG_ROOT")
local CLIPTAG_DB   = os.getenv("CLIPTAG_DB")

local HELPER = os.getenv("HOME") .. "/.local/share/vlc/lua/intf/cliptag-dialog.py"

local function sh_quote(s) return "'" .. s:gsub("'", "'\\''") .. "'" end



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

local function current_clip_path()
  local ok, item = pcall(vlc.input.item)
  if not ok or not item then return nil end
  local uri = item:uri()
  if not uri or not uri:find("^file://") then return nil end
  return vlc.strings.decode_uri(uri:gsub("^file://", ""))
end

local function tags_dialog()
  local clip = current_clip_path()
  if not clip then osd("Tagger: no local clip playing") return end
  -- /usr/bin/python3 explicitly: the GTK dialog needs PyGObject, which the
  -- pyenv shim python3 doesn't have
  local f = io.popen("/usr/bin/python3 " .. sh_quote(HELPER) .. " tags " .. sh_quote(clip)
    .. " 2>>/tmp/cliptag-dialog.err")
  local out = f:read("*a") or ""
  f:close()
  local saved = out:match("SAVED: (.-)%s*\n")
  if saved then
    osd("Tags: " .. saved)
  elseif out:match("CANCELLED") then
    osd("Tags: unchanged")
  elseif out:match("NODB") then
    osd("Tagger: no cliptags.json found above clip")
  else
    osd("Tagger error — see /tmp/cliptag-dialog.err")
  end
end

-- os.execute / io.popen block only this lua thread; playback keeps running.
local function series_dialog()
  local clip = current_clip_path()  -- only needed to discover the root db
  local f = io.popen("/usr/bin/python3 " .. sh_quote(HELPER) .. " series"
    .. (clip and (" " .. sh_quote(clip)) or "")
    .. " 2>>/tmp/cliptag-dialog.err")
  local out = f:read("*a") or ""
  f:close()
  if out:match("DONE") then
    osd("Series saved")
  elseif out:match("NODB") then
    osd("Tagger: no cliptags.json found above clip")
  else
    osd("Series dialog error — see /tmp/cliptag-dialog.err")
  end
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
vlc.msg.info("[rotate_hotkey] active, rotate=" .. ROTATE_KEY .. " mirror=" .. MIRROR_KEY
  .. (CLIPTAG_ROOT and (" cliptag root=" .. CLIPTAG_ROOT) or " (cliptag off)"))

if CLIPTAG_ROOT and os.getenv("CLIPTAG_SELFTEST") then
  vlc.msg.info("[rotate_hotkey] selftest: opening series dialog")
  series_dialog()
  vlc.msg.info("[rotate_hotkey] selftest: series dialog closed")
end

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
  elseif ok and (key == TAGS_KEY or key == SERIES_KEY) then
    pcall(vlc.var.set, libvlc, "key-pressed", 0)
    if key == TAGS_KEY then tags_dialog() else series_dialog() end
  end
  msleep(50)
end
