-- A discoverable route to the same reference panel, not a command runner.
local guideId = "utopia/shortcuts:guide"
local keywords = "快捷键 快捷键说明 帮助 按键 热键 shortcuts keybindings hotkeys keyboard help super+/"

function onQuery(text)
  local title = noctalia.tr("launcher.title")
  local subtitle = noctalia.tr("launcher.subtitle")
  local query = string.lower(noctalia.string.trim(text))
  local score = 1
  if query ~= "" then
    score = noctalia.fuzzyScore(query, string.lower(title .. " " .. keywords))
    if score == nil then
      launcher.setResults(text, {})
      return
    end
  end
  launcher.setResults(text, {
    { id = "guide", title = title, subtitle = subtitle, glyph = "keyboard", score = score },
  })
end

function onActivate(id)
  if id == "guide" then
    noctalia.togglePanel(guideId)
  end
end
