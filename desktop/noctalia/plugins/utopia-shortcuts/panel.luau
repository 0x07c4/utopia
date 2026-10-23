--!nonstrict
-- Read-only help: never dispatch a binding or evaluate its command.
local rows = {}
local query = ""
local category = "all"
local selected = 1
local focusSerial = 0
local requestSerial = 0
local loading = false
local errorMessage = ""
local bindingCount = 0
local categories = { "all", "apps", "windows", "workspaces", "desktop", "media", "capture", "session", "other" }
local render
local strings = {}
local searchIndex = {}
local chordViews = {}
local rowViews = {}
local displayedRows = {}

local function tr(key, values)
  if values ~= nil then
    return noctalia.tr(key, values)
  end
  if strings[key] == nil then
    strings[key] = noctalia.tr(key)
  end
  return strings[key]
end

local function matches(row)
  if category ~= "all" and row.group ~= category then
    return false
  end
  local cached = searchIndex[row]
  if cached == nil then
    local keys = table.concat(row.keys, " ")
    local compactKeys = string.gsub(keys, "%s*%+%s*", "+")
    local common = row.common and tr("group.frequent") or ""
    local haystack = string.lower(row.label .. " " .. (row.detail or "") .. " " .. row.search .. " " .. keys .. " " .. compactKeys .. " " .. tr("group." .. row.group) .. " " .. common)
    cached = { haystack, string.gsub(haystack, "%s+", "") }
    searchIndex[row] = cached
  end
  local haystack, tight = cached[1], cached[2]
  for word in string.gmatch(string.lower(query), "%S+") do
    if not string.find(haystack, word, 1, true) and not string.find(tight, word, 1, true) then
      return false
    end
  end
  return true
end

local function visibleRows()
  local output = {}
  local searching = noctalia.string.trim(query) ~= ""
  for _, row in ipairs(rows) do
    -- Search the original rows, not the range endpoints: workspace 5 must
    -- resolve to its actual key, and searching 1 must never imply 2–9 match.
    local candidates = searching and row.members or nil
    for _, candidate in ipairs(candidates or { row }) do
      if matches(candidate) then
        table.insert(output, candidate)
      end
    end
  end
  table.sort(output, function(left, right)
    local leftGroup = category == "all" and left.common and 0 or (table.find(categories, left.group) or 99)
    local rightGroup = category == "all" and right.common and 0 or (table.find(categories, right.group) or 99)
    if leftGroup ~= rightGroup then
      return leftGroup < rightGroup
    end
    local leftPriority = left.priority or 1000
    local rightPriority = right.priority or 1000
    if leftPriority ~= rightPriority then
      return leftPriority < rightPriority
    end
    return (left.order or tonumber(left.id) or 0) < (right.order or tonumber(right.id) or 0)
  end)
  return output
end

local function chordCaps(chord)
  if chordViews[chord] ~= nil then
    return chordViews[chord]
  end
  local caps = {}
  for part in string.gmatch(chord, "[^+]+") do
    local key = noctalia.string.trim(part)
    if key ~= "" then
      table.insert(caps, ui.row({ paddingH = 6, paddingV = 3, fill = "surface_variant", radius = 5 }, {
        ui.label({ text = key, fontSize = 11, fontFamily = "Maple Mono NF CN", color = "on_surface_variant" }),
      }))
    end
  end
  local view = ui.row({ gap = 4, align = "center", justify = "end" }, caps)
  chordViews[chord] = view
  return view
end

local function bindingRow(row, index)
  local active = selected == index
  local state = active and "active" or "normal"
  local cached = rowViews[row]
  if cached ~= nil and cached[state] ~= nil then
    return cached[state]
  end
  local aliases = {}
  for _, chord in ipairs(row.keys) do
    table.insert(aliases, chordCaps(chord))
  end
  local description = {
    ui.label({ text = row.label, fontSize = 13, maxLines = 2, color = selected == index and "on_secondary_container" or "on_surface" }),
  }
  if row.detail ~= nil and row.detail ~= "" then
    table.insert(description, ui.label({ text = row.detail, fontSize = 11, maxLines = 3, color = "on_surface_variant" }))
  end
  local view = ui.row({
    key = "binding-" .. row.id,
    gap = 12,
    paddingH = 12,
    paddingV = 9,
    align = "center",
    radius = 8,
    fill = selected == index and "secondary_container" or "surface",
    onClick = function()
      -- A cached row can move after filtering; resolve its current position.
      selected = table.find(displayedRows, row) or 1
      render()
    end,
  }, {
    ui.column({ flexGrow = 1, gap = 4, align = "stretch" }, description),
    ui.column({ width = 340, gap = 4, align = "end" }, aliases),
  })
  cached = cached or {}
  cached[state] = view
  rowViews[row] = cached
  return view
end

