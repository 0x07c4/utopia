import json
from pathlib import Path
import subprocess
import tempfile
import unittest

from utopia import audit, profiles


class HomeArtifactAuditTest(unittest.TestCase):
    @staticmethod
    def _artifact(kind: str, *, mode: str | None = None) -> dict[str, object]:
        artifact: dict[str, object] = {
            "id": f"test.{kind}",
            "domain": "test",
            "source": "source",
            "destination": ".config/test",
            "kind": kind,
            "excludes": [],
        }
        if mode is not None:
            artifact["mode"] = mode
        return artifact

    def test_file_reports_content_and_mode_drift(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            live = root / "live"
            source.write_text("expected\n")
            live.write_text("actual\n")
            live.chmod(0o644)

            status_name, changes = audit._audit_file(
                source, live, self._artifact("file", mode="0600")
            )

            self.assertEqual(status_name, "drift")
            self.assertEqual(
                [item["status"] for item in changes],
                ["modified", "mode-mismatch"],
            )

    def test_file_symlink_is_not_followed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            target = root / "target"
            live = root / "live"
            source.write_text("same\n")
            target.write_text("same\n")
            live.symlink_to(target)

            status_name, changes = audit._audit_file(
                source, live, self._artifact("file")
            )

            self.assertEqual(status_name, "unsafe")
            self.assertEqual(changes[0]["status"], "symlink")

    def test_tree_reports_drift_but_honors_excludes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            live = root / "live"
            source.mkdir()
            live.mkdir()
            (source / "same").write_text("same\n")
            (live / "same").write_text("same\n")
            (source / "changed").write_text("expected\n")
            (live / "changed").write_text("actual\n")
            (live / "extra").write_text("extra\n")
            (source / "ignored").write_text("repository\n")
            (live / "ignored").write_text("live\n")
            artifact = self._artifact("tree")
            artifact["excludes"] = ["ignored"]

            status_name, changes = audit._audit_tree(source, live, artifact)

            self.assertEqual(status_name, "drift")
            self.assertEqual(
                {(item["path"], item["status"]) for item in changes},
                {
                    (".config/test/changed", "modified"),
                    (".config/test/extra", "extra"),
                },
            )

    def test_tree_does_not_descend_into_git_metadata(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            live = root / "live"
            source.mkdir()
            live.mkdir()
            (source / "config").write_text("same\n")
            (live / "config").write_text("same\n")
            metadata = live / ".git"
            metadata.mkdir()
            (metadata / "private-state").write_text("not inspected\n")

            status_name, changes = audit._audit_tree(
                source, live, self._artifact("tree")
            )

            self.assertEqual(status_name, "unsafe")
            self.assertEqual(
                changes,
                [{"path": ".config/test/.git", "status": "git-metadata"}],
            )

    def test_gitlink_compares_recorded_commit_and_clean_worktree(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            repository = root / "repository"
            live = root / "live"
            repository.mkdir()
            live.mkdir()
            subprocess.run(["git", "init", "-q", repository], check=True)
            subprocess.run(["git", "init", "-q", live], check=True)
            (live / "init.lua").write_text("return {}\n")
            subprocess.run(["git", "-C", live, "add", "init.lua"], check=True)
            subprocess.run(
                [
                    "git",
                    "-C",
                    live,
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
                ["git", "-C", live, "rev-parse", "HEAD"],
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()
            subprocess.run(
                [
                    "git",
                    "-C",
                    repository,
                    "update-index",
                    "--add",
                    "--cacheinfo",
                    f"160000,{commit},source",
                ],
                check=True,
            )

            status_name, changes, commits = audit._audit_gitlink(
                repository, live, self._artifact("gitlink")
            )

            self.assertEqual(status_name, "match")
            self.assertEqual(changes, [])
            self.assertEqual(commits["expected_commit"], commit)
            self.assertEqual(commits["actual_commit"], commit)

    def test_full_audit_is_json_serializable_and_omits_home_path(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)

            result = audit.audit_home(profiles.REPO_ROOT, "arch-laptop", home)
            encoded = json.dumps(result)

            self.assertEqual(result["profile"], "arch-laptop")
            self.assertEqual(result["summary"]["total"], 17)
            self.assertEqual(result["summary"]["missing"], 17)
            self.assertNotIn(str(home), encoded)
            self.assertTrue(audit.has_drift(result))

    def test_home_root_must_not_be_a_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            link = root / "link"
            home.mkdir()
            link.symlink_to(home, target_is_directory=True)

            with self.assertRaisesRegex(audit.AuditError, "non-symlink"):
                audit.audit_home(profiles.REPO_ROOT, "arch-laptop", link)

    def test_full_audit_does_not_follow_intermediate_symlink(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            home = root / "home"
            outside = root / "outside"
            home.mkdir()
            outside.mkdir()
            (home / ".config").symlink_to(outside, target_is_directory=True)

            result = audit.audit_home(profiles.REPO_ROOT, "arch-laptop", home)
            starship = next(
                item for item in result["artifacts"] if item["id"] == "shell.starship"
            )

            self.assertEqual(starship["status"], "unsafe")
            self.assertEqual(
                starship["changes"],
                [{"path": ".config", "status": "symlink"}],
            )

    def test_human_report_contains_only_relative_artifact_paths(self) -> None:
        result = {
            "profile": "test",
            "artifacts": [
                {
                    "id": "test.file",
                    "status": "drift",
                    "changes": [
                        {"path": ".config/test", "status": "modified"}
                    ],
                }
            ],
            "summary": {
                "match": 0,
                "drift": 1,
                "missing": 0,
                "unsafe": 0,
            },
        }

        report = audit.format_audit(result)

        self.assertIn("modified:.config/test", report)
        self.assertNotIn(str(Path.home()), report)


if __name__ == "__main__":
    unittest.main()
