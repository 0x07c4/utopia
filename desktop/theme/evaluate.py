"""Render an offline comparison of Noctalia and Utopia palette policies."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
from html import escape
import json
from pathlib import Path
import re
import shutil
import subprocess
from typing import Mapping, Sequence

from .palette import controlled_palette, load_policy, rank_candidates


THEME_ROOT = Path(__file__).resolve().parent
DEFAULT_POLICY = THEME_ROOT / "policy-v1.toml"
FIXTURES = THEME_ROOT / "fixtures"
NOCTALIA_DEFAULT_WALLPAPER = Path(
    "/usr/share/noctalia/assets/noctalia-wallpaper.png"
)
SCHEMES = ("m3-content", "vibrant")
DISPLAY_ROLES = (
    "surface",
    "surface_variant",
    "on_surface",
    "primary",
    "secondary",
    "tertiary",
    "error",
    "terminal_normal_green",
    "terminal_normal_yellow",
)
HISTOGRAM_LINE = re.compile(r"^\s*(\d+):.*#([0-9A-Fa-f]{6})(?:[0-9A-Fa-f]{2})?\b")


class EvaluationError(RuntimeError):
    """Raised when an external offline evaluator cannot produce a result."""


def fixture_sources(
    include_noctalia_default: bool,
    selected_wallpaper: Path | None = None,
) -> list[tuple[str, Path, str]]:
    fixtures = [
        (source.stem, source, f"desktop/theme/fixtures/{source.name}")
        for source in sorted(FIXTURES.glob("*.svg"))
    ]
    if include_noctalia_default:
        fixtures.append(
            (
                "noctalia-default",
                NOCTALIA_DEFAULT_WALLPAPER,
                "package:noctalia/assets/noctalia-wallpaper.png",
            )
        )
    if selected_wallpaper is not None:
        fixtures.append(
            (
                "selected-wallpaper",
                selected_wallpaper,
                "local:selected-wallpaper",
            )
        )
    return fixtures


def _run(command: Sequence[str]) -> str:
    try:
        result = subprocess.run(
            command,
            check=True,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as error:
        raise EvaluationError(f"required command is unavailable: {command[0]}") from error
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or error.stdout.strip() or "no diagnostic"
        raise EvaluationError(f"{command[0]} failed: {detail}") from error
    return result.stdout


def _rasterize(source: Path, destination: Path) -> None:
    _run(
        [
            "magick",
            str(source),
            "-background",
            "#171922",
            "-alpha",
            "remove",
            "-alpha",
            "off",
            "-resize",
            "640x360!",
            str(destination),
        ]
    )


def _histogram(image: Path, color_count: int) -> list[tuple[int, str]]:
    output = _run(
        [
            "magick",
            str(image),
            "-resize",
            "64x64!",
            "-colors",
            str(color_count),
            "-depth",
            "8",
            "-format",
            "%c",
            "histogram:info:-",
        ]
    )
    histogram: list[tuple[int, str]] = []
    for line in output.splitlines():
        match = HISTOGRAM_LINE.match(line)
        if match:
            histogram.append((int(match.group(1)), f"#{match.group(2).lower()}"))
    if not histogram:
        raise EvaluationError(f"ImageMagick returned no colors for {image.name}")
    return histogram


def _noctalia_palette(image: Path, scheme: str) -> dict[str, str]:
    output = _run(["noctalia", "theme", str(image), "--scheme", scheme, "--dark"])
    try:
        palette = json.loads(output)
    except json.JSONDecodeError as error:
        raise EvaluationError(f"Noctalia returned invalid JSON for {image.name}") from error
    if not isinstance(palette, dict) or not palette:
        raise EvaluationError(f"Noctalia returned an empty palette for {image.name}")
    if not all(isinstance(key, str) and isinstance(value, str) for key, value in palette.items()):
        raise EvaluationError(f"Noctalia returned unexpected tokens for {image.name}")
    return palette


def _swatches(palette: Mapping[str, str]) -> str:
    blocks = []
    for role in DISPLAY_ROLES:
        color = palette[role]
        blocks.append(
            '<div class="swatch">'
            f'<span style="background:{escape(color)}"></span>'
            f"<code>{escape(role)}<br>{escape(color)}</code>"
            "</div>"
        )
    return "".join(blocks)


def _component_mock(palette: Mapping[str, str], fixture_id: str) -> str:
    style = ";".join(
        [
            f"--surface:{palette['surface']}",
            f"--surface-variant:{palette['surface_variant']}",
            f"--surface-container:{palette['surface_container']}",
            f"--surface-high:{palette['surface_container_high']}",
            f"--text:{palette['on_surface']}",
            f"--muted:{palette['on_surface_variant']}",
            f"--primary:{palette['primary']}",
            f"--primary-container:{palette['primary_container']}",
            f"--secondary:{palette['secondary']}",
            f"--tertiary:{palette['tertiary']}",
            f"--error:{palette['error']}",
            f"--success:{palette['terminal_normal_green']}",
            f"--warning:{palette['terminal_normal_yellow']}",
            f"background-image:linear-gradient(#0e101755,#0e101777),url('fixtures/{fixture_id}.png')",
        ]
    )
    return (
        f'<div class="desktop-mock" style="{escape(style)}">'
        '<div class="bar"><div class="bar-start"><span class="launcher">U</span>'
        '<span>▧</span><span class="workspace active">1</span><span class="workspace">2</span>'
        '<span class="workspace">3</span></div><strong>09:41</strong>'
        '<div class="bar-end"><span>♪ Utopia</span><span>◉</span><span>Wi-Fi</span>'
        '<span>68%</span><span>⚙</span></div></div>'
        '<div class="desktop-body"><div class="kitty-window">'
        '<div class="kitty-title"><span>utopia — zsh</span><span>— □ ×</span></div>'
        '<div class="terminal"><div class="prompt-line">'
        '<span class="segment os"> Arch user </span>'
        '<span class="segment directory"> ~/utopia </span>'
        '<span class="segment git">  work/theme </span>'
        '<span class="segment language"> Python 3.14 </span>'
        '<span class="segment context"> Docker </span>'
        '<span class="segment time"> 09:41 </span></div>'
        '<div class="command">❯ python -m unittest discover -s tests</div>'
        '<div class="test-line">47 tests passed in 0.71s</div>'
        '<div class="command">❯ <span class="cursor"> </span></div></div></div>'
        '<div class="side-stack"><div class="panel-card"><strong>控制中心</strong>'
        '<div class="quick-row"><span class="quick active">网络</span>'
        '<span class="quick">蓝牙</span><span class="quick">夜览</span></div>'
        '<div class="slider"><span></span></div><small>音量 42%</small></div>'
        '<div class="notification"><strong>Utopia</strong><small>主题评估完成</small></div>'
        '</div></div><div class="palette-strip"><span>PRIMARY</span>'
        '<span>SECONDARY</span><span>TERTIARY</span><span>ERROR</span></div></div>'
    )


def _render_html(report: Mapping[str, object]) -> str:
    sections: list[str] = []
    fixtures = report["fixtures"]
    assert isinstance(fixtures, list)
    for fixture in fixtures:
        assert isinstance(fixture, dict)
        palettes = fixture["palettes"]
        assert isinstance(palettes, dict)
        panels = []
        for palette_id in (*SCHEMES, "controlled"):
            palette = palettes[palette_id]
            assert isinstance(palette, dict)
            panels.append(
                '<article class="palette">'
                f"<h3>{escape(palette_id)}</h3>"
                f"{_component_mock(palette, str(fixture['id']))}"
                f'<div class="swatches">{_swatches(palette)}</div>'
                "</article>"
            )
        metrics = fixture["controlled_metrics"]
        assert isinstance(metrics, dict)
        sections.append(
            "<section>"
            f"<h2>{escape(str(fixture['id']))}</h2>"
            '<div class="fixture-row">'
            f'<img src="fixtures/{escape(str(fixture["id"]))}.png" '
            f'alt="{escape(str(fixture["id"]))} wallpaper fixture">'
            '<div class="decision"><strong>Controlled selection</strong>'
            f"<code>{escape(', '.join(metrics['selected_accents']))}</code>"
            f"<small>{escape(str(metrics['candidate_count']))} suitable candidates; "
            f"text contrast {escape(str(metrics['text_contrast']))}:1</small></div></div>"
            f'<div class="palettes">{"".join(panels)}</div>'
            "</section>"
        )
    policy = report["policy"]
    generator = report["generator"]
    assert isinstance(policy, dict)
    assert isinstance(generator, dict)
    return f"""<!doctype html>
