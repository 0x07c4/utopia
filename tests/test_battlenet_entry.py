import os
import shlex
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / "desktop/gaming/utopia-battlenet-cn"


class BattleNetEntryTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="utopia-bnet-test-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.data = self.root / "data with spaces"
        self.prefix = self.data / "utopia/gameprefixes/battlenet-cn-legacy"
        self.runner = self.data / "lutris/runners/wine/wine-11.19-staging-amd64/bin/wine"
        self.client = self.prefix / "drive_c/Program Files (x86)/Battle.net/Battle.net.exe"
        self.env = dict(os.environ, HOME=str(self.root), XDG_DATA_HOME=str(self.data), PATH="/usr/bin:/bin")
        # Keep error notifications inside the test rather than the live session.
        self.env.pop("DBUS_SESSION_BUS_ADDRESS", None)
        self.env.pop("DISPLAY", None)
        self.env.pop("WAYLAND_DISPLAY", None)
        self.env.pop("NIRI_SOCKET", None)

    def ready(self):
        self.client.parent.mkdir(parents=True)
        self.client.touch()
        (self.prefix / "system.reg").touch()
        self.runner.parent.mkdir(parents=True)
        self.runner.write_text(
            '#!/bin/sh\n'
            'printf "%s\\n" "$WINEPREFIX" "$PWD" "$1" '
            '"${WINEARCH-unset}" "${WINEDLLOVERRIDES-unset}" '
            '"${WINELOADER-unset}" "${WINESERVER-unset}"\n'
        )
        self.runner.chmod(0o755)

    def run_entry(self, *args):
        return subprocess.run(["sh", str(SCRIPT), *args], env=self.env,
                              capture_output=True, text=True, timeout=10)

    def test_missing_prefix_is_not_created(self):
        result = self.run_entry("--check")
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.data.exists())

    def test_missing_runner_and_client_fail(self):
        self.ready()
        self.runner.chmod(0o644)
        self.assertNotEqual(self.run_entry("--check").returncode, 0)
        self.runner.chmod(0o755)
        self.client.unlink()
        self.assertNotEqual(self.run_entry("--check").returncode, 0)

    def test_check_does_not_execute_runner(self):
        self.ready()
        result = self.run_entry("--check")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn(str(self.prefix), result.stdout)

    def test_launch_uses_isolated_prefix_and_handles_spaces(self):
        self.ready()
        self.env.update(WINEPREFIX="/unrelated", WINEARCH="win32",
                        WINEDLLOVERRIDES="test=n", WINELOADER="/unrelated",
                        WINESERVER="/unrelated")
        result = self.run_entry()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines(), [str(self.prefix), str(self.client.parent),
                         r"C:\Program Files (x86)\Battle.net\Battle.net.exe",
                         "unset", "unset", "unset", "unset"])

    def test_rejects_relative_root_and_arguments(self):
        self.env["XDG_DATA_HOME"] = "relative"
        self.assertNotEqual(self.run_entry("--check").returncode, 0)
        self.assertNotEqual(self.run_entry("--unexpected").returncode, 0)
        self.assertNotEqual(self.run_entry("--check", "extra").returncode, 0)

    def test_desktop_entry_does_not_require_local_bin_on_path(self):
        self.ready()
        home = self.root / "home with spaces"
        target = home / ".local/bin/utopia-battlenet-cn"
        target.parent.mkdir(parents=True)
        target.write_bytes(SCRIPT.read_bytes())
        target.chmod(0o755)
        self.env["HOME"] = str(home)
        entry = SCRIPT.with_suffix(".desktop").read_text()
        command = next(line[5:] for line in entry.splitlines() if line.startswith("Exec="))
        result = subprocess.run(shlex.split(command), env=self.env,
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.splitlines()[0], str(self.prefix))

    def mock_niri(self, response):
        commands = self.root / "commands"
        commands.mkdir()
        script = commands / "niri"
        script.write_text(
            '#!/bin/sh\n'
            'if [ "$2" = --json ]; then\n'
            f"    printf '%s\\n' '{response}'\n"
            'else\n'
            '    printf "%s\\n" "$*" > "$HOME/focus-call"\n'
            'fi\n'
        )
        script.chmod(0o755)
        self.env.update(PATH=f"{commands}:/usr/bin:/bin", NIRI_SOCKET="test-only")

    def test_existing_client_is_focused_without_wine(self):
        self.ready()
        self.mock_niri('[{"id": 42, "app_id": "battle.net.exe"}]')
        result = self.run_entry()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout, "")
        self.assertEqual((self.root / "focus-call").read_text(),
                         "msg action focus-window --id 42\n")

    def test_absent_ambiguous_or_invalid_windows_fall_back_to_runner(self):
        self.ready()
        self.mock_niri('[]')
        niri = self.root / "commands/niri"
        for response in ('[]', 'invalid', '[{"id":1,"app_id":"battle.net.exe"},'
                         '{"id":2,"app_id":"battle.net.exe"}]'):
            niri.write_text(f"#!/bin/sh\nprintf '%s\\n' '{response}'\n")
            result = self.run_entry()
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.startswith(str(self.prefix)))
        self.assertFalse((self.root / "focus-call").exists())
