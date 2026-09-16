from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from install import plan, storage


class StorageTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    def build(self, *, encrypted: bool, device: str = "/dev/nvme0n1"):
        install_plan = plan.build_plan(
            self.config,
            plan.REPO_ROOT,
            device_override=device,
            encryption_override=encrypted,
            probe_device=False,
        )
        install_plan["storage"]["device"]["size_bytes"] = 100 * 1024**3
        return install_plan

    def test_partition_paths_cover_nvme_and_scsi_names(self) -> None:
        self.assertEqual(storage.partition_path("/dev/nvme0n1", 1), "/dev/nvme0n1p1")
        self.assertEqual(storage.partition_path("/dev/mmcblk0", 2), "/dev/mmcblk0p2")
        self.assertEqual(storage.partition_path("/dev/sda", 2), "/dev/sda2")

    def test_unencrypted_operations_create_plain_btrfs_layout(self) -> None:
        result = self.build(encrypted=False, device="/dev/sda")
        operations = storage.build_operations(result, Path("/mnt"))
        commands = [operation.argv for operation in operations]
        table = next(operation.stdin for operation in operations if operation.argv[0] == "sfdisk")

        self.assertIn(storage.LINUX_FILESYSTEM_GUID, table)
        self.assertNotIn(storage.LINUX_LUKS_GUID, table)
        self.assertFalse(any(command[0] == "cryptsetup" for command in commands))
        self.assertIn(
            ("mkfs.btrfs", "--force", "--label", "arch", "/dev/sda2"), commands
        )
        self.assertEqual(commands[-1], ("mount", "/dev/sda1", "/mnt/boot"))

    def test_encrypted_operations_leave_passphrases_on_the_terminal(self) -> None:
        result = self.build(encrypted=True)
        operations = storage.build_operations(result, Path("/mnt"))
        cryptsetup = [operation for operation in operations if operation.argv[0] == "cryptsetup"]
        table = next(operation.stdin for operation in operations if operation.argv[0] == "sfdisk")

        self.assertIn(storage.LINUX_LUKS_GUID, table)
        self.assertEqual(len(cryptsetup), 2)
        self.assertTrue(all(operation.interactive for operation in cryptsetup))
        self.assertTrue(all(operation.stdin is None for operation in cryptsetup))
        self.assertFalse(any("key-file" in argument for operation in cryptsetup for argument in operation.argv))
        self.assertIn(
            ("mkfs.btrfs", "--force", "--label", "arch", "/dev/mapper/cryptroot"),
            [operation.argv for operation in operations],
        )

    def test_apply_requires_exact_device_confirmation_before_other_checks(self) -> None:
        result = self.build(encrypted=False)
        operations = storage.build_operations(result, Path("/mnt"))
        with self.assertRaisesRegex(storage.StorageError, "exactly match"):
            storage.preflight_apply(result, operations, Path("/mnt"), "/dev/sda")

    def test_apply_refuses_a_confirmed_disk_with_active_mounts(self) -> None:
        result = self.build(encrypted=False)
        result["storage"]["device"]["active_mounts"] = [
            {"path": "/dev/nvme0n1p1", "mountpoint": "/boot"}
        ]
        operations = storage.build_operations(result, Path("/mnt"))
        with mock.patch("install.storage.os.geteuid", return_value=0):
            with self.assertRaisesRegex(storage.StorageError, "still has mounted"):
                storage.preflight_apply(
                    result, operations, Path("/mnt"), "/dev/nvme0n1"
                )

    def test_preview_calls_out_active_mounts_and_exact_confirmation(self) -> None:
        result = self.build(encrypted=False)
        result["storage"]["device"]["active_mounts"] = [
            {"path": "/dev/nvme0n1p1", "mountpoint": "/boot"}
        ]
        output = storage.format_operations(
            storage.build_operations(result, Path("/mnt")), result
        )

        self.assertIn("/dev/nvme0n1p1 -> /boot", output)
        self.assertIn("confirmation must exactly equal: /dev/nvme0n1", output)

    def test_live_system_target_roots_are_rejected(self) -> None:
        for target in (Path("/"), Path("/home/install"), Path("/etc/utopia")):
            with self.subTest(target=target):
                with self.assertRaises(storage.StorageError):
                    storage.canonical_target_root(target)

    def test_failed_execution_cleans_up_open_mapper_and_mounts(self) -> None:
        operations = [
            storage.Operation("open", ("cryptsetup", "open", "/dev/x2", "cryptroot"), effect="mapper-open"),
            storage.Operation("mount", ("mount", "/dev/mapper/cryptroot", "/mnt"), effect="target-mounted"),
            storage.Operation("fail", ("false",)),
        ]
        calls = 0

        def run(*args, **kwargs):
            nonlocal calls
            calls += 1
            if calls == 3:
                raise subprocess.CalledProcessError(1, args[0])
            return subprocess.CompletedProcess(args[0], 0)

        with mock.patch("install.storage.cleanup_failed_apply") as cleanup:
            with self.assertRaisesRegex(storage.StorageError, "operation failed"):
                storage.execute_operations(
                    operations,
                    device="/dev/x",
                    target_root=Path("/mnt"),
                    mapper="cryptroot",
                    run=run,
                )
            cleanup.assert_called_once_with(Path("/mnt"), "cryptroot", mounted=True)

    def test_partition_script_is_accepted_by_installed_sfdisk(self) -> None:
        if storage.shutil.which("sfdisk") is None:
            self.skipTest("sfdisk is not installed")
        with tempfile.TemporaryDirectory() as temporary:
            image = Path(temporary) / "disk.img"
            with image.open("wb") as disk:
                disk.truncate(5 * 1024**3)
            subprocess.run(
                ["sfdisk", "--no-act", image],
                input=storage.partition_script(2048, encrypted=True),
                text=True,
                check=True,
                capture_output=True,
            )


if __name__ == "__main__":
    unittest.main()
