"""Comprueba el formato de CHANGELOG.md y extrae las notas de publicación.

python3 tools/changelog.py check   -> valida formato y que la versión de arriba sea mod_version
python3 tools/changelog.py notes   -> imprime los apartados de la versión de arriba (para la publicación)
"""
import os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RELEASE = re.compile(r"^## \[(\d+\.\d+\.\d+)\](?: - \d{4}-\d{2}-\d{2})?$")
SECTIONS = ("### Players", "### Technical")


def parse(text):
    """Devuelve [(versión, {apartado: [viñetas]})] o lanza ValueError con la línea culpable."""
    releases = []
    for n, line in enumerate(text.splitlines(), 1):
        if line.startswith("## "):
            m = RELEASE.match(line)
            if not m:
                raise ValueError(f"línea {n}: cabecera de versión inválida: {line}")
            releases.append((m.group(1), {}))
            current = None
        elif line.startswith("### "):
            if not releases or line not in SECTIONS or line in releases[-1][1]:
                raise ValueError(f"línea {n}: apartado inesperado: {line}")
            current = line
            releases[-1][1][current] = []
        elif line.startswith("- ") and releases:
            if current is None:
                raise ValueError(f"línea {n}: viñeta fuera de un apartado")
            releases[-1][1][current].append(line)
        elif line.strip() and releases:
            raise ValueError(f"línea {n}: solo se admiten viñetas '- ' dentro de una versión")
    for version, sections in releases:
        if tuple(sections) != SECTIONS:
            raise ValueError(f"versión {version}: debe tener {SECTIONS} en ese orden")
    if not releases:
        raise ValueError("no hay ninguna versión")
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
            raise ValueError(f"la versión de arriba ({top}) no coincide con mod_version ({mod_version()})")
        print(f"CHANGELOG OK: {len(releases)} versiones, la última {top}")
    elif cmd == "notes":
        print("\n".join(sections["### Players"]))
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    try:
        main(sys.argv[1] if len(sys.argv) > 1 else "")
    except ValueError as e:
        raise SystemExit(f"CHANGELOG inválido: {e}")
