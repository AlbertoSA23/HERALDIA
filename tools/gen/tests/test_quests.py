"""Encargos del tablón y reputación (encargos.py, T38): textos en los 8 idiomas, logros, la página de la Guía, las opciones
y el comando, y que el Java solo use claves que existen."""
import json
import os
import re
import pytest
import commands
import quests
import guide
import languages
import options
from uniques._common import chest_loot

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
JAVA = os.path.join(ROOT, "src", "main", "java", "io", "github", "albertosa23", "heraldia")
CAVITY = re.compile(r"%(?:\d+\$)?[sd]")


def _java(route):
    with open(os.path.join(JAVA, route), encoding="utf-8") as f:
        return f.read()


def _all():
    """Claves nuevas de T38 en es_es/en_us: los textos, la Guía y las opciones."""
    out = {"es_es": {}, "en_us": {}}
    for part in (quests.lang(), guide.lang(), options.lang()):
        for k in part["es_es"]:
            if "encargos" in k or k.startswith("heraldia.config.reputacion."):
                out["es_es"][k], out["en_us"][k] = part["es_es"][k], part["en_us"][k]
    return out


def test_same_keys_and_gaps_in_es_and_en():
    lang = quests.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    for k, es in lang["es_es"].items():
        assert es.strip() and lang["en_us"][k].strip(), k
        assert CAVITY.findall(es) == CAVITY.findall(lang["en_us"][k]), k


@pytest.mark.parametrize("codigo", list(languages.TRANSLATIONS))
def test_translated_in_each_language(codigo):
    with open(languages.route(codigo), encoding="utf-8") as f:
        t = json.load(f)
    base = _all()
    assert len(base["en_us"]) >= 60
    for k, en in base["en_us"].items():
        assert k in t, f"{codigo}: falta {k}"
        assert t[k].strip(), f"{codigo}: {k} vacía"
        assert sorted(CAVITY.findall(t[k])) == sorted(CAVITY.findall(en)), f"{codigo}: {k} con otros huecos"


def test_the_java_only_uses_keys_that_exist():
    lang = quests.lang()["es_es"]
    src = _java("quests/Quests.java")
    used = set(re.findall(r'"(heraldia\.(?:encargos|estado\.encargos)[a-z_.]*)"', src))
    dynamic = {k for k in used if k.endswith(".")}
    for k in used - dynamic:
        assert k in lang, f"el Java usa {k}, que no está en encargos.py"
    # las que se completan en Java: nivel.<nivel>, estado.<estado>, saludo.<nivel>, no_aceptable.<motivo>
    for pre in dynamic:
        assert any(k.startswith(pre) for k in lang), pre
    for n in quests.LEVELS:
        assert f"heraldia.encargos.nivel.{n}" in lang
        if n != "desconocido":
            assert f"heraldia.encargos.saludo.{n}" in lang
    for e in ("entregado", "aceptado", "cumplido", "caido", "en_curso", "vencido"):
        assert f"heraldia.encargos.estado.{e}" in lang
    for m in ("hecho", "ya", "lleno", "caido"):
        assert f"heraldia.encargos.no_aceptable.{m}" in lang


def test_levels_same_as_in_java():
    src = _java("quests/Reputation.java")
    m = re.search(r"enum Tier \{\s*(.*?);", src, re.S)
    assert re.findall(r'\("(\w+)"', m.group(1)) == list(quests.LEVELS)


def test_advancements():
    advs = quests.advancements()
    ids = [lid for lid, *_ in quests.ADVANCEMENTS]
    assert list(advs) == [f"encargos/{i}" for i in ids]
    parent = "heraldia:raiz"
    for route, a in advs.items():
        assert a["parent"] == parent
        assert a["criteria"] == {"hecho": {"trigger": "minecraft:impossible"}}
        assert a["requirements"] == [["hecho"]]
        assert 0 < a["rewards"]["experience"] <= 150, "recompensa modesta"
        lid = route.split("/")[1]
        assert a["display"]["title"]["translate"] in quests.lang()["es_es"]
        assert a["display"]["description"]["translate"] in quests.lang()["es_es"]
        parent = f"heraldia:{route}"
    src = _java("quests/Quests.java")
    for lid in ids:
        assert f'"encargos/{lid}"' in src, f"el Java no concede encargos/{lid}"
    assert '"hecho"' in src


