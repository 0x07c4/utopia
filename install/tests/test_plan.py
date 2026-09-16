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
        self.assertEqual(
            result["services"]["enable"],
            ["NetworkManager.service", "bluetooth.service", "greetd.service"],
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
                "enable",
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

    def test_manifest_paths_cannot_escape_repository(self) -> None:
        with self.assertRaisesRegex(plan.PlanError, "escapes the repository"):
            plan.manifest_path(Path(plan.REPO_ROOT), "../outside.txt")


if __name__ == "__main__":
    unittest.main()
