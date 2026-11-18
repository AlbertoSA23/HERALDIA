"""Heraldia biome tags: vanilla biomes of each village family and each unique structure, plus conventional tags
(#c:..., from Fabric API / NeoForge) and #minecraft:is_* so that they also appear in biomes from other mods.

Rule: an extra tag is only included if, in vanilla (26.3 with Fabric API 0.166.2+26.3), it resolves to a subset of
the vanilla list. That way the set in vanilla is identical to the list and the mods (Terralith, Biomes O' Plenty...)
that add their biomes to those tags receive the structure. All tag entries carry
"required": false: if a mod or Fabric API does not define it, the pack loads anyway. `check` verifies this when generating.

Without an extra tag (none is narrow enough; only the vanilla list remains):
  taiga, sabana, cerezos and the unique structures coliseo, observatorio, piramide, monasterio, ciudadela, palacio, salon_jarl and
  isla_corsario (ocean, temperate and warm; #c:is_shallow_ocean includes the cold and frozen ones):
  #c:is_taiga (= #minecraft:is_taiga) includes snowy_taiga (snow family); #c:is_savanna includes windswept_savanna
  (observatorio); #c:is_windswept, windswept_forest; #c:is_jungle, bamboo_jungle (palacio); #c:is_mountain/slope,
  snowy_slopes and cherry_grove; #c:is_mountain/peak, frozen_peaks; #c:is_forest, dark_forest, pale_garden and grove
  (torre de mago, nieve); #c:is_beach, snowy_beach (faro). The #c:primary_wood_type/* are about the wood, not the climate.
"""
import json, os

NS = "heraldia"
HERE = os.path.dirname(os.path.abspath(__file__))

# name of the heraldia:<name> tag -> extra tags (without "#"); village families and unicas/<id>
CONVENTIONAL = {
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
    "unicas/santuario": ["c:is_birch_forest"],
    "unicas/laboratorio_micelio": ["c:is_mushroom"],
    "unicas/faro": ["c:is_stony_shores"],
    "unicas/acueducto": ["c:is_desert"],
    "unicas/galeon": ["minecraft:is_beach", "c:is_beach"],
    "unicas/atlantida": ["minecraft:is_ocean", "c:is_ocean"],
}

_WRITTEN = {}      # heraldia:<name> -> vanilla list, for checking


def tag(out, name, vanilla):
    """Writes data/heraldia/tags/worldgen/biome/<nombre>.json and returns "#heraldia:<nombre>".
    vanilla: biome ids ("plains" or "minecraft:plains")."""
    ids = [b if ":" in b else f"minecraft:{b}" for b in vanilla]
    values = ids + [{"id": f"#{t}", "required": False} for t in CONVENTIONAL.get(name, [])]
    path = os.path.join(out, "data", NS, "tags", "worldgen", "biome", f"{name}.json")
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump({"values": values}, f, indent=2, ensure_ascii=False)
    _WRITTEN[f"{NS}:{name}"] = ids
    return f"#{NS}:{name}"


def for_unique(out, sid, biomes):
    """biomes of a unique structure: a vanilla list becomes the tag heraldia:unicas/<id>; a tag is left as is."""
    return tag(out, f"unicas/{sid}", biomes) if isinstance(biomes, list) else biomes


def conventional():
    with open(os.path.join(HERE, "c_tags.json"), encoding="utf-8") as f:
        return json.load(f)["etiquetas"]


def check(out, summary_dir):
    """Resolves against the 26.3 registries (vanilla tags from mcmeta and #c: from Fabric API) all the Heraldia biome
    tags and the "biomes" of each structure. Errors if an extra tag puts into vanilla a biome
    that is not in the list, if any id or tag is missing, or if a structure does not list its biomes with a
    Heraldia tag."""
    with open(os.path.join(summary_dir, "data", "tag", "worldgen", "biome", "data.json"), encoding="utf-8") as f:
        vanilla_tags = {f"minecraft:{k}": v["values"] for k, v in json.load(f).items()}
    with open(os.path.join(summary_dir, "registries", "data.json"), encoding="utf-8") as f:
        biomes = {f"minecraft:{b}" for b in json.load(f)["worldgen/biome"]}
    tags = dict(vanilla_tags, **{f"c:{k}": v for k, v in conventional().items()})
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
                elif req or not tag.startswith("c:"):    # the Fabric ones may cite optional tags from other mods
                    errs.append(f"{tag}: {i} no existe en 26.3 ni en Fabric API 0.166.2+26.3 (etiquetas_c.json)")
            elif i in biomes:
                found.add(i)
            elif req:
                errs.append(f"{tag}: bioma inexistente {i}")
        return found

    for name, ids in sorted(_WRITTEN.items()):
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
            if not (isinstance(b, str) and b[1:] in _WRITTEN):
                errs.append(f"{os.path.relpath(os.path.join(root, fn), sdir)}: biomes {b!r} is not a Heraldia tag")
            elif not resolve(b[1:]):
                errs.append(f"{fn}: no biome in vanilla")
    return errs


def regenerate(jar, version):
    """Regenerates etiquetas_c.json from the fabric-convention-tags-v2 jar (or the full Fabric API jar that contains it):
    python3 tools/gen/biomes.py <jar> "<Fabric API version>"."""
    import io, zipfile
    prefix, found = "data/c/tags/worldgen/biome/", {}

    def scan(z):
        for n in z.namelist():
            if n.startswith(prefix) and n.endswith(".json"):
                found[n[len(prefix):-5]] = json.loads(z.read(n))["values"]
            elif n.startswith("META-INF/jars/") and "convention-tags" in n:
                scan(zipfile.ZipFile(io.BytesIO(z.read(n))))
    scan(zipfile.ZipFile(jar))
    with open(os.path.join(HERE, "c_tags.json"), "w", encoding="utf-8") as f:
        json.dump({"_fuente": f"data/c/tags/worldgen/biome/*.json de Fabric API {version}; "
                              "src/test/.../BiomasTest.java comprueba que coincide con el jar",
                   "etiquetas": dict(sorted(found.items()))}, f, indent=1, ensure_ascii=False)
    return len(found)


if __name__ == "__main__":
    import sys
    print(regenerate(sys.argv[1], sys.argv[2]), "etiquetas")
