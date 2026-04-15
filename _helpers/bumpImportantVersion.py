"""Version bump helper using repo-local JSON configuration.

Behavior:
- Uses VERSION.txt as source of truth.
- Bumps only when at least one important app file changed (unless --force).
- Scans repo files for version tags and synchronizes the bumped version only where a tag is found.

Repo-specific configuration is loaded from:
    `_helpers/bumpImportantVersion.config.json`
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from functools import lru_cache
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
APP_ROOT = SCRIPT_DIR.parent
VERSION_FILE = APP_ROOT / "VERSION.txt"

CONFIG_FILE = SCRIPT_DIR / "bumpImportantVersion.config.json"

VERSION_TAG_EXTENSIONS = {".py", ".md", ".html", ".htm", ".js", ".yaml", ".yml"}
VERSION_MARKER_RE = re.compile(r"(?m)^\s*(?:#\s*)?(?:\*\*Version:\*\*|\*\*Version\*\*:|Version:|version:)\s*\d+\.\d+\.\d+")

SEMVER_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


@lru_cache
def load_config() -> dict[str, list[str]]:
    if not CONFIG_FILE.exists():
        raise ValueError(f"Missing configuration file: {CONFIG_FILE.relative_to(APP_ROOT)}")

    try:
        raw_config = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {CONFIG_FILE.relative_to(APP_ROOT)}: {exc}") from exc

    if not isinstance(raw_config, dict):
        raise ValueError(f"Configuration file must contain a JSON object: {CONFIG_FILE.relative_to(APP_ROOT)}")

    important_files = raw_config.get("important_files")

    if not isinstance(important_files, list) or any(not isinstance(item, str) for item in important_files):
        raise ValueError("important_files must be a list of relative paths")

    return {"important_files": important_files}


def resolve_paths(relative_paths: list[str]) -> list[Path]:
    return [APP_ROOT / Path(relative_path) for relative_path in relative_paths]


def important_file_paths() -> list[Path]:
    return resolve_paths(load_config()["important_files"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Bump version for UnityAssetsManager important files only")
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

    rel_paths = [normalize_repo_path(path, repo_root) for path in important_file_paths()]
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


def discover_version_tag_files() -> list[Path]:
    discovered: list[Path] = []
    for path in APP_ROOT.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in VERSION_TAG_EXTENSIONS:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if VERSION_MARKER_RE.search(text):
            discovered.append(path)
    return sorted(discovered)


def version_tag_patterns(new_version: str) -> list[tuple[str, str]]:
    return [
        (r"^(\s*(?:#|//|::|REM)\s*Version:\s*)\d+\.\d+\.\d+(\s*)$", rf"\g<1>{new_version}\g<2>"),
        (r"^(\s*<!--\s*Version:\s*)\d+\.\d+\.\d+(\s*-->)", rf"\g<1>{new_version}\g<2>"),
        (r"^(\s*\*\*Version:\*\*\s*)\d+\.\d+\.\d+(\s*)$", rf"\g<1>{new_version}\g<2>"),
        (r"^(\s*\*\*Version\*\*:\s*)\d+\.\d+\.\d+(\s*)$", rf"\g<1>{new_version}\g<2>"),
        (r"^(\s*Version:\s*)\d+\.\d+\.\d+(\s*)$", rf"\g<1>{new_version}\g<2>"),
        (r"^(\s*version:\s*)\d+\.\d+\.\d+(\s*)$", rf"\g<1>{new_version}\g<2>"),
    ]


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
    for pattern, replacement in version_tag_patterns(new_version):
        new_text, changed = replace_first(pattern, replacement, text)
        if changed:
            if new_text != text:
                file_path.write_text(new_text, encoding="utf-8")
                return True
            return False

    return False


def get_sync_files(version_tag_files: list[Path]) -> list[Path]:
    return [*version_tag_files, VERSION_FILE]


def sync_all(new_version: str) -> list[str]:
    touched: list[str] = []
    version_tag_files = discover_version_tag_files()

    if sync_version_txt(new_version):
        touched.append("VERSION.txt")

    for file_path in version_tag_files:
        if sync_version_tag(file_path, new_version):
            touched.append(str(file_path.relative_to(APP_ROOT)).replace("\\", "/"))

    return touched


def main() -> int:
    args = parse_args()

    repo_root = get_repo_root()
    important_changes = changed_important_files(args.base_ref, repo_root)

    if not args.force and not important_changes:
        print("No important file change detected. Version bump skipped.")
        print("Tracked important files:")
        for file_path in important_file_paths():
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
        for file_path in get_sync_files(discover_version_tag_files()):
            print(f"- {file_path.relative_to(APP_ROOT)}")
        return 0

    touched = sync_all(new_version)
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
