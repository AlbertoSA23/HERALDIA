"""Checks the format of CHANGELOG.md and extracts the release notes.

python3 tools/changelog.py check   -> validates the format and that the top version matches mod_version
python3 tools/changelog.py notes   -> prints the sections of the top version (for the release)
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE = re.compile(r"^## \[(\d+\.\d+\.\d+)\](?: - \d{4}-\d{2}-\d{2})?$")
SECTIONS = ("### Players", "### Technical")


def parse(text):
    """Returns [(version, {section: [bullets]})] or raises ValueError with the offending line."""
    releases = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            m = RELEASE.match(line)
            if not m:
                raise ValueError(f"line {n}: invalid version header: {line}")
            releases.append((m.group(1), {}))
            current = None
        elif line.startswith("### "):
            if not releases or line not in SECTIONS or line in releases[-1][1]:
                raise ValueError(f"line {n}: unexpected section: {line}")
            current = line
            releases[-1][1][current] = []
        elif line.startswith("- ") and releases:
            if current is None:
                raise ValueError(f"line {n}: bullet outside a section")
            releases[-1][1][current].append(line)
        elif line.strip() and releases:
            raise ValueError(f"line {n}: only '- ' bullets are allowed inside a version")
    for version, sections in releases:
        if tuple(sections) != SECTIONS:
            raise ValueError(f"version {version}: must have {SECTIONS} in that order")
    if not releases:
        raise ValueError("there are no versions")
    return releases


def mod_version():
    with open(os.path.join(ROOT, "gradle.properties"), encoding="utf-8") as f:
        return next(l.split("=", 1)[1].strip() for l in f if l.startswith("mod_version="))


def main(cmd):
    with open(os.path.join(ROOT, "CHANGELOG.md"), encoding="utf-8") as f:
        releases = parse(f.read())
    top, sections = releases[0]
    if cmd == "check":
        if top != mod_version():
            raise ValueError(f"the top version ({top}) does not match mod_version ({mod_version()})")
        print(f"CHANGELOG OK: {len(releases)} versions, latest {top}")
    elif cmd == "notes":
        print("\n".join(sections["### Players"]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv[1] if len(sys.argv) > 1 else "")
    except ValueError as e:
        raise SystemExit(f"invalid CHANGELOG: {e}")
