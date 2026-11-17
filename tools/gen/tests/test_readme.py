"""README de cada idioma del mod (idiomas.README) y documentación de docs/ en inglés y español: que existan todos, que
lleven el selector de idiomas con todos los enlaces, que tengan las mismas secciones, las mismas cifras y los mismos
nombres de opciones y comandos, que las cifras sean las del generador (estructuras, logros, guardianes...) y que todos
los enlaces relativos lleven a un fichero y a un encabezado que existen."""
import os
import re
import pytest
import arena_oleadas
import caravanas
import encargos
import idiomas
import logros
import medianas
import minas
import opciones
import tablon
import unicas
from themes import THEMES, FAMILIES

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
MODS = unicas.modules()
README = idiomas.README
# documentación movida desde el README: (inglés, español)
DOCS = [("CONTENT.md", "CONTENIDO.md"), ("CONFIGURATION.md", "CONFIGURACION.md"), ("COMPATIBILITY.md", "COMPATIBILIDAD.md"),
        ("BUILDING.md", "COMPILAR.md")]


def leer(rel):
    with open(os.path.join(ROOT, rel), encoding="utf-8") as f:
        return f.read()


def ancla(encabezado):
    """El ancla que GitHub da a un encabezado."""
    a = re.sub(r"[^\w\- ]", "", encabezado.strip().lower())
    return a.replace(" ", "-")


def encabezados(texto):
    """[(nivel, texto)] fuera de los bloques de código."""
    out, codigo = [], False
    for linea in texto.split("\n"):
        if linea.startswith("```"):
            codigo = not codigo
        elif not codigo:
            m = re.match(r"(#{1,6}) (.*)", linea)
            if m:
                out.append((len(m.group(1)), m.group(2)))
    return out


def numeros(texto):
    """Cifras del texto con los separadores de miles de cada idioma quitados (1,500 / 1.500 / 1 500 -> 1500)."""
    texto = re.sub(r"(?<=\d)[,.   ](?=\d{3}\b)", "", texto)
    return sorted(int(n) for n in re.findall(r"\d+", texto))


def codigos(texto):
    """Lo que va entre comillas invertidas (opciones, comandos, ids): igual en todos los idiomas."""
    return re.findall(r"`([^`]+)`", texto)


def forma(texto):
    """Esqueleto del documento: por cada sección, cuántas viñetas, filas de tabla y pasos numerados lleva."""
    out, actual = [], None
    for linea in texto.split("\n"):
        if linea.startswith("#"):
            actual = [linea.count("#", 0, linea.index(" ")), 0, 0, 0]
            out.append(actual)
        elif actual is not None:
            actual[1] += linea.startswith("- ")
            actual[2] += linea.startswith("|")
            actual[3] += bool(re.match(r"\d+\. ", linea))
    return out


def selector(codigo):
    """La línea del selector de idiomas del README de `codigo`: el suyo en negrita y los demás enlazados."""
    return " · ".join(f"**{idiomas.NOMBRES[c]}**" if c == codigo else f"[{idiomas.NOMBRES[c]}]({README[c]})" for c in README)


# ------------------------------------------------------------------ un README por idioma, con su selector
def test_un_readme_por_idioma_del_mod():
    assert set(README) == set(idiomas.todos())
    assert README["en_us"] == "README.md"
    for c, f in README.items():
        assert os.path.exists(os.path.join(ROOT, f)), f"falta {f} ({c})"


@pytest.mark.parametrize("codigo", list(README))
def test_selector_de_idiomas(codigo):
    lineas = leer(README[codigo]).split("\n")
    assert lineas[0] == "# Heraldia"
    assert lineas[2] == selector(codigo)
    enlazados = set(re.findall(r"\]\((README[^)]*)\)", lineas[2]))
    assert enlazados == set(README.values()) - {README[codigo]}


@pytest.mark.parametrize("codigo", [c for c in README if c != "en_us"])
def test_misma_forma_que_el_ingles(codigo):
    en, otro = leer(README["en_us"]), leer(README[codigo])
    assert [n for n, _ in encabezados(otro)] == [n for n, _ in encabezados(en)]
    assert forma(otro) == forma(en)
    assert codigos(otro) == codigos(en)
    assert numeros(otro) == numeros(en)


@pytest.mark.parametrize("codigo", list(README))
def test_enlaza_la_documentacion(codigo):
    """Cada README enlaza la documentación (la española, el de español; la inglesa, los demás) y la guía de desarrollo."""
    texto = leer(README[codigo])
    docs = [es if codigo == "es_es" else en for en, es in DOCS]
    for d in docs + ["DESARROLLO.md"]:
        assert f"(docs/{d})" in texto, (codigo, d)


