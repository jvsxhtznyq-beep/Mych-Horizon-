"""Tests for mych-plugin/scripts/package-skill.py."""

from __future__ import annotations

import hashlib
import os
import shutil
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest import mock

from support import SKILL_DIR, load_script, make_skill, run_script

packager = load_script("package-skill")
validator = load_script("validate-skill")


class PackageTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()


class BuildTest(PackageTestCase):
    def test_builds_a_verified_archive_of_the_real_skill(self):
        status, result = packager.package(SKILL_DIR, self.root / "dist")
        self.assertEqual(status, 0, result)
        archive = Path(result["archive"])
        self.assertEqual(archive.name, "mych-plugin-1.0.0.zip")
        with zipfile.ZipFile(archive) as zf:
            names = zf.namelist()
        self.assertTrue(all(name.startswith("mych-plugin/") for name in names))
        self.assertIn("mych-plugin/SKILL.md", names)
        expected_files, _ = packager.collect_files(SKILL_DIR, validator)
        self.assertEqual(result["facts"]["files"], len(expected_files))
        self.assertEqual(result["verification_errors"], [])

    def test_builds_are_byte_identical(self):
        _, first = packager.package(SKILL_DIR, self.root / "one")
        _, second = packager.package(SKILL_DIR, self.root / "two")
        self.assertEqual(Path(first["archive"]).read_bytes(), Path(second["archive"]).read_bytes())

    def test_scripts_are_executable_and_documents_are_not(self):
        _, result = packager.package(SKILL_DIR, self.root / "dist")
        with zipfile.ZipFile(result["archive"]) as zf:
            modes = {info.filename: (info.external_attr >> 16) & 0o777 for info in zf.infolist()}
        self.assertEqual(modes["mych-plugin/scripts/validate-skill.py"], 0o755)
        self.assertEqual(modes["mych-plugin/SKILL.md"], 0o644)

    def test_archive_file_is_world_readable(self):
        _, result = packager.package(SKILL_DIR, self.root / "dist")
        self.assertEqual(os.stat(result["archive"]).st_mode & 0o777, 0o644)

    def test_source_date_epoch_sets_timestamps(self):
        with mock.patch.dict(os.environ, {"SOURCE_DATE_EPOCH": "1700000000"}):
            _, result = packager.package(SKILL_DIR, self.root / "dist")
        with zipfile.ZipFile(result["archive"]) as zf:
            self.assertEqual(zf.getinfo("mych-plugin/SKILL.md").date_time[:3], (2023, 11, 14))

    def test_development_artifacts_are_excluded(self):
        copy = self.root / "src" / "mych-plugin"
        shutil.copytree(SKILL_DIR, copy)
        (copy / "scripts" / "__pycache__").mkdir(exist_ok=True)
        (copy / "scripts" / "__pycache__" / "x.pyc").write_bytes(b"\0")
        (copy / ".DS_Store").write_bytes(b"\0")
        (copy / "core" / "notes.md~").write_text("backup", encoding="utf-8")
        status, result = packager.package(copy, self.root / "dist")
        self.assertEqual(status, 0, result)
        with zipfile.ZipFile(result["archive"]) as zf:
            names = zf.namelist()
        self.assertFalse(any("__pycache__" in name or ".DS_Store" in name or name.endswith("~") for name in names))
        self.assertTrue(result["skipped"])

    def test_output_inside_skill_is_refused(self):
        skill = make_skill(self.root)
        status, result = packager.package(skill, skill / "dist")
        self.assertEqual(status, 2)
        self.assertIn("outside the skill folder", result["error"])

    def test_validation_failure_blocks_packaging(self):
        skill = make_skill(self.root, body="# Demo\n\n[missing](missing.md)\n" + "line\n" * 8)
        status, result = packager.package(skill, self.root / "dist")
        self.assertEqual(status, 1)
        self.assertEqual(result["error"], "validation failed")
        self.assertFalse((self.root / "dist").exists() and any((self.root / "dist").iterdir()))

    def test_unversioned_skill_uses_plain_name(self):
        skill = make_skill(self.root)
        status, result = packager.package(skill, self.root / "dist")
        self.assertEqual(status, 0, result)
        self.assertEqual(Path(result["archive"]).name, "demo-skill.zip")


class VerifyTest(PackageTestCase):
    def write_zip(self, entries):
        path = self.root / "test.zip"
        with zipfile.ZipFile(path, "w") as zf:
            for name, data in entries.items():
                zf.writestr(name, data)
        return path

    def test_skill_md_at_archive_root_is_rejected(self):
        path = self.write_zip({"SKILL.md": "---\nname: demo\ndescription: x\n---\n"})
        errors, _ = packager.verify_archive(path, validator)
        self.assertTrue(errors)

    def test_unsafe_paths_are_rejected(self):
        path = self.write_zip({
            "demo/SKILL.md": "---\nname: demo\ndescription: Use when testing.\n---\n",
            "demo/../evil.txt": "x",
        })
        errors, _ = packager.verify_archive(path, validator)
        self.assertTrue(any("unsafe entry path" in error for error in errors))

    def test_name_mismatch_is_rejected(self):
        path = self.write_zip({"demo/SKILL.md": "---\nname: other\ndescription: Use when testing.\n---\n"})
        errors, _ = packager.verify_archive(path, validator)
        self.assertTrue(any("does not match the top-level folder" in error for error in errors))

    def test_content_mismatch_is_detected(self):
        _, result = packager.package(SKILL_DIR, self.root / "dist")
        archive = Path(result["archive"])
        files, _ = packager.collect_files(SKILL_DIR, validator)
        expected = {"mych-plugin/" + rel: hashlib.sha256(path.read_bytes()).hexdigest() for rel, path in files}
        expected["mych-plugin/SKILL.md"] = "0" * 64
        errors, _ = packager.verify_archive(archive, validator, expected=expected, skill_name="mych-plugin")
        self.assertTrue(any("differs from the source" in error for error in errors))

    def test_cli_verify_only(self):
        _, result = packager.package(SKILL_DIR, self.root / "dist")
        completed = run_script("package-skill", "--verify-only", result["archive"])
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertIn("verified", completed.stdout)

    def test_packaging_does_not_write_bytecode_into_the_skill(self):
        run_script("package-skill", str(SKILL_DIR), "--out", str(self.root / "dist"))
        self.assertFalse((SKILL_DIR / "scripts" / "__pycache__").exists())


if __name__ == "__main__":
    unittest.main()
