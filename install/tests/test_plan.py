import copy
from pathlib import Path
import unittest

from install import plan


class InstallPlanTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    def test_example_schema_allows_intentionally_empty_device(self) -> None:
        plan.validate_config(self.config, allow_empty_device=True)
        plan.validate_all_manifests(self.config, plan.REPO_ROOT)

    def test_normal_plan_requires_a_selected_disk(self) -> None:
        with self.assertRaisesRegex(plan.PlanError, "storage.device is empty"):
            plan.build_plan(self.config, plan.REPO_ROOT, probe_device=False)

    def test_unencrypted_plan_uses_plain_btrfs_boot_path(self) -> None:
        result = plan.build_plan(
            self.config,
            plan.REPO_ROOT,
            device_override="/dev/example-disk",
            encryption_override=False,
            probe_device=False,
        )

        self.assertFalse(result["storage"]["encryption"])
        self.assertNotIn("sd-encrypt", result["boot"]["mkinitcpio_hooks"])
        self.assertEqual(
            result["boot"]["kernel_cmdline_template"],
            "root=UUID=<BTRFS_UUID> rootflags=subvol=@ rw",
        )
        self.assertNotIn(
            "packages/features/disk-encryption.txt",
            [item["path"] for item in result["packages"]["manifests"]],
        )

    def test_plan_captures_current_identity_and_login_services(self) -> None:
        result = plan.build_plan(
            self.config,
            plan.REPO_ROOT,
            device_override="/dev/example-disk",
            probe_device=False,
        )

        self.assertEqual(result["system"]["groups"], ["wheel"])
        self.assertEqual(result["system"]["sudo_group"], "wheel")
        self.assertEqual(
            result["services"]["enable_after_official"],
            ["NetworkManager.service", "bluetooth.service"],
        )
        self.assertEqual(
            result["services"]["enable_after_archlinuxcn"], ["greetd.service"]
        )
        self.assertEqual(
            result["greetd"]["command"], "/usr/bin/noctalia-greeter-session"
        )
        self.assertEqual(result["greetd"]["user"], "greeter")
        self.assertEqual(
            result["greetd"]["setup_command"],
            "/usr/share/noctalia-greeter/setup_greeter_system.sh",
        )

    def test_rejects_unsafe_identity_and_service_values(self) -> None:
        cases = (
            ("user", "groups", ["wheel", "bad group"], "user.groups"),
            (
                "services",
                "enable_after_official",
                ["NetworkManager.service", "not/a/unit"],
                "services.enable",
            ),
            ("greetd", "command", "noctalia-greeter-session", "greetd.command"),
            ("greetd", "setup_command", "setup-greeter", "greetd.setup_command"),
        )
        for section, key, value, message in cases:
            with self.subTest(section=section, key=key):
                invalid = copy.deepcopy(self.config)
                invalid[section][key] = value
                with self.assertRaisesRegex(plan.PlanError, message):
                    plan.validate_config(invalid, allow_empty_device=True)

        invalid_sudo_group = copy.deepcopy(self.config)
        invalid_sudo_group["user"]["sudo_group"] = "admin"
        with self.assertRaisesRegex(plan.PlanError, "one of user.groups"):
            plan.validate_config(invalid_sudo_group, allow_empty_device=True)

    def test_rejects_unsafe_btrfs_paths_and_options(self) -> None:
        cases = (
            ("name", "@home/../../escape", "safe single path component"),
            ("mountpoint", "/boot", "conflicts with system mounts"),
            ("mountpoint", "/home/../escape", "normalized"),
        )
        for key, value, message in cases:
            with self.subTest(key=key, value=value):
                invalid = copy.deepcopy(self.config)
                invalid["storage"]["btrfs"]["subvolumes"][1][key] = value
                with self.assertRaisesRegex(plan.PlanError, message):
                    plan.validate_config(invalid, allow_empty_device=True)

        invalid_options = copy.deepcopy(self.config)
        invalid_options["storage"]["btrfs"]["mount_options"] = ["noatime,ro"]
        with self.assertRaisesRegex(plan.PlanError, "invalid option"):
            plan.validate_config(invalid_options, allow_empty_device=True)

        mismatched_root = copy.deepcopy(self.config)
        mismatched_root["storage"]["btrfs"]["subvolumes"][0] = {
            "name": "@root",
            "mountpoint": "/",
        }
        with self.assertRaisesRegex(plan.PlanError, "define @ mounted at /"):
            plan.validate_config(mismatched_root, allow_empty_device=True)

    def test_encrypted_plan_inserts_only_sd_encrypt(self) -> None:
        result = plan.build_plan(
            self.config,
            plan.REPO_ROOT,
            device_override="/dev/example-disk",
            encryption_override=True,
            probe_device=False,
        )

        hooks = result["boot"]["mkinitcpio_hooks"]
        self.assertEqual(hooks.count("sd-encrypt"), 1)
        self.assertEqual(hooks.index("sd-encrypt"), hooks.index("block") + 1)
        self.assertNotIn("encrypt", hooks)
        self.assertIn(
            "rd.luks.name=<LUKS_UUID>=cryptroot",
            result["boot"]["kernel_cmdline_template"],
        )
        self.assertIn(
            "packages/features/disk-encryption.txt",
            [item["path"] for item in result["packages"]["manifests"]],
        )
        encryption_manifest = next(
            item
            for item in result["packages"]["manifests"]
            if item["path"] == "packages/features/disk-encryption.txt"
        )
        self.assertEqual(encryption_manifest["source"], "official")

    def test_package_sources_are_kept_separate(self) -> None:
        official_manifests, official = plan.resolve_package_source(
            self.config, plan.REPO_ROOT, source="official", encrypted=False
        )
        _, archlinuxcn = plan.resolve_package_source(
            self.config, plan.REPO_ROOT, source="archlinuxcn", encrypted=False
        )
        _, aur = plan.resolve_package_source(
            self.config, plan.REPO_ROOT, source="aur", encrypted=False
        )

        self.assertEqual(
            [item["path"] for item in official_manifests],
            ["packages/arch.txt", "packages/hardware-intel-laptop.txt"],
        )
        self.assertIn("noctalia", official)
        self.assertNotIn("noctalia-greeter-git", official)
        self.assertIn("noctalia-greeter-git", archlinuxcn)
        self.assertEqual(aur, ["clash-verge-rev-bin", "google-chrome", "qqmusic-bin"])

    def test_manifest_paths_cannot_escape_repository(self) -> None:
        with self.assertRaisesRegex(plan.PlanError, "escapes the repository"):
            plan.manifest_path(Path(plan.REPO_ROOT), "../outside.txt")


if __name__ == "__main__":
    unittest.main()
