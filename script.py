#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Собирает Python-модули по проекту и складывает в один файл.
Пример:
  python collect_modules.py --root . --out all_modules.txt
"""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable, List, Optional, Set


DEFAULT_EXCLUDE_DIRS = {
    ".git", ".hg", ".svn",
    ".venv", "venv", "env",
    "__pycache__",
    ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".tox", ".nox",
    "node_modules",
    "dist", "build", ".eggs",
    ".idea", ".vscode",
}


def is_under_any_dir(path: Path, excluded_names: Set[str]) -> bool:
    """True если в пути есть директория с именем из excluded_names."""
    return any(part in excluded_names for part in path.parts)


def find_python_package_root(file_path: Path, project_root: Path) -> Optional[Path]:
    """
    Ищем ближайшую директорию, из которой можно построить import-путь:
    поднимаемся вверх, пока есть __init__.py; возвращаем директорию НАД пакетом.
    """
    current = file_path.parent
    last_pkg_dir = None

    while True:
        if current == project_root.parent or current == current.parent:
            break
        if (current / "__init__.py").exists():
            last_pkg_dir = current
            current = current.parent
            continue
        break

    if last_pkg_dir is None:
        return None

    return last_pkg_dir.parent


def module_name_from_path(py_file: Path, project_root: Path) -> str:
    """
    Строим имя модуля:
    - если файл в пакете (есть __init__.py по цепочке) => package.sub.module
    - иначе => relative/path/to/file.py -> relative.path.to.file
    """
    pkg_root = find_python_package_root(py_file, project_root)
    if pkg_root is not None and pkg_root in py_file.parents:
        rel = py_file.relative_to(pkg_root)
    else:
        rel = py_file.relative_to(project_root)

    parts = list(rel.parts)
    if parts[-1].endswith(".py"):
        parts[-1] = parts[-1][:-3]

    # Если это __init__.py, то модуль = имя пакета
    if parts[-1] == "__init__":
        parts = parts[:-1] or parts  # если вдруг корневой __init__.py

    return ".".join(parts)


def iter_py_files(
    root: Path,
    exclude_dirs: Set[str],
    include_init: bool,
) -> Iterable[Path]:
    for p in root.rglob("*.py"):
        if not p.is_file():
            continue
        if is_under_any_dir(p, exclude_dirs):
            continue
        if not include_init and p.name == "__init__.py":
            continue
        yield p


def write_merged_file(files: List[Path], root: Path, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    # Стабильный порядок
    files = sorted(files, key=lambda x: str(x).lower())

    with out_path.open("w", encoding="utf-8", newline="\n") as out:
        out.write("# Collected project modules\n")
        out.write(f"# Root: {root.resolve()}\n")
        out.write(f"# Files: {len(files)}\n\n")

        for py_file in files:
            mod_name = module_name_from_path(py_file, root)
            rel_path = py_file.relative_to(root)

            try:
                content = py_file.read_text(encoding="utf-8")
            except UnicodeDecodeError:
                # на случай файлов не в utf-8 — читаем как bytes и пробуем заменить
                content = py_file.read_bytes().decode("utf-8", errors="replace")

            out.write("\n" + "=" * 100 + "\n")
            out.write(f"MODULE: {mod_name}\n")
            out.write(f"PATH:   {rel_path.as_posix()}\n")
            out.write("=" * 100 + "\n\n")
            out.write(content.rstrip() + "\n")  # аккуратно заканчиваем блок
            out.write("\n")  # пустая строка между модулями


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Collect Python modules into one file.")
    parser.add_argument("--root", type=str, default=".", help="Project root directory")
    parser.add_argument("--out", type=str, default="all_modules.txt", help="Output file path")
    parser.add_argument(
        "--exclude-dir",
        action="append",
        default=[],
        help="Directory name to exclude (can be used multiple times)",
    )
    parser.add_argument(
        "--include-init",
        action="store_true",
        help="Include __init__.py files (default: excluded)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    root = Path(args.root).resolve()
    out_path = Path(args.out).resolve()

    exclude_dirs = set(DEFAULT_EXCLUDE_DIRS)
    exclude_dirs.update(args.exclude_dir or [])

    py_files = list(iter_py_files(root, exclude_dirs, include_init=args.include_init))
    write_merged_file(py_files, root, out_path)

    print(f"OK: collected {len(py_files)} modules into: {out_path}")


if __name__ == "__main__":
    main()
