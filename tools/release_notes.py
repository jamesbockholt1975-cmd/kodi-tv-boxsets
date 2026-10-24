#!/usr/bin/env python3
# SPDX-License-Identifier: GPL-2.0-or-later
"""Print one version's section of CHANGELOG.md:  python3 tools/release_notes.py 0.11.1

Used by the release workflow for the text of a GitHub release. Exits with an error if the
version has no section, so a release can't go out without release notes.
"""
import os
import re
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))


def section(changelog, version):
    """The body of the '## <version> ...' section, or None."""
    m = re.search(r"^## {}(?:\s.*)?$".format(re.escape(version)), changelog, re.M)
    if not m:
        return None
    rest = changelog[m.end():]
    nxt = re.search(r"^## ", rest, re.M)
    return rest[:nxt.start()] if nxt else rest


def main():
    if len(sys.argv) != 2:
        sys.exit("usage: release_notes.py <version>, for example 0.11.1")
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        body = section(f.read(), sys.argv[1])
    if body is None:
        sys.exit("CHANGELOG.md has no section for version {}".format(sys.argv[1]))
    print(body.strip())
    print("\n---\nThe zip was built by GitHub from this tag's source; its SHA256 is in `SHA256SUMS`. "
          "To check a download, compare it with that file, or build it yourself with "
          "`python3 tools/build_zip.py`.")


if __name__ == "__main__":
    main()
