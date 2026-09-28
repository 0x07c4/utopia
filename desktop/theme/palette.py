"""Pure color policy for the experimental Utopia palette evaluator."""

from __future__ import annotations

from dataclasses import dataclass
import colorsys
from itertools import combinations
from pathlib import Path
import tomllib
from typing import Mapping, Sequence


RGB = tuple[int, int, int]
Histogram = Sequence[tuple[int, str]]


@dataclass(frozen=True)
class Candidate:
    color: str
    population: int
    share: float
    hue: float
    saturation: float
    lightness: float


def parse_hex(value: str) -> RGB:
    if len(value) != 7 or not value.startswith("#"):
        raise ValueError(f"expected #RRGGBB color, got {value!r}")
    try:
        return tuple(int(value[index : index + 2], 16) for index in (1, 3, 5))  # type: ignore[return-value]
    except ValueError as error:
        raise ValueError(f"expected #RRGGBB color, got {value!r}") from error


def to_hex(color: RGB) -> str:
    return "#" + "".join(f"{channel:02x}" for channel in color)


def _linear(channel: int) -> float:
    value = channel / 255.0
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(color: str) -> float:
    red, green, blue = parse_hex(color)
    return 0.2126 * _linear(red) + 0.7152 * _linear(green) + 0.0722 * _linear(blue)


def contrast_ratio(first: str, second: str) -> float:
    lighter, darker = sorted(
        (relative_luminance(first), relative_luminance(second)), reverse=True
    )
    return (lighter + 0.05) / (darker + 0.05)


def _hsl(color: str) -> tuple[float, float, float]:
    red, green, blue = (channel / 255.0 for channel in parse_hex(color))
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    return hue * 360.0, saturation, lightness


def hue_distance(first: float, second: float) -> float:
    difference = abs(first - second) % 360.0
    return min(difference, 360.0 - difference)


def _ensure_contrast(color: str, background: str, minimum: float) -> str:
    if contrast_ratio(color, background) >= minimum:
        return color.lower()

    red, green, blue = (channel / 255.0 for channel in parse_hex(color))
    hue, lightness, saturation = colorsys.rgb_to_hls(red, green, blue)
    options: list[tuple[float, str]] = []
    for step in range(201):
        candidate_lightness = step / 200.0
        candidate_rgb = colorsys.hls_to_rgb(hue, candidate_lightness, saturation)
        candidate = to_hex(
            tuple(round(channel * 255) for channel in candidate_rgb)  # type: ignore[arg-type]
        )
        if contrast_ratio(candidate, background) >= minimum:
            options.append((abs(candidate_lightness - lightness), candidate))
    if not options:
        raise ValueError(f"cannot satisfy contrast {minimum} for {color} on {background}")
    return min(options, key=lambda item: (item[0], item[1]))[1]


def _blend(foreground: str, background: str, amount: float) -> str:
    front = parse_hex(foreground)
    back = parse_hex(background)
    return to_hex(
        tuple(
            round(front[index] * amount + back[index] * (1.0 - amount))
            for index in range(3)
        )  # type: ignore[arg-type]
    )


def _on_color(background: str) -> str:
    dark = "#000000"
    light = "#ffffff"
    return max((dark, light), key=lambda color: contrast_ratio(color, background))


def load_policy(path: Path) -> dict[str, object]:
    with path.open("rb") as source:
        policy = tomllib.load(source)
    if policy.get("schema_version") != 1:
        raise ValueError("theme policy schema_version must be 1")
    for section in ("policy", "stable", "fallback"):
        if not isinstance(policy.get(section), dict):
            raise ValueError(f"theme policy is missing [{section}]")
    stable = policy["stable"]
    fallback = policy["fallback"]
    assert isinstance(stable, dict)
    assert isinstance(fallback, dict)
    for name, value in {**stable, **fallback}.items():
        if not isinstance(value, str):
            raise ValueError(f"theme color {name} must be a string")
        parse_hex(value)
    return policy


def rank_candidates(
    histogram: Histogram, settings: Mapping[str, object]
) -> list[Candidate]:
    total = sum(population for population, _ in histogram)
    if total <= 0:
        return []

    minimum_population = float(settings["minimum_population"])
    minimum_saturation = float(settings["minimum_saturation"])
    minimum_lightness = float(settings["minimum_lightness"])
    maximum_lightness = float(settings["maximum_lightness"])
    candidates: list[Candidate] = []
    for population, color in histogram:
        hue, saturation, lightness = _hsl(color)
        share = population / total
        if share < minimum_population:
            continue
        if saturation < minimum_saturation:
            continue
        if not minimum_lightness <= lightness <= maximum_lightness:
            continue
        candidates.append(
            Candidate(
                color=color.lower(),
                population=population,
                share=share,
                hue=hue,
                saturation=saturation,
                lightness=lightness,
            )
        )
    return sorted(
        candidates,
        key=lambda item: (item.share * (0.5 + item.saturation), item.population),
        reverse=True,
    )


