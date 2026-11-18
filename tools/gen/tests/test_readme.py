"""README de cada idioma del mod (idiomas.README) y documentación de docs/ en inglés y español: que existan todos, que
lleven el selector de idiomas con todos los enlaces, que tengan las mismas secciones, las mismas cifras y los mismos
nombres de opciones y comandos, que las cifras sean las del generador (estructuras, logros, guardianes...) y que todos
los enlaces relativos lleven a un fichero y a un encabezado que existen."""
import os
import re
import pytest
import arena_waves
import caravans
import shore as coast
import quests
import languages
import advancements
import mediums
import mines
import options
import board
import uniques
from themes import THEMES, FAMILIES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MODS = uniques.modules()
README = languages.README
# documentación movida desde el README: (inglés, español)
DOCS = [("CONTENT.md", "CONTENIDO.md"), ("CONFIGURATION.md", "CONFIGURACION.md"), ("COMPATIBILITY.md", "COMPATIBILIDAD.md"),
        ("BUILDING.md", "COMPILAR.md")]


def read(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def anchor_point(header):
    """El ancla que GitHub da a un encabezado."""
    a = re.sub(r"[^\w\- ]", "", header.strip().lower())
    return a.replace(" ", "-")


def headers(text):
    """[(nivel, texto)] fuera de los bloques de código."""
    out, codigo = [], False
    for line in text.split("\n"):
        if line.startswith("```"):
            codigo = not codigo
        elif not codigo:
            m = re.match(r"(#{1,6}) (.*)", line)
            if m:
                out.append((len(m.group(1)), m.group(2)))
    return out


def numbers(text):
    """Cifras del texto con los separadores de miles de cada idioma quitados (1,500 / 1.500 / 1 500 -> 1500)."""
    text = re.sub(r"(?<=\d)[,.   ](?=\d{3}\b)", "", text)
    return sorted(int(n) for n in re.findall(r"\d+", text))


def codigos(text):
    """Lo que va entre comillas invertidas (opciones, comandos, ids): igual en todos los idiomas."""
    return re.findall(r"`([^`]+)`", text)


def form(text):
    """Esqueleto del documento: por cada sección, cuántas viñetas, filas de tabla y pasos numerados lleva."""
    out, current = [], None
    for line in text.split("\n"):
        if line.startswith("#"):
            current = [line.count("#", 0, line.index(" ")), 0, 0, 0]
            out.append(current)
        elif current is not None:
            current[1] += line.startswith("- ")
            current[2] += line.startswith("|")
            current[3] += bool(re.match(r"\d+\. ", line))
    return out


def selector(codigo):
    """La línea del selector de idiomas del README de `codigo`: el suyo en negrita y los demás enlazados."""
    return " · ".join(f"**{languages.NAMES[c]}**" if c == codigo else f"[{languages.NAMES[c]}]({README[c]})" for c in README)


# ------------------------------------------------------------------ un README por idioma, con su selector
def test_one_readme_per_mod_language():
    assert set(README) == set(languages.everyone())
    assert README["en_us"] == "README.md"
    for c, f in README.items():
        assert os.path.exists(os.path.join(ROOT, f)), f"falta {f} ({c})"


@pytest.mark.parametrize("codigo", list(README))
def test_language_selector(codigo):
    lines = read(README[codigo]).split("\n")
    assert lines[0] == "# Heraldia"
    assert lines[2] == selector(codigo)
    linked = set(re.findall(r"\]\((README[^)]*)\)", lines[2]))
    assert linked == set(README.values()) - {README[codigo]}


@pytest.mark.parametrize("codigo", [c for c in README if c != "en_us"])
def test_same_shape_as_english(codigo):
    en, other_one = read(README["en_us"]), read(README[codigo])
    assert [n for n, _ in headers(other_one)] == [n for n, _ in headers(en)]
    assert form(other_one) == form(en)
    assert codigos(other_one) == codigos(en)
    assert numbers(other_one) == numbers(en)


@pytest.mark.parametrize("codigo", list(README))
def test_links_the_documentation(codigo):
    """Cada README enlaza la documentación (la española, el de español; la inglesa, los demás) y la guía de desarrollo."""
    text = read(README[codigo])
    docs = [es if codigo == "es_es" else en for en, es in DOCS]
    for d in docs + ["DEVELOPMENT.md"]:
        assert f"(docs/{d})" in text, (codigo, d)


# ------------------------------------------------------------------ cifras del generador
def figures():
    structures = (2 * len(THEMES) + len(MODS) + sum(len(m.STYLES) for _, m in mediums.modules())
                   + len(mines.structures()) + len(coast.structures()))

    class _Template:
        def __init__(self, sid):
            self.entities = [(0, 0, 0, {"id": "minecraft:zombie", "Tags": [f"{advancements.GUARDIAN_TAG}.{sid}"]})]

    class _Registry:     # todas las únicas tienen guardián (el de la Atlántida incluido)
        templates = {f"unicas/{sid}/x": _Template(sid) for sid, _ in MODS}
    advs, _ = advancements.build(_Registry, MODS, mediums.modules(), mines, coast)
    advancements_n = len(advs) + len(board.ADVANCEMENTS) + len(arena_waves.advancements()) + len(quests.ADVANCEMENTS) + len(caravans.ADVANCEMENTS)
    return {"estructuras": structures, "logros": advancements_n}


def test_figures_of_the_generator():
    c = figures()
    # las que se comprueban también en el servidor (server_smoke.py cuenta los ficheros generados)
    assert c == {"estructuras": 180, "logros": 122}, "si cambian, cámbialas en los README y en docs/"


def test_figures_of_the_readme():
    text = read("README.md")
    endings = [sid for sid, m in MODS if m.STORY.get("final")]
    expected = {
        r"(\d+) hand-designed villages": 2 * len(THEMES),
        r"(\d+) styles, one for each": len(THEMES),
        r"grouped in (\d+) families": len(FAMILIES),
        r"(\d+) kinds of medium structures": len(mediums.modules()),
        r"(\d+) unique structures\*\*": len(MODS) - len(endings),
        r"tab with (\d+) advancements": figures()["logros"],
        r"Each of the (\d+) guardians": len(MODS),
        r"gather all (\d+)": len(MODS),
        r"in (\d+) sizes": len(mines.SIZES),
        r"in (\d+) languages": len(languages.everyone()),
    }
    for pattern, n in expected.items():
        m = re.search(pattern, text)
        assert m and int(m.group(1)) == n, (pattern, m and m.group(1), n)


@pytest.mark.parametrize("doc, pattern, which", [
    ("CONTENT.md", r"\*\*Huge villages\*\*: (\d+) structures", "aldeas"),
    ("CONTENIDO.md", r"\*\*Aldeas enormes\*\*: (\d+) estructuras", "aldeas"),
    ("CONTENT.md", r"\((\d+) advancements\)", "logros"),
    ("CONTENIDO.md", r"\((\d+) logros\)", "logros"),
    ("CONFIGURATION.md", r"Heraldia: (\d+) estructuras registradas", "estructuras"),
    ("CONFIGURACION.md", r"Heraldia: (\d+) estructuras registradas", "estructuras"),
    ("BUILDING.md", r"all (\d+) structures", "estructuras"),
    ("BUILDING.md", r"all (\d+) advancements", "logros"),
    ("COMPILAR.md", r"las (\d+) estructuras", "estructuras"),
    ("COMPILAR.md", r"los (\d+) logros", "logros"),
])
def test_figures_of_the_documentation(doc, pattern, which):
    n = dict(figures(), aldeas=2 * len(THEMES))[which]
    m = re.search(pattern, read(f"docs/{doc}"))
    assert m and int(m.group(1)) == n, (doc, pattern, m and m.group(1), n)


@pytest.mark.parametrize("codigo", list(README))
def test_options_table_with_the_generator_values(codigo):
    defaults = {o["clave"]: o["defecto"] for o in options.schema()["opciones"]}
    rows = re.findall(r"^\| `([a-z_.<>]+)` \| ([^|]+) \|", read(README[codigo]), re.M)
    assert len(rows) >= 8
    for key, default in rows:
        real = [v for k, v in defaults.items() if re.fullmatch(re.escape(key).replace("<id>", r"\w+"), k)]
        assert real, f"{key} no es una opción"
        d = default.strip().strip("`")
        assert all(d == (str(v).lower() if isinstance(v, bool) else str(v)) for v in real), (key, d, real)


# ------------------------------------------------------------------ docs/ en inglés y español
@pytest.mark.parametrize("en, es", DOCS)
def test_documentation_in_the_two_languages(en, es):
    ten, tes = read(f"docs/{en}"), read(f"docs/{es}")
    assert ten.split("\n")[2] == f"**English** · [Español]({es})"
    assert tes.split("\n")[2] == f"[English]({en}) · **Español**"
    assert [n for n, _ in headers(ten)] == [n for n, _ in headers(tes)]
    assert len(re.findall(r"^\|", ten, re.M)) == len(re.findall(r"^\|", tes, re.M))


def _links(rel):
    """[(destino, ancla)] de los enlaces relativos de un documento."""
    out = []
    for destination in re.findall(r"\]\(([^)\s]+)\)", read(rel)):
        if not re.match(r"[a-z]+:", destination):
            f, _, a = destination.partition("#")
            out.append((os.path.normpath(os.path.join(os.path.dirname(rel), f)) if f else rel, a))
    return out


@pytest.mark.parametrize("rel", list(README.values()) + [f"docs/{d}" for pair in DOCS for d in pair])
def test_links_that_lead_to_somewhat(rel):
    for f, a in _links(rel):
        assert os.path.exists(os.path.join(ROOT, f)), (rel, f)
        if a and f.endswith(".md"):
            assert a in {anchor_point(t) for _, t in headers(read(f))}, (rel, f, a)
