--!nonstrict

local function render()
  barWidget.setGlyph(noctalia.getConfig("glyph"))
  barWidget.setTooltip(noctalia.tr("title"))
end

function update()
  render()
end

function onClick()
  noctalia.togglePanel("utopia/wallpaper:center")
end

render()
