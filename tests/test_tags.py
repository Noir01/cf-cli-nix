import runpy
import unittest
from pathlib import Path

MODULE = runpy.run_path(str(Path(__file__).parents[1] / "scripts/tag-version.py"))


class TagTests(unittest.TestCase):
    def test_beta_version(self):
        self.assertEqual(MODULE["tag_name"]("1.0.0-beta.12"), "v1.0.0-beta.12")

    def test_bad_versions(self):
        for version in ["latest", "1/2/3", "1.0.0\n", "$(command)"]:
            with self.assertRaises(ValueError):
                MODULE["tag_name"](version)

    def test_existing_tag_is_idempotent(self):
        refs = [{"ref": "refs/tags/v1.0.0", "object": {"type": "commit", "sha": "abc"}}]
        self.assertTrue(MODULE["existing_tag_sha"](refs, "v1.0.0", "abc"))
        with self.assertRaises(ValueError):
            MODULE["existing_tag_sha"](refs, "v1.0.0", "other")

    def test_prefix_is_not_exact_match(self):
        refs = [{"ref": "refs/tags/v1.0.0-beta.1", "object": {"type": "commit", "sha": "abc"}}]
        self.assertFalse(MODULE["existing_tag_sha"](refs, "v1.0.0", "abc"))

    def test_annotated_tag_is_not_silently_replaced(self):
        refs = [{"ref": "refs/tags/v1.0.0", "object": {"type": "tag", "sha": "abc"}}]
        with self.assertRaises(ValueError):
            MODULE["existing_tag_sha"](refs, "v1.0.0", "abc")
