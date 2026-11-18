"""comandos.py: los comandos en inglés y sus nombres antiguos (T35b). Que el mapa de alias es el mismo que el de Java
(comando/Alias.ANTIGUOS), que ningún texto del mod (los 8 idiomas) ni ningún botón (run_command / suggest_command de los
textos generados y de los ClickEvent del Java) manda a un nombre antiguo, y que los nombres nuevos son ingleses y ASCII.
"""
import glob
import json
import os
import re
import pytest
import commands
import languages
import advancements
import uniques
import writer

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
JAVA = os.path.join(ROOT, "src", "main", "java")
ALIAS = os.path.join(JAVA, "io", "github", "albertosa23", "heraldia", "command", "Alias.java")
MODS = uniques.modules()


class _Template:
    def __init__(self, sid):
        self.entities = [(0, 0, 0, {"id": "minecraft:zombie", "Tags": [f"{advancements.GUARDIAN_TAG}.{sid}"]})]


class _Registry:
    templates = {f"unicas/{sid}/x": _Template(sid) for sid, _ in MODS}


@pytest.fixture(scope="module")
def texts():
    base = writer.texts(_Registry)
    out = dict(base)
    for c in languages.TRANSLATIONS:
        out[c] = languages.load_data(c)
    return out


def _java():
    for f in glob.glob(os.path.join(JAVA, "**", "*.java"), recursive=True):
        with open(f, encoding="utf-8") as h:
            yield os.path.relpath(f, ROOT), h.read()


# ------------------------------------------------------------------ lógica pura
def test_old_paths_cover_the_mixes():
    r = set(commands.old_paths())
    assert {"guia", "llave", "info cerca", "info aqui", "arena colocar", "arena colocar confirmar", "arena place confirmar",
            "arena colocar confirm", "arena quitar confirmar", "arena empezar", "arena parar", "arena salir"} <= r
    assert not r & set(commands.OLD), "una ruta canónica no puede salir como antigua"


@pytest.mark.parametrize("text,expected", [
    ("Usa /heraldia guia.", ["heraldia guia"]),
    ("execute as X run heraldia arena colocar confirmar", ["heraldia arena colocar confirmar"]),
    ("/heraldia arena place confirmar", ["heraldia arena place confirmar"]),
    ("/heraldia key @a todas", ["heraldia key @a todas"]),
    ("/heraldia info cerca 500", ["heraldia info cerca"]),
    ("/heraldia guide, /heraldia arena place confirm, /heraldia key @a all, /heraldia info nearby 500", []),
    ("heraldia.guia.nombre y guia.entregar_al_entrar", []),
    ("/heraldia guiado", []),
])
def test_old_in(text, expected):
    assert commands.old_in(text) == expected


def test_click_orders():
    comp = {"text": "a", "extra": [{"text": "b", "click_event": {"action": "run_command", "command": "/heraldia guia"}},
                                   {"text": "c", "clickEvent": {"action": "suggest_command", "value": "/heraldia arena place "}},
                                   {"text": "d", "click_event": {"action": "open_url", "url": "https://x"}}]}
    assert commands.click_orders(comp) == [("run_command", "/heraldia guia"), ("suggest_command", "/heraldia arena place ")]
    assert commands.click_errors(comp) == ["run_command «/heraldia guia» usa un nombre antiguo"]
    snbt = 'tellraw @a {"text":"x","click_event":{"action":"run_command","command":"/heraldia arena salir"}}'
    assert commands.click_errors([snbt]) == ["texto «/heraldia arena salir» usa un nombre antiguo"]
    assert commands.click_errors({"click_event": {"action": "run_command", "command": "/heraldia review next"}}) == []


# ------------------------------------------------------------------ el mod real
def test_same_map_as_java():
    with open(ALIAS, encoding="utf-8") as f:
        src = f.read()
    java = dict(re.findall(r'Map\.entry\("([^"]+)", "([^"]+)"\)', src))
    assert java == commands.OLD


def test_canonical_names_in_english_and_ascii():
    for route in commands.CANONICAL + list(commands.OLD):
        for segment in route.split():
            assert re.fullmatch(r"<?[a-z]+(-[a-z]+)?>?", segment), route
    assert set(commands.OLD) <= set(commands.CANONICAL)
    old = set(commands.OLD.values())
    assert not old & {t for r in commands.CANONICAL for t in r.split()}, "un nombre nuevo no puede ser uno antiguo"


def test_no_text_names_an_old_command(texts):
    errors = []
    for language, t in texts.items():
        errors += commands.text_errors(t, f"{language}: ")
    assert errors == [], errors[:20]


def test_no_java_button_sends_to_an_old_name():
    """Las órdenes de los ClickEvent (RunCommand / SuggestCommand) y todo texto "/heraldia ..." del Java."""
    errors = []
    for route, src in _java():
        if route.endswith("Alias.java"):
            continue
        for lit in re.findall(r'"((?:/|run )?heraldia [^"]*)"', src):
            errors += [f"{route}: «{lit}»" for _ in commands.old_in(lit)]
        for m in re.finditer(r"ClickEvent\.(?:RunCommand|SuggestCommand)\(([^;]*)\)", src):
            errors += [f"{route}: {m.group(0)}" for _ in commands.old_in(m.group(1))]
    assert errors == [], errors


def test_buttons_of_generated_texts(texts, tmp_path):
    """Los componentes de los textos y, si está generado, todo el datapack: ningún run_command ni suggest_command a un
    nombre antiguo."""
    errors = commands.click_errors(texts)
    gen = os.path.join(ROOT, "build", "generated", "heraldia")
    for f in glob.glob(os.path.join(gen, "**", "*.json"), recursive=True) + glob.glob(os.path.join(gen, "**", "*.mcfunction"), recursive=True):
        with open(f, encoding="utf-8") as h:
            txt = h.read()
        if "run_command" not in txt and "suggest_command" not in txt and "heraldia " not in txt:
            continue
        dataset = json.loads(txt) if f.endswith(".json") else txt.splitlines()
        errors += commands.click_errors(dataset, f"{os.path.relpath(f, gen)}: ")
        if f.endswith(".mcfunction"):
            errors += [f"{os.path.relpath(f, gen)}: {m}" for m in commands.old_in(txt)]
    assert errors == [], errors[:20]


@pytest.mark.parametrize("lang_code", languages.everyone())
def test_new_texts_in_the_8_languages(lang_code, texts):
    t = texts[lang_code]
    for k in ("heraldia.comando.obsoleto", "heraldia.version.nueva", "heraldia.version.descargar", "heraldia.version.copia",
              "heraldia.version.al_dia", "heraldia.version.comprobando", "heraldia.version.sin_respuesta",
              "heraldia.config.update_check.activado", "heraldia.config.update_check.prereleases",
              "heraldia.config.seccion.actualizaciones"):
        assert t.get(k, "").strip(), (lang_code, k)
    assert languages.markers(t["heraldia.comando.obsoleto"])[0] == [1, 2]
    assert languages.markers(t["heraldia.version.nueva"])[0] == [1, 2, 3]
    # la copia de seguridad se recomienda en todos
    assert "config" in t["heraldia.version.copia"]
