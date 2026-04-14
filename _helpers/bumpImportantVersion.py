#!/usr/bin/env python3
"""Bump version using a central VERSION file.

Behavior:
- Uses VERSION.txt as source of truth.
- Bumps only when at least one important app file changed (unless --force).
- Synchronizes the bumped version to key app files only to avoid noisy commits.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from datetime import date
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
APP_ROOT = SCRIPT_DIR.parent
VERSION_FILE = APP_ROOT / "VERSION.txt"

VERSION_TAG_FILES = [
    APP_ROOT / "app.py",
    APP_ROOT / "static" / "index.html",
    APP_ROOT / "fetch_fab_library.py",
    APP_ROOT / "cache_manager.py",
    APP_ROOT / "models.py",
    APP_ROOT / "errors.py",
    APP_ROOT / "README.md",
    APP_ROOT / "_helpers" / "specs.md",
    APP_ROOT / "tests" / "test_api.py",
    APP_ROOT / "tests" / "test_cache.py",
    APP_ROOT / "tests" / "test_connection.py",
    APP_ROOT / "tests" / "test_parser.py",
]

IMPORTANT_FILES = [
    APP_ROOT / "app.py",
    APP_ROOT / "static" / "index.html",
    APP_ROOT / "fetch_fab_library.py",
    APP_ROOT / "cache_manager.py",
    APP_ROOT / "models.py",
    APP_ROOT / "errors.py",
    APP_ROOT / "openapi.yaml",
    APP_ROOT / "start-FabAssetsManager.bat",
]

SYNC_FILES = [
    *VERSION_TAG_FILES,
    APP_ROOT / "API_GUIDE.md",
    APP_ROOT / "openapi.yaml",
    APP_ROOT / "CHANGELOG.md",
    VERSION_FILE,
]

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bump version for important files only")
    parser.add_argument("--scope", choices=["patch", "minor", "major"], default="patch", help="Semver bump scope")
    parser.add_argument("--base-ref", default="HEAD", help="Git ref used to detect changes")
    parser.add_argument("--force", action="store_true", help="Force bump even if no important file changed")
    parser.add_argument("--dry-run", action="store_true", help="Show planned changes without writing files")
    return parser.parse_args()


def run_git_command(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(args, cwd=str(cwd), capture_output=True, text=True, check=False)


def get_repo_root() -> Path | None:
    probe = run_git_command(["git", "rev-parse", "--show-toplevel"], APP_ROOT)
    if probe.returncode != 0:
        return None
    return Path(probe.stdout.strip())


def normalize_repo_path(path: Path, repo_root: Path) -> str:
    return str(path.resolve().relative_to(repo_root.resolve())).replace("\\", "/")


def changed_important_files(base_ref: str, repo_root: Path | None) -> list[str]:
    if repo_root is None:
        return []

    rel_paths = [normalize_repo_path(path, repo_root) for path in IMPORTANT_FILES]
    cmd = ["git", "diff", "--name-only", base_ref, "--", *rel_paths]
    probe = run_git_command(cmd, repo_root)
    if probe.returncode != 0:
        return []

    return [line.strip() for line in probe.stdout.splitlines() if line.strip()]


def parse_semver(raw: str) -> tuple[int, int, int]:
    match = SEMVER_RE.fullmatch(raw.strip())
    if not match:
        raise ValueError(f"Invalid semver: {raw!r}")
    return int(match.group(1)), int(match.group(2)), int(match.group(3))


def bump_semver(current: str, scope: str) -> str:
    major, minor, patch = parse_semver(current)
    if scope == "major":
        return f"{major + 1}.0.0"
    if scope == "minor":
        return f"{major}.{minor + 1}.0"
    return f"{major}.{minor}.{patch + 1}"


def detect_current_version() -> str:
    if VERSION_FILE.exists():
        value = VERSION_FILE.read_text(encoding="utf-8").strip()
        parse_semver(value)
        return value

    openapi_file = APP_ROOT / "openapi.yaml"
    if openapi_file.exists():
        text = openapi_file.read_text(encoding="utf-8")
        match = re.search(r"(?m)^\s*version:\s*(\d+\.\d+\.\d+)\s*$", text)
        if match:
            return match.group(1)

    return "1.0.0"


def replace_first(pattern: str, replacement: str, text: str) -> tuple[str, bool]:
    compiled = re.compile(pattern, flags=re.MULTILINE)
    new_text, count = compiled.subn(replacement, text, count=1)
    return new_text, count == 1

def replace_all(pattern: str, replacement: str, text: str) -> tuple[str, bool]:
    compiled = re.compile(pattern, flags=re.MULTILINE)
    new_text, count = compiled.subn(replacement, text)
    return new_text, count > 0

def sync_version_txt(new_version: str) -> bool:
    previous = VERSION_FILE.read_text(encoding="utf-8").strip() if VERSION_FILE.exists() else ""
    if previous == new_version:
        return False
    VERSION_FILE.write_text(f"{new_version}\n", encoding="utf-8")
    return True

def sync_version_tag(file_path: Path, new_version: str) -> bool:
    if not file_path.exists():
        return False
    text = file_path.read_text(encoding="utf-8")
    new_text, changed = replace_all(r"^(Version:\s*)\d+\.\d+\.\d+(.*)$", rf"\g<1>{new_version}\g<2>", text)
    if not changed:
        return False
    if new_text == text:
        return False
    file_path.write_text(new_text, encoding="utf-8")
    return True


def sync_readme(new_version: str) -> bool:
    target = APP_ROOT / "README.md"
    if not target.exists():
        return False
    text = target.read_text(encoding="utf-8")
    new_text, changed = replace_first(r"^(Version:\s*)\d+\.\d+\.\d+(.*)$", rf"\g<1>{new_version}\g<2>", text)
    if not changed:
        return False
    if new_text == text:
        return False
    target.write_text(new_text, encoding="utf-8")
    return True


def sync_api_guide(new_version: str) -> bool:
    target = APP_ROOT / "API_GUIDE.md"
    text = target.read_text(encoding="utf-8")

    # Replace if already present
    new_text, replaced = replace_first(r"^\*\*Version:\*\*\s*\d+\.\d+\.\d+\s*$", f"**Version:** {new_version}", text)
    if replaced:
        if new_text != text:
            target.write_text(new_text, encoding="utf-8")
            return True
        return False

    # Else inject after title line
    lines = text.splitlines()
    if not lines:
        lines = ["# API Guide - FabAssetsManager\n"]

    insert_at = 1
    if len(lines) > 1 and lines[1].strip() == "":
        insert_at = 2

    lines.insert(insert_at, f"**Version:** {new_version}")
    if insert_at == 1:
        lines.insert(2, "")

    updated = "\n".join(lines) + "\n"
    if updated == text:
        return False
    target.write_text(updated, encoding="utf-8")
    return True


def sync_openapi(new_version: str) -> bool:
    target = APP_ROOT / "openapi.yaml"
    text = target.read_text(encoding="utf-8")
    new_text, changed = replace_first(r"^(\s*version:\s*)\d+\.\d+\.\d+\s*$", rf"\g<1>{new_version}", text)
    if not changed:
        return False
    if new_text == text:
        return False
    target.write_text(new_text, encoding="utf-8")
    return True


def sync_changelog(new_version: str, scope: str, changed_files: list[str]) -> bool:
    target = APP_ROOT / "CHANGELOG.md"
    text = target.read_text(encoding="utf-8")

    if f"## [{new_version}]" in text:
        return False

    today = date.today().isoformat()
    pretty_changed = ", ".join(changed_files) if changed_files else "(manual)"
    entry = (
        f"## [{new_version}] - {today}\n\n"
        "### 🔧 Modifié\n\n"
        f"- Bump automatique `{scope}` déclenché sur fichiers importants.\n"
        f"- Fichiers importants détectés: {pretty_changed}.\n\n"
        "---\n\n"
    )

    lines = text.splitlines(keepends=True)
    if not lines:
        new_text = "# Changelog\n\n" + entry
    else:
        # Keep title as first line and insert new release block right after.
        head = lines[0]
        tail = "".join(lines[1:])
        if not tail.startswith("\n"):
            tail = "\n" + tail
        new_text = head + "\n" + entry + tail

    if new_text == text:
        return False
    target.write_text(new_text, encoding="utf-8")
    return True


def sync_all(new_version: str, scope: str, changed_files: list[str]) -> list[str]:
    touched: list[str] = []

    if sync_version_txt(new_version):
        touched.append("VERSION.txt")

    for file_path in VERSION_TAG_FILES:
        if sync_version_tag(file_path, new_version):
            touched.append(str(file_path.relative_to(APP_ROOT)).replace("\\", "/"))

    if sync_api_guide(new_version):
        touched.append("API_GUIDE.md")
    if sync_openapi(new_version):
        touched.append("openapi.yaml")
    if sync_changelog(new_version, scope, changed_files):
        touched.append("CHANGELOG.md")

    return touched


def main() -> int:
    args = parse_args()

    repo_root = get_repo_root()
    important_changes = changed_important_files(args.base_ref, repo_root)

    if not args.force and not important_changes:
        print("No important file change detected. Version bump skipped.")
        print("Tracked important files:")
        for file_path in IMPORTANT_FILES:
            print(f"- {file_path.relative_to(APP_ROOT)}")
        return 0

    current = detect_current_version()
    new_version = bump_semver(current, args.scope)

    if args.dry_run:
        print(f"Current version: {current}")
        print(f"Next version:    {new_version}")
        if important_changes:
            print("Detected important changes:")
            for rel in important_changes:
                print(f"- {rel}")
        else:
            print("Detected important changes: none (forced)")
        print("Files synchronized on real run:")
        for file_path in SYNC_FILES:
            print(f"- {file_path.relative_to(APP_ROOT)}")
        return 0

    touched = sync_all(new_version, args.scope, important_changes)
    print(f"Version bumped: {current} -> {new_version}")

    if important_changes:
        print("Important file changes detected:")
        for rel in important_changes:
            print(f"- {rel}")

    if touched:
        print("Updated files:")
        for rel in touched:
            print(f"- {rel}")
    else:
        print("No file content changes were needed.")

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"Version bump failed: {exc}", file=sys.stderr)
        raise SystemExit(2)
