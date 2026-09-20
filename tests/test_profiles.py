import json
from pathlib import Path
import tempfile
import unittest

from utopia import profiles


class ProfileResolutionTest(unittest.TestCase):
    def test_desktop_profile_resolves_with_provenance(self) -> None:
        result = profiles.resolve_profile(profiles.REPO_ROOT, "cachyos-desktop")

        self.assertEqual(result["values"]["system"]["distribution"], "cachyos")
        self.assertEqual(result["values"]["host"]["id"], "cachyos-desktop")
        self.assertEqual(result["values"]["display"]["connector"], "DP-3")
        self.assertEqual(result["values"]["workstation"]["terminal"], "kitty")
        self.assertIn("eza", result["values"]["packages"]["required"])
        self.assertIn("rime-ice-git", result["values"]["packages"]["required"])
        self.assertIn("wezterm", result["values"]["packages"]["disabled"])
        self.assertEqual(
            result["provenance"]["display.connector"]["layer"],
            "host.cachyos-desktop",
        )
        json.dumps(result)

    def test_laptop_profile_keeps_bore_lto_as_an_experiment(self) -> None:
        result = profiles.resolve_profile(profiles.REPO_ROOT, "arch-laptop")

        self.assertEqual(result["values"]["system"]["distribution"], "arch")
        self.assertEqual(result["values"]["display"]["connector"], "eDP-1")
        self.assertEqual(
            result["values"]["kernel"]["package"], "linux-cachyos-bore-lto"
        )
        self.assertEqual(
            result["provenance"]["kernel.package"]["kind"], "experiment"
        )

    def _write_repo(
        self,
        root: Path,
        *,
        second_overrides: str = "[]",
        second_value: str = 'terminal = "foot"',
    ) -> None:
        layers = root / "profiles/layers/test"
        layers.mkdir(parents=True)
        (root / "profiles/test.toml").write_text(
            """schema_version = 1
[profile]
id = "test"
description = "test profile"
layers = ["test.first", "test.second"]
"""
        )
        (layers / "first.toml").write_text(
            """schema_version = 1
[layer]
id = "test.first"
kind = "workstation"
description = "first"
overrides = []
[values.workstation]
terminal = "kitty"
"""
        )
        (layers / "second.toml").write_text(
            f"""schema_version = 1
[layer]
id = "test.second"
kind = "host"
description = "second"
overrides = {second_overrides}
[values.workstation]
{second_value}
"""
        )

    def test_override_requires_an_explicit_declaration(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_repo(root)
            with self.assertRaisesRegex(
                profiles.ProfileError, "without declaring it"
            ):
                profiles.resolve_profile(root, "test")

    def test_declared_override_changes_value_and_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_repo(root, second_overrides='["workstation.terminal"]')
            result = profiles.resolve_profile(root, "test")

        self.assertEqual(result["values"]["workstation"]["terminal"], "foot")
        self.assertEqual(
            result["provenance"]["workstation.terminal"]["layer"], "test.second"
        )

    def test_unused_override_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            self._write_repo(
                root,
                second_overrides='["workstation.shell"]',
                second_value='shell = "zsh"',
            )
            with self.assertRaisesRegex(profiles.ProfileError, "unused overrides"):
                profiles.resolve_profile(root, "test")

    def test_package_intents_must_be_disjoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            layers = root / "profiles/layers/test"
            layers.mkdir(parents=True)
            (root / "profiles/test.toml").write_text(
                """schema_version = 1
[profile]
id = "test"
description = "test profile"
layers = ["test.packages"]
"""
            )
            (layers / "packages.toml").write_text(
                """schema_version = 1
[layer]
id = "test.packages"
kind = "workstation"
description = "packages"
overrides = []
[values.packages]
required = ["kitty"]
optional = ["kitty"]
disabled = ["wezterm"]
"""
            )
            with self.assertRaisesRegex(profiles.ProfileError, "both required and optional"):
                profiles.resolve_profile(root, "test")

    def test_schema_documents_are_valid_json(self) -> None:
        for name in ("profile.schema.json", "layer.schema.json"):
            schema = json.loads((profiles.REPO_ROOT / "schemas" / name).read_text())
            self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")


if __name__ == "__main__":
    unittest.main()
