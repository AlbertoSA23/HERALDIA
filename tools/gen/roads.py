"""Roads between villages (aldeas.caminos.*): the heraldia:camino feature and the texts of its signs.

The layout and placement are Java (caminos/Trazado.java and caminos/CaminoFeature.java): a feature that the mod adds to
all the biomes of the overworld (Fabric BiomeModifications, decoration step STRONGHOLDS) if the option is
enabled. Only the data that the registry needs goes here: the feature (worldgen/feature) and its placement without
modifiers (worldgen/placed_feature: once per chunk, at its corner), plus the texts of the sign's distance.
"""
from core import NS

FEATURE = f"{NS}:camino"

LANG = {
    "es_es": {
        "heraldia.camino.cartel.derecha": "%s bloques →",
        "heraldia.camino.cartel.izquierda": "← %s bloques",
    },
    "en_us": {
        "heraldia.camino.cartel.derecha": "%s blocks →",
        "heraldia.camino.cartel.izquierda": "← %s blocks",
    },
}


def feature():
    return {"type": FEATURE}


def placed_feature():
    return {"feature": FEATURE, "placement": []}


def write(out, jdump):
    """Writes the feature and its placement; returns the texts per language."""
    jdump(out, f"data/{NS}/worldgen/feature/camino.json", feature())
    jdump(out, f"data/{NS}/worldgen/placed_feature/camino.json", placed_feature())
    return LANG
