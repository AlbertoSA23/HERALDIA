"""Acueducto con ciudad en ruinas (desierto y badlands). Diseño: docs/unicas/acueducto.md."""
from .._comun.piezas import open_stairwells
from loot import item, empty, table
from .obra import Obra
from . import ciudad, agua, subsuelo, auditoria

STRUCTURE = dict(
    biomes=["minecraft:desert", "minecraft:badlands", "minecraft:wooded_badlands"],
    start_pool="unicas/acueducto/inicio",
    size=4, max_distance=116,
    terrain_adaptation="beard_box",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
)
NOMBRE = {"es_es": "Acueducto en ruinas", "en_us": "Ruined Aqueduct"}
TROFEO = {"objeto": "iron_chestplate", "rareza": "uncommon",
          "nombre": ("Lorica del Centurión Aquilio", "Lorica of Centurion Aquilius"),
          "lore": [("Forjada para la legión que custodiaba el agua.", "Forged for the legion that guarded the water.")],
          "encantamientos": {"minecraft:protection": 1},
          "componentes": {"minecraft:trim": {"material": "minecraft:gold", "pattern": "minecraft:dune"}}}   # trofeo del guardián (_comun/botin.trofeo)
HISTORIA = {   # su pliego de la Crónica de los Heraldos (docs/historia.md, _comun/botin.historia_*)
    "cofre": "cisterna",
    "relato": [
        ("La colonia se llamaba Aquae Siccae, «aguas secas», y aun así su acueducto llevaba agua por el "
         "desierto. El centurión Aquilio y su legión la custodiaban como si fuera oro. Me dieron de beber"
         " sin preguntar de dónde venía.",
         "The colony was called Aquae Siccae, “dry waters”, and still its aqueduct carried water across "
         "the desert. Centurion Aquilius and his legion guarded it as if it were gold. They gave me drink"
         " without asking where I came from."),
        ("Aquilio aceptó el pliego a cambio de un óbolo para las aguas. Juró por la tierra y el agua no "
         "entregarlo jamás, y que el fuego consumiera la colonia si faltaba a su palabra. Lo escondimos "
         "junto a la cisterna.",
         "Aquilius took the leaf in exchange for an obol to the waters. He swore by earth and water never"
         " to give it up, and that fire might consume the colony should he break his word. We hid it by "
         "the cistern."),
    ],
    "pista": ("el desierto, donde un acueducto de arcos lleva agua a una colonia de legionarios",
              "the desert, where an arched aqueduct carries water to a colony of legionaries"),
}
LOGRO = {"icono": "minecraft:water_bucket"}   # logros.py

K = "heraldia.unicas.acueducto."
TEXTOS = {   # clave: (español, inglés)
    "cartel.colonia1": ("COLONIA", "COLONIA"), "cartel.colonia2": ("AQVAE SICCAE", "AQVAE SICCAE"),
    "cartel.cisterna": ("CISTERNA", "CISTERNA"), "cartel.termas": ("THERMAE", "THERMAE"),
    "cartel.villa": ("DOMVS PRAEFECTI", "DOMVS PRAEFECTI"),
    "cartel.castellum1": ("CASTELLVM", "CASTELLVM"), "cartel.castellum2": ("AQVAE", "AQVAE"),
    "palanca.aqva": ("AQVA", "AQVA"), "palanca.ignis": ("IGNIS", "IGNIS"), "palanca.terra": ("TERRA", "TERRA"),
    "pista1": ("El agua y la tierra", "Water and earth"), "pista2": ("sostienen la ciudad;", "uphold the city;"),
    "pista3": ("el fuego", "fire"), "pista4": ("la consume.", "consumes it."),
    "ofrenda1": ("OBOLVM AQVIS", "OBOLVM AQVIS"), "ofrenda2": ("Da tu óbolo", "Give your coin"),
    "ofrenda3": ("a las aguas", "to the waters"),
    "guardian": ("Centurión Aquilio", "Centurion Aquilius"),
    "gladius": ("Gladius del Prefecto", "Prefect's Gladius"), "galea": ("Galea del Centurión", "Centurion's Galea"),
    "copa": ("Copa del Curator", "Curator's Cup"),
}
LANG = {"es_es": {K + k: v[0] for k, v in TEXTOS.items()}, "en_us": {K + k: v[1] for k, v in TEXTOS.items()}}


def named(base, key, w, mods=()):
    e = {"type": "minecraft:item", "name": "minecraft:" + base, "weight": w,
         "modifier": [{"type": "minecraft:set_name", "target": "item_name",
                       "name": {"translate": K + key, "fallback": TEXTOS[key][0], "color": "gold"}}] + list(mods)}
    return e


def ench(d):
    return {"type": "minecraft:set_enchantments", "enchantments": {"minecraft:" + k: v for k, v in d.items()}}


def extra(t, rolls, entries):
    t["pools"].append({"rolls": rolls if isinstance(rolls, int) else {"type": "minecraft:uniform", "min": rolls[0], "max": rolls[1]},
                       "entries": entries, "solo_sin_lootr": True})
    return t


