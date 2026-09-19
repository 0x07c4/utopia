from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from install import bootstrap, plan


class BootstrapTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    def build(self, target: Path, *, encrypted: bool):
        return bootstrap.build_bootstrap_plan(
            self.config,
            target_root=target,
            encryption_override=encrypted,
        )

    def test_plain_bootstrap_contains_only_official_packages(self) -> None:
        result = self.build(Path("/mnt"), encrypted=False)

        self.assertEqual(result["official"]["total"], 80)
        self.assertEqual(
            result["command"][:5],
            (
                "pacstrap",
                "-C",
                str(bootstrap.OFFICIAL_PACMAN_CONFIG),
                "-K",
                "/mnt",
            ),
        )
        self.assertIn("noctalia", result["official"]["packages"])
        self.assertNotIn("cryptsetup", result["official"]["packages"])
        self.assertNotIn("noctalia-greeter-git", result["command"])
        self.assertNotIn("google-chrome", result["command"])
        self.assertEqual(result["deferred"]["archlinuxcn"]["total"], 5)
        self.assertEqual(result["deferred"]["aur"]["total"], 3)

    def test_encrypted_bootstrap_adds_only_conditional_cryptsetup(self) -> None:
        plain = self.build(Path("/mnt"), encrypted=False)
        encrypted = self.build(Path("/mnt"), encrypted=True)

        self.assertEqual(encrypted["official"]["total"], 81)
        self.assertEqual(
            set(encrypted["official"]["packages"])
            - set(plain["official"]["packages"]),
            {"cryptsetup"},
        )

    def mount_probe(self, target: Path, root: Path, *, encrypted: bool):
        relative = target.relative_to(root)
        mountpoint = "/" if not relative.parts else "/" + relative.as_posix()
        names = {
            "/": "@",
            "/home": "@home",
            "/var/log": "@log",
            "/var/cache/pacman/pkg": "@pkg",
        }
        if mountpoint == "/boot":
            return {
                "target": str(target),
                "source": "/dev/vda1",
                "fstype": "vfat",
                "options": "rw,relatime",
            }
        source = "/dev/mapper/cryptroot" if encrypted else "/dev/vda2"
        name = names[mountpoint]
        return {
            "target": str(target),
            "source": f"{source}[/{name}]",
            "fstype": "btrfs",
            "options": (
                "rw,noatime,compress=zstd:3,ssd,space_cache=v2,"
                f"subvol=/{name}"
            ),
        }

    def test_preflight_accepts_complete_plain_mount_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.build(root, encrypted=False)
            probe = lambda target: self.mount_probe(target, root, encrypted=False)
            with (
                mock.patch("install.bootstrap.os.geteuid", return_value=0),
                mock.patch("install.bootstrap.shutil.which", return_value="/usr/bin/pacstrap"),
            ):
                bootstrap.preflight_apply(
                    self.config,
                    result,
                    mount_probe=probe,
                    repository_check=lambda _: None,
                )

    def test_preflight_accepts_complete_encrypted_mount_layout(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.build(root, encrypted=True)
            probe = lambda target: self.mount_probe(target, root, encrypted=True)
            with (
                mock.patch("install.bootstrap.os.geteuid", return_value=0),
                mock.patch("install.bootstrap.shutil.which", return_value="/usr/bin/pacstrap"),
            ):
                bootstrap.preflight_apply(
                    self.config,
                    result,
                    mount_probe=probe,
                    repository_check=lambda _: None,
                )

    def test_preflight_rejects_encryption_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.build(root, encrypted=False)
            probe = lambda target: self.mount_probe(target, root, encrypted=True)
            with (
                mock.patch("install.bootstrap.os.geteuid", return_value=0),
                mock.patch("install.bootstrap.shutil.which", return_value="/usr/bin/pacstrap"),
            ):
                with self.assertRaisesRegex(bootstrap.BootstrapError, "encryption off"):
                    bootstrap.preflight_apply(
                        self.config,
                        result,
                        mount_probe=probe,
                        repository_check=lambda _: None,
                    )

    def test_preflight_rejects_missing_subvolume_mount(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            result = self.build(root, encrypted=False)

            def probe(target: Path):
                mount = self.mount_probe(target, root, encrypted=False)
                if target == root / "home":
                    mount["options"] = mount["options"].replace("subvol=/@home", "subvol=/@")
                return mount

            with (
                mock.patch("install.bootstrap.os.geteuid", return_value=0),
                mock.patch("install.bootstrap.shutil.which", return_value="/usr/bin/pacstrap"),
            ):
                with self.assertRaisesRegex(bootstrap.BootstrapError, "does not match"):
                    bootstrap.preflight_apply(
                        self.config,
                        result,
                        mount_probe=probe,
                        repository_check=lambda _: None,
                    )

    def test_repository_check_rejects_non_official_resolution(self) -> None:
        result = self.build(Path("/mnt"), encrypted=False)
        output = "\n".join(
            f"core/{package}" for package in result["official"]["packages"]
        ).replace("core/noctalia", "archlinuxcn/noctalia")
        runner = mock.Mock(
            return_value=subprocess.CompletedProcess(["pacman"], 0, stdout=output)
        )

        with self.assertRaisesRegex(bootstrap.BootstrapError, "non-official"):
            bootstrap.verify_official_resolution(result, run=runner)

    def test_pacstrap_failure_is_reported(self) -> None:
        result = self.build(Path("/mnt"), encrypted=False)
        with mock.patch(
            "install.bootstrap.subprocess.run",
            side_effect=subprocess.CalledProcessError(1, ["pacstrap"]),
        ):
            with self.assertRaisesRegex(bootstrap.BootstrapError, "pacstrap failed"):
                bootstrap.execute_bootstrap(result)


if __name__ == "__main__":
    unittest.main()
