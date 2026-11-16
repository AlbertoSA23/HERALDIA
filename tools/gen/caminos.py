"""Caminos entre aldeas (aldeas.caminos.*): el rasgo heraldia:camino y los textos de sus carteles.

El trazado y la colocación son Java (caminos/Trazado.java y caminos/CaminoFeature.java): un rasgo que el mod añade a
todos los biomas del mundo principal (Fabric BiomeModifications, paso de decoración STRONGHOLDS) si la opción está
activada. Aquí solo van los datos que el registro necesita: el rasgo (worldgen/feature) y su colocación sin
modificadores (worldgen/placed_feature: una vez por chunk, en su esquina), más los textos de la distancia del cartel.
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
    """Escribe el rasgo y su colocación; devuelve los textos por idioma."""
    jdump(out, f"data/{NS}/worldgen/feature/camino.json", feature())
    jdump(out, f"data/{NS}/worldgen/placed_feature/camino.json", placed_feature())
    return LANG
