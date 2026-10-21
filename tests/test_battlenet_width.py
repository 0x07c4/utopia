import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "desktop/gaming/battlenet-width.py"
spec = importlib.util.spec_from_file_location("battlenet_width", SOURCE)
widths = importlib.util.module_from_spec(spec)
spec.loader.exec_module(widths)


class BattleNetWidthTest(unittest.TestCase):
    def test_three_distinct_steps_forward(self):
        self.assertEqual([widths.width_target(w, 1920, "forward") for w in (1000, 1253, 1888)],
                         ["66.667%", "100%", "1000"])

    def test_reverse_is_inverse(self):
        self.assertEqual([widths.width_target(w, 1920, "back") for w in (1000, 1253, 1888)],
                         ["100%", "1000", "66.667%"])

    def test_custom_width_moves_to_next_valid_step(self):
        self.assertEqual(widths.width_target(1100, 1920, "forward"), "66.667%")
        self.assertEqual(widths.width_target(1500, 1920, "forward"), "100%")
        self.assertEqual(widths.width_target(1100, 1920, "back"), "1000")

    def client(self, **changes):
        result = dict(id=42, app_id="battle.net.exe", title="战网", is_focused=True,
                      is_floating=False, workspace_id=1, layout=dict(window_size=[1000, 1014]))
        result.update(changes)
        return result

    def query(self, window, scale=2, size=1920):
        values = {"windows": [window], "workspaces": [dict(id=1, output="test-output")],
                  "outputs": {"test-output": dict(logical=dict(scale=scale, width=size))}}
        return lambda kind: values[kind]

    def test_main_window_uses_id_not_future_focus(self):
        with patch.object(widths, "query", self.query(self.client())):
            self.assertEqual(widths.action("forward"), ["set-window-width", "--id", "42", "66.667%"])

    def test_other_apps_login_and_floating_keep_native_behavior(self):
        for window in (self.client(app_id="kitty"), self.client(title="战网登录"),
                       self.client(is_floating=True), self.client(is_focused=False)):
            with patch.object(widths, "query", self.query(window)):
                self.assertEqual(widths.action("forward"), ["switch-preset-column-width"])
                self.assertEqual(widths.action("back"), ["switch-preset-column-width-back"])

    def test_other_display_scopes_keep_native_behavior(self):
        for scale, size in ((1, 1920), (2, 1280)):
            with patch.object(widths, "query", self.query(self.client(), scale=scale, size=size)):
                self.assertEqual(widths.action("forward"), ["switch-preset-column-width"])

    def test_ipc_failure_keeps_native_action(self):
        with patch.object(widths, "query", side_effect=ValueError):
            self.assertEqual(widths.action("back"), ["switch-preset-column-width-back"])
