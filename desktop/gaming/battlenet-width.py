#!/usr/bin/env python3
"""Desktop opt-in: three distinct valid Battle.net widths; native elsewhere."""
import argparse
import json
import subprocess


def width_target(current, output_width, direction):
    minimum = 1000
    estimates = [minimum, output_width * 2 / 3, output_width]
    commands = [str(minimum), "66.667%", "100%"]
    # Niri subtracts gaps when resolving percentages. Recognize its resolved
    # widths, but let Niri calculate them rather than hard-coding screen gaps.
    index = min(range(3), key=lambda i: abs(current - estimates[i]))
    if abs(current - minimum) <= 1:
        index = 0
    elif abs(current - estimates[index]) > output_width * .025:
        if direction == "forward":
            return next((commands[i] for i in range(3) if estimates[i] > current), commands[0])
        return next((commands[i] for i in reversed(range(3)) if estimates[i] < current), commands[-1])
    return commands[(index + (1 if direction == "forward" else -1)) % 3]


def query(kind):
    result = subprocess.run(["niri", "msg", "--json", kind], capture_output=True,
                            text=True, check=True, timeout=3)
    return json.loads(result.stdout)


def action(direction):
    native = "switch-preset-column-width" + ("-back" if direction == "back" else "")
    try:
        focused = next((w for w in query("windows") if w["is_focused"]), None)
        if not focused or focused.get("app_id") != "battle.net.exe" or focused.get("title") != "战网":
            return [native]
        if focused["is_floating"]:
            return [native]
        output = next(w["output"] for w in query("workspaces") if w["id"] == focused["workspace_id"])
        logical = query("outputs")[output]["logical"]
        if logical["scale"] != 2 or logical["width"] < 1600:
            return [native]  # Other display/DPI scopes need a separate review.
        target = width_target(focused["layout"]["window_size"][0], logical["width"], direction)
        return ["set-window-width", "--id", str(focused["id"]), target]
    except (OSError, ValueError, TypeError, KeyError, StopIteration, subprocess.SubprocessError):
        return [native]


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("direction", choices=("forward", "back"))
    args = parser.parse_args()
    raise SystemExit(subprocess.run(["niri", "msg", "action", *action(args.direction)], timeout=3).returncode)
