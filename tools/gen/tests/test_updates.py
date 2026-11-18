"""actualizaciones.py (T46): los textos del panel de configuración, del idioma por jugador, de los arreglos y de
/heraldia update, en los 8 idiomas, iguales en el módulo y en idiomas/<código>.json, con los mismos huecos, sin inglés
copiado, y que el Java solo pide claves que existen (y todas las que pide existen)."""
import os
import re
import pytest
import updates as a
import languages
import options

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
JAVA = os.path.join(ROOT, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
FILES = [os.path.join(JAVA, *p) for p in (("command", "ConfigPanel.java"), ("command", "Preferences.java"),
                                            ("update", "Updater.java"), ("update", "Execution.java"))]
TEXTS = a.lang()


def _java():
    out = ""
    for f in FILES:
        with open(f, encoding="utf-8") as fh:
            out += fh.read()
    return out


def test_es_y_en_with_the_same_keys_and_gaps():
    es, en = TEXTS["es_es"], TEXTS["en_us"]
    assert es.keys() == en.keys()
    for k in es:
        assert k.startswith(("heraldia.panel.", "heraldia.idioma.", "heraldia.actualizar.", "heraldia.arreglos.")), k
        assert languages.markers(es[k]) == languages.markers(en[k]), k
        assert es[k].strip() and en[k].strip(), k


@pytest.mark.parametrize("codigo", list(languages.TRANSLATIONS))
def test_each_translation_is_in_its_file_with_the_gaps_of_the_english(codigo):
    translated = languages.load_data(codigo)
    for k, v in a.translation(codigo).items():
        assert translated.get(k) == v, f"{codigo} {k}: ejecuta python3 tools/gen/updates.py"
    for k, en in TEXTS["en_us"].items():
        assert languages.markers(translated[k]) == languages.markers(en), f"{codigo} {k}"


@pytest.mark.parametrize("codigo", list(languages.TRANSLATIONS))
def test_translations_are_not_copied_english(codigo):
    translated, en = a.translation(codigo), TEXTS["en_us"]
    copied = [k for k in en if not k.startswith("heraldia.idioma.nombre.") and translated[k] == en[k]
                and re.search(r"[A-Za-z]{4,}", re.sub(r"Heraldia|Arena|config/heraldia\.json", "", en[k]))]
    assert not copied, f"{codigo}: {copied}"


def test_new_option_has_text_in_all():
    k = "heraldia.config.actualizar.margen_bloques"
    assert k in options.lang()["es_es"] and k + ".nombre" in options.lang()["en_us"]
    for c in languages.TRANSLATIONS:
        assert a.translation(c)[k].strip() and a.translation(c)[k + ".nombre"].strip()


def test_the_java_requests_keys_that_exist():
    src = _java()
    requested = set(re.findall(r'"(heraldia\.(?:panel|idioma|actualizar|arreglos)\.[a-z_.]*[a-z_])"', src))
    assert requested, "no se encontraron claves en el Java"
    missing = sorted(k for k in requested if k not in TEXTS["es_es"])
    assert not missing, missing
    # las que se arman con un trozo: un submenú, un perfil, un arreglo y un idioma
    for m in a.MENUS:
        assert f"heraldia.panel.menu.{m}" in TEXTS["es_es"] and f"heraldia.panel.menu.{m}.ayuda" in TEXTS["es_es"]
    for p in a.PROFILES:
        assert f"heraldia.panel.perfil.{p}" in TEXTS["es_es"]
    for r in a.FIXES:
        assert f"heraldia.arreglos.{r}" in TEXTS["es_es"]
    for c in languages.everyone():
        assert f"heraldia.idioma.nombre.{c}" in TEXTS["es_es"]


def test_menus_and_arrays_as_in_java():
    with open(os.path.join(JAVA, "config", "Menus.java"), encoding="utf-8") as f:
        menus = re.findall(r'new Menu\("(\w+)"', f.read())
    assert tuple(menus) == a.MENUS
    with open(os.path.join(JAVA, "update", "MobFixes.java"), encoding="utf-8") as f:
        fixes = re.findall(r'new Fix<>\(\d+, "(\w+)"', f.read())
    assert tuple(fixes) == a.FIXES
    assert set(a.LANGUAGES) == set(languages.everyone())


def test_button_orders_are_canonical_commands():
    """Lo que ejecutan los botones (/heraldia config ..., update ...) usa solo nombres en inglés de comandos.CANONICOS."""
    import commands
    src = _java()
    for cmd in re.findall(r'"heraldia ((?:config|update|language)[a-z \-]*)', src):
        segments = cmd.split()
        route = " ".join(t for t in segments if re.fullmatch(r"[a-z]+(-[a-z]+)?", t))
        assert any(c.startswith(route) for c in commands.CANONICAL), cmd
