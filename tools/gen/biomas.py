"""Etiquetas de biomas de Heraldia: biomas vanilla de cada familia de aldeas y de cada única, más etiquetas
convencionales (#c:..., de Fabric API / NeoForge) y #minecraft:is_* para que también salgan en biomas de otros mods.

Regla: una etiqueta extra solo entra si, en vanilla (26.3 con Fabric API 0.166.2+26.3), resuelve a un subconjunto de
la lista vanilla. Así el conjunto en vanilla queda idéntico al de la lista y los mods (Terralith, Biomes O' Plenty...)
que añaden sus biomas a esas etiquetas reciben la estructura. Todas las entradas de etiqueta van con
"required": false: si un mod o Fabric API no la define, el paquete carga igual. `comprobar` lo verifica al generar.

Sin etiqueta extra (no hay ninguna lo bastante estrecha; queda solo la lista vanilla):
  taiga, sabana, cerezos y las únicas coliseo, observatorio, piramide, monasterio, ciudadela y palacio:
  #c:is_taiga (= #minecraft:is_taiga) incluye snowy_taiga (familia nieve); #c:is_savanna incluye windswept_savanna
  (observatorio); #c:is_windswept, windswept_forest; #c:is_jungle, bamboo_jungle (palacio); #c:is_mountain/slope,
  snowy_slopes y cherry_grove; #c:is_mountain/peak, frozen_peaks; #c:is_forest, dark_forest, pale_garden y grove
  (torre de mago, nieve); #c:is_beach, snowy_beach (faro). Las #c:primary_wood_type/* hablan de la madera, no del clima.
"""
import json, os

NS = "heraldia"
HERE = os.path.dirname(os.path.abspath(__file__))

# nombre de la etiqueta heraldia:<nombre> -> etiquetas extra (sin "#"); familias de aldeas y unicas/<id>
CONVENCIONALES = {
    "llanuras": ["c:is_plains"],
    "bosque": ["c:is_birch_forest", "c:is_flower_forest"],
    "oscuro": ["c:is_dark_forest"],
    "nieve": ["c:is_snowy_plains"],
    "desierto": ["c:is_desert"],
    "jungla": ["minecraft:is_jungle", "c:is_jungle"],
    "pantano": ["c:is_swamp"],
    "badlands": ["minecraft:is_badlands", "c:is_badlands"],
    "costa": ["minecraft:is_beach", "c:is_beach", "c:is_stony_shores"],
    "unicas/castillo": ["c:is_plains"],
    "unicas/fortaleza_hielo": ["c:is_snowy_plains"],
    "unicas/catedral": ["c:is_flower_forest"],
    "unicas/faro": ["c:is_stony_shores"],
    "unicas/acueducto": ["c:is_desert"],
    "unicas/galeon": ["minecraft:is_beach", "c:is_beach"],
    "unicas/atlantida": ["minecraft:is_ocean", "c:is_ocean"],
}

_ESCRITAS = {}      # heraldia:<nombre> -> lista vanilla, para comprobar


