import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from utopia import deployment, fcitx_deploy as adapter, profiles
from utopia.__main__ import main


class FcitxDeploymentTest(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.repo = profiles.REPO_ROOT
        selector = self.home / adapter.SELECTOR
        selector.parent.mkdir(parents=True)
        shutil.copy2(self.repo / "input/fcitx5/config/conf/classicui.conf", selector)
        fallback = self.home / ".local/share/fcitx5/themes/catppuccin-mocha-green"
        shutil.copytree(self.repo / "input/fcitx5/themes/catppuccin-mocha-green", fallback)
        for relative in (".config/noctalia/visuals.toml",
                         ".config/noctalia/templates/utopia/fcitx5/theme.conf",
                         ".config/noctalia/templates/utopia/fcitx5/apply.sh"):
            target = self.home / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(self.repo / relative, target)
        self.wallpaper = self.home / "wallpaper.png"
        self.wallpaper.write_bytes(b"fixture")
        self.before = {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS}
        original_run = adapter._run

        def command(command, **kwargs):
            if command[:2] == ["noctalia", "theme"]:
                # Only the palette producer is mocked. The actual repository
                # hook, SVG/PNG validator, backups and filesystem writes run.
                source, output = command[-1].split(":")
                text = Path(source).read_text()
                text = re.sub(r"\{\{colors\.[^}]+\}\}", "#aabbcc", text)
                Path(output).write_text(text)
                return subprocess.CompletedProcess(command, 0, b"", b"")
            return original_run(command, **kwargs)

        self.addCleanup(patch.stopall)
        self.runner = patch.object(adapter, "_run", side_effect=command).start()

    def apply(self, **kwargs):
        return adapter.apply(self.repo, "cachyos-desktop", adapter.FEATURE,
                             self.home, self.wallpaper,
                             confirm_host="cachyos-desktop",
                             reload_session=kwargs.pop("reload_session", False), **kwargs)

    def test_preview_does_not_write_home(self):
        before = adapter._snapshot(self.home)
        result = adapter.preview(self.repo, "cachyos-desktop", adapter.FEATURE, self.home)
        self.assertTrue(result["dry_run"])
        self.assertEqual(before, adapter._snapshot(self.home))
        self.runner.assert_not_called()

    def test_apply_is_idempotent_and_rollback_restores_exact_state(self):
        result = self.apply()
        self.assertEqual(result["status"], "applied")
        adapter.validate_theme(self.home / adapter.THEME)
        self.assertIn(b"Theme=utopia-wallpaper", (self.home / adapter.SELECTOR).read_bytes())
        self.assertTrue((self.home / adapter.MARKER).is_file())
        record_path = self.home / adapter.STATE / result["id"] / "record.json"
        record = json.loads(record_path.read_text())
        self.assertEqual(record["status"], "applied")
        self.assertEqual(len(record["repository_commit"]), 40)
        self.assertNotIn(str(self.home), record_path.read_text())
        records_before = sorted(p.name for p in (self.home / adapter.STATE).iterdir())
        self.assertEqual(self.apply()["status"], "unchanged")
        self.assertEqual(records_before, sorted(p.name for p in (self.home / adapter.STATE).iterdir()))
        after = adapter._snapshot(self.home)
        preview = adapter.rollback(self.repo, "cachyos-desktop", result["id"], self.home)
        self.assertEqual(preview["status"], "planned")
        self.assertEqual(after, adapter._snapshot(self.home))
        adapter.rollback(self.repo, "cachyos-desktop", result["id"], self.home,
                         confirm_host="cachyos-desktop")
        self.assertEqual(self.before, {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS})

    def test_render_failure_preserves_targets_and_retry_works(self):
        with patch.object(adapter, "_render", side_effect=deployment.DeploymentError("render failed")):
            with self.assertRaisesRegex(deployment.DeploymentError, "render failed"):
                self.apply()
        self.assertEqual(self.before, {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS})
        self.assertEqual(self.apply()["status"], "applied")

    def test_first_adoption_records_an_existing_matching_dynamic_theme(self):
        plan = deployment.resolve(self.repo, "cachyos-desktop", adapter.FEATURE)
        with tempfile.TemporaryDirectory() as temporary:
            theme = adapter._render(self.repo, plan, self.wallpaper, Path(temporary))
            shutil.copytree(theme, self.home / adapter.THEME)
        selector = self.home / adapter.SELECTOR
        selector.write_bytes(adapter._selector(selector.read_bytes(), "utopia-wallpaper"))
        marker = self.home / adapter.MARKER
        marker.parent.mkdir(parents=True)
        marker.write_bytes(b"# existing opt-in\n")
        result = self.apply()
        self.assertEqual(result["status"], "applied")
        self.assertEqual(len(adapter._records(self.home, "cachyos-desktop")), 1)
        self.assertEqual(self.apply()["status"], "unchanged")

    def test_reload_failure_rolls_back_files(self):
        with patch.object(Path, "home", return_value=self.home), patch.object(
            adapter, "_reload", side_effect=[deployment.DeploymentError("reload failed"), None]
        ):
            with self.assertRaisesRegex(deployment.DeploymentError, "reload failed"):
                self.apply(reload_session=True)
        self.assertEqual(self.before, {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS})
        records = adapter._records(self.home, "cachyos-desktop")
        self.assertEqual(records[-1][1]["status"], "rolled-back")

    def test_local_selector_edit_after_deploy_is_not_overwritten(self):
        self.apply()
        selector = self.home / adapter.SELECTOR
        selector.write_bytes(selector.read_bytes() + b"# local edit\n")
        with self.assertRaisesRegex(deployment.DeploymentError, "local edit since"):
            self.apply()

    def test_first_deployment_refuses_unreviewed_selector(self):
        selector = self.home / adapter.SELECTOR
        selector.write_bytes(selector.read_bytes().replace(b"Sans 10", b"Sans 14"))
        with self.assertRaisesRegex(deployment.DeploymentError, "unrecorded Classic UI"):
            self.apply()

    def test_rollback_refuses_later_wallpaper_or_manual_edits(self):
        result = self.apply()
        theme = self.home / adapter.THEME / "theme.conf"
        theme.write_text(theme.read_text() + "# later wallpaper\n")
        with self.assertRaisesRegex(deployment.DeploymentError, "live change after"):
            adapter.rollback(self.repo, "cachyos-desktop", result["id"], self.home,
                             confirm_host="cachyos-desktop")

    def test_backup_tamper_is_rejected_before_restore(self):
        result = self.apply()
        backup = self.home / adapter.STATE / result["id"] / "backup" / adapter.SELECTOR
        backup.write_text("tampered")
        before = {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS}
        with self.assertRaisesRegex(deployment.DeploymentError, "backup integrity"):
            adapter.rollback(self.repo, "cachyos-desktop", result["id"], self.home,
                             confirm_host="cachyos-desktop")
        self.assertEqual(before, {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS})

    def test_symlink_parent_cannot_escape_home(self):
        with tempfile.TemporaryDirectory() as outside:
            (self.home / ".local/state").symlink_to(outside, target_is_directory=True)
            with self.assertRaisesRegex(deployment.DeploymentError, "symlink"):
                self.apply()
            self.assertEqual(list(Path(outside).iterdir()), [])

    def test_first_deployment_does_not_replace_a_custom_theme(self):
        selector = self.home / adapter.SELECTOR
        selector.write_bytes(selector.read_bytes().replace(b"catppuccin-mocha-green", b"custom-theme"))
        with self.assertRaisesRegex(deployment.DeploymentError, "unrecorded Classic UI"):
            self.apply()
        self.assertIn(b"Theme=custom-theme", selector.read_bytes())

    def test_malformed_record_is_rejected_without_changing_targets(self):
        result = self.apply()
        record_path = self.home / adapter.STATE / result["id"] / "record.json"
        record = json.loads(record_path.read_text())
        record["before"] = None
        record_path.write_text(json.dumps(record))
        before = {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS}
        with self.assertRaisesRegex(deployment.DeploymentError, "unsupported local deployment record"):
            self.apply()
        self.assertEqual(before, {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS})

    def test_confirmation_and_session_isolation_are_required(self):
        with self.assertRaisesRegex(deployment.DeploymentError, "confirm-host"):
            adapter.apply(self.repo, "cachyos-desktop", adapter.FEATURE,
                          self.home, self.wallpaper, confirm_host="arch-laptop")
        with self.assertRaisesRegex(deployment.DeploymentError, "alternate home"):
            self.apply(reload_session=True)

    def test_incomplete_transaction_blocks_apply_and_recovers(self):
        result = self.apply()
        path = self.home / adapter.STATE / result["id"] / "record.json"
        record = json.loads(path.read_text())
        record["status"] = "applying"
        path.write_text(json.dumps(record))
        # Simulate a process dying with a partially switched selector.
        (self.home / adapter.SELECTOR).write_text("partial transaction")
        with self.assertRaisesRegex(deployment.DeploymentError, "unfinished deployment"):
            self.apply()
        adapter.rollback(self.repo, "cachyos-desktop", result["id"], self.home,
                         confirm_host="cachyos-desktop")
        self.assertEqual(self.before, {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS})
        self.assertEqual(self.apply()["status"], "applied")

    def test_cross_host_record_is_refused(self):
        self.apply()
        with self.assertRaisesRegex(deployment.DeploymentError, "another host profile"):
            adapter.preview(self.repo, "arch-laptop", adapter.FEATURE, self.home)

    def test_render_time_edit_is_not_overwritten(self):
        original = adapter._render
        def edit_during_render(*args):
            theme = original(*args)
            selector = self.home / adapter.SELECTOR
            selector.write_bytes(selector.read_bytes() + b"# concurrent edit\n")
            return theme
        with patch.object(adapter, "_render", side_effect=edit_during_render):
            with self.assertRaisesRegex(deployment.DeploymentError, "live state changed while rendering"):
                self.apply()
        self.assertTrue((self.home / adapter.SELECTOR).read_bytes().endswith(b"# concurrent edit\n"))
        self.assertFalse((self.home / adapter.THEME).exists())

    def test_selector_publish_failure_restores_all_targets(self):
        original = adapter._atomic
        failed = False
        def write(path, *args, **kwargs):
            nonlocal failed
            if path == self.home / adapter.SELECTOR and not failed:
                failed = True
                raise OSError("simulated write failure")
            return original(path, *args, **kwargs)
        with patch.object(adapter, "_atomic", side_effect=write):
            with self.assertRaisesRegex(OSError, "simulated write failure"):
                self.apply()
        self.assertEqual(self.before, {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS})
        self.assertEqual(adapter._records(self.home, "cachyos-desktop")[-1][1]["status"], "rolled-back")

    def test_disabled_host_feature_cannot_apply(self):
        plan = deployment.resolve(self.repo, "cachyos-desktop", adapter.FEATURE)
        plan["activation"] = "fallback"
        before = {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS}
        with patch.object(deployment, "resolve", return_value=plan):
            with self.assertRaisesRegex(deployment.DeploymentError, "not enabled"):
                self.apply()
        self.assertEqual(before, {p: adapter._snapshot(self.home / p) for p in adapter.TARGETS})

    def test_cli_apply_without_confirmation_does_not_write(self):
        before = adapter._snapshot(self.home)
        self.assertEqual(main(["deploy", "cachyos-desktop", adapter.FEATURE,
                               "--home", str(self.home), "--apply"]), 2)
        self.assertEqual(before, adapter._snapshot(self.home))


if __name__ == "__main__":
    unittest.main()