def select_accents(
    histogram: Histogram, policy: Mapping[str, object]
) -> tuple[list[str], list[Candidate]]:
    settings = policy["policy"]
    stable = policy["stable"]
    fallback = policy["fallback"]
    assert isinstance(settings, dict)
    assert isinstance(stable, dict)
    assert isinstance(fallback, dict)

    ranked = rank_candidates(histogram, settings)
    minimum_distance = float(settings["minimum_hue_distance"])
    surface = str(stable["surface"])
    minimum_contrast = float(settings["minimum_accent_contrast"])

    options: list[tuple[str, float, bool, int]] = []
    for index, candidate in enumerate(ranked):
        options.append((candidate.color, candidate.hue, True, len(ranked) - index))
    for name in ("primary", "secondary", "tertiary"):
        color = str(fallback[name])
        hue, _, _ = _hsl(color)
        options.append((color, hue, False, 0))

    valid: list[tuple[tuple[int, int, int], tuple[tuple[str, float, bool, int], ...]]] = []
    for indexes, group in zip(combinations(range(len(options)), 3), combinations(options, 3)):
        hues = [item[1] for item in group]
        if any(
            hue_distance(first, second) < minimum_distance
            for position, first in enumerate(hues)
            for second in hues[position + 1 :]
        ):
            continue
        dynamic_count = sum(1 for item in group if item[2])
        candidate_priority = sum(item[3] for item in group)
        valid.append(((dynamic_count, candidate_priority, -sum(indexes)), group))

    if not valid:
        raise ValueError("theme policy cannot produce three hue-separated accents")
    _, chosen = max(valid, key=lambda item: item[0])
    selected = [
        _ensure_contrast(color, surface, minimum_contrast)
        for color, _, _, _ in chosen
    ]
    return selected, ranked


def controlled_palette(
    baseline: Mapping[str, str], histogram: Histogram, policy: Mapping[str, object]
) -> tuple[dict[str, str], dict[str, object]]:
    settings = policy["policy"]
    stable = policy["stable"]
    assert isinstance(settings, dict)
    assert isinstance(stable, dict)
    selected, ranked = select_accents(histogram, policy)
    primary, secondary, tertiary = selected
    surface = str(stable["surface"])
    surface_variant = str(stable["surface_variant"])
    on_surface = str(stable["on_surface"])
    on_surface_variant = str(stable["on_surface_variant"])
    outline = str(stable["outline"])
    error = str(stable["error"])
    warning = str(stable["warning"])
    success = str(stable["success"])

    result = dict(baseline)
    result.update(
        {
            "source_color": primary,
            "primary": primary,
            "on_primary": _on_color(primary),
            "primary_container": _blend(primary, surface, 0.28),
            "on_primary_container": on_surface,
            "surface_tint": primary,
            "secondary": secondary,
            "on_secondary": _on_color(secondary),
            "secondary_container": _blend(secondary, surface, 0.28),
            "on_secondary_container": on_surface,
            "tertiary": tertiary,
            "on_tertiary": _on_color(tertiary),
            "tertiary_container": _blend(tertiary, surface, 0.28),
            "on_tertiary_container": on_surface,
            "error": error,
            "on_error": _on_color(error),
            "error_container": _blend(error, surface, 0.24),
            "on_error_container": on_surface,
            "surface": surface,
            "background": surface,
            "surface_dim": surface,
            "surface_variant": surface_variant,
            "surface_container_lowest": "#101219",
            "surface_container_low": str(stable["surface_container"]),
            "surface_container": str(stable["surface_container"]),
            "surface_container_high": str(stable["surface_container_high"]),
            "surface_container_highest": surface_variant,
            "surface_bright": str(stable["surface_container_high"]),
            "on_surface": on_surface,
            "on_background": on_surface,
            "on_surface_variant": on_surface_variant,
            "outline": outline,
            "outline_variant": surface_variant,
            "terminal_foreground": on_surface,
            "terminal_background": surface,
            "terminal_cursor": on_surface,
            "terminal_cursor_text": surface,
            "terminal_selection_fg": on_surface,
            "terminal_selection_bg": surface_variant,
            "terminal_normal_black": surface_variant,
            "terminal_normal_red": error,
            "terminal_normal_green": success,
            "terminal_normal_yellow": warning,
            "terminal_normal_blue": primary,
            "terminal_normal_magenta": tertiary,
            "terminal_normal_cyan": secondary,
            "terminal_normal_white": on_surface_variant,
            "terminal_bright_black": outline,
            "terminal_bright_red": error,
            "terminal_bright_green": success,
            "terminal_bright_yellow": warning,
            "terminal_bright_blue": primary,
            "terminal_bright_magenta": tertiary,
            "terminal_bright_cyan": secondary,
            "terminal_bright_white": on_surface,
        }
    )

    minimum_accent_contrast = float(settings["minimum_accent_contrast"])
    metrics = {
        "selected_accents": selected,
        "candidate_count": len(ranked),
        "accent_contrast": {
            name: round(contrast_ratio(color, surface), 3)
            for name, color in zip(("primary", "secondary", "tertiary"), selected)
        },
        "text_contrast": round(contrast_ratio(on_surface, surface), 3),
        "minimum_accent_contrast": minimum_accent_contrast,
    }
    return result, metrics