# ------------------------------------------------------------------ cifras del generador
def cifras():
    estructuras = (2 * len(THEMES) + len(MODS) + sum(len(m.ESTILOS) for _, m in medianas.modules())
                   + len(minas.estructuras()))

    class _Plantilla:
        def __init__(self, sid):
            self.entities = [(0, 0, 0, {"id": "minecraft:zombie", "Tags": [f"{logros.GUARDIAN_TAG}.{sid}"]})]

    class _Reg:     # todas las únicas tienen guardián (el de la Atlántida incluido)
        templates = {f"unicas/{sid}/x": _Plantilla(sid) for sid, _ in MODS}
    advs, _ = logros.build(_Reg, MODS, medianas.modules(), minas)
    logros_n = len(advs) + len(tablon.LOGROS) + len(arena_oleadas.LOGROS) + len(encargos.LOGROS) + len(caravanas.LOGROS)
    return {"estructuras": estructuras, "logros": logros_n}


def test_cifras_del_generador():
    c = cifras()
    # las que se comprueban también en el servidor (server_smoke.py cuenta los ficheros generados)
    assert c == {"estructuras": 142, "logros": 101}, "si cambian, cámbialas en los README y en docs/"


def test_cifras_del_readme():
    texto = leer("README.md")
    finales = [sid for sid, m in MODS if m.HISTORIA.get("final")]
    esperado = {
        r"(\d+) hand-designed villages": 2 * len(THEMES),
        r"(\d+) styles, one for each": len(THEMES),
        r"grouped in (\d+) families": len(FAMILIES),
        r"(\d+) kinds of medium structures": len(medianas.modules()),
        r"(\d+) unique structures\*\*": len(MODS) - len(finales),
        r"tab with (\d+) advancements": cifras()["logros"],
        r"Each of the (\d+) guardians": len(MODS),
        r"gather all (\d+)": len(MODS),
        r"in (\d+) sizes": len(minas.TAMANOS),
        r"in (\d+) languages": len(idiomas.todos()),
    }
    for patron, n in esperado.items():
        m = re.search(patron, texto)
        assert m and int(m.group(1)) == n, (patron, m and m.group(1), n)


@pytest.mark.parametrize("doc, patron, cual", [
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
def test_cifras_de_la_documentacion(doc, patron, cual):
    n = dict(cifras(), aldeas=2 * len(THEMES))[cual]
    m = re.search(patron, leer(f"docs/{doc}"))
    assert m and int(m.group(1)) == n, (doc, patron, m and m.group(1), n)


@pytest.mark.parametrize("codigo", list(README))
def test_tabla_de_opciones_con_los_valores_del_generador(codigo):
    defectos = {o["clave"]: o["defecto"] for o in opciones.schema()["opciones"]}
    filas = re.findall(r"^\| `([a-z_.<>]+)` \| ([^|]+) \|", leer(README[codigo]), re.M)
    assert len(filas) >= 8
    for clave, defecto in filas:
        reales = [v for k, v in defectos.items() if re.fullmatch(re.escape(clave).replace("<id>", r"\w+"), k)]
        assert reales, f"{clave} no es una opción"
        d = defecto.strip().strip("`")
        assert all(d == (str(v).lower() if isinstance(v, bool) else str(v)) for v in reales), (clave, d, reales)


# ------------------------------------------------------------------ docs/ en inglés y español
@pytest.mark.parametrize("en, es", DOCS)
def test_documentacion_en_los_dos_idiomas(en, es):
    ten, tes = leer(f"docs/{en}"), leer(f"docs/{es}")
    assert ten.split("\n")[2] == f"**English** · [Español]({es})"
    assert tes.split("\n")[2] == f"[English]({en}) · **Español**"
    assert [n for n, _ in encabezados(ten)] == [n for n, _ in encabezados(tes)]
    assert len(re.findall(r"^\|", ten, re.M)) == len(re.findall(r"^\|", tes, re.M))


def _enlaces(rel):
    """[(destino, ancla)] de los enlaces relativos de un documento."""
    out = []
    for destino in re.findall(r"\]\(([^)\s]+)\)", leer(rel)):
        if not re.match(r"[a-z]+:", destino):
            f, _, a = destino.partition("#")
            out.append((os.path.normpath(os.path.join(os.path.dirname(rel), f)) if f else rel, a))
    return out


@pytest.mark.parametrize("rel", list(README.values()) + [f"docs/{d}" for par in DOCS for d in par])
def test_enlaces_que_llevan_a_algo(rel):
    for f, a in _enlaces(rel):
        assert os.path.exists(os.path.join(ROOT, f)), (rel, f)
        if a and f.endswith(".md"):
            assert a in {ancla(t) for _, t in encabezados(leer(f))}, (rel, f, a)