POCION = {"type": "minecraft:item", "name": "minecraft:potion", "weight": 3,
          "modifier": {"type": "minecraft:set_potion", "id": "minecraft:healing"}}
LOOT = {
    "menor": extra(table(((2, 4), [item("bread", 10, 1, 3), item("cod", 4, 1, 2), item("bone", 8, 1, 3),
                                   item("string", 6, 1, 3), item("paper", 6, 1, 4), item("iron_nugget", 6, 2, 6),
                                   item("gold_nugget", 5, 2, 6), item("brick", 6, 1, 4), item("wheat", 5, 1, 4),
                                   item("clay_ball", 4, 1, 3), empty(10)])),
                   1, [item("emerald", 2), item("gold_ingot", 1), item("bowl", 3), empty(8)]),
    "tienda": extra(table(((2, 4), [item("orange_dye", 6, 1, 3), item("red_dye", 6, 1, 3), item("white_wool", 6, 1, 3),
                                    item("leather", 5, 1, 2), item("bowl", 5, 1, 2), item("flower_pot", 3),
                                    item("honey_bottle", 3), item("paper", 4, 1, 3), item("emerald", 3), empty(6)])),
                    1, [item("emerald", 4, 1, 3), item("book", 2), empty(6)]),
    "termas": extra(table(((2, 4), [item("white_wool", 6, 1, 2), item("glass_bottle", 6, 1, 3), item("sponge", 2),
                                    item("iron_ingot", 4, 1, 2), item("gold_ingot", 3), item("experience_bottle", 3, 1, 3),
                                    item("name_tag", 1), item("book", 3), item("bread", 5, 1, 3)])),
                    1, [item("golden_carrot", 3, 1, 3), item("emerald", 3, 1, 2), empty(6)]),
    "villa": extra(table(((3, 5), [item("gold_ingot", 6, 1, 3), item("iron_ingot", 6, 1, 4), item("emerald", 6, 1, 3),
                                   item("book", 5, 1, 2), item("paper", 6, 2, 6), item("writable_book", 2),
                                   item("name_tag", 2), item("spyglass", 1), item("clock", 2), item("compass", 2),
                                   item("saddle", 1)])),
                   1, [item("diamond", 1), item("golden_apple", 2), item("emerald", 4, 2, 4), empty(6)]),
    "oculto": extra(table(((2, 4), [item("diamond", 3, 1, 2), item("gold_ingot", 6, 2, 4), item("emerald", 6, 2, 5),
                                    item("book", 4, rand_ench=True), item("golden_apple", 3),
                                    item("dune_armor_trim_smithing_template", 2), item("experience_bottle", 4, 2, 5),
                                    item("raw_gold", 3, 2, 5)])),
                    1, [item("diamond", 2), item("golden_apple", 2), item("name_tag", 2), empty(4)]),
    "premium": extra(table(
        (1, [named("iron_sword", "gladius", 4, [ench({"sharpness": 2, "unbreaking": 2})]),
             named("golden_helmet", "galea", 3, [ench({"protection": 2, "unbreaking": 1})]),
             named("gold_block", "copa", 3)]),
        ((3, 4), [item("music_disc_relic", 6), item("music_disc_far", 6), item("music_disc_mall", 6),
                  item("dune_armor_trim_smithing_template", 12), item("coast_armor_trim_smithing_template", 8),
                  item("wild_armor_trim_smithing_template", 6), item("sentry_armor_trim_smithing_template", 6),
                  item("book", 15, ench=(10, 20)), item("emerald", 15, 3, 8), item("gold_ingot", 10, 4, 8),
                  # 10 %: algo más fuerte, sin romper la progresión
                  item("diamond_sword", 3, ench=(20, 30)), item("diamond_chestplate", 3, ench=(20, 30)),
                  item("enchanted_golden_apple", 2), item("diamond", 2, 2, 3)])),
        2, [item("gold_ingot", 4, 2, 4), item("emerald", 4, 2, 4), item("experience_bottle", 3, 3, 6), item("golden_apple", 1)]),
}
_dun = lambda: extra(table(((3, 6), [item("bone", 10, 1, 4), item("rotten_flesh", 10, 1, 3), item("string", 6, 1, 3),
                                    item("arrow", 6, 2, 8), item("iron_ingot", 5, 1, 3), item("gold_ingot", 3, 1, 2),
                                    item("redstone", 5, 2, 5), item("gunpowder", 4, 1, 3), item("iron_nugget", 5, 2, 6)])),
                     (1, 2), [dict(POCION), item("golden_apple", 1), item("iron_pickaxe", 1, dmg=(0.4, 0.8)), empty(6)])
LOOT["cisterna"], LOOT["cloaca"] = _dun(), _dun()

