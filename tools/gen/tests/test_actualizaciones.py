"""actualizaciones.py (T46): los textos del panel de configuración, del idioma por jugador, de los arreglos y de
/heraldia update, en los 8 idiomas, iguales en el módulo y en idiomas/<código>.json, con los mismos huecos, sin inglés
copiado, y que el Java solo pide claves que existen (y todas las que pide existen)."""
import os
import re
import pytest
import actualizaciones as a
import idiomas
import opciones

RAIZ = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..")
JAVA = os.path.join(RAIZ, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
FICHEROS = [os.path.join(JAVA, *p) for p in (("command", "ConfigPanel.java"), ("command", "Preferences.java"),
                                            ("update", "Updater.java"), ("update", "Execution.java"))]
TEXTOS = a.lang()


def _java():
    out = ""
    for f in FICHEROS:
        with open(f, encoding="utf-8") as fh:
            out += fh.read()
    return out


def test_es_y_en_con_las_mismas_claves_y_huecos():
    es, en = TEXTOS["es_es"], TEXTOS["en_us"]
    assert es.keys() == en.keys()
    for k in es:
        assert k.startswith(("heraldia.panel.", "heraldia.idioma.", "heraldia.actualizar.", "heraldia.arreglos.")), k
        assert idiomas.marcadores(es[k]) == idiomas.marcadores(en[k]), k
        assert es[k].strip() and en[k].strip(), k


@pytest.mark.parametrize("codigo", list(idiomas.TRADUCCIONES))
def test_cada_traduccion_esta_en_su_fichero_con_los_huecos_del_ingles(codigo):
    trad = idiomas.cargar(codigo)
    for k, v in a.traduccion(codigo).items():
        assert trad.get(k) == v, f"{codigo} {k}: ejecuta python3 tools/gen/actualizaciones.py"
    for k, en in TEXTOS["en_us"].items():
        assert idiomas.marcadores(trad[k]) == idiomas.marcadores(en), f"{codigo} {k}"


@pytest.mark.parametrize("codigo", list(idiomas.TRADUCCIONES))
def test_las_traducciones_no_son_el_ingles_copiado(codigo):
    trad, en = a.traduccion(codigo), TEXTOS["en_us"]
    copiados = [k for k in en if not k.startswith("heraldia.idioma.nombre.") and trad[k] == en[k]
                and re.search(r"[A-Za-z]{4,}", re.sub(r"Heraldia|Arena|config/heraldia\.json", "", en[k]))]
    assert not copiados, f"{codigo}: {copiados}"


def test_la_opcion_nueva_tiene_texto_en_todos():
    k = "heraldia.config.actualizar.margen_bloques"
    assert k in opciones.lang()["es_es"] and k + ".nombre" in opciones.lang()["en_us"]
    for c in idiomas.TRADUCCIONES:
        assert a.traduccion(c)[k].strip() and a.traduccion(c)[k + ".nombre"].strip()


def test_el_java_pide_claves_que_existen():
    src = _java()
    pedidas = set(re.findall(r'"(heraldia\.(?:panel|idioma|actualizar|arreglos)\.[a-z_.]*[a-z_])"', src))
    assert pedidas, "no se encontraron claves en el Java"
    faltan = sorted(k for k in pedidas if k not in TEXTOS["es_es"])
    assert not faltan, faltan
    # las que se arman con un trozo: un submenú, un perfil, un arreglo y un idioma
    for m in a.MENUS:
        assert f"heraldia.panel.menu.{m}" in TEXTOS["es_es"] and f"heraldia.panel.menu.{m}.ayuda" in TEXTOS["es_es"]
    for p in a.PERFILES:
        assert f"heraldia.panel.perfil.{p}" in TEXTOS["es_es"]
    for r in a.ARREGLOS:
        assert f"heraldia.arreglos.{r}" in TEXTOS["es_es"]
    for c in idiomas.todos():
        assert f"heraldia.idioma.nombre.{c}" in TEXTOS["es_es"]


def test_menus_y_arreglos_como_en_java():
    with open(os.path.join(JAVA, "config", "Menus.java"), encoding="utf-8") as f:
        menus = re.findall(r'new Menu\("(\w+)"', f.read())
    assert tuple(menus) == a.MENUS
    with open(os.path.join(JAVA, "update", "MobFixes.java"), encoding="utf-8") as f:
        arreglos = re.findall(r'new Fix<>\(\d+, "(\w+)"', f.read())
    assert tuple(arreglos) == a.ARREGLOS
    assert set(a.IDIOMAS) == set(idiomas.todos())


def test_las_ordenes_de_los_botones_son_comandos_canonicos():
    """Lo que ejecutan los botones (/heraldia config ..., update ...) usa solo nombres en inglés de comandos.CANONICOS."""
    import comandos
    src = _java()
    for cmd in re.findall(r'"heraldia ((?:config|update|language)[a-z \-]*)', src):
        tramos = cmd.split()
        ruta = " ".join(t for t in tramos if re.fullmatch(r"[a-z]+(-[a-z]+)?", t))
        assert any(c.startswith(ruta) for c in comandos.CANONICOS), cmd
