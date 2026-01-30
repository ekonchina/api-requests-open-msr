#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable


DEFAULT_EXCLUDE_DIRS = {
    ".git",
    ".hg",
    ".svn",
    ".idea",
    ".vscode",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "venv",
    ".venv",
    "env",
    ".env",
    "build",
    "dist",
    ".eggs",
    ".cache",
}

DEFAULT_EXCLUDE_FILE_SUFFIXES = {
    ".pyc",
    ".pyo",
}


def is_under_any_dir(path: Path, dirnames: set[str]) -> bool:
    parts = set(path.parts)
    return any(d in parts for d in dirnames)


def should_skip_file(
    file_path: Path,
    project_root: Path,
    exclude_dirs: set[str],
    include_tests: bool,
) -> bool:
    rel = file_path.relative_to(project_root)

    # Exclude directories by name anywhere in the path
    if is_under_any_dir(rel, exclude_dirs):
        return True

    # Must be .py
    if file_path.suffix != ".py":
        return True

    # Exclude typical compiled suffixes (just in case)
    if file_path.suffix in DEFAULT_EXCLUDE_FILE_SUFFIXES:
        return True

    # Optionally exclude tests
    name = file_path.name
    if not include_tests:
        if name.startswith("test_") and name.endswith(".py"):
            return True
        if name.endswith("_test.py"):
            return True
        if rel.parts and rel.parts[0] in {"tests", "test"}:
            return True

    return False


def iter_python_modules(
    project_root: Path,
    exclude_dirs: set[str],
    include_tests: bool,
) -> Iterable[Path]:
    for p in project_root.rglob("*.py"):
        if p.is_file() and not should_skip_file(p, project_root, exclude_dirs, include_tests):
            yield p


def read_text_safely(path: Path) -> str:
    # Try UTF-8 first, then fallback
    try:
        return path.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        return path.read_text(encoding="utf-8", errors="replace")


def build_bundle(
    project_root: Path,
    output_file: Path,
    exclude_dirs: set[str],
    include_tests: bool,
) -> tuple[int, int]:
    files = sorted(iter_python_modules(project_root, exclude_dirs, include_tests))
    total_bytes = 0

    output_file.parent.mkdir(parents=True, exist_ok=True)

    with output_file.open("w", encoding="utf-8", newline="\n") as out:
        out.write("# Bundled project sources\n")
        out.write(f"# Root: {project_root.resolve()}\n")
        out.write(f"# Files: {len(files)}\n\n")

        for fp in files:
            rel = fp.relative_to(project_root).as_posix()
            content = read_text_safely(fp)

            out.write("\n")
            out.write("#" + "=" * 100 + "\n")
            out.write(f"# FILE: {rel}\n")
            out.write("#" + "=" * 100 + "\n\n")
            out.write(content)
            if not content.endswith("\n"):
                out.write("\n")

            total_bytes += len(content.encode("utf-8", errors="replace"))

    return len(files), total_bytes


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Collect all Python modules from a project and write their contents into a single test file."
    )
    parser.add_argument(
        "project_root",
        nargs="?",
        default=".",
        help="Path to project root (default: current directory).",
    )
    parser.add_argument(
        "-o",
        "--output",
        default="tests/bundled_project_sources_test.txt",
        help="Output file path (default: tests/bundled_project_sources_test.txt).",
    )
    parser.add_argument(
        "--include-tests",
        action="store_true",
        help="Include test files too (test_*.py, *_test.py, tests/).",
    )
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude (can be used multiple times).",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    project_root = Path(args.project_root).resolve()
    output_file = Path(args.output).resolve()

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS) | set(args.exclude_dir)

    if not project_root.exists() or not project_root.is_dir():
        raise SystemExit(f"Project root does not exist or is not a directory: {project_root}")

    count, total_bytes = build_bundle(
        project_root=project_root,
        output_file=output_file,
        exclude_dirs=exclude_dirs,
        include_tests=args.include_tests,
    )

    print(f"OK: bundled {count} files into: {output_file}")
    print(f"Total UTF-8 bytes (approx): {total_bytes}")


if __name__ == "__main__":
    main()
