local wezterm = require("wezterm")
local config = {
	enable_wayland = false, -- 强制用 X11，绕开 Wayland 显式同步
	font = wezterm.font_with_fallback({
		"Maple Mono NF CN",
	}),
	font_size = 18.0,
	line_height = 1.1,

	-- color
	color_scheme = "Gruvbox dark, soft (base16)",
	bold_brightens_ansi_colors = true,

	-- Tab Bar
	enable_tab_bar = true,
	hide_tab_bar_if_only_one_tab = true,
	tab_bar_at_bottom = false,
	use_fancy_tab_bar = false,

	-- cursor
	default_cursor_style = "BlinkingBlock",
	cursor_blink_rate = 600,

	-- layout
	window_padding = {
		left = 8,
		right = 8,
		top = 6,
		bottom = 6,
	},

	-- performance
	front_end = "WebGpu", -- NVIDIA + KDE 下通常比 OpenGL 顺
	max_fps = 120,
	animation_fps = 120,

	-- others
	scrollback_lines = 5000,
	check_for_updates = false,
	audible_bell = "Disabled",
}

return config
