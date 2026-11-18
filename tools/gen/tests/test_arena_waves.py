"""Arena de oleadas (arena_oleadas.py): la plantilla cumple lo que dice arena.json (ruedo cerrado, cristal y techo,
puntos de aparición, campana, puerta, reaparición, luz), solo materiales que no arden ni coge un enderman, sus textos,
recompensas y logros, y su página en la Guía del Heraldo."""
import json
import math
import os
import re

import pytest

import arena_waves as a
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", ".."))
import guide
import loot
from uniques._common import chest_loot


@pytest.fixture(scope="module")
def t():
    return a.construct()


def name(st):
    return st.split("[")[0].removeprefix("minecraft:")


def test_template_complies(t):
    assert a.errors(t) == []


def test_size_content(t):
    sx, sy, sz = t.size()
    assert 48 <= sx <= 64 and 48 <= sz <= 64, "tamaño contenido: 48-64 bloques de lado"
    assert (sx, sy, sz) == tuple(a.dataset()["tamano"])


def test_only_safe_materials(t):
    used_items = {name(st) for st, _ in t.blocks.values()}
    assert used_items <= a.PALETTE
    # ninguno arde ni lo coge un enderman (#minecraft:enderman_holdable de 26.3, sin sus subetiquetas de tierra y flores)
    holdable = {"sand", "red_sand", "gravel", "tnt", "cactus", "clay", "pumpkin", "carved_pumpkin", "melon", "dirt",
                "grass_block", "mud", "moss_block", "brown_mushroom", "red_mushroom"}
    assert not used_items & holdable
    assert not any(set(b.split("_")) & {"planks", "log", "wood", "wool", "leaves", "carpet"} for b in used_items)


def test_closed_ring_without_door(t):
    """Con la puerta abierta (como está en la plantilla) se sale del ruedo; cerrada (rejas), no."""
    d = a.dataset()
    assert a.errors(t, d) == []
    # si quitamos la puerta de la lista, la comprobación debe encontrar la salida
    d2 = dict(d, puerta=[[0, 0, 0], [0, 0, 0]])
    assert any("no está cerrado" in e for e in a.errors(t, d2))


def test_a_gap_in_the_glass_is_detected(t):
    x, z = a.C + a.R_ARENA, a.C              # columna del muro, al este
    t2 = a.construct()
    t2.set(x, a.GLASS[0] + 2, z, "air")
    assert any("cristal" in e for e in a.errors(t2))
    t3 = a.construct()
    t3.set(a.C, a.ROOF, a.C, "air")
    assert any("techo" in e for e in a.errors(t3))


def test_forbidden_material_is_detected():
    t2 = a.construct()
    t2.set(a.C, 0, a.C, "oak_planks")
    assert any("PALETA" in e for e in a.errors(t2))


def test_spawn_points(t):
    d = a.dataset()
    assert len(d["puntos"]) >= 4
    for p in d["puntos"]:
        assert math.hypot(p[0] - a.C, p[2] - a.C) < a.R_ARENA - 1
        assert name(t.get(p[0], 0, p[2])) == "chiseled_red_sandstone", "marca en el suelo"
        assert name(t.get(*p)) == "air" and name(t.get(p[0], 2, p[2])) == "air"
    # repartidos: ninguno en la entrada (sur) y lejos entre sí
    for i, p in enumerate(d["puntos"]):
        assert not (abs(p[0] - a.C) <= 2 and p[2] > a.C), "un punto delante de la entrada"
        for q in d["puntos"][i + 1:]:
            assert math.hypot(p[0] - q[0], p[2] - q[2]) >= 6


def test_bell_door_and_respawn(t):
    d = a.dataset()
    assert name(t.get(*d["campana"])) == "bell"
    (x0, y0, z0), (x1, y1, z1) = d["puerta"]
    for x in range(x0, x1 + 1):
        for y in range(y0, y1 + 1):
            for z in range(z0, z1 + 1):
                assert name(t.get(x, y, z)) == "air"
                assert a.R_ARENA <= math.hypot(x - a.C, z - a.C) < a.R_WALL, "la puerta corta el muro del ruedo"
    rp = d["reaparicion"]
    assert name(t.get(*rp)) == "air" and name(t.get(rp[0], rp[1] - 1, rp[2])) != "air"
    assert rp[1] - 1 == a.FLOOR, "la reaparición está a ras del suelo exterior"


