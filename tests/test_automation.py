"""Unit tests for the automatic merge boundary; no GitHub writes."""
import importlib.util
from pathlib import Path
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("merge_update", Path(__file__).parents[1] / "scripts/merge-update.py")
assert spec is not None and spec.loader is not None
merge = importlib.util.module_from_spec(spec)
spec.loader.exec_module(merge)


class MergeGuards(unittest.TestCase):
    def test_only_pins_are_normalized(self):
        original = '  version = "1.0.0-beta.5";\n    hash = "old";\n  npmDepsHash = "old";\n  dontNpmBuild = true;'
        update = original.replace("beta.5", "beta.12").replace("old", "new")
        self.assertEqual(merge.normalize_package(original), merge.normalize_package(update))
        self.assertNotEqual(merge.normalize_package(original), merge.normalize_package(update.replace("true", "false")))

    def test_unexpected_layout_fails(self):
        with self.assertRaises(RuntimeError):
            merge.normalize_package('version = "1.0.0";')

    def test_test_pr_cannot_merge(self):
        pr = {"state": "open", "draft": True, "user": {"login": "github-actions[bot]"}}
        with patch.dict(merge.os.environ, {"GITHUB_REPOSITORY": "owner/repo", "UPDATE_PR": "1", "UPDATE_SHA": "sha", "UPDATE_BASE": "base"}), patch.object(merge, "api", return_value=pr), patch.object(merge.subprocess, "run") as write:
            with self.assertRaises(RuntimeError):
                merge.main()
            write.assert_not_called()

    def test_changed_main_cannot_merge(self):
        pr = {"state": "open", "draft": False, "user": {"login": "github-actions[bot]"},
              "head": {"ref": "automation/cf-1.0.0", "sha": "sha", "repo": {"full_name": "owner/repo"}},
              "base": {"ref": "main"}}
        with patch.dict(merge.os.environ, {"GITHUB_REPOSITORY": "owner/repo", "UPDATE_PR": "1", "UPDATE_SHA": "sha", "UPDATE_BASE": "base"}), patch.object(merge, "api", side_effect=[pr, {"sha": "new-main"}]), patch.object(merge.subprocess, "run") as write:
            with self.assertRaises(RuntimeError):
                merge.main()
            write.assert_not_called()


if __name__ == "__main__":
    unittest.main()
