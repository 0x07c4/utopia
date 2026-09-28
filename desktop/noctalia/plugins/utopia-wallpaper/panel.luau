--!nonstrict
-- Utopia-owned wallpaper center. Local files and Wallhaven results deliberately
-- share one selection model and one keyboard vocabulary.

local API_URL = "https://wallhaven.cc/api/v1/search"
local COLUMNS = 4
local PAGE_SIZE = 12
local THUMB_CONCURRENCY = 6
local TILE_WIDTH = 205
local TILE_HEIGHT = 116

local tab = "local"
local selected = 1
local localPage = 1
local onlinePage = 1
local onlineTotalPages = 1
local localFiles = {}
local onlineItems = {}
local query = ""
local sorts = { "relevance", "random", "date_added", "views", "favorites", "toplist", "hot" }
local sortIndex = 2
local sortOrder = "desc"
local topRanges = { "1d", "3d", "1w", "1M", "3M", "6M", "1y" }
local topRangeIndex = 3
local categoryGeneral = true
local categoryAnime = true
local categoryPeople = true
local puritySfw = true
local puritySketchy = false
local purityNsfw = false
local ratios = {
  "", "landscape", "portrait", "16x9", "16x10", "21x9", "32x9", "48x9",
  "9x16", "10x16", "9x18", "1x1", "3x2", "4x3", "5x4",
}
local ratioIndex = 0
local resolutionModes = { "", "atleast", "resolutions" }
local resolutionModeIndex = 0
local resolutionWidth = ""
local resolutionHeight = ""
local randomSeed = ""
local loading = false
local applying = false
local errorMessage = ""
local searchFocusSerial = 0
local searchEditing = false
local filterEditing = false
local pageFocusSerial = 0
local pageDraft = "1"
local pageEditing = false
local thumbPaths = {}
local thumbPending = {}
local thumbQueue = {}
local thumbActive = 0

local render
local fetchOnline

local function tr(key, values)
  return noctalia.tr(key, values)
end

local function wallpaperDir()
  local configured = noctalia.getConfig("wallpaper_dir")
  if type(configured) == "string" and configured ~= "" then
    return noctalia.expandPath(configured)
  end
  local native = noctalia.wallpaperDirectory()
  if type(native) == "string" and native ~= "" then
    return noctalia.expandPath(native)
  end
  return noctalia.expandPath("~/Pictures/Wallpapers")
end

local function apiKey()
  local configured = noctalia.getConfig("api_key")
  if type(configured) == "string" then
    return noctalia.string.trim(configured)
  end
  return ""
end

local function boolDigit(value)
  return value and "1" or "0"
end

local function categoriesParameter()
  local value = boolDigit(categoryGeneral) .. boolDigit(categoryAnime) .. boolDigit(categoryPeople)
  return value == "000" and "100" or value
end

local function purityParameter()
  local value = boolDigit(puritySfw) .. boolDigit(puritySketchy) .. boolDigit(purityNsfw and apiKey() ~= "")
  return value == "000" and "100" or value
end

local function resolutionParameter()
  local width = tonumber(resolutionWidth)
  local height = tonumber(resolutionHeight)
  if width == nil or height == nil or width < 1 or height < 1 then
    return nil
  end
  return tostring(math.floor(width)) .. "x" .. tostring(math.floor(height))
end

local function selectedSort()
  return sorts[sortIndex + 1] or "date_added"
end

local function relevanceWithoutQuery()
  return selectedSort() == "relevance" and noctalia.string.trim(query) == ""
end

local function apiPage()
  return relevanceWithoutQuery() and onlinePage + 1 or onlinePage
end

local function normalizeTotalPages(lastPage)
  if relevanceWithoutQuery() then
    return math.max(1, lastPage - 1)
  end
  return math.max(1, lastPage)
end

local function httpHeaders()
  local headers = { "Accept: application/json" }
  local key = apiKey()
  if key ~= "" then
    table.insert(headers, "X-API-Key: " .. key)
  end
  return headers
end

local function resetRandomSeed()
  randomSeed = ""
end

local function resetOnlinePage()
  onlinePage = 1
  resetRandomSeed()
end