render = function()
  local visible = visibleRows()
  displayedRows = visible
  selected = math.max(1, math.min(selected, #visible))
  local content = {}
  if loading then
    table.insert(content, ui.label({ text = tr("loading"), color = "on_surface_variant" }))
  elseif errorMessage ~= "" then
    table.insert(content, ui.label({ text = tr("load_error"), color = "error", fontWeight = "bold" }))
    table.insert(content, ui.label({ text = errorMessage, maxLines = 4, color = "on_surface_variant" }))
    table.insert(content, ui.label({ text = tr("retry"), maxLines = 2, color = "on_surface_variant" }))
  elseif #visible == 0 then
    table.insert(content, ui.column({ gap = 10, padding = 24, align = "center" }, {
      ui.glyph({ name = "search", size = 28, color = "on_surface_variant" }),
      ui.label({ text = tr("empty"), color = "on_surface_variant" }),
    }))
  else
    local group = ""
    for index, row in ipairs(visible) do
      local section = category == "all" and row.common and "frequent" or row.group
      if section ~= group then
        group = section
        table.insert(content, ui.row({ key = "heading-" .. group, paddingH = 10, paddingV = 6 }, {
          ui.label({ text = tr("group." .. group), fontSize = 11, fontWeight = "bold", color = "primary" }),
        }))
      end
      table.insert(content, bindingRow(row, index))
    end
  end
  local options = {}
  for _, group in ipairs(categories) do
    table.insert(options, tr("group." .. group))
  end
  panel.render(ui.column({ gap = 12, flexGrow = 1, align = "stretch" }, {
    ui.row({ key = "header", gap = 10, align = "center" }, {
      ui.glyph({ name = "keyboard", size = 24, color = "primary" }),
      ui.label({ text = tr("title"), fontSize = 18, fontWeight = "bold", flexGrow = 1 }),
      ui.label({ text = tr("read_only"), fontSize = 11, color = "on_surface_variant" }),
      ui.button({ glyph = "refresh", tooltip = tr("refresh"), variant = "ghost", onClick = "onRefresh" }),
      ui.button({ glyph = "close", tooltip = tr("close"), variant = "ghost", onClick = "onClose" }),
    }),
    ui.row({ key = "filters", gap = 10, align = "center" }, {
      ui.input({
        key = "query-" .. tostring(focusSerial),
        value = query,
        placeholder = tr("search"),
        flexGrow = 1,
        focus = true,
        onChange = "onSearchChange",
      }),
      ui.select({ key = "category", width = 130, options = options, selectedIndex = table.find(categories, category) - 1, onChange = "onCategoryChange" }),
    }),
    ui.scroll({ key = "bindings", flexGrow = 1, minHeight = 0, gap = 3, revealKey = visible[selected] and ("binding-" .. visible[selected].id) or "" }, content),
    ui.separator({ color = "outline" }),
    ui.row({ key = "footer", gap = 10, align = "center" }, {
      ui.label({ text = tr("count", { rows = #visible, keys = bindingCount }), fontSize = 11, color = "on_surface_variant", flexGrow = 1 }),
      ui.label({ text = tr("navigation"), fontSize = 11, color = "on_surface_variant" }),
    }),
  }))
end

function onRefresh()
  -- Cache only this configuration/locale generation, never machine activity.
  strings = {}
  searchIndex = {}
  chordViews = {}
  rowViews = {}
  requestSerial += 1
  local serial = requestSerial
  loading = true
  errorMessage = ""
  render()
  local helper = noctalia.pluginDir() .. "/bindings.py"
  local started = noctalia.runAsync({ "python", "-B", helper }, function(result)
    if serial ~= requestSerial then
      return
    end
    loading = false
    local ok, data = pcall(noctalia.json.decode, result.stdout)
    if not ok or type(data) ~= "table" or data.schema_version ~= 1 or type(data.rows) ~= "table" or result.stdoutTruncated then
      errorMessage = tr("reader_error")
      rows = {}
      bindingCount = 0
    elseif result.exitCode ~= 0 or data.error ~= "" then
      errorMessage = data.error ~= "" and data.error or tr("reader_error")
      rows = {}
      bindingCount = 0
    else
      rows = data.rows
      bindingCount = data.binding_count
    end
    selected = 1
    render()
  end)
  if not started then
    loading = false
    rows = {}
    bindingCount = 0
    errorMessage = tr("reader_error")
    render()
  end
end

function onOpen(_context)
  query = ""
  category = "all"
  selected = 1
  focusSerial += 1
  onRefresh()
end

function onClose()
  requestSerial += 1
  panel.close()
end

function onSearchChange(value)
  query = value
  selected = 1
  render()
end

function onCategoryChange(index, _text)
  category = categories[(tonumber(index) or 0) + 1] or "all"
  selected = 1
  render()
end

function onKey(chord, pressed)
  if not pressed then
    return
  end
  if chord == "ctrl+f" then
    focusSerial += 1
  elseif chord == "ctrl+r" then
    onRefresh()
    return
  elseif chord == "Down" then
    selected += 1
  elseif chord == "Up" then
    selected -= 1
  elseif chord == "Page_Down" then
    selected += 7
  elseif chord == "Page_Up" then
    selected -= 7
  end
  render()
end
