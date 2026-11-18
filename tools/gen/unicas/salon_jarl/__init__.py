"""Salón del Jarl: asentamiento nórdico fortificado en un claro de la taiga, con el túmulo de sus reyes bajo la casa
larga (diseño en docs/unicas/salon_jarl.md).

Dos piezas rígidas: el salón (empalizada, torres, casa larga y talleres; y = 0 es el suelo) y el túmulo, unido por un
jigsaw vertical bajo la casa larga, que rellena toda su caja (roca donde no hay salas) para que el ajuste del terreno
no abra un cráter ni cavidades junto a sus muros. La auditoría propia (auditoria.py) es condición para generar.
"""
from .._comun.piezas import open_stairwells
from .._comun.botin import lang
from .botin import LOOT, LANG as LANG_OBJETOS
from .obra import Obra, K
from . import auditoria

STRUCTURE = dict(biomes=["minecraft:taiga", "minecraft:old_growth_pine_taiga", "minecraft:old_growth_spruce_taiga"],
                 start_pool="unicas/salon_jarl/inicio", size=2, max_distance=80, terrain_adaptation="beard_thin",
                 step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
                 spacing=250, separation=190)
NOMBRE = {"es_es": "Salón del Jarl", "en_us": "Jarl's Hall"}
# Refuerzos del guardián en cada fase (jefes.py): su séquito de insepultos.
REFUERZOS = [{"mob": "zombie", "equipo": {"mainhand": "stone_axe"}}, {"mob": "zombie", "equipo": {"mainhand": "stone_axe"}},
             "stray"]
TROFEO = {"objeto": "iron_axe", "rareza": "rare",
          "nombre": ("Rompeescudos de Ulfgrim", "Ulfgrim's Shieldbreaker"),
          "lore": [("Hendió cien escudos en su última incursión.", "It split a hundred shields on its last raid."),
                   ("El jarl no lo soltó ni muerto.", "The jarl would not let go of it even in death.")],
          "encantamientos": {"minecraft:sharpness": 2, "minecraft:unbreaking": 2}}   # trofeo del guardián (_comun/botin.trofeo)
HISTORIA = {   # su pliego de la Crónica de los Heraldos (docs/STORY.md, _comun/botin.historia_*)
    "cofre": "ofrendas",
    "relato": [
        ("En la taiga encontré un salón tras una empalizada de troncos. El jarl Ulfgrim me sentó junto al"
         " hogar y escuchó mi historia toda la noche. Al alba juró por sus antepasados guardar mi pliego.",
         "In the taiga I found a hall behind a palisade of logs. Jarl Ulfgrim sat me by the hearth and "
         "listened to my tale all night. At dawn he swore by his forefathers to keep my leaf."),
        ("Lo bajamos al túmulo de sus reyes, entre las ofrendas. «Ni la muerte me hará soltarlo», dijo. "
         "Cumplió: dicen que aún ronda la cripta con el hacha en la mano, sin tumba que lo acoja.",
         "We carried it down to the barrow of his kings, among the offerings. “Not even death will make "
         "me let go,” he said. He kept his word: they say he still walks the crypt, axe in hand, with no "
         "grave to take him."),
    ],
    "pista": ("la taiga, donde un jarl insepulto guarda su salón tras una empalizada",
              "the taiga, where an unburied jarl keeps his hall behind a palisade"),
}
LOGRO = {"icono": "minecraft:goat_horn"}   # logros.py
MAPA = {"decoration": "minecraft:red_x"}

TEXTOS = {"guardian": ("Jarl Ulfgrim, el Insepulto", "Jarl Ulfgrim the Unburied")}
LANG = {k: dict(v) for k, v in LANG_OBJETOS.items()}
REPORT = {}


def _lang(obra):
    out = lang(K, TEXTOS)
    for key, lines in obra.signs:
        for i, (es, en) in enumerate(lines):
            out["es_es"][f"{K}cartel.{key}.{i + 1}"] = es
            out["en_us"][f"{K}cartel.{key}.{i + 1}"] = en
    return out


def build(reg):
    obra = Obra().build()
    for k, v in _lang(obra).items():        # writer.py lee LANG después de build()
        LANG[k].update(v)
    sup, tum, errores, rep = auditoria.preparar(obra)
    REPORT.update(rep, obra=obra)
    proc = {"processors": [auditoria.PROCESADOR]}
    open_stairwells(sup)
    open_stairwells(tum)
    reg.add(sup, "unica:salon_jarl")
    reg.add(tum, "unica:salon_jarl")
    reg.pool("unicas/salon_jarl/inicio", [(sup.name, 1, "rigid", proc)])
    reg.pool("unicas/salon_jarl/tumulo", [(tum.name, 1, "rigid", proc)])
    reg.warnings += [f"salon_jarl: {e}" for e in errores]