# piezas: caja global (x0, y0, z0, x1, y1, z1)
PIEZAS = {
    "castellum": (72, 0, -12, 86, 17, 4),
    "acueducto": (77, 0, -98, 81, 17, -13),
    "ciudad": (-1, 0, 5, 96, 19, 97),
    "cloaca": subsuelo.CLOACA,
    "cisterna": subsuelo.CISTERNA,
}
# (padre, pos en el padre, orientación, hijo, pos en el hijo, orientación)
UNIONES = [
    ("castellum", (82, 1, 4), "south_up", "ciudad", (82, 1, 5), "north_up"),
    ("castellum", (79, 14, -12), "north_up", "acueducto", (79, 14, -13), "south_up"),
    ("castellum", (80, 0, 0), "down_south", "cloaca", (80, -1, 0), "up_south"),
    ("ciudad", (52, 0, 46), "down_south", "cisterna", (52, -1, 46), "up_south"),
]
P = "unicas/acueducto/"
SUELO = {"processor_type": "heraldia:acueducto_hasta_el_suelo", "bloques": ["minecraft:smooth_sandstone"],
         "profundidad_maxima": 64}


def rule(block, prob, out):
    return {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:" + block,
                                "probability": prob},
            "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:" + out}


PROC = {
    "acueducto": {"processors": [SUELO]},
    "cloaca": {"processors": [{"processor_type": "minecraft:rule", "rules": [
        rule("stone_bricks", 0.25, "mossy_stone_bricks"), rule("stone_bricks", 0.1, "cracked_stone_bricks")]}]},
    "cisterna": {"processors": [{"processor_type": "minecraft:rule", "rules": [
        rule("stone_bricks", 0.35, "mossy_stone_bricks"), rule("stone_bricks", 0.1, "cracked_stone_bricks")]}]},
    "ciudad": {"processors": [{"processor_type": "minecraft:rule", "rules": [
        rule("cut_sandstone", 0.06, "sandstone"), rule("brick_slab", 0.03, "granite_slab")]}]},
}


def mundo():
    o = Obra()
    ciudad.construir(o)
    agua.construir(o)
    subsuelo.cloaca(o)
    subsuelo.cisterna(o)
    auditoria.estabilizar(o)
    return o


def dentro(p, b):
    return b[0] <= p[0] <= b[3] and b[1] <= p[1] <= b[4] and b[2] <= p[2] <= b[5]


def piezas(o):
    """Corta la plantilla global en piezas y comprueba cajas y uniones. Devuelve ({nombre: Template}, errores)."""
    from core import Template
    errs = []
    names = list(PIEZAS)
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            A, Bx = PIEZAS[a], PIEZAS[b]
            if all(A[k] <= Bx[k + 3] and Bx[k] <= A[k + 3] for k in range(3)):
                errs.append(f"las cajas de {a} y {b} se solapan")
    out = {n: Template(P + n) for n in names}
    for p, v in o.t.blocks.items():
        hit = [n for n in names if dentro(p, PIEZAS[n])]
        if not hit:
            errs.append(f"bloque fuera de toda pieza {p}")
            continue
        out[hit[0]].blocks[p] = v
    for x, y, z, nbt in o.t.entities:
        out[next(n for n in names if dentro((x, y, z), PIEZAS[n]))].entity(x, y, z, nbt)
    c = PIEZAS["castellum"]
    cx, cz = (c[0] + c[3]) / 2, (c[2] + c[5]) / 2
    for n, b in PIEZAS.items():
        if max(abs(b[0] - cx), abs(b[3] - cx), abs(b[2] - cz), abs(b[5] - cz)) > 116:
            errs.append(f"{n} sale del radio 116")
    for (pa, pp, po, ch, cp, co) in UNIONES:
        for piece, pos, ori in ((pa, pp, po), (ch, cp, co)):
            b, f = PIEZAS[piece], ori.split("_")[0]
            face = {"north": pos[2] == b[2], "south": pos[2] == b[5], "east": pos[0] == b[3], "west": pos[0] == b[0],
                    "down": pos[1] == b[1], "up": pos[1] == b[4]}[f]
            if not face or pos not in out[piece].blocks:
                errs.append(f"unión {piece} {pos} no está en la cara de su caja")
        fs = lambda t, pos: t.blocks[pos][0]
        out[pa].jigsaw(*pp, po, P + pa + "_" + ch, P + ch + "_" + pa, P + ch, final_state=fs(out[pa], pp))
        out[ch].jigsaw(*cp, co, P + ch + "_" + pa, P + pa + "_" + ch, "minecraft:empty", final_state=fs(out[ch], cp))
    return out, errs


def build(reg):
    o = mundo()
    errs, _ = auditoria.auditar(o)
    out, e2 = piezas(o)
    errs += e2
    reg.warnings += [f"acueducto: {e}" for e in errs]
    for n, t in out.items():
        open_stairwells(t)   # huecos de escalera cortos
        name = reg.add(t, "unica:acueducto")
        reg.pool(P + n, [(name, 1, "rigid", PROC.get(n))])
    reg.pool(P + "inicio", [(P + "castellum", 1, "rigid", None)])
