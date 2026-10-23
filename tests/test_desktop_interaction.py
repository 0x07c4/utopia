from pathlib import Path
import re
import unittest


class DesktopInteractionTest(unittest.TestCase):
    def test_approved_notification_clipboard_and_media_entries(self) -> None:
        keybinds = (
            Path(__file__).resolve().parents[1]
            / "desktop/niri/cfg/keybinds.kdl"
        ).read_text()
        for chord, label, command in (
            ("Mod+N", "通知中心", "panel-toggle control-center notifications"),
            ("Mod+Y", "剪贴板历史", "panel-toggle clipboard"),
        ):
            self.assertRegex(
                keybinds,
                re.escape(chord) + r'\s+hotkey-overlay-title="' + label
                + r'"\s+\{ spawn-sh "noctalia msg ' + command + r'"; \}',
            )
        self.assertRegex(keybinds, r'XF86AudioPlay\s+allow-when-locked=true \{ spawn-sh "noctalia msg media toggle"; \}')
        self.assertRegex(keybinds, r'XF86AudioPause\s+allow-when-locked=true \{ spawn-sh "noctalia msg media pause"; \}')
        self.assertRegex(keybinds, r'Mod\+V\s+\{ toggle-window-floating; \}')

    def test_application_help_uses_chinese_labels_and_keeps_aliases(self) -> None:
        keybinds = (
            Path(__file__).resolve().parents[1]
            / "desktop/niri/cfg/keybinds.kdl"
        ).read_text()
        for label in (
            "终端", "浏览器", "壁纸中心", "控制中心", "桌面设置",
            "应用启动器", "锁屏", "会话菜单", "文件管理器",
        ):
            self.assertIn(f'hotkey-overlay-title="{label}"', keybinds)
        self.assertRegex(
            keybinds,
            r'Mod\+T\s+hotkey-overlay-title="终端"\s+\{ spawn "kitty"; \}',
        )
        self.assertNotRegex(keybinds, r"(?m)^\s*Mod\+Return\s")
        self.assertRegex(
            keybinds,
            r'Mod\+CTRL\+Return\s+hotkey-overlay-title=null\s+'
            r'\{ spawn-sh "noctalia msg panel-toggle launcher"; \}',
        )
        self.assertNotIn("(Utopia)", keybinds)
        self.assertNotIn("Open Text Editor: Zed", keybinds)

    def test_help_has_one_panel_entry_without_native_fallback(self) -> None:
        keybinds = (
            Path(__file__).resolve().parents[1]
            / "desktop/niri/cfg/keybinds.kdl"
        ).read_text()
        self.assertRegex(
            keybinds,
            r'Mod\+Slash\s+hotkey-overlay-title="快捷键说明"\s+'
            r'\{\s*spawn-sh "noctalia msg panel-toggle utopia/shortcuts:guide";\s*\}',
        )
        self.assertNotRegex(keybinds, r"(?mi)^\s*Mod\+Shift\+Escape\s")
        self.assertNotIn("show-hotkey-overlay", keybinds)
        active = [
            line.strip() for line in keybinds.splitlines()
            if line.strip() and not line.lstrip().startswith("//")
        ]
        self.assertEqual(
            sum(bool(re.match(r"Mod\+Slash\s", line)) for line in active), 1
        )