def test_bleachers_protected_by_glass(t):
    """Entre el ruedo y las gradas hay cristal hasta el techo de barreras en toda la vuelta (también sobre la puerta)."""
    for g in range(0, 360, 5):
        r = math.radians(g)
        x, z = a.C + round(15 * math.cos(r)), a.C + round(15 * math.sin(r))
        col = [name(t.get(x, y, z)) for y in range(a.GLASS[0], a.ROOF + 1)]
        assert col == ["glass"] * (a.GLASS[1] - a.GLASS[0] + 1) + ["barrier"], (g, col)


def test_entry_low_of_the_walkway_to_the_ring(t):
    """La rampa de la entrada sube de peldaño en peldaño (escaleras) del suelo del ruedo al del paseo."""
    stories = []
    for z in range(a.DOOR_Z[0], a.N):
        y = next(y for y in range(a.HEIGHT) if name(t.get(a.C, y, z)) == "air") - 1     # el piso: bajo el primer aire
        stories.append(y)
    assert stories[0] == 0 and stories[-1] == a.FLOOR
    assert all(0 <= b - c <= 1 for c, b in zip(stories, stories[1:])), stories


def test_data_json_serializable_and_complete():
    d = a.dataset()
    json.dumps(d)
    assert set(d) >= {"plantilla", "tamano", "suelo", "centro", "radio_ruedo", "ruedo_y", "puntos", "campana", "puerta",
                      "reaparicion"}
    assert d["plantilla"] == "heraldia:arena/arena"


def test_texts_complete():
    lang = a.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    assert all(v.strip() for texts in lang.values() for v in texts.values())
    for k, es in lang["es_es"].items():
        assert re.findall(r"%[sd]", es) == re.findall(r"%[sd]", lang["en_us"][k]), k
    for i in range(len(a.BOSSES)):
        assert f"heraldia.arena.jefe.{i}" in lang["es_es"]
    # los textos de éxito no deben cortar la espera de las pruebas de servidor (ERROR_PATTERN de server_smoke)
    for texts in lang.values():
        for k, v in texts.items():
            assert not re.search(r"Unknown|Incorrect|Failed|Invalid|error|not loaded", v), k


def test_rewards_improve_with_the_wave():
    tables = a.tables()
    assert sorted(tables) == [f"arena/recompensa_{n}" for n in range(1, 5)]
    for t in tables.values():
        s = json.dumps(t)
        assert "netherite" not in s and "elytra" not in s
        assert all(p["rolls"] for p in t["pools"])
    pricey = lambda t: json.dumps(t).count("diamond")
    assert pricey(tables["arena/recompensa_1"]) < pricey(tables["arena/recompensa_4"])


def test_advancements_5_10_20():
    ls = {k: v for k, v in a.advancements().items() if k.startswith("arena/oleada_")}
    assert sorted(ls) == ["arena/oleada_10", "arena/oleada_20", "arena/oleada_5"]
    assert ls["arena/oleada_5"]["parent"] == "heraldia:raiz"
    assert ls["arena/oleada_10"]["parent"] == "heraldia:arena/oleada_5"
    assert ls["arena/oleada_20"]["parent"] == "heraldia:arena/oleada_10"
    for l in ls.values():
        assert l["criteria"] == {"oleada": {"trigger": "minecraft:impossible"}}
        assert set(l["rewards"]) == {"experience"}


def test_guide_page():
    pages = {pid: (title, text) for pid, title, text in guide.PAGES}
    assert "arena" in pages
    title, text = pages["arena"]
    for i in (0, 1):
        assert guide.page_lines(title[i], text[i]) <= chest_loot.BOOK_LINES
        assert "/heraldia arena" in text[i]
    assert guide.lang()["es_es"]["heraldia.guia.pagina.arena.titulo"] == "La arena"


# --- T41: modos, salón de la fama y logros de los modos ---

