from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from install import aur, plan


class AURTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    def build(self, target: Path, *, skip_review: bool = False):
        return aur.build_aur_plan(
            self.config,
            target_root=target,
            encryption_override=False,
            skip_review=skip_review,
        )

    def test_plan_uses_only_aur_manifest_and_non_root_builder(self) -> None:
        result = self.build(Path("/mnt"))

        self.assertEqual(result["packages"], ["clash-verge-rev-bin", "google-chrome", "qqmusic-bin"])
        self.assertEqual(result["command"][:6], ("arch-chroot", "-u", "utopia", "/mnt", "env", "HOME=/home/utopia"))
        self.assertIn("--aur", result["command"])
        self.assertNotIn("--skipreview", result["command"])
        self.assertIn("PKGBUILD review remains enabled", aur.format_aur_plan(result, dry_run=True))

    def test_skip_review_is_explicit(self) -> None:
        result = self.build(Path("/mnt"), skip_review=True)
        self.assertIn("--skipreview", result["command"])
        self.assertIn("explicitly skipped", aur.format_aur_plan(result, dry_run=True))

    def test_preflight_requires_non_root_owned_home(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            result = self.build(target)
            (target / "etc").mkdir()
            (target / "etc/passwd").write_text("utopia:x:1234:1235::/home/utopia:/bin/zsh\n")
            for path in (
                "usr/bin/git",
                "usr/bin/makepkg",
                "usr/bin/pacman",
                "usr/bin/paru",
            ):
                item = target / path
                item.parent.mkdir(parents=True, exist_ok=True)
                item.touch()
            home = target / "home/utopia"
            home.mkdir(parents=True)

            with (
                mock.patch("install.aur.os.geteuid", return_value=0),
                mock.patch("install.aur.shutil.which", return_value="/usr/bin/arch-chroot"),
                mock.patch("install.aur.bootstrap.validate_target_mounts"),
            ):
                with self.assertRaisesRegex(aur.AURError, "not owned"):
                    aur.preflight_apply(self.config, result)

    def test_execution_verifies_after_paru(self) -> None:
        result = self.build(Path("/mnt"))
        calls: list[list[str]] = []

        def runner(argv, **kwargs):
            calls.append(argv)
            self.assertTrue(kwargs["check"])
            return subprocess.CompletedProcess(argv, 0, stdout="")

        aur.execute_aur(
            result,
            run=runner,
            installation_check=lambda _: calls.append(["verified"]),
        )

        self.assertEqual(calls[0], list(result["command"]))
        self.assertEqual(calls[1], ["verified"])


if __name__ == "__main__":
    unittest.main()
