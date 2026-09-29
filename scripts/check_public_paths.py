#!/usr/bin/env python3
"""Keep private campaign files out of this public repository.

Only the top-level names in PUBLIC may be committed or pushed. DM notes,
handouts, gods, PCs, the Discord export, maps, tokens and the private DM site
stay on this computer. Staged mode checks the whole index, so `git add -f`
cannot slip a file in. Pre-push mode checks every path added or changed
anywhere in the outgoing history. No third-party packages needed.
"""

import argparse
import re
import subprocess
import sys


PUBLIC = frozenset(
    ".gitignore .gitattributes .githooks .github scripts Website GIT_SETUP.md CLAUDE.md LICENSE".split()
)
OID_PATTERN = re.compile(r"(?:[0-9a-f]{40}|[0-9a-f]{64})\Z")


def git(*args):
    result = subprocess.run(["git", *args], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False)
    if result.returncode:
        raise RuntimeError(result.stderr.decode("utf-8", "replace").strip())
    return result.stdout


def private(paths):
    return sorted({p for p in paths if p and p.split(b"/", 1)[0].decode("utf-8", "replace") not in PUBLIC})


def outgoing_tips():
    tips = set()
    for line in sys.stdin:
        fields = line.strip().split()
        if not fields:
            continue
        if len(fields) != 4 or not OID_PATTERN.fullmatch(fields[1]):
            raise RuntimeError("Invalid pre-push ref input")
        if fields[1].strip("0"):
            tips.add(fields[1])
    return sorted(tips)


def check(mode):
    if mode == "staged":
        paths = git("ls-files", "-z").split(b"\x00")
    else:
        tips = outgoing_tips()
        if not tips:
            return 0
        # -m includes files introduced while resolving a merge
        paths = git("log", "-m", "--no-renames", "--name-only", "--format=", "-z", *tips, "--").split(b"\x00")
        paths = [p.strip(b"\n") for p in paths]
    found = private(paths)
    if found:
        print("Blocked: this public repo only carries the campaign website.", file=sys.stderr)
        for path in found[:30]:
            print("  " + path.decode("utf-8", "backslashreplace"), file=sys.stderr)
        if len(found) > 30:
            print("  ... and " + str(len(found) - 30) + " more", file=sys.stderr)
        print("Allowed top-level names: " + ", ".join(sorted(PUBLIC)), file=sys.stderr)
        return 1
    print("Public-path guard: " + str(len({p for p in paths if p})) + " paths are all public.")
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("staged", "pre-push"))
    try:
        return check(parser.parse_args().mode)
    except (OSError, RuntimeError, ValueError) as error:
        print("Public-path guard could not complete; operation blocked: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
