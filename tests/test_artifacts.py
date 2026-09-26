import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import tomllib
import unittest

from utopia import artifacts, profiles, workstation


class ArtifactResolutionTest(unittest.TestCase):
    def test_desktop_resolves_shared_domains_and_thin_host_overlay(self) -> None:
        result = workstation.resolve(profiles.REPO_ROOT, "cachyos-desktop")
        by_id = {artifact["id"]: artifact for artifact in result["artifacts"]}

        self.assertIn("shell.zshrc", by_id)
        self.assertIn("terminal.kitty", by_id)
        self.assertIn("desktop.niri", by_id)
        self.assertIn("desktop.niri-display-cachyos-desktop", by_id)
        self.assertNotIn("desktop.niri-display-arch-laptop", by_id)
        self.assertEqual(
            by_id["desktop.niri-display-cachyos-desktop"]["destination"],
            ".config/niri/cfg/display.kdl",
        )
        self.assertNotIn(
            "themes/frappe.conf", by_id["terminal.kitty"]["excludes"]
        )
        kitty_config = (profiles.REPO_ROOT / "terminal/kitty/kitty.conf").read_text()
        self.assertIn("include themes/frappe.conf", kitty_config)
        self.assertIn("globinclude themes/noctalia.conf", kitty_config)
        self.assertFalse(
            any("wezterm" in item["source"] for item in result["artifacts"])
        )
        json.dumps(result)

    def test_laptop_selects_only_its_display_overlay(self) -> None:
        result = workstation.resolve(profiles.REPO_ROOT, "arch-laptop")
        identifiers = {artifact["id"] for artifact in result["artifacts"]}

        self.assertIn("desktop.niri", identifiers)
        self.assertIn("desktop.niri-display-arch-laptop", identifiers)
        self.assertNotIn("desktop.niri-display-cachyos-desktop", identifiers)

    def test_shell_artifacts_are_owned_by_the_shell_domain(self) -> None:
        result = workstation.resolve(profiles.REPO_ROOT, "arch-laptop")
        shell_artifacts = [
            artifact
            for artifact in result["artifacts"]
            if artifact["domain"] == "shell"
        ]

        self.assertEqual(len(shell_artifacts), 3)
        self.assertEqual(
            {artifact["source"] for artifact in shell_artifacts},
            {
                "shell/zsh/zshrc",
                "shell/zsh/zimrc",
                "shell/starship/starship.toml",
            },
        )
        self.assertTrue(
            all(artifact["source"].startswith("shell/") for artifact in shell_artifacts)
        )

    def test_eza_icons_option_cannot_consume_the_ls_path(self) -> None:
        zshrc = (profiles.REPO_ROOT / "shell/zsh/zshrc").read_text()

        self.assertIn('eza --icons=auto "$@"', zshrc)
        self.assertNotIn('eza --icons "$@"', zshrc)

    def test_terminal_artifact_is_owned_by_the_terminal_domain(self) -> None:
        result = workstation.resolve(profiles.REPO_ROOT, "arch-laptop")
        terminal = next(
            artifact
            for artifact in result["artifacts"]
            if artifact["id"] == "terminal.kitty"
        )

        self.assertEqual(terminal["source"], "terminal/kitty")
        self.assertEqual(terminal["destination"], ".config/kitty")
        self.assertEqual(
            terminal["excludes"],
            ["kitty.conf.bak", "themes/noctalia.conf"],
        )
        backup = profiles.REPO_ROOT / "terminal/kitty/kitty.conf.bak"
        self.assertFalse(backup.exists())

    def test_noctalia_theme_has_exact_core_adapters_and_fallbacks(self) -> None:
        visuals = profiles.REPO_ROOT / ".config/noctalia/visuals.toml"
        with visuals.open("rb") as source:
            config = tomllib.load(source)

        self.assertEqual(config["theme"]["source"], "wallpaper")
        templates = config["theme"]["templates"]
        self.assertEqual(templates["builtin_ids"], ["starship"])
        self.assertFalse(templates["enable_community_templates"])
        self.assertEqual(
            set(templates["user"]), {"utopia-kitty", "utopia-niri"}
        )
        for template in templates["user"].values():
            path = template["input_path"]
            self.assertTrue(
                (profiles.REPO_ROOT / ".config/noctalia" / path).is_file()
            )

        plan = workstation.resolve(profiles.REPO_ROOT, "arch-laptop")
        niri = next(
            artifact
            for artifact in plan["artifacts"]
            if artifact["id"] == "desktop.niri"
        )
        self.assertIn("noctalia.kdl", niri["excludes"])
        niri_config = (profiles.REPO_ROOT / "desktop/niri/config.kdl").read_text()
        self.assertIn('include optional=true "./noctalia.kdl"', niri_config)

        starship = next(
            artifact
            for artifact in plan["artifacts"]
            if artifact["id"] == "shell.starship"
        )
        self.assertEqual(len(starship["generated_blocks"]), 1)
        starship_config = (
            profiles.REPO_ROOT / "shell/starship/starship.toml"
        ).read_text()
        self.assertEqual(
            starship_config.splitlines()[:2],
            [
                '"$schema" = "https://starship.rs/config-schema.json"',
                'palette = "noctalia"',
            ],
        )

    def test_input_artifacts_are_owned_by_the_input_domain(self) -> None:
        result = workstation.resolve(profiles.REPO_ROOT, "arch-laptop")
        input_artifacts = [
            artifact
            for artifact in result["artifacts"]
            if artifact["domain"] == "input"
        ]

        self.assertEqual(len(input_artifacts), 6)
        self.assertTrue(
            all(artifact["source"].startswith("input/") for artifact in input_artifacts)
        )
        self.assertEqual(
            next(
                artifact["source"]
                for artifact in input_artifacts
                if artifact["id"] == "input.fcitx5"
            ),
            "input/fcitx5/config",
        )
        self.assertNotIn(
            "input.fcitx5-theme",
            {artifact["id"] for artifact in input_artifacts},
        )
        classicui = (
            profiles.REPO_ROOT / "input/fcitx5/config/conf/classicui.conf"
        ).read_text()
        self.assertIn("Theme=default\n", classicui)
        self.assertIn("DarkTheme=default-dark\n", classicui)
        self.assertNotIn("catppuccin-mocha-green", classicui)
        self.assertFalse((profiles.REPO_ROOT / "input/fcitx5/themes").exists())

    def test_editor_gitlink_is_owned_by_the_editor_domain(self) -> None:
        result = workstation.resolve(profiles.REPO_ROOT, "arch-laptop")
        editor = next(
            artifact
            for artifact in result["artifacts"]
            if artifact["id"] == "editor.nvim"
        )

        self.assertEqual(editor["source"], "editor/nvim")
        self.assertEqual(editor["destination"], ".config/nvim")
        self.assertEqual(editor["kind"], "gitlink")

    def test_development_has_only_reviewed_nonempty_artifacts(self) -> None:
        result = workstation.resolve(profiles.REPO_ROOT, "arch-laptop")
        development = [
            artifact
            for artifact in result["artifacts"]
            if artifact["domain"] == "development"
        ]

        self.assertEqual(
            {artifact["id"] for artifact in development},
            {"development.ssh-client"},
        )
        ssh = development[0]
        self.assertEqual(ssh["source"], "development/ssh/config")
        self.assertEqual(ssh["destination"], ".ssh/config")
        self.assertEqual(ssh["mode"], "0600")
        self.assertGreater((profiles.REPO_ROOT / ssh["source"]).stat().st_size, 0)

    def test_host_display_artifact_matches_profile_facts(self) -> None:
        for profile_id in ("arch-laptop", "cachyos-desktop"):
            with self.subTest(profile=profile_id):
                result = workstation.resolve(profiles.REPO_ROOT, profile_id)
                display = result["values"]["display"]
                artifact = next(
                    item
                    for item in result["artifacts"]
                    if item["id"].startswith("desktop.niri-display-")
                )
                content = (profiles.REPO_ROOT / artifact["source"]).read_text()
                connector = re.search(r'^output "([^"]+)"', content, re.MULTILINE)
                mode = re.search(r'^\s+mode "([^"]+)"', content, re.MULTILINE)
                scale = re.search(r"^\s+scale ([0-9.]+)", content, re.MULTILINE)

                self.assertIsNotNone(connector)
                self.assertIsNotNone(mode)
                self.assertIsNotNone(scale)
                self.assertEqual(connector.group(1), display["connector"])
                self.assertEqual(mode.group(1), display["mode"])
                self.assertEqual(float(scale.group(1)), display["scale"])

    def _write_repo(self, root: Path, catalog: str) -> None:
        layers = root / "profiles/layers/test"
        layers.mkdir(parents=True)
        (layers / "workstation.toml").write_text(
            """schema_version = 1
[layer]
id = "workstation.test"
kind = "workstation"
description = "test"
overrides = []
[values.test]
enabled = true
"""
        )
        (root / "profiles/artifacts.toml").write_text(catalog)

    @staticmethod
    def _entry(
        identifier: str, source: str, destination: str, *, extra: str = ""
    ) -> str:
        return f"""
[[artifacts]]
id = "{identifier}"
layer = "workstation.test"
domain = "test"
source = "{source}"
destination = "{destination}"
kind = "file"
state = "managed"
capture = true
deploy = true
validators = []
{extra}
"""

    def test_sensitive_destination_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "source").write_text("secret")
            self._write_repo(
                root,
                "schema_version = 1\n"
                + self._entry("test.secret", "source", ".ssh/id_ed25519"),
            )

            with self.assertRaisesRegex(
                artifacts.ArtifactError, "forbidden destination"
            ):
                artifacts.resolve_artifacts(root, ["workstation.test"])

    def test_source_must_not_escape_repository(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_repo(
                root,
                "schema_version = 1\n"
                + self._entry("test.escape", "../outside", ".config/test"),
            )

            with self.assertRaisesRegex(
                artifacts.ArtifactError, "normalized relative POSIX path"
            ):
                artifacts.resolve_artifacts(root, ["workstation.test"])

    def test_tree_cannot_hide_a_sensitive_destination(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source/gh"
            source.mkdir(parents=True)
            (source / "hosts.yml").write_text("token")
            catalog = """schema_version = 1
[[artifacts]]
id = "test.tree"
layer = "workstation.test"
domain = "test"
source = "source"
destination = ".config"
kind = "tree"
state = "managed"
capture = true
deploy = true
validators = []
"""
            self._write_repo(root, catalog)

            with self.assertRaisesRegex(
                artifacts.ArtifactError, "contains forbidden destination"
            ):
                artifacts.resolve_artifacts(root, ["workstation.test"])

    def test_destination_collision_requires_exact_replacement(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "first").write_text("first")
            (root / "second").write_text("second")
            catalog = (
                "schema_version = 1\n"
                + self._entry("test.first", "first", ".config/test")
                + self._entry("test.second", "second", ".config/test")
            )
            self._write_repo(root, catalog)

            with self.assertRaisesRegex(
                artifacts.ArtifactError, "declare the exact replacement"
            ):
                artifacts.resolve_artifacts(root, ["workstation.test"])

    def test_exact_replacement_removes_previous_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "first").write_text("first")
            (root / "second").write_text("second")
            catalog = (
                "schema_version = 1\n"
                + self._entry("test.first", "first", ".config/test")
                + self._entry(
                    "test.second",
                    "second",
                    ".config/test",
                    extra='replaces = "test.first"',
                )
            )
            self._write_repo(root, catalog)

            resolved, _ = artifacts.resolve_artifacts(root, ["workstation.test"])

            self.assertEqual([item["id"] for item in resolved], ["test.second"])

    def test_file_cannot_also_be_a_parent_directory(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / "first").write_text("first")
            (root / "second").write_text("second")
            catalog = (
                "schema_version = 1\n"
                + self._entry("test.first", "first", ".config/tool")
                + self._entry("test.second", "second", ".config/tool/config.toml")
            )
            self._write_repo(root, catalog)

            with self.assertRaisesRegex(
                artifacts.ArtifactError, "declare the exact replacement"
            ):
                artifacts.resolve_artifacts(root, ["workstation.test"])

    def test_uninitialized_registered_gitlink_can_be_planned(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            editor = root / "editor"
            editor.mkdir()
            subprocess.run(["git", "init", "-q", root], check=True)
            subprocess.run(["git", "init", "-q", editor], check=True)
            (editor / "init.lua").write_text("return {}\n")
            subprocess.run(["git", "-C", editor, "add", "init.lua"], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    editor,
                    "-c",
                    "user.name=Utopia Test",
                    "-c",
                    "user.email=utopia@example.invalid",
                    "commit",
                    "-qm",
                    "fixture",
                ],
                check=True,
            )
            commit = subprocess.run(
                ["git", "-C", editor, "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                [
                    "git",
                    "-C",
                    root,
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"160000,{commit},editor",
                ],
                check=True,
            )
            shutil.rmtree(editor)
            catalog = """schema_version = 1
[[artifacts]]
id = "test.editor"
layer = "workstation.test"
domain = "editor"
source = "editor"
destination = ".config/editor"
kind = "gitlink"
state = "managed"
capture = true
deploy = true
validators = []
"""
            self._write_repo(root, catalog)

            resolved, _ = artifacts.resolve_artifacts(
                root, ["workstation.test"]
            )

            self.assertEqual(resolved[0]["id"], "test.editor")

    def test_schema_document_is_valid_json(self) -> None:
        schema = json.loads(
            (profiles.REPO_ROOT / "schemas/artifacts.schema.json").read_text()
        )
        self.assertEqual(
            schema["$schema"], "https://json-schema.org/draft/2020-12/schema"
        )


if __name__ == "__main__":
    unittest.main()
