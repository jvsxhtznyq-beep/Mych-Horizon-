#!/usr/bin/env python3
"""Build an upload-ready ZIP of an Agent Skill, then verify the archive.

The archive holds the skill folder as its single top-level entry
(<skill-name>/SKILL.md, <skill-name>/scripts/..., and so on), which is the
layout Claude's skill upload expects. Hidden files, development artifacts
and secret-like files are left out, using the same rules as
validate-skill.py. Builds are deterministic: entries are sorted, timestamps
and permissions are fixed, so the same input produces the same archive
bytes with the same Python and zlib build.

Usage:
  python3 package-skill.py [SKILL_DIR] [--out DIR]
  python3 package-skill.py --verify-only path/to/skill.zip

SKILL_DIR defaults to the skill that contains this script; --out defaults
to a 'dist' folder next to the skill folder. Exit status is 0 on success,
1 when validation or verification fails, and 2 for usage errors.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.util
import json
import os
import sys
import tempfile
import time
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Optional, Sequence, Tuple

# The ZIP format cannot store dates before 1980; using its earliest date keeps
# builds reproducible. SOURCE_DATE_EPOCH, when set, overrides it.
DEFAULT_TIMESTAMP = (1980, 1, 1, 0, 0, 0)
# Claude's skill upload documentation caps a skill at 30 MB uncompressed.
MAX_UNCOMPRESSED_BYTES = 30 * 1024 * 1024
# Files under scripts/ with these suffixes are stored as executable.
EXECUTABLE_SUFFIXES = (".py", ".sh")
FILE_MODE = 0o100644
EXECUTABLE_MODE = 0o100755
DIRECTORY_MODE = 0o40755
MSDOS_DIRECTORY_FLAG = 0x10
UNIX_SYSTEM = 3
# Permissions of the archive file itself on disk.
ARCHIVE_FILE_MODE = 0o644

DEFAULT_SKILL_DIR = Path(__file__).resolve().parent.parent


def load_validator() -> Any:
    """Import validate-skill.py from this folder (its name is not importable directly)."""
    path = Path(__file__).resolve().with_name("validate-skill.py")
    spec = importlib.util.spec_from_file_location("mych_validate_skill", path)
    if spec is None or spec.loader is None:
        raise ImportError("cannot load {}".format(path))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    # Importing would otherwise write __pycache__ into the skill folder itself.
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        spec.loader.exec_module(module)
    finally:
        sys.dont_write_bytecode = previous
    return module


def build_timestamp() -> Tuple[int, int, int, int, int, int]:
    raw = os.environ.get("SOURCE_DATE_EPOCH")
    if not raw:
        return DEFAULT_TIMESTAMP
    try:
        moment = time.gmtime(int(raw))
    except (ValueError, OverflowError, OSError):
        return DEFAULT_TIMESTAMP
    if moment.tm_year < 1980:
        return DEFAULT_TIMESTAMP
    return (moment.tm_year, moment.tm_mon, moment.tm_mday, moment.tm_hour, moment.tm_min, moment.tm_sec)


def collect_files(skill_dir: Path, validator: Any) -> Tuple[List[Tuple[str, Path]], List[str]]:
    """Return (relative POSIX path, absolute path) pairs to package, plus skipped-item notes."""
    files: List[Tuple[str, Path]] = []
    skipped: List[str] = []
    root = skill_dir.resolve()
    for current, dirnames, filenames in os.walk(root, followlinks=False):
        current_path = Path(current)
        kept = []
        for dirname in sorted(dirnames):
            dir_path = current_path / dirname
            rel_parts = dir_path.relative_to(root).parts
            verdict = validator.classify_path(rel_parts, is_dir=True)
            if dir_path.is_symlink():
                skipped.append("{} (symbolic link)".format(PurePosixPath(*rel_parts)))
            elif verdict:
                skipped.append("{} ({})".format(PurePosixPath(*rel_parts), verdict[1]))
            else:
                kept.append(dirname)
        dirnames[:] = kept
        for filename in sorted(filenames):
            file_path = current_path / filename
            rel_parts = file_path.relative_to(root).parts
            verdict = validator.classify_path(rel_parts)
            if file_path.is_symlink():
                skipped.append("{} (symbolic link)".format(PurePosixPath(*rel_parts)))
            elif verdict:
                skipped.append("{} ({})".format(PurePosixPath(*rel_parts), verdict[1]))
            else:
                files.append((PurePosixPath(*rel_parts).as_posix(), file_path))
    files.sort(key=lambda item: item[0])
    return files, skipped


def file_mode(rel_path: str) -> int:
    parts = rel_path.split("/")
    if parts[0] == "scripts" and rel_path.endswith(EXECUTABLE_SUFFIXES):
        return EXECUTABLE_MODE
    return FILE_MODE


def write_archive(destination: Path, skill_name: str, files: Sequence[Tuple[str, Path]]) -> Dict[str, str]:
    """Write a deterministic ZIP and return {archive path: sha256} for the files written."""
    timestamp = build_timestamp()
    digests: Dict[str, str] = {}
    directories = {skill_name + "/"}
    for rel_path, _ in files:
        parts = rel_path.split("/")[:-1]
        for depth in range(1, len(parts) + 1):
            directories.add("{}/{}/".format(skill_name, "/".join(parts[:depth])))
    entries: List[Tuple[str, Optional[bytes], int]] = [(name, None, DIRECTORY_MODE) for name in directories]
    for rel_path, path in files:
        data = path.read_bytes()
        arcname = "{}/{}".format(skill_name, rel_path)
        digests[arcname] = hashlib.sha256(data).hexdigest()
        entries.append((arcname, data, file_mode(rel_path)))
    entries.sort(key=lambda entry: entry[0])

    destination.parent.mkdir(parents=True, exist_ok=True)
    # Temporary files are created private (0600); a release archive gets
    # normal read permissions instead.
    handle, temp_name = tempfile.mkstemp(prefix=".package-", suffix=".zip", dir=str(destination.parent))
    os.close(handle)
    os.chmod(temp_name, ARCHIVE_FILE_MODE)
    try:
        with zipfile.ZipFile(temp_name, "w") as archive:
            for arcname, data, mode in entries:
                info = zipfile.ZipInfo(arcname, date_time=timestamp)
                info.create_system = UNIX_SYSTEM
                if data is None:
                    info.external_attr = (mode << 16) | MSDOS_DIRECTORY_FLAG
                    info.compress_type = zipfile.ZIP_STORED
                    archive.writestr(info, b"")
                else:
                    info.external_attr = mode << 16
                    info.compress_type = zipfile.ZIP_DEFLATED
                    archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED, compresslevel=9)
        os.replace(temp_name, str(destination))
    except BaseException:
        if os.path.exists(temp_name):
            os.unlink(temp_name)
        raise
    return digests


def verify_archive(
    archive_path: Path,
    validator: Any,
    expected: Optional[Dict[str, str]] = None,
    skill_name: Optional[str] = None,
) -> Tuple[List[str], Dict[str, Any]]:
    """Check an archive's structure and contents. Returns (errors, facts)."""
    errors: List[str] = []
    facts: Dict[str, Any] = {}
    try:
        archive = zipfile.ZipFile(str(archive_path))
    except (zipfile.BadZipFile, OSError) as exc:
        return ["cannot open {} as a ZIP archive: {}".format(archive_path, exc)], facts
    with archive:
        corrupt = archive.testzip()
        if corrupt:
            errors.append("CRC check failed for {}".format(corrupt))
        infos = archive.infolist()
        names = [info.filename for info in infos]
        if len(names) != len(set(names)):
            errors.append("the archive contains duplicate entries")
        tops = {name.split("/", 1)[0] for name in names if name}
        if skill_name is None:
            skill_name = sorted(tops)[0] if len(tops) == 1 else None
        if len(tops) != 1 or skill_name not in tops:
            errors.append("the archive must contain exactly one top-level folder named after the skill; found {}".format(
                ", ".join(sorted(tops)) or "nothing"))
        for name in names:
            path = PurePosixPath(name)
            if name.startswith("/") or "\\" in name or ".." in path.parts or (path.parts and ":" in path.parts[0]):
                errors.append("unsafe entry path {!r}".format(name))
            parts = path.parts[1:]
            if parts and validator.classify_path(parts, is_dir=name.endswith("/")):
                errors.append("excluded item packaged: {}".format(name))
        file_infos = [info for info in infos if not info.filename.endswith("/")]
        total = sum(info.file_size for info in file_infos)
        facts.update({
            "skill_name": skill_name,
            "files": len(file_infos),
            "directories": len(infos) - len(file_infos),
            "uncompressed_bytes": total,
            "compressed_bytes": sum(info.compress_size for info in file_infos),
        })
        if total > MAX_UNCOMPRESSED_BYTES:
            errors.append("uncompressed size {} bytes exceeds the {} byte upload limit".format(
                total, MAX_UNCOMPRESSED_BYTES))
        skill_md = "{}/SKILL.md".format(skill_name) if skill_name else None
        if not skill_md or skill_md not in names:
            errors.append("{} is missing from the archive".format(skill_md or "<skill>/SKILL.md"))
        else:
            text = archive.read(skill_md).decode("utf-8", errors="replace")
            parsed = validator.parse_frontmatter(text)
            name = parsed.data.get("name") if isinstance(parsed.data, dict) else None
            if parsed.errors:
                errors.append("SKILL.md frontmatter in the archive has errors: {}".format("; ".join(parsed.errors)))
            if name != skill_name:
                errors.append("frontmatter name {!r} does not match the top-level folder {!r}".format(name, skill_name))
            facts["version"] = (parsed.data.get("metadata") or {}).get("version") if isinstance(
                parsed.data, dict) and isinstance(parsed.data.get("metadata"), dict) else None
        if expected is not None:
            packaged = {info.filename for info in file_infos}
            missing = sorted(set(expected) - packaged)
            extra = sorted(packaged - set(expected))
            if missing:
                errors.append("files missing from the archive: {}".format(", ".join(missing)))
            if extra:
                errors.append("unexpected files in the archive: {}".format(", ".join(extra)))
            for arcname, digest in sorted(expected.items()):
                if arcname in packaged:
                    actual = hashlib.sha256(archive.read(arcname)).hexdigest()
                    if actual != digest:
                        errors.append("content of {} differs from the source".format(arcname))
    return errors, facts


