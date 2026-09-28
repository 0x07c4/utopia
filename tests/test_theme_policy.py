from pathlib import Path
import unittest

from desktop.theme.palette import (
    contrast_ratio,
    controlled_palette,
    hue_distance,
    load_policy,
    parse_hex,
    select_accents,
)
from desktop.theme.evaluate import SCHEMES, _component_mock, fixture_sources


REPO_ROOT = Path(__file__).resolve().parents[1]
POLICY_PATH = REPO_ROOT / "desktop/theme/policy-v1.toml"


class ThemePolicyTest(unittest.TestCase):
    def setUp(self) -> None:
        self.policy = load_policy(POLICY_PATH)

    def test_policy_is_explicitly_experimental_and_has_valid_colors(self) -> None:
        settings = self.policy["policy"]
        self.assertEqual(settings["id"], "utopia-controlled-dark-v1")
        self.assertEqual(settings["status"], "experimental")
        self.assertEqual(settings["minimum_saturation"], 0.20)
        for section in ("stable", "fallback"):
            for color in self.policy[section].values():
                self.assertEqual(len(parse_hex(color)), 3)

    def test_review_compares_distinct_noctalia_directions(self) -> None:
        self.assertEqual(SCHEMES, ("m3-content", "vibrant"))

    def test_packaged_wallpaper_fixture_has_public_provenance_label(self) -> None:
        fixture_id, _, source = fixture_sources(True)[-1]
        self.assertEqual(fixture_id, "noctalia-default")
        self.assertEqual(
            source, "package:noctalia/assets/noctalia-wallpaper.png"
        )
        self.assertFalse(source.startswith("/"))

    def test_selected_wallpaper_fixture_hides_its_local_path(self) -> None:
        local_path = Path("/private/example/liked-wallpaper.jpg")
        fixture_id, source_path, source = fixture_sources(
            False, selected_wallpaper=local_path
        )[-1]
        self.assertEqual(fixture_id, "selected-wallpaper")
        self.assertEqual(source_path, local_path)
        self.assertEqual(source, "local:selected-wallpaper")
        self.assertNotIn(str(local_path), source)

    def test_review_uses_one_complete_desktop_scene(self) -> None:
        roles = (
            "surface",
            "surface_variant",
            "surface_container",
            "surface_container_high",
            "on_surface",
            "on_surface_variant",
            "primary",
            "primary_container",
            "secondary",
            "tertiary",
            "error",
            "terminal_normal_green",
            "terminal_normal_yellow",
        )
        palette = {role: "#445566" for role in roles}
        rendered = _component_mock(palette, "review-fixture")
        for marker in (
            "desktop-mock",
            "kitty-window",
            "prompt-line",
            "Arch user",
            "work/theme",
            "Python 3.14",
            "Docker",
            "控制中心",
            "主题评估完成",
        ):
            self.assertIn(marker, rendered)
        self.assertIn("fixtures/review-fixture.png", rendered)

    def test_hue_distance_wraps_around_zero(self) -> None:
        self.assertEqual(hue_distance(350.0, 10.0), 20.0)
        self.assertEqual(hue_distance(30.0, 210.0), 180.0)

    def test_candidate_selection_rejects_near_duplicate_hues(self) -> None:
        histogram = [
            (500, "#527a3a"),
            (400, "#638b45"),
            (260, "#2c7b84"),
            (220, "#d18445"),
            (20, "#777777"),
        ]
        selected, _ = select_accents(histogram, self.policy)
        self.assertEqual(len(selected), 3)
        hues = []
        import colorsys

        for color in selected:
            red, green, blue = (channel / 255 for channel in parse_hex(color))
            hue, _, _ = colorsys.rgb_to_hls(red, green, blue)
            hues.append(hue * 360)
        minimum = float(self.policy["policy"]["minimum_hue_distance"])
        for index, first in enumerate(hues):
            for second in hues[index + 1 :]:
                self.assertGreaterEqual(hue_distance(first, second), minimum - 1.0)

    def test_grayscale_input_uses_versioned_fallback(self) -> None:
        selected, ranked = select_accents(
            [(700, "#303030"), (300, "#b0b0b0")], self.policy
        )
        self.assertEqual(ranked, [])
        self.assertEqual(
            selected,
            [
                self.policy["fallback"]["primary"],
                self.policy["fallback"]["secondary"],
                self.policy["fallback"]["tertiary"],
            ],
        )

    def test_candidate_layout_cannot_block_complete_fallback(self) -> None:
        selected, _ = select_accents(
            [
                (500, "#465ac4"),
                (350, "#3e978c"),
            ],
            self.policy,
        )
        self.assertEqual(len(selected), 3)

    def test_controlled_palette_preserves_surfaces_semantics_and_contrast(self) -> None:
        baseline = {
            "primary_fixed": "#ffffff",
            "primary_fixed_dim": "#eeeeee",
        }
        palette, metrics = controlled_palette(
            baseline,
            [(450, "#354f27"), (300, "#2f7278"), (250, "#b76742")],
            self.policy,
        )
        stable = self.policy["stable"]
        self.assertEqual(palette["surface"], stable["surface"])
        self.assertEqual(palette["error"], stable["error"])
        self.assertEqual(palette["terminal_normal_green"], stable["success"])
        self.assertEqual(palette["terminal_normal_yellow"], stable["warning"])
        self.assertGreaterEqual(metrics["text_contrast"], 7.0)
        minimum = self.policy["policy"]["minimum_accent_contrast"]
        for value in metrics["accent_contrast"].values():
            self.assertGreaterEqual(value, minimum)
        for role in ("primary", "secondary", "tertiary", "error"):
            self.assertGreaterEqual(
                contrast_ratio(palette[f"on_{role}"], palette[role]), 4.5
            )

    def test_wallpaper_fixtures_are_owned_static_svg_files(self) -> None:
        fixtures = sorted((REPO_ROOT / "desktop/theme/fixtures").glob("*.svg"))
        self.assertEqual(
            [fixture.stem for fixture in fixtures],
            ["cool-spectrum", "green-dominant", "warm-spectrum"],
        )
        for fixture in fixtures:
            content = fixture.read_text()
            self.assertIn("Utopia-owned synthetic wallpaper fixture", content)
            self.assertNotIn("<image", content)
            forbidden_root = "/" + "home" + "/"
            self.assertNotIn(forbidden_root, content)


if __name__ == "__main__":
    unittest.main()
