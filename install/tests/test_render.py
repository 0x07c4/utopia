from pathlib import Path
import tempfile
import unittest

from install import plan, render


class RenderTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    def build(self, *, encrypted: bool) -> tuple[dict[str, str], dict]:
        return render.build_artifacts(
            self.config,
            root_uuid=None,
            esp_uuid=None,
            luks_uuid=None,
            encryption_override=encrypted,
            placeholders=True,
        )

    def test_unencrypted_files_have_no_encryption_configuration(self) -> None:
        artifacts, metadata = self.build(encrypted=False)

        self.assertFalse(metadata["encryption"])
        self.assertNotIn("sd-encrypt", artifacts["etc/mkinitcpio.conf.d/utopia.conf"])
        self.assertNotIn("rd.luks", artifacts["boot/limine.conf"])
        self.assertIn(
            f"root=UUID={render.PLACEHOLDER_ROOT_UUID}",
            artifacts["boot/limine.conf"],
        )

    def test_encrypted_files_use_only_sd_encrypt(self) -> None:
        artifacts, metadata = self.build(encrypted=True)

        hooks = artifacts["etc/mkinitcpio.conf.d/utopia.conf"]
        self.assertTrue(metadata["encryption"])
        self.assertEqual(hooks.count("sd-encrypt"), 1)
        self.assertNotIn(" encrypt ", hooks)
        self.assertIn(
            f"rd.luks.name={render.PLACEHOLDER_LUKS_UUID}=cryptroot",
            artifacts["boot/limine.conf"],
        )

    def test_fstab_uses_inner_btrfs_uuid_for_every_subvolume(self) -> None:
        artifacts, _ = self.build(encrypted=True)
        fstab = artifacts["etc/fstab"]

        self.assertEqual(fstab.count(f"UUID={render.PLACEHOLDER_ROOT_UUID}"), 4)
        self.assertIn(f"UUID={render.PLACEHOLDER_ESP_UUID}\t/boot\tvfat", fstab)

    def test_identity_and_noctalia_greeter_files_are_staged(self) -> None:
        artifacts, metadata = self.build(encrypted=False)

        self.assertEqual(artifacts["etc/hostname"], "arch-laptop\n")
        self.assertEqual(artifacts["etc/locale.conf"], "LANG=en_US.UTF-8\n")
        self.assertEqual(
            artifacts["etc/locale.gen"],
            "en_US.UTF-8 UTF-8\nzh_CN.UTF-8 UTF-8\n",
        )
        self.assertEqual(artifacts["etc/vconsole.conf"], "KEYMAP=us\n")
        self.assertIn(
            'command = "/usr/bin/noctalia-greeter-session"',
            artifacts["etc/greetd/config.toml"],
        )
        self.assertEqual(
            metadata["symlinks"]["etc/localtime"],
            "/usr/share/zoneinfo/Asia/Shanghai",
        )
        self.assertEqual(
            artifacts["etc/sudoers.d/10-utopia-admin"],
            "%wheel ALL=(ALL:ALL) ALL\n",
        )
        self.assertEqual(metadata["modes"]["etc/sudoers.d/10-utopia-admin"], 0o440)

    def test_render_is_atomic_and_refuses_existing_destination(self) -> None:
        artifacts, metadata = self.build(encrypted=False)
        with tempfile.TemporaryDirectory() as temporary:
            destination = Path(temporary) / "root"
            files = render.write_artifacts(
                destination,
                artifacts,
                metadata["symlinks"],
                metadata["modes"],
            )
            self.assertEqual(len(files), 11)
            self.assertTrue((destination / "boot/limine.conf").is_file())
            self.assertTrue((destination / "etc/localtime").is_symlink())
            self.assertEqual(
                (destination / "etc/localtime").readlink(),
                Path("/usr/share/zoneinfo/Asia/Shanghai"),
            )
            self.assertEqual(
                (destination / "etc/sudoers.d/10-utopia-admin").stat().st_mode
                & 0o777,
                0o440,
            )
            with self.assertRaisesRegex(render.RenderError, "already exists"):
                render.write_artifacts(destination, artifacts)

    def test_live_system_paths_are_rejected(self) -> None:
        for destination in (
            Path("/"),
            Path("/boot/utopia"),
            Path("/dev/utopia"),
            Path("/etc"),
            Path("/proc/utopia"),
            Path("/run/utopia"),
            Path("/sys/utopia"),
        ):
            with self.subTest(destination=destination):
                with self.assertRaises(render.RenderError):
                    render.validate_output_directory(destination)

    def test_encrypted_render_requires_luks_uuid(self) -> None:
        with self.assertRaisesRegex(render.RenderError, "LUKS UUID is required"):
            render.build_artifacts(
                self.config,
                root_uuid=render.PLACEHOLDER_ROOT_UUID,
                esp_uuid=render.PLACEHOLDER_ESP_UUID,
                luks_uuid=None,
                encryption_override=True,
                placeholders=False,
            )

    def test_unencrypted_render_rejects_luks_uuid(self) -> None:
        with self.assertRaisesRegex(render.RenderError, "only valid"):
            render.build_artifacts(
                self.config,
                root_uuid=render.PLACEHOLDER_ROOT_UUID,
                esp_uuid=render.PLACEHOLDER_ESP_UUID,
                luks_uuid=render.PLACEHOLDER_LUKS_UUID,
                encryption_override=False,
                placeholders=False,
            )


if __name__ == "__main__":
    unittest.main()
