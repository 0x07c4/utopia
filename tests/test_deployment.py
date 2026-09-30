import json
import tempfile
import unittest
from pathlib import Path

from utopia import deployment, profiles


class DeploymentPlanTest(unittest.TestCase):
    def test_fcitx_plan_is_host_scoped_and_ordered(self) -> None:
        result = deployment.resolve(
            profiles.REPO_ROOT, "cachyos-desktop", "fcitx-wallpaper-theme"
        )

        self.assertEqual(result["state"], "experimental")
        self.assertEqual(result["activation"], "enabled")
        self.assertEqual(
            result["provenance"]["profile_state"]["layer"],
            "host.cachyos-desktop",
        )
        self.assertTrue(result["safety"]["dry_run"])
        self.assertFalse(result["safety"]["writes_home"])
        self.assertTrue(result["safety"]["requires_confirmation"])
        self.assertEqual(
            [stage["id"] for stage in result["stages"]],
            [
                "backup-live-state",
                "render-dynamic-theme",
                "validate-generated-assets",
                "switch-classicui-theme",
                "reload-classicui",
            ],
        )
        self.assertEqual(
            result["stages"][1]["hook"],
            ".config/noctalia/templates/utopia/fcitx5/apply.sh",
        )
        self.assertEqual(
            result["stages"][2]["directory"],
            ".local/share/fcitx5/themes/utopia-wallpaper",
        )
        self.assertEqual(
            result["stages"][3]["from"], "catppuccin-mocha-green"
        )
        self.assertEqual(result["stages"][3]["to"], "utopia-wallpaper")
        self.assertEqual(
            result["rollback"]["steps"][0]["destination"],
            ".config/fcitx5/conf/classicui.conf",
        )
        self.assertEqual(
            result["rollback"]["steps"][1]["paths"],
            [".local/share/fcitx5/themes/utopia-wallpaper"],
        )
        self.assertEqual(
            result["provenance"]["required_artifacts"][0]["id"],
            "desktop.noctalia",
        )
        encoded = json.dumps(result)
        self.assertNotIn(str(Path.home()), encoded)

    def test_laptop_and_desktop_have_explicit_feature_provenance(self) -> None:
        for profile_id, layer_id in (
            ("arch-laptop", "host.arch-laptop"),
            ("cachyos-desktop", "host.cachyos-desktop"),
        ):
            result = deployment.resolve(
                profiles.REPO_ROOT, profile_id, "fcitx-wallpaper-theme"
            )
            self.assertEqual(result["state"], "experimental")
            self.assertEqual(
                result["provenance"]["profile_state"]["layer"], layer_id
            )

    def test_plan_has_no_home_side_effects(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            before = sorted(Path(temporary).iterdir())
            deployment.resolve(
                profiles.REPO_ROOT, "cachyos-desktop", "fcitx-wallpaper-theme"
            )
            self.assertEqual(before, sorted(Path(temporary).iterdir()))

    def test_unknown_feature_is_rejected(self) -> None:
        with self.assertRaisesRegex(
            deployment.DeploymentError, "unknown deployment feature"
        ):
            deployment.resolve(
                profiles.REPO_ROOT, "cachyos-desktop", "missing-feature"
            )


if __name__ == "__main__":
    unittest.main()
