"""Tests for mych-plugin/scripts/validate-skill.py."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from support import SKILL_DIR, call_main, load_script, make_skill

validator = load_script("validate-skill")

try:
    import yaml  # noqa: F401
    HAVE_YAML = True
except ImportError:
    HAVE_YAML = False


def all_errors(report):
    return [message for check in report.checks.values() for message in check.errors]


def all_warnings(report):
    return [message for check in report.checks.values() for message in check.warnings]


class RealPackageTest(unittest.TestCase):
    def test_mych_plugin_passes_strict_validation(self):
        report = validator.validate_skill(SKILL_DIR)
        self.assertEqual(all_errors(report), [])
        self.assertEqual(all_warnings(report), [])
        self.assertTrue(report.ok(strict=True))
        self.assertEqual(report.skill_name, "mych-plugin")

    def test_cli_strict_exit_code(self):
        status, out, _ = call_main(validator, [str(SKILL_DIR), "--strict"])
        self.assertEqual(status, 0, out)
        self.assertIn("Result: PASSED", out)


class SkillFolderTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def validate(self, **kwargs):
        return validator.validate_skill(make_skill(self.root, **kwargs))

    def assertErrorContains(self, report, text):
        errors = all_errors(report)
        self.assertTrue(any(text in message for message in errors), "{!r} not in {}".format(text, errors))

    def assertWarningContains(self, report, text):
        warnings = all_warnings(report)
        self.assertTrue(any(text in message for message in warnings), "{!r} not in {}".format(text, warnings))


class StructureAndFrontmatterTest(SkillFolderTestCase):
    def test_minimal_skill_is_valid(self):
        report = self.validate()
        self.assertEqual(all_errors(report), [])

    def test_missing_skill_md(self):
        folder = self.root / "empty-skill"
        folder.mkdir()
        report = validator.validate_skill(folder)
        self.assertErrorContains(report, "SKILL.md is missing")

    def test_skill_md_must_be_exact_case(self):
        skill = make_skill(self.root)
        (skill / "SKILL.md").rename(skill / "skill.md")
        report = validator.validate_skill(skill)
        self.assertErrorContains(report, "must be named exactly SKILL.md")

    def test_frontmatter_must_open_on_line_one(self):
        skill = make_skill(self.root)
        (skill / "SKILL.md").write_text("# Title\n\nNo frontmatter here.\n", encoding="utf-8")
        report = validator.validate_skill(skill)
        self.assertErrorContains(report, "must start with a '---' line")

    def test_frontmatter_must_close(self):
        skill = make_skill(self.root)
        (skill / "SKILL.md").write_text("---\nname: demo-skill\ndescription: x\n", encoding="utf-8")
        report = validator.validate_skill(skill)
        self.assertErrorContains(report, "never closed")

    def test_tab_indentation_rejected(self):
        report = self.validate(
            frontmatter="name: demo-skill\ndescription: Formats demo reports. Use when asked.\nmetadata:\n\tversion: \"1\"\n")
        self.assertErrorContains(report, "tab")

    def test_duplicate_field_rejected(self):
        report = self.validate(frontmatter="name: demo-skill\nname: demo-skill\ndescription: Use when testing it.\n")
        self.assertErrorContains(report, "duplicate field 'name'")

    def test_unknown_field_rejected(self):
        report = self.validate(
            frontmatter="name: demo-skill\ndescription: Formats reports. Use when asked.\nversion: \"1.0.0\"\n")
        self.assertErrorContains(report, "unknown frontmatter field(s): version")

    def test_value_typed_by_yaml_is_flagged(self):
        report = self.validate(frontmatter=(
            "name: demo-skill\ndescription: Formats reports. Use when asked.\nmetadata:\n  version: 1.0\n"))
        self.assertErrorContains(report, "read as a number")

    def test_colon_space_in_plain_value_is_rejected(self):
        report = self.validate(frontmatter="name: demo-skill\ndescription: Use this: for reports\n")
        self.assertErrorContains(report, "cannot contain ': '")

    def test_inline_comment_warning(self):
        report = self.validate(frontmatter="name: demo-skill\ndescription: Formats reports #1. Use when asked.\n")
        self.assertWarningContains(report, "YAML comment")

    def test_folded_block_description(self):
        text = "---\nname: demo-skill\ndescription: >-\n  Formats demo reports\n  for the team. Use when asked.\n---\nbody\n"
        parsed = validator.parse_frontmatter(text)
        self.assertEqual(parsed.errors, [])
        self.assertEqual(parsed.data["description"], "Formats demo reports for the team. Use when asked.")

    @unittest.skipUnless(HAVE_YAML, "PyYAML not installed")
    def test_builtin_parser_agrees_with_pyyaml(self):
        import yaml
        samples = [
            'name: demo\ndescription: "Quoted \\"text\\" with \\u00e9scapes"\n',
            "name: demo\ndescription: 'It''s single quoted'\n",
            "name: demo\ndescription: |\n  Line one\n  Line two\n\n",
            "name: demo\ndescription: >\n  Folded one\n  folded two\n\n  New paragraph\n",
            "name: demo\ndescription: plain value\n  continued here\nallowed-tools:\n  - Read\n  - Grep\n",
            "name: demo\nmetadata:\n  author: Kim\n  version: \"1.0.0\"\ndescription: x\n",
            "name: demo\ndescription: >+\n  kept\n\n",
        ]
        for sample in samples:
            with self.subTest(sample=sample):
                parsed = validator.parse_frontmatter("---\n" + sample + "---\nbody\n")
                self.assertEqual(parsed.errors, [])
                self.assertFalse(any("outside the conservative subset" in w for w in parsed.warnings))
                self.assertEqual(parsed.data, yaml.safe_load(sample))

    def test_flow_collections_are_unsupported_without_crashing(self):
        parsed = validator.parse_frontmatter("---\nname: demo\ndescription: x\nallowed-tools: [Read, Grep]\n---\n")
        if HAVE_YAML:
            self.assertTrue(any("outside the conservative subset" in w for w in parsed.warnings))
        else:
            self.assertTrue(any("flow collections" in e for e in parsed.errors))


class MetadataAndNamingTest(SkillFolderTestCase):
    def test_missing_description(self):
        report = self.validate(frontmatter="name: demo-skill\n")
        self.assertErrorContains(report, "required field 'description'")

    def test_description_too_long(self):
        report = self.validate(frontmatter="name: demo-skill\ndescription: {}\n".format("Use when asked. " * 70))
        self.assertErrorContains(report, "the limit is 1024")

    def test_description_with_xml_tag(self):
        report = self.validate(frontmatter="name: demo-skill\ndescription: Formats <b>reports</b>. Use when asked.\n")
        self.assertErrorContains(report, "XML or HTML tags")

    def test_description_without_when_cue_warns(self):
        report = self.validate(frontmatter="name: demo-skill\ndescription: Formats demo reports in a tidy layout.\n")
        self.assertWarningContains(report, "say when to use the skill")

    def test_name_must_match_folder(self):
        report = self.validate(name="demo-skill", frontmatter="name: other-skill\ndescription: Use when asked to.\n")
        self.assertErrorContains(report, "must match the folder name")

    def test_invalid_names(self):
        for bad in ("Demo-Skill", "demo--skill", "-demo", "demo_skill"):
            with self.subTest(name=bad):
                report = validator.validate_skill(make_skill(
                    self.root / bad.strip("-").lower(), name=bad,
                    frontmatter="name: {}\ndescription: Use when testing names.\n".format(bad)))
                self.assertErrorContains(report, "must use lowercase letters")

    def test_reserved_word(self):
        report = self.validate(name="claude-helper",
                               frontmatter="name: claude-helper\ndescription: Use when testing names.\n")
        self.assertErrorContains(report, "reserved word 'claude'")

    def test_name_too_long(self):
        long_name = "a" * 65
        report = self.validate(name=long_name, frontmatter="name: {}\ndescription: Use when testing.\n".format(long_name))
        self.assertErrorContains(report, "the limit is 64")


class ReferencesAndLinksTest(SkillFolderTestCase):
    def test_broken_link(self):
        report = self.validate(body="# Demo\n\nSee [the guide](references/missing.md).\n" + "line\n" * 8)
        self.assertErrorContains(report, "does not exist")

    def test_anchor_checking(self):
        body = "# Demo\n\n## Setup steps\n\nJump to [setup](#setup-steps) or [nowhere](#nowhere).\n" + "line\n" * 8
        report = self.validate(body=body)
        errors = all_errors(report)
        self.assertTrue(any("#nowhere" in message for message in errors))
        self.assertFalse(any("#setup-steps" in message for message in errors))

    def test_link_outside_skill(self):
        report = self.validate(body="# Demo\n\nSee [readme](../README.md).\n" + "line\n" * 8)
        self.assertErrorContains(report, "points outside the skill folder")

    def test_missing_skill_dir_reference(self):
        report = self.validate(body="# Demo\n\nRun `python3 ${CLAUDE_SKILL_DIR}/scripts/missing.py`.\n" + "line\n" * 8)
        self.assertErrorContains(report, "${CLAUDE_SKILL_DIR}/scripts/missing.py")

    def test_unreferenced_file_warns_for_generic_skills(self):
        report = self.validate(files={"references/notes.md": "# Notes\n" + "Useful line.\n" * 10})
        self.assertWarningContains(report, "not referenced from SKILL.md")

    def test_linked_file_counts_as_referenced(self):
        body = "# Demo\n\nRead [notes](references/notes.md).\n" + "line\n" * 8
        report = self.validate(body=body, files={"references/notes.md": "# Notes\n" + "Useful line.\n" * 10})
        self.assertFalse(any("not referenced" in message for message in all_warnings(report)))

    def test_github_slug(self):
        cases = {
            "Track A: new product or interface": "track-a-new-product-or-interface",
            "Verification, optimization and delivery": "verification-optimization-and-delivery",
            "`scripts/` folder": "scripts-folder",
            "Hello \u2014 World": "hello--world",
            "1. Intelligence before execution": "1-intelligence-before-execution",
            "**Bold** heading": "bold-heading",
        }
        for heading, slug in cases.items():
            with self.subTest(heading=heading):
                self.assertEqual(validator.github_slug(heading), slug)

    def test_duplicate_headings_get_numbered_anchors(self):
        info = validator.scan_markdown(Path("x.md"), "## Setup\ntext\n## Setup\n")
        self.assertEqual(info.anchors, {"setup", "setup-1"})

    def test_code_fences_are_ignored_for_links(self):
        info = validator.scan_markdown(Path("x.md"), "```\n[not a link](missing.md)\n```\n[real](real.md)\n")
        self.assertEqual([target for _, target in info.links], ["real.md"])


class ContentAndHygieneTest(SkillFolderTestCase):
    def test_empty_file(self):
        report = self.validate(body="# Demo\n\n[empty](references/empty.md)\n" + "line\n" * 8,
                               files={"references/empty.md": ""})
        self.assertErrorContains(report, "file is empty")

    def test_placeholder_marker(self):
        report = self.validate(body="# Demo\n\n[draft](references/draft.md)\n" + "line\n" * 8,
                               files={"references/draft.md": "# Draft\n\nTODO: write this section\n" + "x\n" * 8})
        self.assertErrorContains(report, "placeholder text")

    def test_python_syntax_error(self):
        report = self.validate(body="# Demo\n\nRun `scripts/broken.py`.\n" + "line\n" * 8,
                               files={"scripts/broken.py": "def broken(:\n    pass\n"})
        self.assertErrorContains(report, "Python syntax error")

    def test_development_artifacts_warn(self):
        skill = make_skill(self.root)
        (skill / "__pycache__").mkdir()
        (skill / "__pycache__" / "x.pyc").write_bytes(b"\0")
        (skill / ".DS_Store").write_bytes(b"\0")
        report = validator.validate_skill(skill)
        self.assertEqual(all_errors(report), [])
        self.assertWarningContains(report, "__pycache__")
        self.assertWarningContains(report, ".DS_Store")

    def test_secret_file_is_an_error(self):
        report = self.validate(files={".env": "API_KEY=abc\n"})
        self.assertErrorContains(report, "secret-like file '.env'")

    def test_classify_path(self):
        self.assertIsNone(validator.classify_path(("scripts", "tool.py")))
        self.assertEqual(validator.classify_path((".env.local",))[0], "secret")
        self.assertEqual(validator.classify_path((".env.example",))[0], "artifact")
        self.assertEqual(validator.classify_path(("keys", "server.pem"))[0], "secret")
        self.assertEqual(validator.classify_path(("node_modules",), is_dir=True)[0], "artifact")
        self.assertEqual(validator.classify_path(("notes.md~",))[0], "artifact")

    def test_cli_usage_errors(self):
        status, _, err = call_main(validator, [str(self.root / "does-not-exist")])
        self.assertEqual(status, 2)
        self.assertIn("does not exist", err)

    def test_cli_failure_exit_code(self):
        skill = make_skill(self.root, frontmatter="name: wrong-name\ndescription: Use when testing.\n")
        status, out, _ = call_main(validator, [str(skill)])
        self.assertEqual(status, 1)
        self.assertIn("Result: FAILED", out)


if __name__ == "__main__":
    unittest.main()


SPECIALIST_SECTIONS = ["Identity", "Core knowledge", "Workflows", "Decision rules", "Tool requirements",
                       "Inputs and outputs", "Quality standards", "Failure modes", "Security", "Examples",
                       "Integration", "Testing criteria"]


def specialist_body(skip=None, extra_links=""):
    parts = ["# Demo specialist", "", "Reference: [guide](references/guide.md)." + extra_links, ""]
    for section in SPECIALIST_SECTIONS:
        if section == skip:
            continue
        parts += ["## " + section, "", "Content for {} that is long enough to be real guidance.".format(section), ""]
    return "\n".join(parts)


SPECIALIST_FRONTMATTER = (
    "name: mych-demo\n"
    "description: Demo specialist for validator tests. Use when testing the specialist layout.\n"
    "metadata:\n  version: \"2.0.0\"\n  display-name: Demo\n  framework: MYCH-HORIZON\n")


class SpecialistLayoutTest(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self):
        self._tmp.cleanup()

    def build(self, body=None, frontmatter=SPECIALIST_FRONTMATTER, files=None):
        all_files = {"references/guide.md": "# Guide\n\nUseful reference text for the demo specialist.\n"}
        all_files.update(files or {})
        return make_skill(self.root, "mych-demo", frontmatter=frontmatter,
                          body=specialist_body() if body is None else body, files=all_files)

    def test_complete_specialist_passes(self):
        report = validator.validate_skill(self.build())
        self.assertEqual(report.error_count(), 0, validator.format_report(report))
        self.assertIn("applied the 'mych-specialist' layout rules", validator.format_report(report))

    def test_missing_section_is_an_error(self):
        report = validator.validate_skill(self.build(body=specialist_body(skip="Failure modes")))
        self.assertIn("missing the required section '## Failure modes'", validator.format_report(report))
        self.assertGreater(report.error_count(), 0)

    def test_framework_metadata_is_required(self):
        frontmatter = SPECIALIST_FRONTMATTER.replace("  framework: MYCH-HORIZON\n", "")
        report = validator.validate_skill(self.build(frontmatter=frontmatter))
        self.assertIn("requires metadata 'framework'", validator.format_report(report))

    def test_snake_case_python_allowed_but_other_names_strict(self):
        links = " Tools: [codec](scripts/png_codec.py), [bad](scripts/BadName.py)."
        report = validator.validate_skill(self.build(body=specialist_body(extra_links=links), files={
            "scripts/png_codec.py": "print('ok')\n", "scripts/BadName.py": "print('bad')\n"}))
        rendered = validator.format_report(report)
        self.assertNotIn("png_codec.py: file name", rendered)
        self.assertIn("BadName.py: file name is not lowercase kebab-case", rendered)

    def test_unreferenced_file_is_an_error_for_specialists(self):
        report = validator.validate_skill(self.build(files={"references/orphan.md": "# Orphan\n\nNot linked.\n"}))
        self.assertIn("references/orphan.md: not referenced from SKILL.md", validator.format_report(report))
        self.assertGreater(report.error_count(), 0)
