"""comandos.py: los comandos en inglés y sus nombres antiguos (T35b). Que el mapa de alias es el mismo que el de Java
(comando/Alias.ANTIGUOS), que ningún texto del mod (los 8 idiomas) ni ningún botón (run_command / suggest_command de los
textos generados y de los ClickEvent del Java) manda a un nombre antiguo, y que los nombres nuevos son ingleses y ASCII.
"""
import glob
import json
import os
import re
import pytest
import comandos
import idiomas
import logros
import unicas
import writer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
JAVA = os.path.join(ROOT, "src", "main", "java")
ALIAS = os.path.join(JAVA, "io", "github", "albertosa23", "heraldia", "comando", "Alias.java")
MODS = unicas.modules()


class _Plantilla:
    def __init__(self, sid):
        self.entities = [(0, 0, 0, {"id": "minecraft:zombie", "Tags": [f"{logros.GUARDIAN_TAG}.{sid}"]})]


class _Reg:
    templates = {f"unicas/{sid}/x": _Plantilla(sid) for sid, _ in MODS}


@pytest.fixture(scope="module")
def textos():
    base = writer.textos(_Reg)
    out = dict(base)
    for c in idiomas.TRADUCCIONES:
        out[c] = idiomas.cargar(c)
    return out


def _java():
    for f in glob.glob(os.path.join(JAVA, "**", "*.java"), recursive=True):
        with open(f, encoding="utf-8") as h:
            yield os.path.relpath(f, ROOT), h.read()


# ------------------------------------------------------------------ lógica pura
def test_rutas_antiguas_cubren_las_mezclas():
    r = set(comandos.rutas_antiguas())
    assert {"guia", "llave", "info cerca", "info aqui", "arena colocar", "arena colocar confirmar", "arena place confirmar",
            "arena colocar confirm", "arena quitar confirmar", "arena empezar", "arena parar", "arena salir"} <= r
    assert not r & set(comandos.ANTIGUOS), "una ruta canónica no puede salir como antigua"


@pytest.mark.parametrize("texto,esperado", [
    ("Usa /heraldia guia.", ["heraldia guia"]),
    ("execute as X run heraldia arena colocar confirmar", ["heraldia arena colocar confirmar"]),
    ("/heraldia arena place confirmar", ["heraldia arena place confirmar"]),
    ("/heraldia key @a todas", ["heraldia key @a todas"]),
    ("/heraldia info cerca 500", ["heraldia info cerca"]),
    ("/heraldia guide, /heraldia arena place confirm, /heraldia key @a all, /heraldia info nearby 500", []),
    ("heraldia.guia.nombre y guia.entregar_al_entrar", []),
    ("/heraldia guiado", []),
])
def test_antiguos_en(texto, esperado):
    assert comandos.antiguos_en(texto) == esperado


def test_ordenes_de_clic():
    comp = {"text": "a", "extra": [{"text": "b", "click_event": {"action": "run_command", "command": "/heraldia guia"}},
                                   {"text": "c", "clickEvent": {"action": "suggest_command", "value": "/heraldia arena place "}},
                                   {"text": "d", "click_event": {"action": "open_url", "url": "https://x"}}]}
    assert comandos.ordenes_de_clic(comp) == [("run_command", "/heraldia guia"), ("suggest_command", "/heraldia arena place ")]
    assert comandos.errores_clic(comp) == ["run_command «/heraldia guia» usa un nombre antiguo"]
    snbt = 'tellraw @a {"text":"x","click_event":{"action":"run_command","command":"/heraldia arena salir"}}'
    assert comandos.errores_clic([snbt]) == ["texto «/heraldia arena salir» usa un nombre antiguo"]
    assert comandos.errores_clic({"click_event": {"action": "run_command", "command": "/heraldia review next"}}) == []


# ------------------------------------------------------------------ el mod real
def test_mismo_mapa_que_java():
    with open(ALIAS, encoding="utf-8") as f:
        src = f.read()
    java = dict(re.findall(r'Map\.entry\("([^"]+)", "([^"]+)"\)', src))
    assert java == comandos.ANTIGUOS


def test_nombres_canonicos_en_ingles_y_ascii():
    for ruta in comandos.CANONICOS + list(comandos.ANTIGUOS):
        for tramo in ruta.split():
            assert re.fullmatch(r"<?[a-z]+>?", tramo), ruta
    assert set(comandos.ANTIGUOS) <= set(comandos.CANONICOS)
    viejos = set(comandos.ANTIGUOS.values())
    assert not viejos & {t for r in comandos.CANONICOS for t in r.split()}, "un nombre nuevo no puede ser uno antiguo"


def test_ningun_texto_nombra_un_comando_antiguo(textos):
    errores = []
    for idioma, t in textos.items():
        errores += comandos.errores_textos(t, f"{idioma}: ")
    assert errores == [], errores[:20]


def test_ningun_boton_del_java_manda_a_un_nombre_antiguo():
    """Las órdenes de los ClickEvent (RunCommand / SuggestCommand) y todo texto "/heraldia ..." del Java."""
    errores = []
    for ruta, src in _java():
        if ruta.endswith("Alias.java"):
            continue
        for lit in re.findall(r'"((?:/|run )?heraldia [^"]*)"', src):
            errores += [f"{ruta}: «{lit}»" for _ in comandos.antiguos_en(lit)]
        for m in re.finditer(r"ClickEvent\.(?:RunCommand|SuggestCommand)\(([^;]*)\)", src):
            errores += [f"{ruta}: {m.group(0)}" for _ in comandos.antiguos_en(m.group(1))]
    assert errores == [], errores


def test_los_botones_de_los_textos_generados(textos, tmp_path):
    """Los componentes de los textos y, si está generado, todo el datapack: ningún run_command ni suggest_command a un
    nombre antiguo."""
    errores = comandos.errores_clic(textos)
    gen = os.path.join(ROOT, "build", "generated", "heraldia")
    for f in glob.glob(os.path.join(gen, "**", "*.json"), recursive=True) + glob.glob(os.path.join(gen, "**", "*.mcfunction"), recursive=True):
        with open(f, encoding="utf-8") as h:
            txt = h.read()
        if "run_command" not in txt and "suggest_command" not in txt and "heraldia " not in txt:
            continue
        datos = json.loads(txt) if f.endswith(".json") else txt.splitlines()
        errores += comandos.errores_clic(datos, f"{os.path.relpath(f, gen)}: ")
        if f.endswith(".mcfunction"):
            errores += [f"{os.path.relpath(f, gen)}: {m}" for m in comandos.antiguos_en(txt)]
    assert errores == [], errores[:20]


@pytest.mark.parametrize("codigo", idiomas.todos())
def test_textos_nuevos_en_los_8_idiomas(codigo, textos):
    t = textos[codigo]
    for k in ("heraldia.comando.obsoleto", "heraldia.version.nueva", "heraldia.version.descargar", "heraldia.version.copia",
              "heraldia.version.al_dia", "heraldia.version.comprobando", "heraldia.version.sin_respuesta",
              "heraldia.config.update_check.activado", "heraldia.config.update_check.prereleases",
              "heraldia.config.seccion.actualizaciones"):
        assert t.get(k, "").strip(), (codigo, k)
    assert idiomas.marcadores(t["heraldia.comando.obsoleto"])[0] == [1, 2]
    assert idiomas.marcadores(t["heraldia.version.nueva"])[0] == [1, 2, 3]
    # la copia de seguridad se recomienda en todos
    assert "config" in t["heraldia.version.copia"]
