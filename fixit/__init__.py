#!/usr/bin/env python3

from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Iterable, List, Optional, Sequence, Set
import os
import shutil
import subprocess
import sys

_FIXES_PATH = "fixit/fixes/"
_WELL_KNOWN_LAST_FIXED_ALL_FILE = Path("fixit/.last_fixed")


def usage() -> None:
    print("Usage: fixit fix_name", file=sys.stderr)


def _mark_fixed_all() -> None:
    _WELL_KNOWN_LAST_FIXED_ALL_FILE.touch(exist_ok=True)


def _last_fixed() -> Optional[datetime]:
    if not _WELL_KNOWN_LAST_FIXED_ALL_FILE.exists():
        return None

    stat = _WELL_KNOWN_LAST_FIXED_ALL_FILE.stat()
    last_modified = datetime.fromtimestamp(stat.st_mtime, tz=timezone.utc)

    return last_modified


def _first_relevant_commit_since(since_date: datetime) -> Optional[str]:
    int_timestamp = int(since_date.timestamp())
    result = subprocess.run(
        ["git", "rev-list", f"--since={int_timestamp}", _FIXES_PATH],
        capture_output=True,
    ).stdout

    if not result:
        return None

    return result.splitlines()[0].decode("utf-8")


def _list_new_fixes_since(since_date: datetime) -> Optional[Iterable[str]]:
    since_sha = _first_relevant_commit_since(since_date)
    if not since_sha:
        # No changes since this time.
        return None

    output = subprocess.run(
        ["git", "diff", "--name-only", f"{since_sha}..origin/master"],
        capture_output=True,
    ).stdout

    if not output:
        # ???
        return None

    return [os.path.basename(path.decode("utf-8")) for path in output.splitlines()]


def _list_fixes(since_date: Optional[datetime] = None) -> Optional[Iterable[str]]:
    fixes_filter: Optional[Set[str]] = None
    if since_date:
        new_fixes = _list_new_fixes_since(since_date)
        if not new_fixes:
            return None

        fixes_filter = set(new_fixes)

    result = subprocess.run(
        ["git", "ls-files", _FIXES_PATH, "origin/master"], capture_output=True
    )

    items: List[str] = []
    for tree_line in result.stdout.splitlines():
        path = tree_line.split(maxsplit=3)[3].decode("utf-8")
        fix_name = os.path.basename(path)
        # If we have filtered our new fixes, and this is not among them, do not
        # run it. We list changes and use this to filter current state of
        # master to keep master a source of truth for what fixes should be run.
        if fixes_filter and fix_name not in fixes_filter:
            continue

        items.append(fix_name)

    return items


def run_fix(name: str) -> None:
    """
    Runs a fix as committed at current remote state of master
    """
    # TODO: This should all be driven by a committed dotfile at the root of the
    # repo
    prog_root = Path(__file__).parent
    repo_root = prog_root.parent
    fix_path = (prog_root / "fixes" / name).relative_to(repo_root)

    tempfile = NamedTemporaryFile(delete=False)

    try:
        result = subprocess.run(
            ["git", "show", f"origin/master:{fix_path}"],
            stdout=tempfile,
            cwd=repo_root,
        )
        tempfile.close()
        os.chmod(tempfile.name, 0o700)
        subprocess.run([tempfile.name], cwd=repo_root)

    finally:
        os.remove(tempfile.name)


def run_fixes(run_all: bool = False) -> None:
    fixes: Optional[Iterable[str]]
    if run_all:
        fixes = _list_fixes()
    else:
        fixes = _list_fixes(_last_fixed())

    if not fixes:
        print("No fixes to run!")
        return

    for fix in fixes:
        print(f"Running fix {fix}")
        run_fix(fix)


def main(argv: Sequence[str]) -> None:
    argc = len(argv)

    subprocess.run(
        ["git", "fetch", "origin", "master"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    if argc == 0:
        run_fixes()
    elif argc == 1 and argv[0] == "all":
        run_fixes(run_all=True)
    elif argc == 1:
        run_fix(argv[0])
    else:
        usage()
        sys.exit(1)


main(sys.argv[1:])
