import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import tomllib
import unittest


ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "desktop/noctalia/plugins/utopia-shortcuts"
spec = importlib.util.spec_from_file_location("utopia_shortcuts_reader", PLUGIN / "bindings.py")
reader = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = reader
spec.loader.exec_module(reader)


class ShortcutsReaderTest(unittest.TestCase):
    def read(self, text):
        with tempfile.TemporaryDirectory() as temp:
            config = Path(temp) / "config.kdl"
            config.write_text(text)
            return reader.read_bindings(config)

    def test_reads_all_bindings_including_hidden_aliases(self):
        data = self.read('''binds {
            Mod+T hotkey-overlay-title="终端" { spawn "kitty"; }
            Mod+Return hotkey-overlay-title=null { spawn "kitty"; }
            Mod+Shift+F { fullscreen-window; }
        }''')
        self.assertEqual(data["binding_count"], 3)
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual(data["rows"][0]["keys"], ["Super + T", "Super + Enter"])
        self.assertEqual(data["rows"][0]["label"], "终端")
        self.assertEqual(data["rows"][1]["label"], "切换全屏")

    def test_comments_disabled_nodes_and_strings_are_not_bindings(self):
        data = self.read('''// binds { Mod+Q { quit; } }
        /* nested /* comment */ binds { Bad { quit; } } */
        /- binds { Mod+X { quit; } }
        binds {
          /- Mod+Q { quit; }
          Mod+T hotkey-overlay-title="brace { // literal" { spawn "kitty"; }
          Mod+B { spawn r#"/program/{quoted}//path"#; }
        }''')
        self.assertEqual(data["binding_count"], 2)
        self.assertEqual(data["rows"][0]["label"], "brace { // literal")

    def test_raw_v2_strings_and_line_continuations(self):
        data = self.read('binds {\nMod+T \\\n hotkey-overlay-title=#"Terminal"# { spawn "kitty"; }\n}')
        self.assertEqual(data["rows"][0]["label"], "Terminal")

    def test_reads_nested_relative_includes_and_ignores_missing_optional(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "cfg").mkdir()
            (root / "config.kdl").write_text('include "cfg/a.kdl"\ninclude optional=true "palette.kdl"\n')
            (root / "cfg/a.kdl").write_text('include "b.kdl"\n')
            (root / "cfg/b.kdl").write_text('binds { Mod+T { spawn "kitty"; } }')
            data = reader.read_bindings(root / "config.kdl")
            self.assertEqual(data["binding_count"], 1)
            self.assertEqual(data["file_count"], 3)

    def test_required_missing_include_fails_instead_of_partial_results(self):
        with self.assertRaises(reader.ConfigError):
            self.read('binds { Mod+T { spawn "kitty"; } }\ninclude "missing.kdl"')

    def test_include_cycles_fail(self):
        with self.assertRaisesRegex(reader.ConfigError, "Cyclic"):
            self.read('include "config.kdl"')

    def test_outside_includes_and_symlink_escapes_fail(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root / "niri").mkdir()
            (root / "outside.kdl").write_text('binds { Mod+Q { quit; } }')
            (root / "niri/link.kdl").symlink_to(root / "outside.kdl")
            for target in ("../outside.kdl", "link.kdl"):
                config = root / "niri/config.kdl"
                config.write_text(f'include "{target}"')
                with self.subTest(target=target), self.assertRaises(reader.ConfigError):
                    reader.read_bindings(config)

    def test_duplicate_modifier_spellings_are_detected(self):
        with self.assertRaisesRegex(reader.ConfigError, "Duplicate binding"):
            self.read('binds {\nMod+CTRL+T { spawn "kitty"; }\nSuper+Control+t { quit; }\n}')

    def test_properties_prevent_merging_different_action_behavior(self):
        data = self.read('binds {\nMod+T repeat=false { spawn "kitty"; }\nMod+Return { spawn "kitty"; }\n}')
        self.assertEqual(len(data["rows"]), 2)

    def test_action_arguments_keep_workspace_entries_distinct(self):
        data = self.read('binds {\nMod+1 { focus-workspace 1; }\nMod+2 { focus-workspace 2; }\n}')
        self.assertEqual([r["label"] for r in data["rows"]], ["切换到工作区 1", "切换到工作区 2"])

    def test_new_entries_have_known_labels_even_without_custom_titles(self):
        data = self.read('''binds {
          Mod+N { spawn-sh "noctalia msg panel-toggle control-center notifications"; }
          Mod+Y { spawn-sh "noctalia msg panel-toggle clipboard"; }
          XF86AudioPlay { spawn-sh "noctalia msg media toggle"; }
          XF86AudioPause { spawn-sh "noctalia msg media pause"; }
        }''')
        self.assertEqual([r["label"] for r in data["rows"]], ["通知中心", "剪贴板历史", "播放 / 暂停", "暂停"])
        self.assertEqual([r["group"] for r in data["rows"]], ["desktop", "desktop", "media", "media"])

    def test_search_synonyms_do_not_require_or_create_bindings(self):
        data = self.read('''binds {
          Mod+E { spawn "nautilus"; }
          Mod+Y { spawn-sh "noctalia msg panel-toggle clipboard"; }
          Mod+Slash { spawn-sh "noctalia msg panel-toggle utopia/shortcuts:guide"; }
        }''')
        for row, word in zip(data["rows"], ("文件夹", "粘贴", "帮助")):
            self.assertIn(word, row["search"])
        self.assertEqual(data["binding_count"], 3)

    def test_exit_confirmation_details_follow_action_properties(self):
        data = self.read('''binds {
          Mod+Shift+E { quit; }
          Mod+Alt+E { quit skip-confirmation=true; }
        }''')
        self.assertIn("先显示退出确认", data["rows"][0]["detail"])
        self.assertIn("跳过退出确认", data["rows"][1]["detail"])
        self.assertEqual(len(data["rows"]), 2)

    def test_important_semantics_survive_custom_titles(self):
        data = self.read('''binds {
          Mod+Shift+P hotkey-overlay-title="屏幕" { power-off-monitors; }
          Mod+Escape { toggle-keyboard-shortcuts-inhibit; }
        }''')
        self.assertEqual(data["rows"][0]["label"], "屏幕")
        self.assertIn("不会锁屏", data["rows"][0]["detail"])
        self.assertIn("不是每次都强制解除", data["rows"][1]["detail"])

    def test_dimension_adjustments_describe_direction_and_unit(self):
        data = self.read('''binds {
          Mod+Minus { set-column-width "-10%"; }
          Mod+Equal { set-column-width "+10%"; }
          Mod+Shift+Minus { set-window-height "-20"; }
          Mod+Shift+Equal { set-window-height "500"; }
        }''')
        self.assertEqual([r["label"] for r in data["rows"]], ["减小列宽 10%", "增大列宽 10%", "减小窗口高度 20 像素", "设置窗口高度 500"])

    def test_workspace_range_retains_every_original_key_and_target(self):
        data = self.read("binds {\n" + "\n".join(f'Mod+{n} {{ focus-workspace {n}; }}' for n in range(1, 10)) + "\n}")
        self.assertEqual(data["binding_count"], 9)
        self.assertEqual(data["action_count"], 9)
        self.assertEqual(len(data["rows"]), 1)
        row = data["rows"][0]
        self.assertEqual(row["label"], "切换到工作区 1–9")
        self.assertEqual(row["keys"], ["Super + 1–9"])
        self.assertEqual([m["keys"] for m in row["members"]], [[f"Super + {n}"] for n in range(1, 10)])
        self.assertEqual(row["members"][4]["label"], "切换到工作区 5")
        self.assertEqual(row["members"][4]["keys"], ["Super + 5"])
        self.assertNotIn("_series", json.dumps(data))

    def test_range_does_not_invent_gaps(self):
        data = self.read("binds {\n" + "\n".join(f'Mod+{n} {{ focus-workspace {n}; }}' for n in (1, 2, 4, 5, 6)) + "\n}")
        self.assertEqual([r["keys"] for r in data["rows"]], [["Super + 1"], ["Super + 2"], ["Super + 4–6"]])
        self.assertEqual([m["label"] for m in data["rows"][2]["members"]], [f"切换到工作区 {n}" for n in (4, 5, 6)])

    def test_range_keeps_different_behavior_and_custom_titles_separate(self):
        for extra in ('repeat=false', 'hotkey-overlay-title="Special workspace"'):
            text = "binds {\n" + "\n".join(f'Mod+{n} {extra if n == 2 else ""} {{ focus-workspace {n}; }}' for n in (1, 2, 3)) + "\n}"
            with self.subTest(extra=extra):
                data = self.read(text)
                self.assertEqual(len(data["rows"]), 3)
                self.assertFalse(any("members" in row for row in data["rows"]))

    def test_range_does_not_merge_aliases_remapped_digits_or_different_modifiers(self):
        for text in (
            'Mod+1 { focus-workspace 1; }\nMod+2 { focus-workspace 3; }\nMod+3 { focus-workspace 2; }',
            'Mod+1 { focus-workspace 1; }\nMod+2 { focus-workspace 2; }\nMod+3 { focus-workspace 3; }\nMod+F1 { focus-workspace 1; }',
            'Mod+1 { focus-workspace 1; }\nMod+Ctrl+2 { focus-workspace 2; }\nMod+3 { focus-workspace 3; }',
            'Mod+F1 { focus-workspace 1; }\nMod+F2 { focus-workspace 2; }\nMod+F3 { focus-workspace 3; }',
        ):
            with self.subTest(text=text):
                data = self.read("binds {\n" + text + "\n}")
                self.assertEqual(len(data["rows"]), 3)
                self.assertFalse(any("members" in row for row in data["rows"]))

    def test_focus_and_move_workspace_ranges_are_distinct(self):
        data = self.read("binds {\n" + "\n".join(f'Mod+{n} {{ focus-workspace {n}; }}\nMod+Ctrl+{n} {{ move-column-to-workspace {n}; }}' for n in (1, 2, 3)) + "\n}")
        self.assertEqual(data["action_count"], 6)
        self.assertEqual(len(data["rows"]), 2)
        self.assertEqual([r["keys"] for r in data["rows"]], [["Super + 1–3"], ["Super + Ctrl + 1–3"]])

    def test_common_order_uses_action_identity_not_user_title_or_tracking(self):
        data = self.read('''binds {
          Mod+B hotkey-overlay-title="My browser" { spawn "google-chrome-stable"; }
          Mod+T hotkey-overlay-title="Renamed terminal" { spawn "kitty"; }
          Mod+Slash { spawn-sh "noctalia msg panel-toggle utopia/shortcuts:guide"; }
          Mod+Q { close-window; }
        }''')
        common = sorted((r for r in data["rows"] if r["common"]), key=lambda row: row["priority"])
        self.assertEqual([r["keys"] for r in common], [["Super + /"], ["Super + T"], ["Super + B"]])
        self.assertFalse(data["rows"][-1]["common"])

    def test_explicitly_titled_primary_key_precedes_hidden_alias(self):
        data = self.read('''binds {
          Mod+Ctrl+Return hotkey-overlay-title=null { spawn-sh "noctalia msg panel-toggle launcher"; }
          Mod+D hotkey-overlay-title="应用启动器" { spawn-sh "noctalia msg panel-toggle launcher"; }
        }''')
        self.assertEqual(data["rows"][0]["keys"], ["Super + D", "Super + Ctrl + Enter"])
        self.assertEqual(data["binding_count"], 2)

    def test_reader_never_executes_or_outputs_commands(self):
        with tempfile.TemporaryDirectory() as temp:
            marker = Path(temp) / "should-not-exist"
            data = self.read(f'binds {{ Mod+T {{ spawn-sh "touch {marker}"; }} }}')
            self.assertFalse(marker.exists())
            self.assertNotIn(str(marker), json.dumps(data))
            self.assertEqual(data["rows"][0]["label"], "自定义操作")

    def test_unsupported_or_malformed_syntax_fails_closed(self):
        for text in ('binds { Mod+T { quit; }', 'binds { Mod+T { quit; spawn "kitty"; } }',
                     'binds { Mod+T /- repeat=true { quit; } }', '/* unclosed'):
            with self.subTest(text=text), self.assertRaises(reader.ConfigError):
                self.read(text)

    def test_size_limit_is_bounded(self):
        with self.assertRaisesRegex(reader.ConfigError, "size limit"):
            self.read(" " * (1024 * 1024 + 1))

    def test_cli_errors_are_json_and_do_not_disclose_paths(self):
        result = subprocess.run([sys.executable, "-B", str(PLUGIN / "bindings.py"), "--config", "/no-such-private-directory/config.kdl"], text=True, capture_output=True)
        self.assertEqual(result.returncode, 1)
        data = json.loads(result.stdout)
        self.assertEqual(data["rows"], [])
        self.assertNotIn("private-directory", result.stdout + result.stderr)

    def test_both_repository_host_compositions_are_readable(self):
        for host in ("arch-laptop", "cachyos-desktop"):
            with self.subTest(host=host), tempfile.TemporaryDirectory() as temp:
                root = Path(temp) / "niri"
                shutil.copytree(ROOT / "desktop/niri", root)
                shutil.copyfile(ROOT / f"hosts/{host}/desktop/niri/display.kdl", root / "cfg/display.kdl")
                data = reader.read_bindings(root / "config.kdl")
                self.assertGreater(data["binding_count"], 100)
                originals = [member for row in data["rows"] for member in row.get("members", [row])]
                self.assertEqual(sum(len(r["keys"]) for r in originals), data["binding_count"])
                self.assertEqual(len(originals), data["action_count"])
                self.assertEqual(data["error"], "")


