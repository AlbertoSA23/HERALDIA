"""admin.py: textos de /heraldia revisar, estado y recargar en los 8 idiomas, y que el Java (comando/) pide solo claves
que existen (las listas de qué mirar, los botones con su ayuda) y que la lista de opciones recargables (config/Recarga)
nombra opciones reales."""
import os
import re
import pytest
import admin
import idiomas
import opciones
import unicas

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
JAVA = os.path.join(RAIZ, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
CLIENTE = os.path.join(RAIZ, "src", "client", "java", "io", "github", "albertosa23", "heraldia", "client")
TEXTOS = admin.lang()
PREFIJOS = ("heraldia.revisar.", "heraldia.estado.", "heraldia.recargar.")


def _java(*partes):
    with open(os.path.join(JAVA, *partes), encoding="utf-8") as f:
        return f.read()


def test_es_y_en_con_las_mismas_claves_y_huecos():
    es, en = TEXTOS["es_es"], TEXTOS["en_us"]
    assert es.keys() == en.keys()
    for k in es:
        assert k.startswith(PREFIJOS), k
        assert idiomas.marcadores(es[k]) == idiomas.marcadores(en[k]), k
        assert es[k].strip() and en[k].strip(), k


@pytest.mark.parametrize("codigo", list(idiomas.TRADUCCIONES))
def test_cada_traduccion_tiene_todas_las_claves_con_los_huecos_del_ingles(codigo):
    trad = idiomas.cargar(codigo)
    en = TEXTOS["en_us"]
    faltan = sorted(k for k in en if k not in trad)
    assert not faltan, f"{codigo}: faltan {faltan}"
    for k in en:
        assert idiomas.marcadores(trad[k]) == idiomas.marcadores(en[k]), f"{codigo} {k}: {trad[k]!r}"
        assert trad[k].strip(), f"{codigo} {k} vacío"


@pytest.mark.parametrize("codigo", list(idiomas.TRADUCCIONES))
def test_las_traducciones_no_son_el_ingles_copiado(codigo):
    """Salvo los textos que son solo huecos y símbolos (« ✔ %s = %s», «%s. %s (%s): %s»...) o «Lootr: %s»."""
    trad, en = idiomas.cargar(codigo), TEXTOS["en_us"]
    copiados = [k for k in en if trad[k] == en[k] and re.search(r"[A-Za-z]{4,}", re.sub(r"Lootr|Heraldia", "", en[k]))]
    assert len(copiados) <= 3, f"{codigo}: {copiados}"


def test_listas_de_que_mirar_iguales_en_java_y_en_python():
    src = _java("comando", "RevisarCommand.java")
    m = re.search(r"PUNTOS = Map\.of\((.*?)\);", src, re.S)
    java = {t.lower(): int(n) for t, n in re.findall(r"Revision\.Tipo\.(\w+), (\d+)", m.group(1))}
    assert java == admin.PUNTOS
    propios = re.search(r"CON_PUNTO_PROPIO = Set\.of\((.*?)\);", src, re.S).group(1)
    assert set(re.findall(r'"(\w+)"', propios)) == set(admin.CON_PUNTO_PROPIO)
    for k in admin.claves_mirar():
        assert k in TEXTOS["es_es"], k
    sids = {sid for sid, _ in unicas.modules()}
    assert set(admin.CON_PUNTO_PROPIO) <= sids


def test_los_tipos_de_parada_de_java_tienen_su_lista():
    src = _java("comando", "Revision.java")
    tipos = re.search(r"enum Tipo \{(.*?)\}", src).group(1)
    assert {t.strip().lower() for t in tipos.split(",")} == set(admin.PUNTOS)


def test_botones_con_su_ayuda():
    for b in admin.BOTONES:
        assert f"heraldia.revisar.boton.{b}" in TEXTOS["es_es"], b
        assert f"heraldia.revisar.boton.{b}.ayuda" in TEXTOS["es_es"], b
    src = _java("comando", "RevisarCommand.java")
    usados = set(re.findall(r'"heraldia\.revisar\.boton\.(\w+)"', src))
    assert usados <= set(admin.BOTONES)


def test_el_java_solo_pide_claves_que_existen():
    """Toda cadena literal «heraldia.revisar|estado|recargar.*» del Java (completa: sin las que se terminan de armar
    con + en el código) está en los textos."""
    fuentes = ["RevisarCommand.java", "EstadoCommand.java", "RecargarCommand.java"]
    pedidas = set()
    for f in fuentes:
        for k in re.findall(r'"(heraldia\.(?:revisar|estado|recargar)\.[\w.]+)"', _java("comando", f)):
            if not k.endswith("."):
                pedidas.add(k)
    assert pedidas, "no se encontró ninguna clave en el Java"
    faltan = sorted(pedidas - TEXTOS["es_es"].keys())
    assert not faltan, faltan
    # estados de las marcas: heraldia.revisar.estado.<marca> (Revision.Marca en minúsculas) y pendiente
    marcas = re.search(r"enum Marca \{(.*?)\}", _java("comando", "Revision.java")).group(1)
    for m in [x.strip().lower() for x in marcas.split(",")] + ["pendiente"]:
        assert f"heraldia.revisar.estado.{m}" in TEXTOS["es_es"], m


def test_opciones_recargables_existen_y_las_de_generacion_no_lo_son():
    src = _java("config", "Recarga.java")
    recargables = re.findall(r'"([\w.]+)"', re.search(r"RECARGABLES = List\.of\((.*?)\);", src, re.S).group(1))
    solo = re.findall(r'"([\w.]+)"', re.search(r"SOLO_AL_ARRANCAR = List\.of\((.*?)\);", src, re.S).group(1))
    claves = [o["clave"] for o in opciones.schema()["opciones"]]
    for r in recargables + solo:
        assert any(c.startswith(r) if r.endswith(".") else c == r for c in claves), f"{r} no nombra ninguna opción"

    def recargable(c):
        return c not in solo and any(c.startswith(r) if r.endswith(".") else c == r for r in recargables)
    # lo que decide dónde y cómo se genera nunca se recarga en caliente
    for c in claves:
        if c.startswith(("aldeas.separacion", "aldeas.maximo", "aldeas.porcentaje", "aldeas.distancia", "aldeas.familias.",
                         "aldeas.estilos.", "aldeas.caminos.", "aldeas.vida.tablon", "medianas.", "minas.",
                         "compatibilidad.", "unicas.rejilla", "unicas.distancia")) \
                or re.fullmatch(r"unicas\.\w+\.(activada|separacion_bloques)", c) or c == "arena.generar_en_mundos_nuevos":
            assert not recargable(c), c
    # y lo que se lee cada vez que se usa, sí
    for c in ("dificultad.nivel", "jefes.fases.activado", "botin.reponer.activado", "botin.reponer.dias", "arena.max_mobs_vivos",
              "guia.entregar_al_entrar", "golems.limite_grande", "aldeas.vida.asedios", "unicas.atlantida.cofre_unico_por_jugador"):
        assert recargable(c), c


def test_el_aviso_de_la_pantalla_menciona_la_recarga_en_todos_los_idiomas():
    es = opciones.PANTALLA_ES["heraldia.config.pantalla.aviso_mundo"]
    en = opciones.PANTALLA_EN["heraldia.config.pantalla.aviso_mundo"]
    assert "/heraldia recargar" in es and "/heraldia recargar" in en
    for codigo in idiomas.TRADUCCIONES:
        assert "/heraldia recargar" in idiomas.cargar(codigo)["heraldia.config.pantalla.aviso_mundo"], codigo
    with open(os.path.join(CLIENTE, "HeraldiaClient.java"), encoding="utf-8") as f:
        assert "RecargarCommand.aplicar" in f.read()
