"""Checks that the committed release archive in dist/ matches the skill folder.

A stale archive would ship outdated guidance to everyone who installs it. File
contents are compared rather than archive bytes, because compressed bytes can
differ between zlib builds even when the contents are identical.
"""

from __future__ import annotations

import hashlib
import unittest

from support import REPO_ROOT, SKILL_DIR, load_script

packager = load_script("package-skill")
validator = load_script("validate-skill")

REBUILD_HINT = "rebuild it with: python3 mych-plugin/scripts/package-skill.py"


def current_version() -> str:
    parsed = validator.parse_frontmatter((SKILL_DIR / "SKILL.md").read_text(encoding="utf-8"))
    return parsed.data["metadata"]["version"]


class DistArchiveTest(unittest.TestCase):
    def setUp(self):
        self.archive = REPO_ROOT / "dist" / "mych-plugin-{}.zip".format(current_version())
        self.assertTrue(self.archive.is_file(), "missing {}; {}".format(self.archive, REBUILD_HINT))

    def test_archive_structure_verifies(self):
        errors, facts = packager.verify_archive(self.archive, validator)
        self.assertEqual(errors, [])
        self.assertEqual(facts["skill_name"], "mych-plugin")
        self.assertEqual(facts["version"], current_version())

    def test_archive_contents_match_the_source(self):
        files, _ = packager.collect_files(SKILL_DIR, validator)
        expected = {"mych-plugin/" + rel: hashlib.sha256(path.read_bytes()).hexdigest() for rel, path in files}
        errors, _ = packager.verify_archive(self.archive, validator, expected=expected, skill_name="mych-plugin")
        self.assertEqual(errors, [], "the committed archive is stale; " + REBUILD_HINT)


if __name__ == "__main__":
    unittest.main()