class ShortcutsPluginTest(unittest.TestCase):
    def test_manifest_and_ui_have_read_only_scrollable_contract(self):
        manifest = tomllib.loads((PLUGIN / "plugin.toml").read_text())
        self.assertEqual(manifest["id"], "utopia/shortcuts")
        self.assertEqual(manifest["plugin_api"], 33)
        panel = manifest["panel"][0]
        self.assertLessEqual(panel["height"], 600)
        self.assertEqual(panel["placement"], "floating")
        source = (PLUGIN / "panel.luau").read_text()
        self.assertIn("ui.scroll", source)
        self.assertIn("minHeight = 0", source)
        self.assertIn("revealKey", source)
        self.assertIn('searching and row.members', source)
        self.assertIn('"frequent" or row.group', source)
        self.assertIn('"python", "-B", helper', source)
        self.assertNotIn("dispatch", source.replace("never dispatch", ""))
        self.assertNotIn("writeFile", source)
        for language in ("zh-Hans", "en"):
            strings = json.loads((PLUGIN / f"translations/{language}.json").read_text())
            self.assertIn("read_only", strings)
            self.assertIn("retry", strings)
            self.assertNotIn("fallback", strings)

    def test_plugin_is_enabled_and_has_a_profile_artifact(self):
        from utopia import workstation

        config = tomllib.loads((ROOT / ".config/noctalia/plugins.toml").read_text())
        self.assertIn("utopia/shortcuts", config["plugins"]["enabled"])
        for host in ("arch-laptop", "cachyos-desktop"):
            result = workstation.resolve(ROOT, host)
            artifact = next(a for a in result["artifacts"] if a["id"] == "desktop.noctalia-shortcuts-plugin")
            self.assertEqual(artifact["source"], "desktop/noctalia/plugins/utopia-shortcuts")
            self.assertEqual(artifact["destination"], ".local/share/noctalia/plugins/utopia-shortcuts")
