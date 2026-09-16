from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from install import configure, plan, render


class ConfigureTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    def build(self, target: Path, *, encrypted: bool):
        return configure.build_configuration_plan(
            self.config,
            target_root=target,
            encryption_override=encrypted,
            identifiers=None,
            placeholders=True,
        )

    def test_placeholder_plan_separates_official_and_deferred_services(self) -> None:
        result = self.build(Path("/mnt"), encrypted=False)

        self.assertEqual(result["identifiers"]["root_uuid"], render.PLACEHOLDER_ROOT_UUID)
        self.assertEqual(
            result["enable_services"],
            ["NetworkManager.service", "bluetooth.service"],
        )
        self.assertEqual(result["deferred_services"], ["greetd.service"])
        self.assertIn("etc/sudoers.d/10-utopia-admin", result["files"])
        self.assertNotIn(
            "sd-encrypt", result["artifacts"]["etc/mkinitcpio.conf.d/utopia.conf"]
        )

    def test_encrypted_placeholder_plan_uses_sd_encrypt_and_luks_uuid(self) -> None:
        result = self.build(Path("/mnt"), encrypted=True)

        self.assertEqual(
            result["identifiers"]["luks_uuid"], render.PLACEHOLDER_LUKS_UUID
        )
        self.assertIn(
            "sd-encrypt", result["artifacts"]["etc/mkinitcpio.conf.d/utopia.conf"]
        )
        self.assertIn(
            render.PLACEHOLDER_LUKS_UUID, result["artifacts"]["boot/limine.conf"]
        )

    def test_identifier_discovery_reads_inner_btrfs_esp_and_outer_luks(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)

            def mount_probe(path: Path):
                if path == target / "boot":
                    return {
                        "target": str(path),
                        "source": "/dev/vda1",
                        "fstype": "vfat",
                        "options": "rw,relatime",
                    }
                names = {
                    target: "@",
                    target / "home": "@home",
                    target / "var/log": "@log",
                    target / "var/cache/pacman/pkg": "@pkg",
                }
                name = names[path]
                return {
                    "target": str(path),
                    "source": f"/dev/mapper/cryptroot[/{name}]",
                    "fstype": "btrfs",
                    "options": (
                        "rw,noatime,compress=zstd:3,ssd,space_cache=v2,"
                        f"subvol=/{name}"
                    ),
                }

            uuids = {
                "/dev/mapper/cryptroot": "00000000-0000-4000-8000-000000000010",
                "/dev/vda1": "ABCD-1234",
                "/dev/vda2": "00000000-0000-4000-8000-000000000020",
            }
            result = configure.discover_identifiers(
                self.config,
                target_root=target,
                encrypted=True,
                mount_probe=mount_probe,
                uuid_probe=uuids.__getitem__,
                backing_probe=lambda _: "/dev/vda2",
            )

            self.assertEqual(
                result,
                {
                    "root_uuid": "00000000-0000-4000-8000-000000000010",
                    "esp_uuid": "ABCD-1234",
                    "luks_uuid": "00000000-0000-4000-8000-000000000020",
                },
            )

    def test_artifact_install_is_atomic_and_uses_upstream_limine_binary(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "root"
            limine = target / "usr/share/limine/BOOTX64.EFI"
            limine.parent.mkdir(parents=True)
            limine.write_bytes(b"limine-efi")
            result = self.build(target, encrypted=False)

            configure.install_artifacts(result)

            self.assertEqual(
                (target / "boot/EFI/BOOT/BOOTX64.EFI").read_bytes(), b"limine-efi"
            )
            self.assertEqual(
                (target / "etc/sudoers.d/10-utopia-admin").stat().st_mode & 0o777,
                0o440,
            )
            self.assertTrue((target / "etc/localtime").is_symlink())
            self.assertEqual(
                (target / "etc/localtime").readlink(),
                Path("/usr/share/zoneinfo/Asia/Shanghai"),
            )

    def test_execute_prompts_passwd_directly_and_locks_root_last(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            etc = target / "etc"
            etc.mkdir()
            (etc / "passwd").write_text("root:x:0:0::/root:/bin/bash\n")
            result = self.build(target, encrypted=False)
            calls: list[list[str]] = []

            def runner(argv, **kwargs):
                calls.append(argv)
                self.assertEqual(kwargs, {"check": True})
                return subprocess.CompletedProcess(argv, 0)

            configure.execute_configuration(self.config, result, run=runner)

            self.assertIn("useradd", calls[1])
            self.assertEqual(
                calls[-2], ["arch-chroot", str(target), "passwd", "chikee"]
            )
            self.assertEqual(
                calls[-1],
                ["arch-chroot", str(target), "passwd", "--lock", "root"],
            )

    def test_preflight_does_not_require_deferred_greeter_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            result = self.build(target, encrypted=False)
            required = [
                "etc/os-release",
                "etc/passwd",
                "etc/group",
                "usr/bin/bash",
                "usr/bin/hwclock",
                "usr/bin/locale-gen",
                "usr/bin/mkinitcpio",
                "usr/bin/passwd",
                "usr/bin/useradd",
                "usr/bin/usermod",
                "usr/bin/visudo",
                "usr/share/limine/BOOTX64.EFI",
                "boot/vmlinuz-linux",
                "usr/lib/systemd/system/NetworkManager.service",
                "usr/lib/systemd/system/bluetooth.service",
                "bin/zsh",
            ]
            for relative in required:
                path = target / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.touch()

            with (
                mock.patch("install.configure.os.geteuid", return_value=0),
                mock.patch("install.configure.shutil.which", return_value="/usr/bin/tool"),
                mock.patch("install.configure.bootstrap.validate_target_mounts"),
            ):
                configure.preflight_apply(self.config, result)


if __name__ == "__main__":
    unittest.main()
