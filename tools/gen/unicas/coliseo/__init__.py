"""Coliseo en ruinas: anfiteatro elíptico con hipogeo (sabana). Diseño en docs/unicas/coliseo.md."""
from .._comun.piezas import open_stairwells
from .botin import LOOT, LANG_ITEMS

STRUCTURE = dict(
    biomes=["minecraft:savanna", "minecraft:savanna_plateau"],
    start_pool="unicas/coliseo/inicio",
    size=2, max_distance=80,
    terrain_adaptation="beard_thin",
    step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
    spacing=250, separation=190,
)
NOMBRE = {"es_es": "Coliseo en ruinas", "en_us": "Ruined Colosseum"}
TROFEO = {"objeto": "shield", "rareza": "rare",
          "nombre": ("Escudo del Campeón de la Arena", "Shield of the Arena Champion"),
          "lore": [("Cien combates y ni una sola derrota.", "A hundred bouts and not a single defeat.")],
          "encantamientos": {"minecraft:unbreaking": 2},
          # sin base_color: con él el escudo se llama «Escudo rojo» e ignora item_name; el fondo es la capa «base»
          "componentes": {"minecraft:banner_patterns": [
              {"pattern": "minecraft:base", "color": "red"}, {"pattern": "minecraft:triangles_bottom", "color": "yellow"}, {"pattern": "minecraft:circle", "color": "yellow"},
              {"pattern": "minecraft:border", "color": "black"}]}}   # trofeo del guardián (_comun/botin.trofeo)
LOGRO = {"icono": "minecraft:shield"}   # logros.py

LANG = {
    "es_es": {"heraldia.coliseo.campeon": "Campeón de la Arena"},
    "en_us": {"heraldia.coliseo.campeon": "Champion of the Arena"},
}
for _k, (_es, _en) in LANG_ITEMS.items():
    LANG["es_es"][f"item.heraldia.coliseo.{_k}"] = _es
    LANG["en_us"][f"item.heraldia.coliseo.{_k}"] = _en


def _rules(*rs):
    return {"processors": [{"processor_type": "minecraft:rule", "rules": [
        {"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": f"minecraft:{a}", "probability": p},
         "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": f"minecraft:{b}"}
        for a, b, p in rs]}]}


PROC_MAIN = _rules(("smooth_sandstone", "sandstone", 0.06), ("cut_sandstone", "sandstone", 0.06))
PROC_HYP = _rules(("stone_bricks", "cracked_stone_bricks", 0.15), ("stone_bricks", "mossy_stone_bricks", 0.07))


def build(reg):
    from . import plano, auditoria
    o, main, hyp, _ = plano.construir()
    reg.warnings.extend(f"coliseo: {m}" for m in auditoria.auditar(o, main, hyp))
    open_stairwells(main)
    open_stairwells(hyp)   # huecos de escalera cortos
    a = reg.add(main, "unica:coliseo")
    b = reg.add(hyp, "unica:coliseo")
    reg.pool("unicas/coliseo/inicio", [(a, 1, "rigid", PROC_MAIN)])
    reg.pool("unicas/coliseo/hipogeo", [(b, 1, "rigid", PROC_HYP)])
