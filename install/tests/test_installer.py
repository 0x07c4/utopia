from pathlib import Path
import tempfile
import unittest
from unittest import mock

from install import installer, plan


class InstallerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)
        cls.device = {
            "path": "/dev/vda",
            "size_bytes": 80 * 1024**3,
            "model": "test disk",
            "active_mounts": [],
        }

    def build(self, target: Path, *, encrypted: bool = False):
        with mock.patch("install.plan.probe_whole_disk", return_value=self.device):
            return installer.build_install_plan(
                self.config,
                target_root=target,
                device_override=self.device["path"],
                encryption_override=encrypted,
            )

    def test_pipeline_propagates_disk_and_encryption_to_every_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.build(Path(temporary), encrypted=True)

        self.assertEqual(result["storage"]["storage"]["device"]["path"], "/dev/vda")
        self.assertTrue(result["storage"]["storage"]["encryption"])
        self.assertTrue(result["bootstrap"]["encryption"])
        self.assertTrue(result["configuration_preview"]["encryption"])
        self.assertTrue(result["archlinuxcn"]["encryption"])
        self.assertIn("LUKS2", installer.format_install_plan(result, dry_run=True))
        self.assertIn("AUR packages are deferred", installer.format_install_plan(result, dry_run=True))
        self.assertIsNone(result["aur"])

    def test_pipeline_can_include_audited_aur_stage(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with mock.patch(
                "install.installer.aur.build_aur_plan",
                return_value={
                    "target_root": "/tmp/target",
                    "encryption": False,
                    "manifests": [],
                    "packages": ["google-chrome"],
                    "user": "chikee",
                    "skip_review": False,
                    "command": ("arch-chroot",),
                },
            ) as build_aur:
                with mock.patch("install.plan.probe_whole_disk", return_value=self.device):
                    result = installer.build_install_plan(
                        self.config,
                        target_root=Path(temporary),
                        device_override=self.device["path"],
                        encryption_override=False,
                        with_aur=True,
                    )

        build_aur.assert_called_once()
        self.assertIsNotNone(result["aur"])
        formatted = installer.format_install_plan(result, dry_run=True)
        self.assertIn("UTOPIA AUR STAGE", formatted)
        self.assertNotIn("AUR packages are deferred", formatted)

    def test_pipeline_requires_an_explicit_device_for_example_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(plan.PlanError, "storage.device is empty"):
                installer.build_install_plan(
                    self.config,
                    target_root=Path(temporary),
                    device_override=None,
                    encryption_override=False,
                )

    def test_apply_runs_stages_in_reviewed_order(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            result = self.build(Path(temporary))
            result["aur"] = {
                "target_root": str(temporary),
                "encryption": False,
                "packages": ["google-chrome"],
                "user": "chikee",
            }
            events: list[str] = []
            identifiers = {
                "root_uuid": "00000000-0000-4000-8000-000000000001",
                "esp_uuid": "ABCD-1234",
                "luks_uuid": None,
            }
            configuration = {"encryption": False}

            with (
                mock.patch(
                    "install.installer.storage.preflight_apply",
                    side_effect=lambda *args: events.append("storage-preflight"),
                ),
                mock.patch(
                    "install.installer._verify_device_identity",
                    side_effect=lambda _: events.append("disk-identity"),
                ),
                mock.patch(
                    "install.installer.storage.execute_operations",
                    side_effect=lambda *args, **kwargs: events.append("storage"),
                ),
                mock.patch(
                    "install.installer.bootstrap.preflight_apply",
                    side_effect=lambda *args, **kwargs: events.append("bootstrap-preflight"),
                ),
                mock.patch(
                    "install.installer.bootstrap.execute_bootstrap",
                    side_effect=lambda _: events.append("bootstrap"),
                ),
                mock.patch(
                    "install.installer.configure.discover_identifiers",
                    side_effect=lambda *args, **kwargs: identifiers,
                ),
                mock.patch(
                    "install.installer.configure.build_configuration_plan",
                    side_effect=lambda *args, **kwargs: configuration,
                ),
                mock.patch(
                    "install.installer.configure.preflight_apply",
                    side_effect=lambda *args, **kwargs: events.append("configure-preflight"),
                ),
                mock.patch(
                    "install.installer.configure.install_artifacts",
                    side_effect=lambda _: events.append("artifacts"),
                ),
                mock.patch(
                    "install.installer.configure.execute_configuration",
                    side_effect=lambda *args, **kwargs: events.append("configure"),
                ),
                mock.patch(
                    "install.installer.archlinuxcn.preflight_apply",
                    side_effect=lambda *args, **kwargs: events.append("archlinuxcn-preflight"),
                ),
                mock.patch(
                    "install.installer.archlinuxcn.execute_archlinuxcn",
                    side_effect=lambda _: events.append("archlinuxcn"),
                ),
                mock.patch(
                    "install.installer.aur.preflight_apply",
                    side_effect=lambda *args, **kwargs: events.append("aur-preflight"),
                ),
                mock.patch(
                    "install.installer.aur.execute_aur",
                    side_effect=lambda _: events.append("aur"),
                ),
                mock.patch(
                    "install.installer.dotfiles.preflight_apply",
                    side_effect=lambda *args, **kwargs: events.append("dotfiles-preflight")
                    or (1000, 1000, Path(temporary) / "home"),
                ),
                mock.patch(
                    "install.installer.dotfiles.execute_dotfiles",
                    side_effect=lambda *args, **kwargs: events.append("dotfiles"),
                ),
            ):
                installer.execute_install(result, confirmation="/dev/vda")

        self.assertEqual(
            events,
            [
                "storage-preflight",
                "disk-identity",
                "storage",
                "bootstrap-preflight",
                "bootstrap",
                "configure-preflight",
                "artifacts",
                "configure",
                "archlinuxcn-preflight",
                "archlinuxcn",
                "aur-preflight",
                "aur",
                "dotfiles-preflight",
                "dotfiles",
            ],
        )


if __name__ == "__main__":
    unittest.main()