def _human(size: int) -> str:
    value = float(size)
    for unit in ("bytes", "KB", "MB"):
        if value < 1024 or unit == "MB":
            return "{:.0f} {}".format(value, unit) if unit == "bytes" else "{:.1f} {}".format(value, unit)
        value /= 1024
    return "{} bytes".format(size)


def package(skill_dir: Path, out_dir: Path, validate: bool = True, strict: bool = False) -> Tuple[int, Dict[str, Any]]:
    """Validate, build and verify. Returns (exit status, result details)."""
    validator = load_validator()
    root = skill_dir.resolve()
    out = out_dir.resolve()
    result: Dict[str, Any] = {"skill_dir": str(root), "ok": False}
    try:
        out.relative_to(root)
        result["error"] = "the output folder must be outside the skill folder"
        return 2, result
    except ValueError:
        pass

    if validate:
        report = validator.validate_skill(root)
        result["validation"] = {"errors": report.error_count(), "warnings": report.warning_count()}
        if not report.ok(strict=strict):
            result["error"] = "validation failed"
            result["validation_report"] = validator.format_report(report, strict=strict)
            return 1, result

    skill_md = root / "SKILL.md"
    parsed = validator.parse_frontmatter(skill_md.read_text(encoding="utf-8"))
    name = parsed.data.get("name") if isinstance(parsed.data, dict) else None
    if not isinstance(name, str) or not name:
        result["error"] = "SKILL.md has no usable 'name'"
        return 1, result
    meta = parsed.data.get("metadata") if isinstance(parsed.data.get("metadata"), dict) else {}
    version = meta.get("version") if isinstance(meta.get("version"), str) else None
    archive_name = "{}-{}.zip".format(name, version) if version else "{}.zip".format(name)
    destination = out / archive_name

    files, skipped = collect_files(root, validator)
    replaced = destination.exists()
    digests = write_archive(destination, name, files)
    errors, facts = verify_archive(destination, validator, expected=digests, skill_name=name)
    archive_hash = hashlib.sha256(destination.read_bytes()).hexdigest()
    result.update({
        "archive": str(destination),
        "replaced_existing": replaced,
        "skipped": skipped,
        "sha256": archive_hash,
        "facts": facts,
        "verification_errors": errors,
        "ok": not errors,
    })
    return (0 if not errors else 1), result


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description="Package an Agent Skill folder into an upload-ready, verified ZIP.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python3 package-skill.py                       package the skill containing this script\n"
            "  python3 package-skill.py path/to/skill --out dist\n"
            "  python3 package-skill.py --verify-only dist/my-skill-1.0.0.zip\n"
            "\nexit status: 0 success, 1 validation or verification failed, 2 usage error"
        ),
    )
    parser.add_argument("skill_dir", nargs="?", default=str(DEFAULT_SKILL_DIR),
                        help="skill folder to package (default: the skill containing this script)")
    parser.add_argument("--out", help="output folder (default: 'dist' next to the skill folder)")
    parser.add_argument("--strict", action="store_true", help="refuse to package when validation has warnings")
    parser.add_argument("--no-validate", action="store_true", help="skip validation (not recommended)")
    parser.add_argument("--verify-only", metavar="ZIP", help="verify an existing archive instead of building one")
    parser.add_argument("--json", action="store_true", help="print the result as JSON")
    args = parser.parse_args(argv)

    if args.verify_only:
        archive_path = Path(args.verify_only).expanduser()
        if not archive_path.is_file():
            print("error: {} is not a file".format(archive_path), file=sys.stderr)
            return 2
        validator = load_validator()
        errors, facts = verify_archive(archive_path, validator)
        if args.json:
            print(json.dumps({"archive": str(archive_path), "ok": not errors, "errors": errors, "facts": facts},
                             indent=2))
        else:
            for error in errors:
                print("error: {}".format(error))
            print("{}: {} ({} files)".format(archive_path, "verified" if not errors else "FAILED",
                                             facts.get("files", 0)))
        return 0 if not errors else 1

    skill_dir = Path(args.skill_dir).expanduser()
    if not skill_dir.is_dir():
        print("error: {} is not a directory".format(skill_dir), file=sys.stderr)
        return 2
    out_dir = Path(args.out).expanduser() if args.out else skill_dir.resolve().parent / "dist"
    status, result = package(skill_dir, out_dir, validate=not args.no_validate, strict=args.strict)

    if args.json:
        print(json.dumps(result, indent=2))
        return status
    if "validation_report" in result:
        print(result["validation_report"])
    if result.get("error"):
        print("error: {}".format(result["error"]), file=sys.stderr)
        return status
    facts = result.get("facts", {})
    print("Packaged {} {}".format(facts.get("skill_name"), facts.get("version") or ""))
    print("  archive: {}{}".format(result["archive"], " (replaced existing file)" if result["replaced_existing"] else ""))
    print("  files:   {} (plus {} folder entries)".format(facts.get("files"), facts.get("directories")))
    print("  size:    {} compressed, {} uncompressed".format(
        _human(facts.get("compressed_bytes", 0)), _human(facts.get("uncompressed_bytes", 0))))
    print("  sha256:  {}".format(result["sha256"]))
    if result["skipped"]:
        print("  skipped: {}".format("; ".join(result["skipped"])))
    if result["verification_errors"]:
        for error in result["verification_errors"]:
            print("error: {}".format(error))
        print("Archive verification FAILED")
    else:
        print("Archive verified: single top-level folder, SKILL.md present, frontmatter valid, "
              "contents match the source, CRC OK.")
    return status


if __name__ == "__main__":
    sys.exit(main())
