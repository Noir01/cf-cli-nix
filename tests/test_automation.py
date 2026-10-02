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

    def test_server_rule_rejects_non_strict_or_bypassable_checks(self):
        import copy
        import json
        rule = json.loads((Path(__file__).parents[1] / ".github/main-ruleset.json").read_text())
        summary = [{"id": 1, "name": rule["name"]}]
        with patch.object(merge, "api", side_effect=[summary, rule]):
            merge.require_server_merge_guard("owner/repo")
        hidden_bypass = copy.deepcopy(rule)
        hidden_bypass.pop("bypass_actors")  # GitHub hides this from non-admin tokens.
        with patch.object(merge, "api", side_effect=[summary, hidden_bypass]):
            merge.require_server_merge_guard("owner/repo")
        weak = copy.deepcopy(rule)
        weak["rules"][0]["parameters"]["strict_required_status_checks_policy"] = False
        bypass = copy.deepcopy(rule)
        bypass["bypass_actors"] = [{"actor_id": 5, "actor_type": "RepositoryRole", "bypass_mode": "always"}]
        wrong_source = copy.deepcopy(rule)
        wrong_source["rules"][0]["parameters"]["required_status_checks"][0]["integration_id"] = 0
        for unsafe in (weak, bypass, wrong_source):
            with self.subTest(rule=unsafe), patch.object(merge, "api", side_effect=[summary, unsafe]):
                with self.assertRaises(RuntimeError):
                    merge.require_server_merge_guard("owner/repo")

    def test_missing_server_rules_cannot_merge(self):
        pr = {"state": "open", "draft": False, "user": {"login": "github-actions[bot]"},
              "head": {"ref": "automation/cf-1.0.0", "sha": "sha", "repo": {"full_name": "owner/repo"}},
              "base": {"ref": "main"}}
        def read(endpoint):
            if endpoint.endswith("/pulls/1"):
                return pr
            if endpoint.endswith("/commits/main"):
                return {"sha": "base"}
            if endpoint.endswith("/rulesets"):
                return []
            raise AssertionError("Continued past missing server-side base protection")
        with patch.dict(merge.os.environ, {"GITHUB_REPOSITORY": "owner/repo", "UPDATE_PR": "1", "UPDATE_SHA": "sha", "UPDATE_BASE": "base"}), patch.object(merge, "api", side_effect=read), patch.object(merge.subprocess, "run") as write:
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
