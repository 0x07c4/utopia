import importlib.util
from pathlib import Path
import tempfile
import signal
import unittest
from unittest.mock import patch

SOURCE = Path(__file__).resolve().parents[1] / "desktop/gaming/battlenet-repaint.py"
spec = importlib.util.spec_from_file_location("battlenet_repaint", SOURCE)
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)


def window(identifier=1, app="battle.net.exe", title="战网", size=(1000, 1014)):
    return dict(id=identifier, app_id=app, title=title, layout=dict(window_size=list(size)))


class RepaintStateTest(unittest.TestCase):
    def test_only_main_client_is_selected(self):
        state = adapter.ClientWindows()
        self.assertTrue(state.accept(dict(WindowsChanged=dict(windows=[
            window(), window(2, title="战网登录"), window(3, app="Hearthstone.exe")]))))
        self.assertEqual(state.bounds, {1: (1000, 1014)})

    def test_focus_and_position_updates_do_not_schedule_repaints(self):
        state = adapter.ClientWindows()
        event = dict(WindowOpenedOrChanged=dict(window=window()))
        self.assertTrue(state.accept(event))
        event["WindowOpenedOrChanged"]["window"]["is_focused"] = True
        self.assertFalse(state.accept(event))
        self.assertFalse(state.accept(dict(WindowFocusChanged=dict(id=1))))

    def test_resize_and_close_state(self):
        state = adapter.ClientWindows()
        state.accept(dict(WindowsChanged=dict(windows=[window()])))
        event = dict(WindowLayoutsChanged=dict(changes=[(1, dict(window_size=[1253, 1014])),
                                                        (9, dict(window_size=[20, 20]))]))
        self.assertTrue(state.accept(event))
        self.assertFalse(state.accept(event))
        self.assertEqual(state.bounds, {1: (1253, 1014)})
        self.assertTrue(state.accept(dict(WindowClosed=dict(id=1))))
        self.assertEqual(state.bounds, {})

    def test_title_transition_removes_login_or_unrelated_window(self):
        state = adapter.ClientWindows()
        state.accept(dict(WindowOpenedOrChanged=dict(window=window())))
        self.assertTrue(state.accept(dict(WindowOpenedOrChanged=dict(window=window(title="other")))))
        self.assertFalse(state.bounds)

    def test_lock_is_prefix_specific(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict("os.environ", {"XDG_STATE_HOME": temporary}):
            a = adapter.state_lock(Path(temporary) / "a")
            b = adapter.state_lock(Path(temporary) / "b")
            self.assertNotEqual(a, b)
            self.assertEqual(a.parent, Path(temporary) / "utopia")
            self.assertNotIn(temporary, a.name)

    def test_stop_missing_monitor_is_harmless(self):
        with tempfile.TemporaryDirectory() as temporary, patch.dict("os.environ", {"XDG_STATE_HOME": temporary}):
            adapter.stop(Path(temporary) / "prefix")

    def test_stop_checks_process_identity_and_prefix(self):
        prefix = Path("/tmp/utopia-test-prefix")
        commands = [
            b"python3\0other.py\0--prefix\0/tmp/utopia-test-prefix\0",
            b"python3\0battlenet-repaint.py\0--prefix\0/tmp/unrelated-prefix\0",
            b"python3\0battlenet-repaint.py\0--prefix\0/tmp/utopia-test-prefix\0",
        ]
        for index, command in enumerate(commands):
            with patch.object(Path, "read_text", return_value="12345"), \
                 patch.object(Path, "read_bytes", return_value=command), \
                 patch.object(adapter.os, "kill") as kill:
                adapter.stop(prefix)
                if index == 2:
                    kill.assert_called_once_with(12345, signal.SIGTERM)
                else:
                    kill.assert_not_called()