<html lang="en">
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Utopia dynamic palette review</title>
<style>
:root {{ color-scheme: dark; font-family: system-ui, sans-serif; background:#0e1017; color:#e7e9f2; }}
body {{ margin:0 auto; max-width:1600px; padding:32px; }}
h1 {{ margin-bottom:8px; }} h2 {{ margin-top:48px; }} h3 {{ margin:0 0 16px; }}
.meta {{ color:#aeb4c4; }}
.fixture-row {{ display:flex; gap:24px; align-items:center; margin:16px 0; }}
.fixture-row img {{ width:320px; aspect-ratio:16/9; object-fit:cover; border-radius:14px; }}
.decision {{ display:grid; gap:8px; }} .decision code {{ color:#d9a4ff; }}
.palettes {{ display:grid; grid-template-columns:repeat(3,minmax(0,1fr)); gap:18px; }}
.palette {{ background:#171922; border:1px solid #303442; border-radius:16px; padding:18px; min-width:0; }}
.desktop-mock {{ position:relative; aspect-ratio:16/10; overflow:hidden; border-radius:12px; color:var(--text); background-size:cover; background-position:center; box-shadow:inset 0 0 0 1px var(--surface-high); }}
.bar {{ height:30px; padding:0 9px; display:grid; grid-template-columns:1fr auto 1fr; align-items:center; gap:8px; background:color-mix(in srgb,var(--surface) 92%,transparent); backdrop-filter:blur(10px); font-size:9px; }}
.bar-start,.bar-end {{display:flex;align-items:center;gap:7px;white-space:nowrap}} .bar-end{{justify-content:flex-end}}
.launcher {{display:grid;place-items:center;width:18px;height:18px;border-radius:5px;background:var(--primary);color:#101219;font-weight:800}}
.workspace {{color:var(--muted)}} .workspace.active {{color:var(--surface);background:var(--secondary);padding:2px 6px;border-radius:5px}}
.desktop-body {{display:grid;grid-template-columns:minmax(0,2.35fr) minmax(105px,1fr);gap:12px;padding:20px 16px 16px;align-items:start}}
.kitty-window {{min-width:0;border:3px solid var(--primary);border-radius:10px;overflow:hidden;background:color-mix(in srgb,var(--surface) 92%,transparent);box-shadow:0 12px 28px #0008}}
.kitty-title {{display:flex;justify-content:space-between;padding:7px 10px;background:var(--surface-variant);font-size:9px;color:var(--muted)}}
.terminal {{min-height:120px;padding:12px 10px;font-family:"Maple Mono NF CN",ui-monospace,monospace;font-size:9px;line-height:1.9;overflow:hidden}}
.prompt-line {{display:flex;white-space:nowrap;overflow:hidden;color:#101219;margin-bottom:8px}}
.segment {{padding:1px 6px}} .segment.os{{background:var(--primary)}} .segment.directory{{background:var(--tertiary)}}
.segment.git{{background:var(--secondary)}} .segment.language{{background:var(--primary-container);color:var(--text)}}
.segment.context{{background:var(--surface-high);color:var(--text)}} .segment.time{{background:var(--surface-variant);color:var(--text)}}
.command {{color:var(--text);white-space:nowrap}} .test-line{{color:var(--success)}} .cursor{{display:inline-block;width:6px;height:11px;background:var(--text);vertical-align:middle}}
.side-stack {{display:grid;gap:10px}} .panel-card,.notification{{background:color-mix(in srgb,var(--surface) 94%,transparent);backdrop-filter:blur(10px);border:1px solid var(--surface-high);border-radius:10px;padding:10px;font-size:9px;box-shadow:0 8px 22px #0006}}
.panel-card{{display:grid;gap:9px}} .quick-row{{display:grid;grid-template-columns:repeat(3,1fr);gap:5px}} .quick{{padding:6px 3px;text-align:center;border-radius:6px;background:var(--surface-variant);color:var(--muted)}} .quick.active{{background:var(--primary);color:#101219}}
.slider{{height:5px;border-radius:9px;background:var(--surface-variant);overflow:hidden}} .slider span{{display:block;width:42%;height:100%;background:var(--tertiary)}}
.notification{{display:grid;gap:3px;border-left:3px solid var(--secondary)}} .notification small,.panel-card small{{color:var(--muted)}}
.palette-strip {{position:absolute;left:16px;right:16px;bottom:8px;display:grid;grid-template-columns:repeat(4,1fr);font-size:7px;text-align:center;overflow:hidden;border-radius:5px}}
.palette-strip span{{padding:4px;color:#101219}} .palette-strip span:nth-child(1){{background:var(--primary)}} .palette-strip span:nth-child(2){{background:var(--secondary)}} .palette-strip span:nth-child(3){{background:var(--tertiary)}} .palette-strip span:nth-child(4){{background:var(--error)}}
.swatches {{ display:grid; grid-template-columns:repeat(3,1fr); gap:9px; margin-top:14px; }}
.swatch {{ min-width:0; }} .swatch span {{ display:block; height:30px; border-radius:6px; }}
.swatch code {{ font-size:9px; color:#aeb4c4; overflow-wrap:anywhere; }}
@media (max-width:1100px) {{ .palettes {{grid-template-columns:1fr}} .fixture-row {{align-items:flex-start}} }}
</style>
<body>
<h1>Utopia dynamic palette review</h1>
<p class="meta">Policy {escape(str(policy['id']))} ({escape(str(policy['status']))});
generator {escape(str(generator['noctalia']))}. Layouts are identical across columns.</p>
{"".join(sections)}
</body></html>
"""


def _svg_text(x: int, y: int, text: str, *, size: int = 16, color: str = "#e7e9f2") -> str:
    return f'<text x="{x}" y="{y}" font-family="sans-serif" font-size="{size}" fill="{color}">{escape(text)}</text>'


def _render_svg(report: Mapping[str, object]) -> str:
    fixtures = report["fixtures"]
    assert isinstance(fixtures, list)
    width = 1500
    row_height = 340
    height = 100 + len(fixtures) * row_height
    output = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" fill="#0e1017"/>',
        _svg_text(40, 48, "Utopia dynamic palette review", size=28),
        _svg_text(40, 76, "Same component layout; Noctalia m3-content, vibrant, and controlled multi-accent.", size=14, color="#aeb4c4"),
    ]
    for row, fixture in enumerate(fixtures):
        assert isinstance(fixture, dict)
        palettes = fixture["palettes"]
        assert isinstance(palettes, dict)
        top = 100 + row * row_height
        output.append(_svg_text(40, top + 28, str(fixture["id"]), size=22))
        for column, palette_id in enumerate((*SCHEMES, "controlled")):
            palette = palettes[palette_id]
            assert isinstance(palette, dict)
            left = 40 + column * 480
            card_top = top + 48
            output.append(
                f'<rect x="{left}" y="{card_top}" width="440" height="255" rx="14" fill="{palette["surface"]}" stroke="{palette["outline"]}"/>'
            )
            output.append(_svg_text(left + 18, card_top + 30, palette_id, size=17, color=str(palette["on_surface"])))
            output.append(
                f'<rect x="{left + 18}" y="{card_top + 50}" width="404" height="102" rx="8" fill="{palette["surface_variant"]}" stroke="{palette["primary"]}" stroke-width="4"/>'
            )
            output.append(_svg_text(left + 35, card_top + 80, "Niri / Kitty / Starship", size=15, color=str(palette["on_surface"])))
            for index, role in enumerate(("primary", "secondary", "tertiary", "error")):
                x = left + 35 + index * 94
                color = str(palette[role])
                output.append(f'<rect x="{x}" y="{card_top + 101}" width="82" height="32" rx="4" fill="{color}"/>')
            for index, role in enumerate(("surface", "surface_variant", "on_surface", "primary", "secondary", "tertiary", "error")):
                x = left + 18 + index * 58
                color = str(palette[role])
                output.append(f'<rect x="{x}" y="{card_top + 174}" width="48" height="48" rx="5" fill="{color}"/>')
                output.append(_svg_text(x, card_top + 241, role.replace("surface_variant", "variant")[:8], size=9, color="#aeb4c4"))
        output.append(f'<line x1="40" y1="{top + 328}" x2="1460" y2="{top + 328}" stroke="#303442"/>')
    output.append("</svg>")
    return "".join(output)


def evaluate(
    output: Path,
    policy_path: Path = DEFAULT_POLICY,
    *,
    include_noctalia_default: bool = False,
    selected_wallpaper: Path | None = None,
) -> dict[str, object]:
    if output.exists():
        raise EvaluationError(f"output path already exists: {output}")
    if shutil.which("magick") is None:
        raise EvaluationError("ImageMagick 'magick' is required")
    if shutil.which("noctalia") is None:
        raise EvaluationError("Noctalia CLI is required")

    policy = load_policy(policy_path)
    settings = policy["policy"]
    assert isinstance(settings, dict)
    output.mkdir(parents=True)
    rendered_fixtures = output / "fixtures"
    rendered_fixtures.mkdir()

    version = _run(["noctalia", "--version"]).strip()
    fixture_reports: list[dict[str, object]] = []
    for fixture_id, source, source_label in fixture_sources(
        include_noctalia_default,
        selected_wallpaper,
    ):
        if not source.is_file():
            raise EvaluationError(f"wallpaper fixture is unavailable: {source_label}")
        raster = rendered_fixtures / f"{fixture_id}.png"
        _rasterize(source, raster)
        histogram = _histogram(raster, int(settings["candidate_colors"]))
        palettes = {
            scheme: _noctalia_palette(raster, scheme) for scheme in SCHEMES
        }
        controlled, metrics = controlled_palette(
            palettes["m3-content"], histogram, policy
        )
        ranked = rank_candidates(histogram, settings)
        palettes["controlled"] = controlled
        fixture_report: dict[str, object] = {
            "id": fixture_id,
            "source": source_label,
            "histogram": [
                {"population": population, "color": color}
                for population, color in histogram
            ],
            "candidates": [asdict(candidate) for candidate in ranked],
            "controlled_metrics": metrics,
            "palettes": palettes,
        }
        if fixture_id == "noctalia-default":
            fixture_report["provenance"] = {
                "package": "noctalia",
                "version": version,
                "license": "MIT",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "distribution": "local-review-only",
            }
        elif fixture_id == "selected-wallpaper":
            fixture_report["provenance"] = {
                "kind": "active-host-wallpaper",
                "sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
                "distribution": "local-review-only",
            }
        fixture_reports.append(fixture_report)

    report: dict[str, object] = {
        "schema_version": 1,
        "policy": {
            "id": settings["id"],
            "status": settings["status"],
            "source": "desktop/theme/policy-v1.toml",
        },
        "generator": {"noctalia": version, "schemes": list(SCHEMES)},
        "fixtures": fixture_reports,
    }
    (output / "report.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (output / "comparison.html").write_text(
        _render_html(report), encoding="utf-8"
    )
    (output / "comparison.svg").write_text(
        _render_svg(report), encoding="utf-8"
    )
    return report


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Compare Noctalia schemes with Utopia's experimental palette policy."
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="new directory for untracked review output",
    )
    parser.add_argument(
        "--include-noctalia-default",
        action="store_true",
        help="also evaluate the installed Noctalia default wallpaper without vendoring it",
    )
    parser.add_argument(
        "--selected-wallpaper",
        type=Path,
        help="evaluate one local wallpaper without recording its path or copying it into Git",
    )
    arguments = parser.parse_args(argv)
    try:
        report = evaluate(
            arguments.output,
            include_noctalia_default=arguments.include_noctalia_default,
            selected_wallpaper=arguments.selected_wallpaper,
        )
    except (EvaluationError, ValueError) as error:
        parser.exit(2, f"error: {error}\n")
    print(
        f"Rendered {len(report['fixtures'])} fixture comparisons to {arguments.output}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
