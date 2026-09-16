import os
from pathlib import Path
import tempfile
import unittest

from install import archlinuxcn, configure, plan, recovery


class RecoveryTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    @staticmethod
    def mount_probe(target: Path, root: Path, *, encrypted: bool):
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
            "options": "rw,noatime,compress=zstd:3,ssd,space_cache=v2,subvol=/" + name,
        }

    def prepare_target(self, target: Path, *, encrypted: bool) -> None:
        ids = {
            "root_uuid": "00000000-0000-4000-8000-000000000001",
            "esp_uuid": "ABCD-1234",
            "luks_uuid": "00000000-0000-4000-8000-000000000002" if encrypted else None,
        }
        configuration = configure.build_configuration_plan(
            self.config,
            target_root=target,
            encryption_override=encrypted,
            identifiers=ids,
            placeholders=False,
        )
        limine = target / "usr/share/limine/BOOTX64.EFI"
        limine.parent.mkdir(parents=True)
        limine.write_bytes(b"limine")
        configure.install_artifacts(configuration)
        for relative_path in (
            "etc/passwd",
            "etc/pam.d/greetd",
            "usr/bin/noctalia-greeter-apply-appearance",
            "usr/bin/noctalia-greeter-session",
            "usr/share/noctalia-greeter/setup_greeter_system.sh",
        ):
            path = target / relative_path
            path.parent.mkdir(parents=True, exist_ok=True)
            if relative_path == "etc/passwd":
                path.write_text(
                    f"greeter:x:{os.getuid()}:{os.getgid()}::/var/lib/noctalia-greeter:/bin/bash\n"
                )
            elif relative_path == "etc/pam.d/greetd":
                path.write_text("session required pam_systemd.so\n")
            else:
                path.write_text("#!/bin/sh\n")
                path.chmod(0o755)
        (target / "var/lib/noctalia-greeter").mkdir(parents=True)

    def test_audit_rebuilds_and_checks_target_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.prepare_target(target, encrypted=True)
            uuid_values = {
                "/dev/mapper/cryptroot": "00000000-0000-4000-8000-000000000001",
                "/dev/vda1": "ABCD-1234",
                "/dev/vda2": "00000000-0000-4000-8000-000000000002",
            }
            result = recovery.audit_target(
                self.config,
                target_root=target,
                encrypted=True,
                mount_probe=lambda path: self.mount_probe(path, target, encrypted=True),
                uuid_probe=uuid_values.__getitem__,
                backing_probe=lambda _: "/dev/vda2",
            )

            self.assertTrue(result["encryption"])
            self.assertIn("etc/fstab", result["files"])
            self.assertIn("UTOPIA", recovery.format_audit(result))

    def test_audit_reports_rendered_file_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.prepare_target(target, encrypted=False)
            (target / "etc/hostname").write_text("tampered\n")
            uuid_values = {
                "/dev/vda2": "00000000-0000-4000-8000-000000000001",
                "/dev/vda1": "ABCD-1234",
            }
            with self.assertRaisesRegex(recovery.RecoveryError, "etc/hostname"):
                recovery.audit_target(
                    self.config,
                    target_root=target,
                    encrypted=False,
                    mount_probe=lambda path: self.mount_probe(path, target, encrypted=False),
                    uuid_probe=uuid_values.__getitem__,
                )


if __name__ == "__main__":
    unittest.main()
