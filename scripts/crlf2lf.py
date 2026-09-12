#!/usr/bin/env python3
"""Preview, convert, or check project text files for non-LF line endings."""

from __future__ import annotations

import argparse
import os
from pathlib import Path
import subprocess
import sys


SKIP_DIRS = {
    ".git",
    ".gradle",
    ".idea",
    ".mypy_cache",
    ".pytest_cache",
    ".tox",
    ".venv",
    "__pycache__",
    "build",
    "coverage",
    "dist",
    "node_modules",
    "target",
    "vendor",
}


def likely_binary(data: bytes) -> bool:
    if not data:
        return False
    if b"\x00" in data:
        return True
    sample = data[:8192]
    controls = sum(byte < 32 and byte not in (9, 10, 12, 13) for byte in sample)
    return controls / len(sample) > 0.10


def files_under(root: Path):
    if root.is_file():
        yield root
        return
    for current, dirs, names in os.walk(root):
        dirs[:] = sorted(name for name in dirs if name not in SKIP_DIRS)
        base = Path(current)
        for name in sorted(names):
            path = base / name
            if not path.is_symlink():
                yield path


def git_project_files(root: Path):
    try:
        result = subprocess.run(
            [
                "git",
                "-C",
                str(root),
                "ls-files",
                "-z",
                "--cached",
                "--others",
                "--exclude-standard",
            ],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except OSError as exc:
        raise RuntimeError(f"unable to run Git: {exc}") from exc
    if result.returncode:
        error = result.stderr.decode(errors="replace").strip()
        raise RuntimeError(error or "unable to list Git project files")
    for raw_path in result.stdout.split(b"\x00"):
        if not raw_path:
            continue
        path = root / os.fsdecode(raw_path)
        if path.is_file() and not path.is_symlink():
            yield path


def is_git_work_tree(root: Path) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "rev-parse", "--is-inside-work-tree"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return result.returncode == 0 and result.stdout.strip() == b"true"


def normalized(data: bytes) -> bytes:
    return data.replace(b"\r\n", b"\n").replace(b"\r", b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Preview or convert CRLF and stray CR line endings to LF."
    )
    parser.add_argument("path", nargs="?", default=".", help="File or project root")
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--git-files",
        "--git-tracked",
        dest="scope",
        action="store_const",
        const="git",
        help=(
            "Process tracked and untracked non-ignored Git files, including tracked "
            "metadata directories (--git-tracked is a compatibility alias)"
        ),
    )
    scope.add_argument(
        "--all-files",
        dest="scope",
        action="store_const",
        const="all",
        help="Traverse all files except generated and dependency directories",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--write", dest="mode", action="store_const", const="write", help="Apply conversions"
    )
    mode.add_argument(
        "--check",
        dest="mode",
        action="store_const",
        const="check",
        help="Exit 1 if conversion is needed without changing files",
    )
    mode.add_argument(
        "--preview",
        dest="mode",
        action="store_const",
        const="preview",
        help="List needed conversions without changing files or failing",
    )
    parser.set_defaults(scope="auto", mode="write")
    args = parser.parse_args()

    root = Path(args.path).expanduser().absolute()
    if not root.exists():
        parser.error(f"path does not exist: {root}")
    if root.is_symlink():
        parser.error(f"path is a symlink: {root}")

    changed = skipped_binary = errors = 0
    label = (
        "converted"
        if args.mode == "write"
        else "needs conversion"
        if args.mode == "check"
        else "would convert"
    )
    is_directory = root.is_dir()
    try:
        use_git = is_directory and (
            args.scope == "git" or (args.scope == "auto" and is_git_work_tree(root))
        )
        paths = git_project_files(root) if use_git else files_under(root)
        for path in paths:
            try:
                data = path.read_bytes()
                if likely_binary(data):
                    skipped_binary += 1
                    continue
                if b"\r" not in data:
                    continue
                if args.mode == "write":
                    path.write_bytes(normalized(data))
            except OSError as exc:
                errors += 1
                print(f"error: {path}: {exc}", file=sys.stderr)
                continue
            changed += 1
            shown = path.relative_to(root) if is_directory else path.name
            print(f"{label}: {shown}")
    except RuntimeError as exc:
        parser.error(str(exc))

    print(
        f"{label.capitalize()} {changed} file(s); "
        f"skipped {skipped_binary} likely binary file(s); "
        f"errors {errors}."
    )
    return 2 if errors else int(args.mode == "check" and changed > 0)


if __name__ == "__main__":
    raise SystemExit(main())