def test_write(tmp_path):
    written_map = {}
    quests.write(str(tmp_path), lambda out, route, data: written_map.__setitem__(route, data))
    assert set(written_map) == {f"data/heraldia/advancement/encargos/{lid}.json" for lid, *_ in quests.ADVANCEMENTS}


def test_guide_page():
    pids = [p[0] for p in guide.PAGES]
    assert "encargos" in pids
    assert pids.index("encargos") == pids.index("vida") + 1, "justo después de la vida en la aldea"
    _, title, text = guide.PAGES[pids.index("encargos")]
    for i in (0, 1):
        assert guide.page_lines(title[i], text[i]) <= chest_loot.BOOK_LINES
        assert "/heraldia quest" in text[i]
    for codigo in languages.TRANSLATIONS:
        with open(languages.route(codigo), encoding="utf-8") as f:
            t = json.load(f)
        kt, kx = "heraldia.guia.pagina.encargos.titulo", "heraldia.guia.pagina.encargos"
        assert guide.title_lines(t[kt]) == 1, codigo
        assert guide.page_lines(t[kt], t[kx]) <= chest_loot.BOOK_LINES, codigo
        assert "/heraldia quest" in t[kx], codigo


def test_options():
    schema = {o["clave"]: o for o in options.schema()["opciones"]}
    assert schema["encargos.activado"]["defecto"] is True
    assert schema["reputacion.activado"]["defecto"] is True
    assert schema["encargos.rotacion_dias"]["defecto"] == 3
    assert (schema["encargos.rotacion_dias"]["min"], schema["encargos.rotacion_dias"]["max"]) == (1, 30)
    for k in ("encargos.activado", "encargos.rotacion_dias", "reputacion.activado"):
        assert schema[k]["seccion"] == "encargos"
        assert not options.is_generation(k), "valor de juego, no de generación"
        assert "generacion" not in schema[k]
        assert k not in options.profile_options(), "el perfil no los toca (no son de dificultad)"
    assert "encargos" in [s for s, *_ in options.SECTIONS]
    reload = _java("config/Reload.java")
    assert '"encargos."' in reload and '"reputacion."' in reload


def test_command_in_english():
    for route in ("quest", "quest list", "quest accept", "quest accept <number>", "quest abandon", "quest abandon <number>",
                 "quest turnin"):
        assert route in commands.CANONICAL
        assert re.fullmatch(r"[a-z <>]+", route)
    # ningún texto ni botón manda a un nombre antiguo
    assert commands.text_errors(_all()["es_es"]) == []
    assert commands.text_errors(_all()["en_us"]) == []
    src = _java("quests/Quests.java")
    for order in re.findall(r'RunCommand\("([^"]*)', src) + re.findall(r'"(/heraldia quest[^"]*)"', src):
        assert order.startswith("/heraldia quest"), order
        assert not commands.old_in(order)


def test_smoke_server_in_the_map():
    import importlib.util
    spec = importlib.util.spec_from_file_location("heraldia_test_selector_encargos", os.path.join(ROOT, "tools", "test.py"))
    t = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(t)
    all_items = ["tools/smoke/quests.py", "tools/smoke/village_life.py"]
    for route in ("src/main/java/io/github/albertosa23/heraldia/quests/Quests.java",
                 "src/main/java/io/github/albertosa23/heraldia/mixin/VillagerPricesMixin.java", "tools/gen/quests.py",
                 "tools/smoke/quests.py"):
        assert t.dest(route, all_items) == ["tools/smoke/quests.py"], route
    assert "tools/smoke/quests.py" in t.DURATION_S
