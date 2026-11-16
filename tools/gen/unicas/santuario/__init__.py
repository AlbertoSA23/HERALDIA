"""Santuario druídico: un claro del bosque de abedules con un círculo de menhires alrededor de un abedul sagrado
enorme (tronco hueco con escalera hasta una plataforma en la copa), cabañas de los druidas, huerto de hierbas con
colmenas, estanque y observatorio de piedras alineadas; bajo el árbol, raíces y galerías excavadas (diseño en
docs/unicas/santuario.md).

Dos piezas rígidas: el claro (y = 0 es el suelo) y las raíces, unidas por un jigsaw vertical, que rellenan toda su caja
(roca donde no hay salas) para que el ajuste del terreno no abra un cráter ni cavidades junto a sus muros. La
auditoría propia (auditoria.py) es condición para generar.
"""
from .._comun.piezas import open_stairwells
from .._comun.botin import lang
from .botin import LOOT, LANG as LANG_OBJETOS
from .obra import Obra, K
from . import auditoria

STRUCTURE = dict(biomes=["minecraft:birch_forest", "minecraft:old_growth_birch_forest"],
                 start_pool="unicas/santuario/inicio", size=2, max_distance=80, terrain_adaptation="beard_thin",
                 step="surface_structures", start_height={"absolute": 0}, project_to="WORLD_SURFACE_WG",
                 spacing=250, separation=190)
NOMBRE = {"es_es": "Santuario druídico", "en_us": "Druid Sanctuary"}
# Refuerzos del guardián en cada fase (jefes.py): las criaturas del bosque marchito.
REFUERZOS = ["witch", "spider"]
TROFEO = {"objeto": "golden_hoe", "rareza": "rare",
          "nombre": ("Hoz de oro de Cadoc", "Cadoc's Golden Sickle"),
          "lore": [("Segaba el muérdago del árbol sagrado.", "It reaped the mistletoe of the sacred tree."),
                   ("Al final segó también sus raíces.", "In the end it reaped its roots as well.")],
          "encantamientos": {"minecraft:efficiency": 2, "minecraft:unbreaking": 2}}   # trofeo del guardián (_comun/botin.trofeo)
HISTORIA = {   # su pliego de la Crónica de los Heraldos (docs/historia.md, _comun/botin.historia_*)
    "cofre": "biblioteca",
    "relato": [
        ("En el bosque de abedules hallé un claro rodeado de menhires y, en medio, un abedul tan ancho como una"
         " torre. Los druidas me dieron pan y miel, y el archidruida Cadoc escuchó mi historia bajo sus ramas.",
         "In the birch forest I found a glade ringed with standing stones and, in its midst, a birch as wide as a"
         " tower. The druids gave me bread and honey, and Archdruid Cadoc heard my tale beneath its boughs."),
        ("Juró por las raíces del árbol guardar mi pliego y lo puso entre las cortezas escritas de su biblioteca, bajo"
         " tierra. Dicen que, cuando el árbol empezó a secarse, Cadoc pactó con poderes oscuros para salvarlo.",
         "He swore by the roots of the tree to keep my leaf and placed it among the inscribed barks of his library,"
         " underground. They say that when the tree began to wither, Cadoc bargained with dark powers to save it."),
    ],
    "pista": ("el bosque de abedules, donde un árbol sagrado alza su copa sobre un círculo de piedras",
              "the birch forest, where a sacred tree spreads its crown over a circle of stones"),
}
LOGRO = {"icono": "minecraft:birch_sapling"}   # logros.py
MAPA = {"decoration": "minecraft:red_x"}

TEXTOS = {"guardian": ("Archidruida Cadoc, el Marchito", "Archdruid Cadoc the Withered")}
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
    sup, sub, errores, rep = auditoria.preparar(obra)
    REPORT.update(rep, obra=obra)
    proc = {"processors": [auditoria.PROCESADOR]}
    open_stairwells(sup)
    open_stairwells(sub)
    reg.add(sup, "unica:santuario")
    reg.add(sub, "unica:santuario")
    reg.pool("unicas/santuario/inicio", [(sup.name, 1, "rigid", proc)])
    reg.pool("unicas/santuario/raices", [(sub.name, 1, "rigid", proc)])
    reg.warnings += [f"santuario: {e}" for e in errores]
