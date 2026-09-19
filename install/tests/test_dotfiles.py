from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from unittest import mock

from install import dotfiles, plan


class DotfilesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = plan.load_config(plan.DEFAULT_CONFIG)

    def test_plan_lists_reviewed_paths_without_runtime_state(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            (source / ".zshrc").write_text("source\n")
            (source / ".zimrc").write_text("zim\n")
            (source / ".config/niri").mkdir(parents=True)
            (source / ".config/niri/config.kdl").write_text("layout\n")
            (source / ".config/noctalia").mkdir(parents=True)
            (source / ".config/noctalia/bar.toml").write_text("bar\n")
            (source / ".config/environment.d").mkdir(parents=True)
            (source / ".config/environment.d/fcitx5.conf").write_text("GTK_IM_MODULE=fcitx\n")
            (source / ".config/fcitx5").mkdir(parents=True)
            (source / ".config/fcitx5/profile").write_text("DefaultIM=rime\n")
            (source / ".local/share/fcitx5/rime").mkdir(parents=True)
            (source / ".local/share/fcitx5/rime/rime_ice.custom.yaml").write_text("patch:\n")
            (source / ".config/nvim").mkdir(parents=True)
            (source / ".config/nvim/init.lua").write_text("return {}\n")
            result = dotfiles.build_dotfiles_plan(
                self.config, target_root=Path(temporary) / "target", source_root=source
            )

        self.assertIn(".zshrc", result["paths"])
        self.assertIn(".config/nvim", result["paths"])
        self.assertIn(".config/fcitx5", result["paths"])
        self.assertIn(".config/environment.d/fcitx5.conf", result["paths"])
        self.assertIn(".local/share/fcitx5/rime/rime_ice.custom.yaml", result["paths"])
        self.assertNotIn(".zhistory", result["paths"])

    def test_preflight_rejects_uninitialized_nvim_submodule(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            source.mkdir()
            (source / ".zshrc").write_text("")
            (source / ".zimrc").write_text("")
            (source / ".config/niri").mkdir(parents=True)
            (source / ".config/niri/config.kdl").write_text("")
            (source / ".config/noctalia").mkdir(parents=True)
            (source / ".config/nvim").mkdir(parents=True)
            target = Path(temporary) / "target"
            (target / "etc").mkdir(parents=True)
            (target / "etc/passwd").write_text(
                f"chikee:x:{os.getuid()}:{os.getgid()}::/home/chikee:/bin/zsh\n"
            )
            home = target / "home/chikee"
            home.mkdir(parents=True)
            result = dotfiles.build_dotfiles_plan(
                self.config, target_root=target, source_root=source
            )
            with (
                mock.patch("install.dotfiles.os.geteuid", return_value=0),
                mock.patch("install.dotfiles.bootstrap.validate_target_mounts"),
            ):
                with self.assertRaisesRegex(dotfiles.DotfilesError, "submodule is empty"):
                    dotfiles.preflight_apply(self.config, result)

    def test_execution_copies_and_protects_ssh_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            target = Path(temporary) / "home"
            (source / ".ssh").mkdir(parents=True)
            (source / ".ssh/config").write_text("Host example\n")
            (source / ".config/gtk-4.0").mkdir(parents=True)
            (source / ".config/gtk-4.0/settings.ini").write_text("[Settings]\n")
            (source / ".config/gtk-4.0/gtk.css").write_text("generated\n")
            plan_result = {
                "source_root": str(source),
                "paths": (".ssh/config", ".config/gtk-4.0"),
            }
            with mock.patch("install.dotfiles.os.chown"):
                dotfiles.execute_dotfiles(plan_result, uid=1000, gid=1000, home=target)

            self.assertTrue((target / ".ssh/config").is_file())
            self.assertEqual((target / ".ssh/config").stat().st_mode & 0o777, 0o600)
            self.assertTrue((target / ".config/gtk-4.0/settings.ini").is_file())
            self.assertFalse((target / ".config/gtk-4.0/gtk.css").exists())

    def test_execution_assigns_generated_parent_directories_to_target_user(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            source = Path(temporary) / "source"
            home = Path(temporary) / "target/home/chikee"
            relative = ".local/share/example/config"
            (source / relative).parent.mkdir(parents=True)
            (source / relative).write_text("value\n")
            plan_result = {
                "source_root": str(source),
                "paths": (relative,),
            }

            with mock.patch("install.dotfiles.os.chown") as chown:
                dotfiles.execute_dotfiles(plan_result, uid=1000, gid=1001, home=home)

            for parent in (
                home / ".local",
                home / ".local/share",
                home / ".local/share/example",
            ):
                chown.assert_any_call(parent, 1000, 1001, follow_symlinks=False)

    def test_rime_deployment_runs_as_target_user_and_verifies_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            home = target / "home/chikee"
            rime_dir = home / dotfiles.RIME_USER_DIR
            rime_dir.mkdir(parents=True)
            (rime_dir / "default.custom.yaml").write_text("patch:\n")
            calls: list[list[str]] = []

            def runner(argv, **kwargs):
                calls.append(argv)
                self.assertTrue(kwargs["check"])
                build = rime_dir / "build"
                build.mkdir()
                for name in dotfiles.RIME_BUILD_OUTPUTS:
                    (build / name).touch()
                return subprocess.CompletedProcess(argv, 0)

            result = {
                "target_root": str(target),
                "user": "chikee",
                "paths": (dotfiles.RIME_SOURCE_PATH,),
            }
            dotfiles.deploy_rime(result, home=home, run=runner)

            self.assertEqual(
                calls,
                [[
                    "arch-chroot",
                    "-u",
                    "chikee",
                    str(target),
                    "env",
                    "HOME=/home/chikee",
                    "rime_deployer",
                    "--build",
                    "/home/chikee/.local/share/fcitx5/rime",
                    "/usr/share/rime-data",
                    "/home/chikee/.local/share/fcitx5/rime/build",
                ]],
            )

    def test_rime_deployment_rejects_an_incomplete_build(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            target = Path(temporary) / "target"
            home = target / "home/chikee"
            (home / dotfiles.RIME_USER_DIR).mkdir(parents=True)
            result = {
                "target_root": str(target),
                "user": "chikee",
                "paths": (dotfiles.RIME_SOURCE_PATH,),
            }

            with self.assertRaisesRegex(dotfiles.DotfilesError, "did not produce"):
                dotfiles.deploy_rime(
                    result,
                    home=home,
                    run=lambda argv, **kwargs: subprocess.CompletedProcess(argv, 0),
                )


if __name__ == "__main__":
    unittest.main()
