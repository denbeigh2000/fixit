#!/usr/bin/env python3

from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Sequence
import os
import subprocess
import sys


def usage() -> None:
    print("Usage: fixit fix_name", file=sys.stderr)


def run_fix(name: str) -> None:
    pwd = Path(__file__).parent
    fix_path = (pwd / "fixes" / name).relative_to(pwd.parent)

    subprocess.run(
        ["git", "fetch", "origin", "master"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )

    tempfile = NamedTemporaryFile(delete=False)

    try:
        result = subprocess.run(
            ["git", "show", f"origin/master:{fix_path}"], stdout=tempfile
        )
        tempfile.close()
        os.chmod(tempfile.name, 0o700)
        subprocess.run([tempfile.name])
    finally:
        os.remove(tempfile.name)


def main(argv: Sequence[str]) -> None:
    if len(argv) != 1:
        usage()
        sys.exit(1)

    run_fix(argv[0])


main(sys.argv[1:])
