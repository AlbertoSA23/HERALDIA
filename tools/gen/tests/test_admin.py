"""admin.py: textos de /heraldia review, status y reload en los 8 idiomas, y que el Java (comando/) pide solo claves
que existen (las listas de qué mirar, los botones con su ayuda) y que la lista de opciones recargables (config/Recarga)
nombra opciones reales."""
import os
import re
import pytest
import admin
import languages
import options
import uniques

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
JAVA = os.path.join(ROOT, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
CLIENT = os.path.join(ROOT, "src", "client", "java", "io", "github", "albertosa23", "heraldia", "client")
TEXTS = admin.lang()
PREFIXES = ("heraldia.revisar.", "heraldia.estado.", "heraldia.recargar.", "heraldia.version.", "heraldia.comando.",
            "heraldia.mapas_web.")


def _java(*parts):
    with open(os.path.join(JAVA, *parts), encoding="utf-8") as f:
        return f.read()


def _ids_enum(src, name):
    """Constante → id guardado de un enum del Java con ids explícitos (p. ej. VILLAGE("aldea"))."""
    body = re.search(r"enum " + name + r" \{(.*?);", src, re.S).group(1)
    return dict(re.findall(r'(\w+)\("(\w+)"', body))


def test_es_y_en_with_the_same_keys_and_gaps():
    es, en = TEXTS["es_es"], TEXTS["en_us"]
    assert es.keys() == en.keys()
    for k in es:
        assert k.startswith(PREFIXES), k
        assert languages.markers(es[k]) == languages.markers(en[k]), k
        assert es[k].strip() and en[k].strip(), k


@pytest.mark.parametrize("codigo", list(languages.TRANSLATIONS))
def test_each_translation_has_all_the_keys_with_the_gaps_of_the_english(codigo):
    translated = languages.load_data(codigo)
    en = TEXTS["en_us"]
    missing = sorted(k for k in en if k not in translated)
    assert not missing, f"{codigo}: faltan {missing}"
    for k in en:
        assert languages.markers(translated[k]) == languages.markers(en[k]), f"{codigo} {k}: {translated[k]!r}"
        assert translated[k].strip(), f"{codigo} {k} vacío"


@pytest.mark.parametrize("codigo", list(languages.TRANSLATIONS))
def test_translations_are_not_copied_english(codigo):
    """Salvo los textos que son solo huecos y símbolos (« ✔ %s = %s», «%s. %s (%s): %s»...) o «Lootr: %s»."""
    translated, en = languages.load_data(codigo), TEXTS["en_us"]
    copied = [k for k in en if translated[k] == en[k] and re.search(r"[A-Za-z]{4,}", re.sub(r"Lootr|Heraldia", "", en[k]))]
    assert len(copied) <= 3, f"{codigo}: {copied}"


def test_lookup_lists_equal_in_java_and_python():
    src = _java("command", "ReviewCommand.java")
    m = re.search(r"POINTS = Map\.of\((.*?)\);", src, re.S)
    ids = _ids_enum(_java("command", "Revision.java"), "Type")
    java = {ids[t]: int(n) for t, n in re.findall(r"Revision\.Type\.(\w+), (\d+)", m.group(1))}
    assert java == admin.POINTS
    own_items = re.search(r"WITH_OWN_POINT = Set\.of\((.*?)\);", src, re.S).group(1)
    assert set(re.findall(r'"(\w+)"', own_items)) == set(admin.WITH_OWN_POINT)
    for k in admin.keys_to_check():
        assert k in TEXTS["es_es"], k
    sids = {sid for sid, _ in uniques.modules()}
    assert set(admin.WITH_OWN_POINT) <= sids


def test_java_stop_kinds_have_their_list():
    src = _java("command", "Revision.java")
    assert set(_ids_enum(src, "Type").values()) == set(admin.POINTS)


def test_buttons_with_its_help():
    for b in admin.BUTTONS:
        assert f"heraldia.revisar.boton.{b}" in TEXTS["es_es"], b
        assert f"heraldia.revisar.boton.{b}.ayuda" in TEXTS["es_es"], b
    src = _java("command", "ReviewCommand.java")
    used_items = set(re.findall(r'"heraldia\.revisar\.boton\.(\w+)"', src))
    assert used_items <= set(admin.BUTTONS)


def test_the_java_only_requests_keys_that_exist():
    """Toda cadena literal «heraldia.revisar|estado|recargar|version|comando.*» del Java (completa: sin las que se terminan de armar
    con + en el código) está en los textos."""
    sources = ["ReviewCommand.java", "StatusCommand.java", "ReloadCommand.java", "VersionNotice.java", "HeraldiaCommands.java"]
    requested = set()
    for f in sources:
        for k in re.findall(r'"(heraldia\.(?:revisar|estado|recargar|version|comando)\.[\w.]+)"', _java("command", f)):
            if not k.endswith("."):
                requested.add(k)
    assert requested, "no se encontró ninguna clave en el Java"
    missing = sorted(requested - TEXTS["es_es"].keys())
    assert not missing, missing
    # estados de las marcas: heraldia.revisar.estado.<marca> (Revision.Marca en minúsculas) y pendiente
    marks = _ids_enum(_java("command", "Revision.java"), "Mark").values()
    for m in list(marks) + ["pendiente"]:
        assert f"heraldia.revisar.estado.{m}" in TEXTS["es_es"], m


def test_reloadable_options_exist_and_generation_ones_are_not():
    src = _java("config", "Reload.java")
    reloadables = re.findall(r'"([\w.]+)"', re.search(r"RELOADABLE = List\.of\((.*?)\);", src, re.S).group(1))
    only = re.findall(r'"([\w.]+)"', re.search(r"STARTUP_ONLY = List\.of\((.*?)\);", src, re.S).group(1))
    keys = [o["clave"] for o in options.schema()["opciones"]]
    for r in reloadables + only:
        assert any(c.startswith(r) if r.endswith(".") else c == r for c in keys), f"{r} no nombra ninguna opción"

    def reloadable(c):
        return c not in only and any(c.startswith(r) if r.endswith(".") else c == r for r in reloadables)
    # lo que decide dónde y cómo se genera nunca se recarga en caliente
    for c in keys:
        if c.startswith(("aldeas.separacion", "aldeas.maximo", "aldeas.porcentaje", "aldeas.distancia", "aldeas.familias.",
                         "aldeas.estilos.", "aldeas.caminos.", "aldeas.vida.tablon", "medianas.", "minas.",
                         "compatibilidad.", "unicas.rejilla", "unicas.distancia")) \
                or re.fullmatch(r"unicas\.\w+\.(activada|separacion_bloques)", c) or c == "arena.generar_en_mundos_nuevos":
            assert not reloadable(c), c
    # y lo que se lee cada vez que se usa, sí
    for c in ("dificultad.nivel", "jefes.fases.activado", "botin.reponer.activado", "botin.reponer.dias", "arena.max_mobs_vivos",
              "guia.entregar_al_entrar", "golems.limite_grande", "aldeas.vida.asedios", "unicas.atlantida.cofre_unico_por_jugador"):
        assert reloadable(c), c


def test_the_warning_of_the_screen_mentions_the_reload_in_all_the_languages():
    es = options.SCREEN_ES["heraldia.config.pantalla.aviso_mundo"]
    en = options.SCREEN_EN["heraldia.config.pantalla.aviso_mundo"]
    assert "/heraldia reload" in es and "/heraldia reload" in en
    for codigo in languages.TRANSLATIONS:
        assert "/heraldia reload" in languages.load_data(codigo)["heraldia.config.pantalla.aviso_mundo"], codigo
    with open(os.path.join(CLIENT, "HeraldiaClient.java"), encoding="utf-8") as f:
        assert "ReloadCommand.apply" in f.read()
