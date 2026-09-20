import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from install import archlinuxcn, plan


class ArchLinuxCNTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    def build(self, target: Path, *, encrypted: bool = False):
        return archlinuxcn.build_archlinuxcn_plan(
            self.config,
            target_root=target,
            encryption_override=encrypted,
        )

    @staticmethod
    def write_target_file(
        target: Path, relative_path: str, content: str = "", mode: int = 0o644
    ) -> Path:
        path = target / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
        path.chmod(mode)
        return path

    def write_preflight_target(self, target: Path) -> None:
        self.write_target_file(target, "etc/pacman.conf", "[core]\n[extra]\n")
        self.write_target_file(
            target,
            "etc/passwd",
            "utopia:x:1000:1000::/home/utopia:/bin/zsh\n"
            "greeter:x:967:967::/var/lib/noctalia-greeter:/usr/bin/nologin\n",
        )
        self.write_target_file(
            target,
            "etc/group",
            "wheel:x:998:utopia\nvideo:x:985:greeter\ngreeter:x:967:\n",
        )
        self.write_target_file(
            target,
            "etc/greetd/config.toml",
            '[terminal]\nvt = 1\n\n[default_session]\n'
            'command = "/usr/bin/noctalia-greeter-session"\nuser = "greeter"\n',
        )
        for relative_path in (
            "etc/pam.d/greetd",
            "usr/bin/greetd",
            "usr/bin/pacman",
            "usr/bin/pacman-conf",
            "usr/bin/pacman-key",
            "usr/lib/systemd/system/greetd.service",
        ):
            self.write_target_file(target, relative_path)

    def test_plan_separates_keyring_and_never_contains_aur_packages(self) -> None:
        result = self.build(Path("/mnt"))

        self.assertEqual(len(result["packages"]), 5)
        self.assertEqual(result["keyring_package"], "archlinuxcn-keyring")
        self.assertEqual(
            result["remaining_packages"],
            [
                "noctalia-greeter-git",
                "paru",
                "rime-ice-git",
                "ttf-maplemono-nf-cn-unhinted",
            ],
        )
        self.assertEqual(
            result["commands"]["keyring"][-1], "archlinuxcn-keyring"
        )
        self.assertIn("--sysupgrade", result["commands"]["packages"])
        self.assertEqual(
            result["commands"]["greeter_setup"][2:4],
            ("env", "GREETER_USER=greeter"),
        )
        self.assertEqual(result["commands"]["enable"][-1], "greetd.service")
        aur_packages = {"clash-verge-rev-bin", "google-chrome", "qqmusic-bin"}
        self.assertTrue(aur_packages.isdisjoint(result["packages"]))

    def test_managed_pacman_section_is_idempotent_and_inherits_siglevel(self) -> None:
        initial = "[options]\nSigLevel = Required DatabaseOptional\n\n[core]\n"

        first = archlinuxcn.render_pacman_conf(
            initial, "https://mirrors.tuna.tsinghua.edu.cn/archlinuxcn/$arch"
        )
        second = archlinuxcn.render_pacman_conf(
            first, "https://mirrors.tuna.tsinghua.edu.cn/archlinuxcn/$arch"
        )

        self.assertEqual(first, second)
        self.assertEqual(first.count("[archlinuxcn]"), 1)
        managed = first.split(archlinuxcn.MANAGED_BEGIN, 1)[1]
        self.assertNotIn("SigLevel", managed)

    def test_pacman_section_rejects_unmanaged_or_malformed_configuration(self) -> None:
        invalid_values = (
            "[core]\n[archlinuxcn]\nServer = https://example.invalid/$arch\n",
            f"[core]\n{archlinuxcn.MANAGED_BEGIN}\n",
            f"[core]\n{archlinuxcn.MANAGED_END}\n{archlinuxcn.MANAGED_BEGIN}\n",
        )
        for existing in invalid_values:
            with self.subTest(existing=existing):
                with self.assertRaisesRegex(
                    archlinuxcn.ArchLinuxCNError, "managed block|unmanaged"
                ):
                    archlinuxcn.render_pacman_conf(
                        existing,
                        "https://mirrors.tuna.tsinghua.edu.cn/archlinuxcn/$arch",
                    )

    def test_preflight_accepts_configured_target_before_greeter_package(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.write_preflight_target(target)
            result = self.build(target)

            self.assertFalse((target / "usr/bin/noctalia-greeter-session").exists())
            with (
                mock.patch("install.archlinuxcn.os.geteuid", return_value=0),
                mock.patch(
                    "install.archlinuxcn.shutil.which", return_value="/usr/bin/tool"
                ),
                mock.patch("install.archlinuxcn.bootstrap.validate_target_mounts"),
            ):
                archlinuxcn.preflight_apply(self.config, result)

    def test_preflight_requires_greeter_video_membership(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            self.write_preflight_target(target)
            (target / "etc/group").write_text(
                "wheel:x:998:utopia\nvideo:x:985:\ngreeter:x:967:\n"
            )
            result = self.build(target)

            with (
                mock.patch("install.archlinuxcn.os.geteuid", return_value=0),
                mock.patch(
                    "install.archlinuxcn.shutil.which", return_value="/usr/bin/tool"
                ),
                mock.patch("install.archlinuxcn.bootstrap.validate_target_mounts"),
            ):
                with self.assertRaisesRegex(
                    archlinuxcn.ArchLinuxCNError, "not in the video group"
                ):
                    archlinuxcn.preflight_apply(self.config, result)

    def test_resolution_rejects_wrong_explicit_or_unexpected_repository(self) -> None:
        result = self.build(Path("/mnt"))
        package_lines = "\n".join(
            f"archlinuxcn/{package}" for package in result["remaining_packages"]
        )

        for repositories, resolution, message in (
            (
                "core\nextra\narchlinuxcn\n",
                package_lines.replace(
                    "archlinuxcn/noctalia-greeter-git",
                    "extra/noctalia-greeter-git",
                ),
                "resolved from extra",
            ),
            (
                "core\nextra\nmultilib\narchlinuxcn\n",
                package_lines,
                "not exactly",
            ),
        ):
            with self.subTest(message=message):
                runner = mock.Mock(
                    side_effect=[
                        subprocess.CompletedProcess([], 0, stdout=repositories),
                        subprocess.CompletedProcess([], 0, stdout=resolution),
                    ]
                )
                with self.assertRaisesRegex(archlinuxcn.ArchLinuxCNError, message):
                    archlinuxcn.verify_resolution(result, run=runner)

    def test_greeter_verification_checks_pam_executables_and_state_owner(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary)
            result = self.build(target)
            uid, gid = os.getuid(), os.getgid()
            self.write_target_file(
                target,
                "etc/passwd",
                f"greeter:x:{uid}:{gid}::/var/lib/noctalia-greeter:/usr/bin/nologin\n",
            )
            self.write_target_file(
                target,
                "etc/greetd/config.toml",
                '[terminal]\nvt = 1\n\n[default_session]\n'
                'command = "/usr/bin/noctalia-greeter-session"\nuser = "greeter"\n',
            )
            self.write_target_file(
                target,
                "etc/pam.d/greetd",
                "auth include system-local-login\n"
                "session required pam_systemd.so\n",
            )
            for relative_path in (
                "usr/bin/noctalia-greeter-apply-appearance",
                "usr/bin/noctalia-greeter-session",
                "usr/share/noctalia-greeter/setup_greeter_system.sh",
            ):
                self.write_target_file(target, relative_path, "#!/bin/sh\n", 0o755)
            (target / "var/lib/noctalia-greeter").mkdir(parents=True)

            archlinuxcn.verify_greeter_setup(result)

            (target / "etc/passwd").write_text(
                f"greeter:x:{uid + 1}:{gid}::/var/lib/noctalia-greeter:/usr/bin/nologin\n"
            )
            with self.assertRaisesRegex(
                archlinuxcn.ArchLinuxCNError, "not owned by greeter"
            ):
                archlinuxcn.verify_greeter_setup(result)

    def test_execution_enables_greetd_only_after_every_verification(self) -> None:
        result = self.build(Path("/mnt"))
        events: list[str] = []

        def runner(argv, **_kwargs):
            commands = result["commands"]
            label = next(name for name, command in commands.items() if list(command) == argv)
            events.append(label)
            return subprocess.CompletedProcess(argv, 0)

        with mock.patch(
            "install.archlinuxcn.install_repository_config",
            side_effect=lambda _: events.append("repository"),
        ):
            archlinuxcn.execute_archlinuxcn(
                result,
                run=runner,
                resolution_check=lambda _: events.append("resolution"),
                installation_check=lambda _: events.append("installation"),
                greeter_check=lambda _: events.append("greeter"),
            )

        self.assertEqual(
            events,
            [
                "repository",
                "keyring",
                "resolution",
                "packages",
                "installation",
                "greeter_setup",
                "greeter",
                "enable",
            ],
        )


if __name__ == "__main__":
    unittest.main()