def etiqueta(out, nombre, vanilla):
    """Escribe data/heraldia/tags/worldgen/biome/<nombre>.json y devuelve "#heraldia:<nombre>".
    vanilla: ids de bioma ("plains" o "minecraft:plains")."""
    ids = [b if ":" in b else f"minecraft:{b}" for b in vanilla]
    values = ids + [{"id": f"#{t}", "required": False} for t in CONVENCIONALES.get(nombre, [])]
    path = os.path.join(out, "data", NS, "tags", "worldgen", "biome", f"{nombre}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"values": values}, f, indent=2, ensure_ascii=False)
    _ESCRITAS[f"{NS}:{nombre}"] = ids
    return f"#{NS}:{nombre}"


def de_unica(out, sid, biomes):
    """biomes de una única: una lista vanilla pasa a la etiqueta heraldia:unicas/<id>; una etiqueta se deja igual."""
    return etiqueta(out, f"unicas/{sid}", biomes) if isinstance(biomes, list) else biomes


def convencionales():
    with open(os.path.join(HERE, "etiquetas_c.json"), encoding="utf-8") as f:
        return json.load(f)["etiquetas"]


def comprobar(out, summary_dir):
    """Resuelve contra los registros de 26.3 (etiquetas vanilla de mcmeta y #c: de Fabric API) todas las etiquetas
    de biomas de heraldia y los "biomes" de cada estructura. Errores si una etiqueta extra mete en vanilla un bioma
    que no está en la lista, si falta algún id o etiqueta, o si una estructura no lista sus biomas con una etiqueta
    de Heraldia."""
    with open(os.path.join(summary_dir, "data", "tag", "worldgen", "biome", "data.json"), encoding="utf-8") as f:
        vanilla_tags = {f"minecraft:{k}": v["values"] for k, v in json.load(f).items()}
    with open(os.path.join(summary_dir, "registries", "data.json"), encoding="utf-8") as f:
        biomes = {f"minecraft:{b}" for b in json.load(f)["worldgen/biome"]}
    tags = dict(vanilla_tags, **{f"c:{k}": v for k, v in convencionales().items()})
    tdir = os.path.join(out, "data", NS, "tags", "worldgen", "biome")
    for root, _, files in os.walk(tdir):
        for fn in files:
            name = os.path.relpath(os.path.join(root, fn), tdir).replace(os.sep, "/")[:-5]
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                tags[f"{NS}:{name}"] = json.load(f)["values"]
    errs = []

    def resolve(tag, stack=()):
        if tag in stack:
            errs.append(f"etiqueta circular {tag}")
            return set()
        found = set()
        for v in tags[tag]:
            i, req = (v["id"], v.get("required", True)) if isinstance(v, dict) else (v, True)
            if i.startswith("#"):
                if i[1:] in tags:
                    found |= resolve(i[1:], stack + (tag,))
                elif req or not tag.startswith("c:"):    # las de Fabric pueden citar etiquetas opcionales ajenas
                    errs.append(f"{tag}: {i} no existe en 26.3 ni en Fabric API 0.166.2+26.3 (etiquetas_c.json)")
            elif i in biomes:
                found.add(i)
            elif req:
                errs.append(f"{tag}: bioma inexistente {i}")
        return found

    for name, ids in sorted(_ESCRITAS.items()):
        got = resolve(name)
        if got != set(ids):
            errs.append(f"#{name} en vanilla: {sorted(got)} != lista {sorted(ids)}")
        for v in tags[name]:
            if isinstance(v, dict) and v.get("required", True):
                errs.append(f"#{name}: {v['id']} debe llevar required: false")
    sdir = os.path.join(out, "data", NS, "worldgen", "structure")
    for root, _, files in os.walk(sdir):
        for fn in files:
            with open(os.path.join(root, fn), encoding="utf-8") as f:
                b = json.load(f)["biomes"]
            if not (isinstance(b, str) and b[1:] in _ESCRITAS):
                errs.append(f"{os.path.relpath(os.path.join(root, fn), sdir)}: biomes {b!r} no es una etiqueta de Heraldia")
            elif not resolve(b[1:]):
                errs.append(f"{fn}: ningún bioma en vanilla")
    return errs


def regenerar(jar, version):
    """Rehace etiquetas_c.json desde el jar de fabric-convention-tags-v2 (o el de Fabric API completo que lo contenga):
    python3 tools/gen/biomas.py <jar> "<versión de Fabric API>"."""
    import io, zipfile
    prefix, found = "data/c/tags/worldgen/biome/", {}

    def scan(z):
        for n in z.namelist():
            if n.startswith(prefix) and n.endswith(".json"):
                found[n[len(prefix):-5]] = json.loads(z.read(n))["values"]
            elif n.startswith("META-INF/jars/") and "convention-tags" in n:
                scan(zipfile.ZipFile(io.BytesIO(z.read(n))))
    scan(zipfile.ZipFile(jar))
    with open(os.path.join(HERE, "etiquetas_c.json"), "w", encoding="utf-8") as f:
        json.dump({"_fuente": f"data/c/tags/worldgen/biome/*.json de Fabric API {version}; "
                              "src/test/.../BiomasTest.java comprueba que coincide con el jar",
                   "etiquetas": dict(sorted(found.items()))}, f, indent=1, ensure_ascii=False)
    return len(found)


if __name__ == "__main__":
    import sys
    print(regenerar(sys.argv[1], sys.argv[2]), "etiquetas")