local function isImage(name)
  local lower = string.lower(name)
  return lower:match("%.jpe?g$") ~= nil
    or lower:match("%.png$") ~= nil
    or lower:match("%.webp$") ~= nil
    or lower:match("%.bmp$") ~= nil
end

local function joinPath(parent, child)
  if child:sub(1, 1) == "/" then
    return child
  end
  if parent:sub(-1) == "/" then
    return parent .. child
  end
  return parent .. "/" .. child
end

local function scanDirectory(directory, depth, output)
  if depth > 2 or #output >= 500 then
    return
  end
  local names = noctalia.listDir(directory)
  if type(names) ~= "table" then
    return
  end
  table.sort(names)
  for _, name in ipairs(names) do
    if #output >= 500 then
      break
    end
    local path = joinPath(directory, name)
    local info = noctalia.fileInfo(path)
    if info ~= nil and info.isDir then
      scanDirectory(path, depth + 1, output)
    elseif info ~= nil and isImage(path) then
      table.insert(output, { id = path, path = path, label = name })
    end
  end
end

local function loadLocal()
  localFiles = {}
  local directory = wallpaperDir()
  noctalia.mkdirAll(directory)
  scanDirectory(directory, 0, localFiles)
  localPage = 1
  selected = math.min(math.max(1, selected), math.max(1, #localFiles))
end

local function localTotalPages()
  return math.max(1, math.ceil(#localFiles / PAGE_SIZE))
end

local function currentPage()
  return tab == "local" and localPage or onlinePage
end

local function currentTotalPages()
  return tab == "local" and localTotalPages() or onlineTotalPages
end

local function currentItems()
  return tab == "local" and localFiles or onlineItems
end

local function visibleItems()
  local items = currentItems()
  if tab == "online" then
    return items
  end
  local first = (localPage - 1) * PAGE_SIZE + 1
  local result = {}
  for index = first, math.min(#items, first + PAGE_SIZE - 1) do
    table.insert(result, items[index])
  end
  return result
end

local function selectedVisibleIndex()
  if tab == "online" then
    return selected
  end
  return selected - ((localPage - 1) * PAGE_SIZE)
end

local function clampSelection()
  local count = #currentItems()
  if count == 0 then
    selected = 1
  else
    selected = math.min(math.max(selected, 1), count)
  end
end

local function selectTab(nextTab)
  if tab == nextTab then
    return
  end
  tab = nextTab
  selected = 1
  errorMessage = ""
  if tab == "local" then
    localPage = 1
    loadLocal()
    render()
  elseif #onlineItems == 0 then
    onlinePage = 1
    fetchOnline()
  else
    render()
  end
end

local function moveSelection(delta)
  local count = #currentItems()
  if count == 0 then
    return
  end
  selected = math.min(math.max(selected + delta, 1), count)
  if tab == "local" then
    localPage = math.floor((selected - 1) / PAGE_SIZE) + 1
  end
  render()
end

local function localApply(item)
  noctalia.setWallpaper(item.path)
  noctalia.notify(tr("title"), tr("applied"))
end

local function onlineExtension(item)
  if item.file_type == "image/png" then
    return ".png"
  end
  return ".jpg"
end

local function onlineApply(item)
  if applying or type(item.path) ~= "string" or item.path == "" then
    return
  end
  applying = true
  render()
  local directory = wallpaperDir()
  local ok = noctalia.mkdirAll(directory)
  if not ok then
    applying = false
    errorMessage = tr("directory_error")
    render()
    return
  end
  local destination = joinPath(directory, "wallhaven-" .. item.id .. onlineExtension(item))
  if noctalia.fileExists(destination) then
    local onlineSelection = selected
    local preservedOnlinePage = onlinePage
    noctalia.setWallpaper(destination)
    applying = false
    noctalia.notify(tr("title"), tr("applied"))
    loadLocal()
    tab = "online"
    selected = onlineSelection
    onlinePage = preservedOnlinePage
    render()
    return
  end
  local started = noctalia.download(item.path, destination, function(downloaded)
    applying = false
    if downloaded then
      local onlineSelection = selected
      local preservedOnlinePage = onlinePage
      noctalia.setWallpaper(destination)
      noctalia.notify(tr("title"), tr("downloaded_and_applied"))
      local previousTab = tab
      loadLocal()
      tab = previousTab
      if previousTab == "online" then
        selected = onlineSelection
        onlinePage = preservedOnlinePage
      end
    else
      errorMessage = tr("download_failed")
    end
    render()
  end)
  if not started then
    applying = false
    errorMessage = tr("download_failed")
    render()
  end
end

local function applySelected()
  local item = currentItems()[selected]
  if item == nil then
    return
  end
  if tab == "local" then
    localApply(item)
  else
    onlineApply(item)
  end
end

local function thumbCachePath(id)
  local dataDir = noctalia.pluginDataDir()
  if type(dataDir) ~= "string" then
    return nil
  end
  return joinPath(dataDir, "thumbs/" .. id .. "-large.jpg")
end

local function pumpThumbQueue()
  while thumbActive < THUMB_CONCURRENCY and #thumbQueue > 0 do
    local item = table.remove(thumbQueue, 1)
    if thumbPaths[item.id] == nil and not thumbPending[item.id] then
      local source = item.thumbs and (item.thumbs.large or item.thumbs.small)
      local destination = thumbCachePath(item.id)
      if type(source) == "string" and destination ~= nil then
        thumbPending[item.id] = true
        thumbActive += 1
        local started = noctalia.download(source, destination, function(ok)
          thumbActive -= 1
          thumbPending[item.id] = nil
          if ok then
            thumbPaths[item.id] = destination
            render()
          end
          pumpThumbQueue()
        end)
        if not started then
          thumbActive -= 1
          thumbPending[item.id] = nil
          break
        end
      end
    end
  end
end

local function queueThumbs()
  local dataDir = noctalia.pluginDataDir()
  if type(dataDir) ~= "string" then
    return
  end
  noctalia.mkdirAll(joinPath(dataDir, "thumbs"))
  for _, item in ipairs(onlineItems) do
    local cached = thumbCachePath(item.id)
    if cached ~= nil and noctalia.fileExists(cached) then
      thumbPaths[item.id] = cached
    elseif not thumbPending[item.id] then
      table.insert(thumbQueue, item)
    end
  end
  pumpThumbQueue()
end

fetchOnline = function()
  if loading then
    return
  end
  loading = true
  errorMessage = ""
  render()
  local parameters = {
    "categories=" .. categoriesParameter(),
    "purity=" .. purityParameter(),
    "sorting=" .. selectedSort(),
    "order=" .. sortOrder,
    "page=" .. tostring(apiPage()),
  }
  local selectedRatio = ratios[ratioIndex + 1]
  if selectedRatio ~= nil and selectedRatio ~= "" then
    table.insert(parameters, "ratios=" .. selectedRatio)
  end
  local selectedResolutionMode = resolutionModes[resolutionModeIndex + 1]
  local selectedResolution = resolutionParameter()
  if selectedResolutionMode ~= nil and selectedResolutionMode ~= "" and selectedResolution ~= nil then
    table.insert(parameters, selectedResolutionMode .. "=" .. selectedResolution)
  end
  if selectedSort() == "toplist" then
    table.insert(parameters, "topRange=" .. (topRanges[topRangeIndex + 1] or "1M"))
  elseif selectedSort() == "random" and randomSeed ~= "" then
    table.insert(parameters, "seed=" .. noctalia.string.urlEncode(randomSeed))
  end
  local trimmed = noctalia.string.trim(query)
  if trimmed ~= "" then
    table.insert(parameters, "q=" .. noctalia.string.urlEncode(trimmed))
  end
  noctalia.http({ url = API_URL .. "?" .. table.concat(parameters, "&"), headers = httpHeaders() }, function(response)
    loading = false
    if not response.ok then
      onlineItems = {}
      errorMessage = tr("request_failed")
      render()
      return
    end
    local decoded = noctalia.json.decode(response.body)
    if type(decoded) ~= "table" or type(decoded.data) ~= "table" then
      onlineItems = {}
      errorMessage = tr("request_failed")
      render()
      return
    end
    onlineItems = decoded.data
    selected = 1
    local meta = decoded.meta
    onlineTotalPages = type(meta) == "table"
      and normalizeTotalPages(math.floor(tonumber(meta.last_page) or 1))
      or 1
    if selectedSort() == "random" and type(meta) == "table" and type(meta.seed) == "string" then
      randomSeed = meta.seed
    end
    noctalia.log(`online page {onlinePage}/{onlineTotalPages}, {#onlineItems} results`)
    queueThumbs()
    render()
  end)
end

local function changePage(delta)
  local activePage = currentPage()
  local nextPage = math.min(math.max(activePage + delta, 1), currentTotalPages())
  if nextPage == activePage then
    return
  end
  if tab == "local" then
    localPage = nextPage
    selected = math.min((localPage - 1) * PAGE_SIZE + 1, math.max(1, #localFiles))
    render()
  else
    onlinePage = nextPage
    fetchOnline()
  end
end

local function goToPage(value)
  local target = math.floor(tonumber(value) or currentPage())
  target = math.min(math.max(target, 1), currentTotalPages())
  pageDraft = tostring(target)
  pageEditing = false
  pageFocusSerial += 1
  if target == currentPage() then
    render()
    return
  end
  if tab == "local" then
    localPage = target
    selected = math.min((localPage - 1) * PAGE_SIZE + 1, math.max(1, #localFiles))
    render()
  else
    onlinePage = target
    fetchOnline()
  end
end

local function tile(item, absoluteIndex, visibleIndex)
  local isSelected = absoluteIndex == selected
  local imagePath = item.path
  if tab == "online" then
    imagePath = thumbPaths[item.id]
  end
  local preview
  local choose = function()
    selected = absoluteIndex
    render()
  end
  if type(imagePath) == "string" and imagePath ~= "" then
    preview = ui.image({
      key = "image-" .. item.id,
      width = TILE_WIDTH,
      height = TILE_HEIGHT,
      path = imagePath,
      fit = "cover",
      radius = 10,
      border = isSelected and "primary" or "outline",
      borderWidth = isSelected and 3 or 1,
      onClick = choose,
    })
  else
    preview = ui.box({
      key = "placeholder-" .. item.id,
      width = TILE_WIDTH,
      height = TILE_HEIGHT,
      fill = "surface_variant",
      radius = 10,
      border = isSelected and "primary" or "outline",
      borderWidth = isSelected and 3 or 1,
      onClick = choose,
    })
  end
  local label = item.resolution or item.label or item.id
  return ui.column({
    key = "tile-" .. item.id,
    gap = 5,
    align = "center",
    onClick = choose,
  }, {
    preview,
    ui.label({
      text = tostring(visibleIndex) .. ". " .. label,
      fontSize = 11,
      color = isSelected and "primary" or "on_surface_variant",
      maxLines = 1,
      maxWidth = TILE_WIDTH,
      textAlign = "center",
    }),
  })
end

local function grid()
  if loading then
    return ui.label({ text = tr("loading"), color = "on_surface_variant" })
  end
  if errorMessage ~= "" then
    return ui.label({ text = errorMessage, color = "error" })
  end
  local items = visibleItems()
  if #items == 0 then
    return ui.column({ gap = 8, align = "center" }, {
      ui.glyph({ name = "photo-off", size = 36, color = "on_surface_variant" }),
      ui.label({ text = tab == "local" and tr("empty_local") or tr("empty_online"), color = "on_surface_variant" }),
    })
  end
  local rows = {}
  local row = {}
  local base = tab == "local" and ((localPage - 1) * PAGE_SIZE) or 0
  for index, item in ipairs(items) do
    table.insert(row, tile(item, base + index, index))
    if #row == COLUMNS or index == #items then
      table.insert(rows, ui.row({ gap = 12, align = "start" }, row))
      row = {}
    end
  end
  return ui.column({ gap = 12, align = "stretch" }, rows)
end

local function tabButton(text, target, shortcut)
  return ui.button({
    key = "tab-" .. target,
    text = text .. "  " .. shortcut,
    selected = tab == target,
    variant = tab == target and "primary" or "ghost",
    onClick = function()
      selectTab(target)
    end,
  })
end

local function filterButton(text, active, callback, enabled)
  return ui.button({
    text = text,
    selected = active,
    variant = active and "primary" or "ghost",
    onClick = callback,
    enabled = enabled == nil or enabled,
  })
end

local function onlineToolbar()
  if tab ~= "online" then
    return ui.row({ visible = false }, {})
  end
  return ui.column({ gap = 8, align = "stretch" }, {
    ui.row({ gap = 8, align = "center" }, {
      ui.input({
        key = "search-" .. tostring(searchFocusSerial),
        value = query,
        placeholder = tr("search_placeholder"),
        flexGrow = 1,
        focus = searchFocusSerial > 0,
        onChange = "onSearchChange",
        onSubmit = "onSearchSubmit",
      }),
      ui.select({
        key = "sort",
        width = 132,
        options = {
          tr("sort_relevance"),
          tr("sort_random"),
          tr("sort_newest"),
          tr("sort_views"),
          tr("sort_favorites"),
          tr("sort_toplist"),
          tr("sort_hot"),
        },
        selectedIndex = sortIndex,
        onChange = "onSortChange",
      }),
      ui.button({
        width = 82,
        text = sortOrder == "desc" and tr("order_desc") or tr("order_asc"),
        glyph = sortOrder == "desc" and "arrow-down" or "arrow-up",
        variant = "ghost",
        onClick = "onToggleOrder",
      }),
      ui.button({ text = tr("search"), glyph = "search", variant = "primary", onClick = "onSearch" }),
    }),
    ui.row({ gap = 6, align = "center" }, {
      ui.label({ text = tr("categories"), color = "on_surface_variant", fontSize = 11 }),
      filterButton(tr("category_general"), categoryGeneral, "onToggleGeneral"),
      filterButton(tr("category_anime"), categoryAnime, "onToggleAnime"),
      filterButton(tr("category_people"), categoryPeople, "onTogglePeople"),
      ui.label({ text = tr("purity"), color = "on_surface_variant", fontSize = 11 }),
      filterButton(tr("purity_sfw"), puritySfw, "onToggleSfw"),
      filterButton(tr("purity_sketchy"), puritySketchy, "onToggleSketchy"),
      filterButton(tr("purity_nsfw"), purityNsfw, "onToggleNsfw", apiKey() ~= ""),
      ui.spacer({ flexGrow = 1 }),
      ui.select({
        key = "top-range",
        width = 112,
        options = {
          tr("range_1d"), tr("range_3d"), tr("range_1w"), tr("range_1m"),
          tr("range_3m"), tr("range_6m"), tr("range_1y"),
        },
        selectedIndex = topRangeIndex,
        onChange = "onTopRangeChange",
        enabled = selectedSort() == "toplist",
      }),
    }),
    ui.row({ gap = 8, align = "center" }, {
      ui.label({ text = tr("ratio"), color = "on_surface_variant", fontSize = 11 }),
      ui.select({
        key = "ratio",
        width = 126,
        options = {
          tr("ratio_any"), tr("ratio_landscape"), tr("ratio_portrait"),
          "16:9", "16:10", "21:9", "32:9", "48:9", "9:16", "10:16",
          "9:18", "1:1", "3:2", "4:3", "5:4",
        },
        selectedIndex = ratioIndex,
        onChange = "onRatioChange",
      }),
      ui.label({ text = tr("resolution"), color = "on_surface_variant", fontSize = 11 }),
      ui.select({
        key = "resolution-mode",
        width = 116,
        options = { tr("resolution_any"), tr("resolution_atleast"), tr("resolution_exact") },
        selectedIndex = resolutionModeIndex,
        onChange = "onResolutionModeChange",
      }),
      ui.input({
        key = "resolution-width",
        value = resolutionWidth,
        placeholder = tr("width"),
        width = 74,
        enabled = resolutionModeIndex > 0,
        onChange = "onResolutionWidthChange",
        onSubmit = "onResolutionWidthSubmit",
      }),
      ui.label({ text = "×", color = "on_surface_variant" }),
      ui.input({
        key = "resolution-height",
        value = resolutionHeight,
        placeholder = tr("height"),
        width = 74,
        enabled = resolutionModeIndex > 0,
        onChange = "onResolutionHeightChange",
        onSubmit = "onResolutionHeightSubmit",
      }),
      ui.spacer({ flexGrow = 1 }),
      ui.button({ text = tr("reset_filters"), glyph = "restore", variant = "ghost", onClick = "onResetFilters" }),
    }),
  })
end

render = function()
  clampSelection()
  local activePage = currentPage()
  local activeTotalPages = currentTotalPages()
  local status = tr("page_status", { page = activePage, total = activeTotalPages })
  if applying then
    status = tr("downloading")
  end
  panel.render(ui.column({ flexGrow = 1, gap = 12, align = "stretch" }, {
    ui.row({ align = "center", gap = 8 }, {
      ui.label({ text = tr("title"), fontSize = 16, fontWeight = "bold", flexGrow = 1 }),
      ui.label({ text = tr("keyboard_hint"), fontSize = 11, color = "on_surface_variant" }),
      ui.button({ glyph = "close", variant = "ghost", onClick = "onClose" }),
    }),
    ui.row({ gap = 8, align = "center" }, {
      tabButton(tr("local_tab"), "local", "Ctrl+1"),
      tabButton(tr("online_tab"), "online", "Ctrl+2"),
      ui.spacer({ flexGrow = 1 }),
      ui.button({ glyph = "refresh", text = tr("refresh"), variant = "ghost", onClick = "onRefresh" }),
    }),
    onlineToolbar(),
    ui.scroll({ flexGrow = 1, gap = 12 }, { grid() }),
    ui.row({ align = "center", justify = "space_between" }, {
      ui.label({ text = tr("selection_status", { index = selectedVisibleIndex(), count = #visibleItems() }), color = "on_surface_variant" }),
      ui.row({ gap = 8, align = "center" }, {
        ui.button({ glyph = "chevron-left", onClick = "onPreviousPage", enabled = not loading and activePage > 1 }),
        tab == "online" and ui.row({ gap = 5, align = "center" }, {
          ui.label({ text = tr("page_prefix"), color = "on_surface_variant" }),
          ui.input({
            key = "page-" .. tostring(pageFocusSerial),
            value = pageEditing and pageDraft or tostring(activePage),
            width = 54,
            enabled = not loading,
            onChange = "onPageChange",
            onSubmit = "onPageSubmit",
          }),
          ui.label({ text = tr("page_suffix", { total = activeTotalPages }), color = "on_surface_variant" }),
        }) or ui.label({ text = status, width = 120, textAlign = "center" }),
        ui.button({ glyph = "chevron-right", onClick = "onNextPage", enabled = not loading and activePage < activeTotalPages }),
      }),
      ui.button({ text = tab == "local" and tr("apply") or tr("download_apply"), glyph = "check", variant = "primary", onClick = "onApply", enabled = not loading and not applying and #currentItems() > 0 }),
    }),
  }))
end

function onOpen(_context)
  local openedTab = tab
  local openedSelection = selected
  loadLocal()
  if openedTab == "online" then
    tab = "online"
    selected = math.min(openedSelection, math.max(1, #onlineItems))
  end
  render()
end

function onClose()
  panel.close()
end

function onSearchChange(value)
  query = value
  searchEditing = true
  filterEditing = false
  pageEditing = false
end

function onSearchSubmit(value)
  query = value
  searchEditing = false
  searchFocusSerial += 1
  resetOnlinePage()
  fetchOnline()
end

function onSearch()
  searchEditing = false
  searchFocusSerial += 1
  resetOnlinePage()
  fetchOnline()
end

function onSortChange(index, _text)
  sortIndex = tonumber(index) or 0
  resetOnlinePage()
  fetchOnline()
end

function onToggleOrder()
  sortOrder = sortOrder == "desc" and "asc" or "desc"
  resetOnlinePage()
  fetchOnline()
end

function onTopRangeChange(index, _text)
  topRangeIndex = tonumber(index) or 3
  if selectedSort() == "toplist" then
    resetOnlinePage()
    fetchOnline()
  else
    render()
  end
end

function onToggleGeneral()
  if categoryGeneral and not categoryAnime and not categoryPeople then
    return
  end
  categoryGeneral = not categoryGeneral
  resetOnlinePage()
  fetchOnline()
end

function onToggleAnime()
  if categoryAnime and not categoryGeneral and not categoryPeople then
    return
  end
  categoryAnime = not categoryAnime
  resetOnlinePage()
  fetchOnline()
end

function onTogglePeople()
  if categoryPeople and not categoryGeneral and not categoryAnime then
    return
  end
  categoryPeople = not categoryPeople
  resetOnlinePage()
  fetchOnline()
end

function onToggleSfw()
  if puritySfw and not puritySketchy and not purityNsfw then
    return
  end
  puritySfw = not puritySfw
  resetOnlinePage()
  fetchOnline()
end

function onToggleSketchy()
  if puritySketchy and not puritySfw and not purityNsfw then
    return
  end
  puritySketchy = not puritySketchy
  resetOnlinePage()
  fetchOnline()
end

function onToggleNsfw()
  if apiKey() == "" then
    return
  end
  if purityNsfw and not puritySfw and not puritySketchy then
    return
  end
  purityNsfw = not purityNsfw
  resetOnlinePage()
  fetchOnline()
end

function onRatioChange(index, _text)
  ratioIndex = tonumber(index) or 0
  resetOnlinePage()
  fetchOnline()
end

function onResolutionModeChange(index, _text)
  resolutionModeIndex = tonumber(index) or 0
  filterEditing = false
  resetOnlinePage()
  fetchOnline()
end

function onResolutionWidthChange(value)
  resolutionWidth = noctalia.string.trim(value)
  filterEditing = true
  searchEditing = false
  pageEditing = false
end

function onResolutionHeightChange(value)
  resolutionHeight = noctalia.string.trim(value)
  filterEditing = true
  searchEditing = false
  pageEditing = false
end

function onResolutionWidthSubmit(value)
  resolutionWidth = noctalia.string.trim(value)
  filterEditing = false
  resetOnlinePage()
  fetchOnline()
end

function onResolutionHeightSubmit(value)
  resolutionHeight = noctalia.string.trim(value)
  filterEditing = false
  resetOnlinePage()
  fetchOnline()
end

function onResetFilters()
  query = ""
  sortIndex = 2
  sortOrder = "desc"
  topRangeIndex = 3
  categoryGeneral = true
  categoryAnime = true
  categoryPeople = true
  puritySfw = true
  puritySketchy = false
  purityNsfw = false
  ratioIndex = 0
  resolutionModeIndex = 0
  resolutionWidth = ""
  resolutionHeight = ""
  searchEditing = false
  filterEditing = false
  searchFocusSerial += 1
  resetOnlinePage()
  fetchOnline()
end

function onRefresh()
  if tab == "local" then
    loadLocal()
    render()
  else
    fetchOnline()
  end
end

function onApply()
  applySelected()
end

function onPreviousPage()
  changePage(-1)
end

function onNextPage()
  changePage(1)
end

function onPageChange(value)
  pageDraft = value
  pageEditing = true
  searchEditing = false
  filterEditing = false
end

function onPageSubmit(value)
  goToPage(value)
end

-- A narrow IPC surface makes the same source switch and refresh actions
-- scriptable for validation without creating a second user-facing entry.
function onIpc(event, payload)
  if event == "source" and (payload == "local" or payload == "online") then
    selectTab(payload)
  elseif event == "refresh" then
    onRefresh()
  end
end

function onKey(chord, pressed)
  if not pressed then
    return
  end
  if chord == "ctrl+1" then
    selectTab("local")
  elseif chord == "ctrl+2" then
    selectTab("online")
  elseif chord == "ctrl+l" then
    if tab ~= "online" then
      tab = "online"
      selected = 1
      onlinePage = 1
    end
    searchEditing = true
    searchFocusSerial += 1
    render()
  elseif chord == "ctrl+r" then
    onRefresh()
  elseif chord == "Left" then
    moveSelection(-1)
  elseif chord == "Right" then
    moveSelection(1)
  elseif chord == "Up" then
    moveSelection(-COLUMNS)
  elseif chord == "Down" then
    moveSelection(COLUMNS)
  elseif chord == "Return" then
    if searchEditing then
      searchEditing = false
      searchFocusSerial += 1
      resetOnlinePage()
      fetchOnline()
    elseif pageEditing then
      goToPage(pageDraft)
    elseif filterEditing then
      filterEditing = false
      resetOnlinePage()
      fetchOnline()
    else
      applySelected()
    end
  elseif chord == "Page_Up" then
    changePage(-1)
  elseif chord == "Page_Down" then
    changePage(1)
  end
end
