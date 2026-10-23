"""Read-only, bounded reader for the KDL subset used by Utopia's Niri tree.

Not a replacement for `niri validate`. Unknown syntax fails closed with no
partial binding list. No subprocesses, shell evaluation, or persistent cache.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import json
import os
from pathlib import Path
import re
import stat


class ConfigError(ValueError):
    pass


@dataclass
class Token:
    text: str
    kind: str = "word"


@dataclass
class Node:
    name: str
    args: list[str]
    props: dict[str, str]
    children: list["Node"]


def tokenize(text: str) -> list[Token]:
    result = []
    i = 0
    while i < len(text):
        if text.startswith("//", i):
            end = text.find("\n", i)
            i = len(text) if end < 0 else end
        elif text.startswith("/*", i):
            depth = 1
            i += 2
            while depth and i < len(text):
                if text.startswith("/*", i):
                    depth += 1
                    i += 2
                elif text.startswith("*/", i):
                    depth -= 1
                    i += 2
                else:
                    i += 1
            if depth:
                raise ConfigError("Unclosed block comment")
        elif text[i] in " \t\r":
            i += 1
        elif text[i] == "\\" and re.match(r"\\[ \t]*\r?\n", text[i:]):
            i += len(re.match(r"\\[ \t]*\r?\n", text[i:])[0])
        elif text.startswith("/-", i):
            result.append(Token("/-", "symbol"))
            i += 2
        elif text[i] in "{};=\n":
            result.append(Token(text[i], "symbol"))
            i += 1
        else:
            raw = re.match(r'(?:r(#{0,16})|(#{1,16}))"', text[i:])
            if raw:
                hashes = raw[1] if raw[1] is not None else raw[2]
                start = i + len(raw[0])
                end = text.find('"' + hashes, start)
                if end < 0:
                    raise ConfigError("Unclosed raw string")
                result.append(Token(text[start:end], "string"))
                i = end + 1 + len(hashes)
            elif text[i] == '"':
                try:
                    value, length = json.JSONDecoder().raw_decode(text[i:])
                except ValueError as exc:
                    raise ConfigError("Unsupported quoted string") from exc
                result.append(Token(value, "string"))
                i += length
            else:
                match = re.match(r'[^\s{};="()]+', text[i:])
                if not match:
                    raise ConfigError("Unsupported KDL syntax")
                result.append(Token(match[0]))
                i += len(match[0])
    return result


def parse(text: str) -> list[Node]:
    tokens = tokenize(text)
    i = 0

    def nodes(nested=False, depth=0):
        nonlocal i
        if depth > 32:
            raise ConfigError("KDL nesting limit exceeded")
        output = []
        while i < len(tokens):
            token = tokens[i]
            if token.kind == "symbol" and token.text in ("\n", ";"):
                i += 1
                continue
            if token.kind == "symbol" and token.text == "}":
                if not nested:
                    raise ConfigError("Unexpected closing brace")
                i += 1
                return output
            disabled = token.kind == "symbol" and token.text == "/-"
            if disabled:
                i += 1
                if i == len(tokens):
                    raise ConfigError("Missing disabled node")
                token = tokens[i]
            if token.kind == "symbol":
                raise ConfigError("Invalid node name")
            node = Node(token.text, [], {}, [])
            i += 1
            while i < len(tokens):
                token = tokens[i]
                if token.kind == "symbol":
                    if token.text in ("\n", ";", "}"):
                        break
                    if token.text == "{":
                        i += 1
                        node.children = nodes(True, depth + 1)
                        break
                    raise ConfigError("Unsupported property syntax")
                if i + 1 < len(tokens) and tokens[i + 1].text == "=" and tokens[i + 1].kind == "symbol":
                    if i + 2 >= len(tokens) or tokens[i + 2].kind == "symbol":
                        raise ConfigError("Missing property value")
                    node.props[token.text] = tokens[i + 2].text
                    i += 3
                else:
                    node.args.append(token.text)
                    i += 1
            if not disabled:
                output.append(node)
        if nested:
            raise ConfigError("Unclosed node")
        return output

    return nodes()


# Labels describe actions, not another inventory of key combinations. Bindings
# and aliases are always read from the selected config, never from this table.
LABELS = {
    "close-window": ("windows", "关闭当前窗口"),
    "switch-preset-column-width": ("windows", "下一个预设列宽"),
    "switch-preset-column-width-back": ("windows", "上一个预设列宽"),
    "switch-preset-window-height": ("windows", "切换预设窗口高度"),
    "reset-window-height": ("windows", "重置窗口高度"),
    "expand-column-to-available-width": ("windows", "扩展到可用宽度"),
    "center-column": ("windows", "居中当前列"),
    "center-visible-columns": ("windows", "居中可见列"),
    "maximize-column": ("windows", "切换列最大化"),
    "maximize-window-to-edges": ("windows", "切换窗口扩展到边缘"),
    "fullscreen-window": ("windows", "切换全屏"),
    "toggle-window-floating": ("windows", "切换浮动与平铺"),
    "toggle-column-tabbed-display": ("windows", "切换列标签模式"),
    "switch-focus-between-floating-and-tiling": ("windows", "切换浮动与平铺焦点"),
    "focus-column-first": ("windows", "聚焦第一列"),
    "focus-column-last": ("windows", "聚焦最后一列"),
    "move-column-to-first": ("windows", "移动到第一列"),
    "move-column-to-last": ("windows", "移动到最后一列"),
    "consume-window-into-column": ("windows", "合并窗口到当前列"),
    "expel-window-from-column": ("windows", "将窗口移出当前列"),
    "focus-workspace-previous": ("workspaces", "返回上一个工作区"),
    "toggle-overview": ("desktop", "切换桌面概览"),
    "screenshot": ("capture", "区域截图"),
    "screenshot-screen": ("capture", "屏幕截图"),
    "screenshot-window": ("capture", "窗口截图"),
    "toggle-keyboard-shortcuts-inhibit": ("desktop", "切换应用接管快捷键"),
    "power-off-monitors": ("session", "关闭显示器"),
    "quit": ("session", "请求退出桌面会话"),
}

COMMANDS = {
    ("kitty",): ("apps", "终端"),
    ("google-chrome-stable",): ("apps", "浏览器"),
    ("nautilus",): ("apps", "文件管理器"),
    ("noctalia", "msg", "panel-toggle", "utopia/shortcuts:guide"): ("desktop", "快捷键说明"),
    ("noctalia", "msg", "panel-toggle", "utopia/wallpaper:center"): ("desktop", "壁纸中心"),
    ("noctalia", "msg", "panel-toggle", "control-center"): ("desktop", "控制中心"),
    ("noctalia", "msg", "panel-toggle", "control-center", "notifications"): ("desktop", "通知中心"),
    ("noctalia", "msg", "panel-toggle", "clipboard"): ("desktop", "剪贴板历史"),
    ("noctalia", "msg", "settings-toggle"): ("desktop", "桌面设置"),
    ("noctalia", "msg", "panel-toggle", "launcher"): ("apps", "应用启动器"),
    ("noctalia", "msg", "panel-toggle", "session"): ("session", "会话菜单"),
    ("noctalia", "msg", "session", "lock"): ("session", "锁屏"),
    **{("noctalia", "msg", command): ("media", title) for command, title in {
        "volume-up": "增大音量", "volume-down": "减小音量", "volume-mute": "切换静音",
        "mic-mute": "切换麦克风静音", "brightness-up": "提高亮度", "brightness-down": "降低亮度",
    }.items()},
    **{("noctalia", "msg", "media", command): ("media", title) for command, title in {
        "next": "下一首", "previous": "上一首", "play": "播放", "pause": "暂停", "stop": "停止播放", "toggle": "播放 / 暂停",
    }.items()},
}


def command_argv(action: Node) -> tuple[str, ...]:
    # Only exact known commands are used for metadata. This never executes or
    # expands a shell command, and raw command arguments are not emitted.
    if action.name == "spawn":
        return tuple(action.args)
    if action.name == "spawn-sh" and len(action.args) == 1:
        return tuple(action.args[0].split())
    return ()


COMMAND_SEARCH = {
    ("kitty",): "terminal shell 终端 命令行 控制台",
    ("google-chrome-stable",): "browser chrome 浏览器 网页 上网",
    ("nautilus",): "files folders file manager 文件 文件夹 文档 目录",
    ("noctalia", "msg", "panel-toggle", "utopia/shortcuts:guide"): "help shortcuts keybindings 帮助 按键 快捷键 使用说明",
    ("noctalia", "msg", "panel-toggle", "utopia/wallpaper:center"): "wallpaper background 壁纸 背景 桌面背景",
    ("noctalia", "msg", "panel-toggle", "control-center"): "control center 控制中心 快捷设置",
    ("noctalia", "msg", "panel-toggle", "control-center", "notifications"): "notification notifications history 通知 消息 通知历史",
    ("noctalia", "msg", "panel-toggle", "clipboard"): "clipboard copy paste history 剪贴板 复制 粘贴 历史",
    ("noctalia", "msg", "settings-toggle"): "settings preferences 设置 偏好",
    ("noctalia", "msg", "panel-toggle", "launcher"): "launcher applications 应用 程序 启动器 搜索 程序菜单",
    ("noctalia", "msg", "panel-toggle", "session"): "session power logout 会话 电源 退出 重启 关机",
    ("noctalia", "msg", "session", "lock"): "lock lockscreen 锁屏 锁定",
    **{("noctalia", "msg", "media", action): "media play pause 媒体 音乐 播放 暂停" for action in ("toggle", "play", "pause")},
}

ACTION_SEARCH = {
    "quit": "logout session 注销 退出 结束会话 确认",
    "power-off-monitors": "display monitor screen off 熄屏 关闭屏幕 显示器",
    "fullscreen-window": "fullscreen 全屏 沉浸",
    "toggle-window-floating": "floating tiling 浮动 平铺 模式",
    "switch-focus-between-floating-and-tiling": "floating tiling focus 浮动 平铺 焦点",
    "maximize-column": "maximize 最大化 列最大化",
    "maximize-window-to-edges": "maximize edges 最大化 窗口 边缘 扩展",
    "toggle-overview": "overview overview grid 概览 总览 桌面概览",
    "toggle-column-tabbed-display": "tabs tabbed 标签 标签页",
    "consume-window-into-column": "merge column 合并 列",
    "expel-window-from-column": "split column 拆分 移出 列",
    "focus-workspace-previous": "previous workspace 上一个 返回 工作区",
    "toggle-keyboard-shortcuts-inhibit": "inhibit keyboard 接管 拦截 应用 快捷键",
}

DETAILS = {
    "power-off-monitors": "仅关闭显示器，不会锁屏；请勿将熄屏当作锁定会话。",
    "toggle-keyboard-shortcuts-inhibit": "切换是否允许应用接管快捷键，不是每次都强制解除，也不会退出应用。",
    "maximize-column": "改变当前列的最大化状态，不等于全屏。",
    "maximize-window-to-edges": "切换当前窗口扩展到边缘的状态，与列最大化和全屏不同。",
    "expand-column-to-available-width": "利用未被其他完整可见列占用的空间，不等于全屏。",
    "switch-focus-between-floating-and-tiling": "只切换焦点，不改变窗口的浮动或平铺模式。",
    "move-workspace-up": "重排工作区本身，不是切换工作区或移动窗口。",
    "move-workspace-down": "重排工作区本身，不是切换工作区或移动窗口。",
}


def action_metadata(action: Node) -> tuple[str, str]:
    detail = DETAILS.get(action.name, "")
    if action.name == "quit":
        skip = action.props.get("skip-confirmation") in ("true", "#true")
        detail = "此绑定跳过退出确认，请谨慎使用。" if skip else "先显示退出确认；不是关闭当前窗口。"
    search = COMMAND_SEARCH.get(command_argv(action), "") if action.name in ("spawn", "spawn-sh") else ACTION_SEARCH.get(action.name, "")
    return detail, search


COMMAND_PRIORITY = {
    ("noctalia", "msg", "panel-toggle", "utopia/shortcuts:guide"): 0,
    ("kitty",): 10,
    ("google-chrome-stable",): 20,
    ("nautilus",): 30,
    ("noctalia", "msg", "panel-toggle", "launcher"): 40,
    ("noctalia", "msg", "panel-toggle", "control-center", "notifications"): 50,
    ("noctalia", "msg", "panel-toggle", "clipboard"): 60,
    ("noctalia", "msg", "panel-toggle", "control-center"): 70,
    ("noctalia", "msg", "settings-toggle"): 80,
    ("noctalia", "msg", "panel-toggle", "utopia/wallpaper:center"): 90,
    ("noctalia", "msg", "session", "lock"): 100,
}


def compact_workspace_rows(rows: list[dict]) -> list[dict]:
    """Compact only proven consecutive digit keys; retain every original row.

    Explicit titles, aliases, remapped digits, and different behavior properties
    are deliberately not guessed into a range. Three consecutive rows are the
    minimum useful compaction. Search expands members in the UI.
    """
    families = {}
    for row in rows:
        series = row.pop("_series", None)
        if series is None or len(row["keys"]) != 1:
            continue
        number = series["number"]
        match = re.fullmatch(r"((?:[^+]+ \+ )*)([1-9])", row["keys"][0])
        if match is None or int(match[2]) != number:
            continue
        family = (series["behavior"], match[1], series["label_prefix"])
        families.setdefault(family, []).append((number, row))

    replaced = {}
    consumed = set()
    for (_, prefix, label_prefix), entries in families.items():
        entries.sort(key=lambda entry: entry[0])
        runs = []
        for entry in entries:
            if not runs or entry[0] != runs[-1][-1][0] + 1:
                runs.append([])
            runs[-1].append(entry)
        for run in runs:
            if len(run) < 3:
                continue
            members = [entry[1] for entry in run]
            first, last = run[0][0], run[-1][0]
            start = min(members, key=lambda row: row["order"])
            compact = dict(start)
            compact.update({
                "id": "range-" + start["id"],
                "label": label_prefix + f"{first}–{last}",
                "keys": [prefix + f"{first}–{last}"],
                "detail": "按编号对应工作区；搜索具体数字可查看原始组合。",
                "members": members,
            })
            replaced[start["id"]] = compact
            consumed.update(row["id"] for row in members)
    return [replaced[row["id"]] if row["id"] in replaced else row
            for row in rows if row["id"] not in consumed or row["id"] in replaced]


def description(action: Node, title: str | None) -> tuple[str, str]:
    name = action.name
    if name in ("spawn", "spawn-sh"):
        # Match only exact known simple commands; never shell-parse/evaluate.
        argv = command_argv(action)
        group, label = COMMANDS.get(argv, ("other", "自定义操作"))
    elif name in LABELS:
        group, label = LABELS[name]
    elif name in ("focus-workspace", "move-column-to-workspace"):
        group = "workspaces"
        label = ("切换到工作区 " if name == "focus-workspace" else "移动列到工作区 ") + " ".join(action.args)
    elif name in ("set-column-width", "set-window-height"):
        group = "windows"
        target = "列宽" if name == "set-column-width" else "窗口高度"
        amount = re.fullmatch(r"([+-])(\d+(?:\.\d+)?)(%?)", action.args[0]) if len(action.args) == 1 else None
        if amount:
            label = ("减小" if amount[1] == "-" else "增大") + target + " " + amount[2] + ("%" if amount[3] else " 像素")
        else:
            label = "设置" + target + " " + " ".join(action.args)
    else:
        directions = {"left": "左", "right": "右", "up": "上", "down": "下"}
        match = re.fullmatch(r"(.+)-(left|right|up|down)", name)
        stem, direction = (match[1], directions[match[2]]) if match else (name, "")
        phrases = {
            "focus-column": ("windows", "聚焦{d}侧列"),
            "focus-window": ("windows", "聚焦{d}方窗口"),
            "move-column": ("windows", "向{d}移动列"),
            "move-window": ("windows", "向{d}移动窗口"),
            "focus-monitor": ("windows", "聚焦{d}方显示器"),
            "move-column-to-monitor": ("windows", "移动列到{d}方显示器"),
            "consume-or-expel-window": ("windows", "向{d}合并或移出窗口"),
            "focus-workspace": ("workspaces", "切换到{d}方工作区"),
            "move-column-to-workspace": ("workspaces", "移动列到{d}方工作区"),
            "move-workspace": ("workspaces", "向{d}移动工作区"),
        }
        group, phrase = phrases.get(stem, ("other", name))
        label = phrase.format(d=direction)
    return group, title if title not in (None, "null", "#null") else label


def canonical_key(key: str) -> str:
    aliases = {"mod": "Super", "super": "Super", "win": "Super", "ctrl": "Ctrl", "control": "Ctrl", "shift": "Shift", "alt": "Alt"}
    names = {"return": "Enter", "escape": "Esc", "slash": "/", "bracketleft": "[", "bracketright": "]", "comma": ",", "period": ".", "minus": "−", "equal": "=", "page_up": "PgUp", "page_down": "PgDn", "tab": "Tab", "left": "←", "right": "→", "up": "↑", "down": "↓", "home": "Home", "end": "End", "print": "Print"}
    pieces = key.split("+")
    mods = [aliases.get(k.lower(), k) for k in pieces[:-1]]
    if len(set(mods)) != len(mods):
        raise ConfigError("Duplicate key modifier")
    mods.sort(key=lambda k: {"Super": 0, "Ctrl": 1, "Alt": 2, "Shift": 3}.get(k, 4))
    last = pieces[-1]
    return " + ".join(mods + [names.get(last.lower(), last.upper() if len(last) == 1 else last)])


def read_bindings(config: Path) -> dict:
    root = config.expanduser().resolve().parent
    active = set()
    total_bytes = 0
    files = 0
    collected = []

    def read(path: Path, depth=0, optional=False):
        nonlocal total_bytes, files
        path = path.resolve()
        if not path.is_relative_to(root):
            raise ConfigError("Include outside selected config directory; choose a self-contained config tree")
        if path in active:
            raise ConfigError("Cyclic include")
        if optional and not path.exists():
            return
        if depth > 16 or files >= 64:
            raise ConfigError("Include limit exceeded")
        try:
            if not stat.S_ISREG(path.stat().st_mode):
                raise ConfigError("Configuration must be a regular file")
            with path.open("rb") as source:
                data = source.read(1024 * 1024 + 1)
        except OSError as exc:
            raise ConfigError("Cannot read a required configuration file") from exc
        files += 1
        total_bytes += len(data)
        if len(data) > 1024 * 1024 or total_bytes > 4 * 1024 * 1024:
            raise ConfigError("Configuration size limit exceeded")
        try:
            tree = parse(data.decode("utf-8"))
        except UnicodeError as exc:
            raise ConfigError("Configuration must be UTF-8") from exc
        active.add(path)
        for node in tree:
            if node.name == "include":
                if len(node.args) != 1:
                    raise ConfigError("Unsupported include")
                read(path.parent / node.args[0], depth + 1, node.props.get("optional") in ("true", "#true"))
            elif node.name == "binds":
                collected.extend(node.children)
        active.remove(path)

    read(config.expanduser())
    if len(collected) > 2048:
        raise ConfigError("Binding limit exceeded")
    rows = {}
    primary_keys = {}
    seen = set()
    for bind in collected:
        if len(bind.children) != 1 or bind.args:
            raise ConfigError("Unsupported binding action")
        action = bind.children[0]
        if action.children:
            raise ConfigError("Unsupported nested action")
        key = canonical_key(bind.name)
        if key in seen:
            raise ConfigError("Duplicate binding; validate the Niri configuration")
        seen.add(key)
        # Properties can change action behavior; do not merge distinct variants.
        signature = json.dumps([action.name, action.args, action.props, {k: v for k, v in bind.props.items() if k != "hotkey-overlay-title"}], sort_keys=True)
        group, label = description(action, bind.props.get("hotkey-overlay-title"))
        detail, search = action_metadata(action)
        if signature not in rows:
            order = len(rows) + 1
            priority = COMMAND_PRIORITY.get(command_argv(action), 1000)
            row = {"id": str(order), "order": order, "priority": priority, "common": priority <= 100, "group": group, "label": label, "detail": detail, "keys": [], "search": action.name + " " + search}
            if action.name in ("focus-workspace", "move-column-to-workspace") and len(action.args) == 1 and re.fullmatch(r"[1-9]", action.args[0]) and bind.props.get("hotkey-overlay-title") in (None, "null", "#null"):
                row["_series"] = {
                    "number": int(action.args[0]),
                    "behavior": json.dumps([action.name, action.props, {k: v for k, v in bind.props.items() if k != "hotkey-overlay-title"}], sort_keys=True),
                    "label_prefix": label[:-1],
                }
            rows[signature] = row
        elif bind.props.get("hotkey-overlay-title") not in (None, "null", "#null"):
            rows[signature]["label"] = label
            rows[signature].pop("_series", None)
        rows[signature]["keys"].append(key)
        rows[signature]["search"] += " " + bind.name
        if bind.props.get("hotkey-overlay-title") not in (None, "null", "#null"):
            primary_keys.setdefault(signature, []).append(key)
    for signature, row in rows.items():
        primary = primary_keys.get(signature, [])
        row["keys"] = primary + [key for key in row["keys"] if key not in primary]
    return {"schema_version": 1, "rows": compact_workspace_rows(list(rows.values())), "action_count": len(rows), "binding_count": len(collected), "file_count": files, "error": ""}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "niri/config.kdl")
    args = parser.parse_args()
    try:
        result = read_bindings(args.config)
    except (ConfigError, RecursionError) as exc:
        message = str(exc) if isinstance(exc, ConfigError) else "Configuration nesting limit exceeded"
        result = {"schema_version": 1, "rows": [], "binding_count": 0, "file_count": 0, "error": message}
    print(json.dumps(result, ensure_ascii=False))
    return 1 if result["error"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