def test_signs_of_the_hall_of_the_fame(t):
    d = a.dataset()
    assert len(d["fama"]) == len(a.MODES) == 3 and d["fama_rotacion"] == 0
    for p in d["fama"]:
        assert name(t.get(*p)) == "crimson_sign"
        assert t.get(*p) == "minecraft:crimson_sign[rotation=0]" or "rotation=0" in t.get(*p)
        assert name(t.get(p[0], p[1] - 1, p[2])) not in ("air", None)      # sobre suelo
        assert name(t.get(p[0], p[1], p[2] + 1)) == "air"                   # con sitio delante (al sur) para leerlo
        assert a.R_BLEACHERS <= a.dist(p[0], p[2]) < 27 and not a.at_entrance(p[0], p[2])
    assert "crimson_sign" in a.PALETTE                                         # madera del Nether: no arde


def test_errors_detects_a_sign_badly_outpost(t):
    d = dict(a.dataset(), fama=[list(a.BELL)] * 3)
    assert any("salón de la fama" in e for e in a.errors(t, d))
    d = dict(a.dataset(), fama=a.dataset()["fama"][:2])
    assert any("uno por modo" in e for e in a.errors(t, d))


def test_advancements_of_the_modes():
    ls = a.advancements()
    new_items = {f"arena/{lid}" for lid, *_ in a.ADVANCEMENTS_MODES}
    assert new_items == {"arena/contrarreloj", "arena/contrarreloj_rapido", "arena/supervivencia_15", "arena/campeon_coop",
                      "arena/campeon_timeattack", "arena/campeon_survival"}
    assert new_items <= set(ls)
    for lid in new_items:
        l = ls[lid]
        assert l["criteria"] == {"logro": {"trigger": "minecraft:impossible"}}
        assert l["parent"].removeprefix("heraldia:") in ls                       # el padre existe
    # los campeones, uno por modo (Java: Marcas.logroCampeon = arena/campeon_<id del modo>)
    assert {f"arena/campeon_{m}" for m in a.MODES} <= new_items
    # las cifras de los textos son las del Java (arena/Marcas)
    marks = open(os.path.join(ROOT, "src/main/java/io/github/albertosa23/heraldia/arena/Marks.java"), encoding="utf-8").read()
    assert f"TIME_TRIAL_WAVES = {a.TIME_ATTACK_WAVES};" in marks
    assert f"TIME_TRIAL_FAST_TICKS = {a.TIME_ATTACK_FAST_MIN} * 60 * 20;" in marks
    assert f"SURVIVAL_WAVES = {a.WAVE_SURVIVAL};" in marks
    lang = a.lang()
    for lid in new_items:
        assert f"advancements.heraldia.{lid.replace('/', '.')}.title" in lang["es_es"]


def test_modes_and_their_texts():
    lang = a.lang()
    java = open(os.path.join(ROOT, "src/main/java/io/github/albertosa23/heraldia/arena/Mode.java"), encoding="utf-8").read()
    for m in a.MODES:
        assert f'"{m}"' in java                                                  # el id del comando (Modo.id)
        for language in ("es_es", "en_us"):
            assert lang[language][f"heraldia.arena.modo.{m}"]
            assert lang[language][f"heraldia.arena.modo.{m}.ayuda"]
    assert "%s" in lang["es_es"]["heraldia.arena.modo.timeattack.ayuda"]       # las oleadas del contrarreloj


def test_the_sign_fits_and_gets_checks():
    assert a.text_errors() == []
    length = {**a.lang()["en_us"], "heraldia.arena.cartel.titulo": "Champion of the whole week"}
    assert any("cartel.titulo" in e for e in a.text_errors({"xx_xx": length}))
    # el nombre del jugador va solo en su línea: uno típico cabe
    import languages
    assert languages.sign_width(a.TYPICAL_NAME) <= languages.SIGN_WIDTH


def test_the_sign_fits_in_each_language():
    import json as _json, glob
    for f in glob.glob(os.path.join(ROOT, "tools/gen/languages/*.json")):
        texts = _json.load(open(f, encoding="utf-8"))
        assert a.text_errors({os.path.basename(f): texts}) == [], f


def test_commands_new_in_english():
    import commands
    for r in ("arena start coop", "arena start timeattack", "arena start survival", "arena leaderboard",
              "arena leaderboard coop <week>", "arena leaderboard timeattack <week>", "arena leaderboard survival <week>",
              "arena season", "arena season reset"):
        assert r in commands.CANONICAL, r
