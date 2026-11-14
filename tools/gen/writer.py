"""Escribe los recursos de datos del mod (data/heraldia/...) en disco."""
import json, os, shutil
from core import NS, nsid
from themes import THEMES, FAMILIES
from pack import ALL_PROFS
import loot
import unicas
import mapas
import opciones

STD = dict(size=6, maxdist=92)
GRANDE = dict(size=7, maxdist=116)


MAX_DIST = 116   # el juego exige radio + adaptación al terreno (12) <= 128


def sizes(th):
    """Temas con casas más voluminosas (pilotes, tejados de pagoda) necesitan un nivel más de calles."""
    if th["stilts"] >= 3 or th["roof_type"] == "pagoda":
        return dict(size=7, maxdist=100), dict(size=8, maxdist=116)
    if th["roof_type"] == "flat":          # casas compactas: caben más por calle
        return dict(size=5, maxdist=86), dict(size=6, maxdist=104)
    return STD, GRANDE


GUIDE = "@a[tag=heraldia_guia]"
# Textos para el jugador: el cliente con el mod los traduce; un cliente sin él ve el texto de respaldo (es_es).
LANG = {
    "es_es": {
        "heraldia.muestrario.inicio": "Muestrario de aldeas: %s estilos en cuadrícula de %s x %s, separados %s bloques. Tarda unos %s min. Hacia el este: estilos; hacia el sur: familias.",
        "heraldia.muestrario.paso": "%s/%s  %s",
        "heraldia.muestrario.terminado": "Muestrario terminado.",
        "heraldia.muestrario.detenido": "Muestrario detenido.",
        "heraldia.familia.terminada": "Familia terminada.",
    },
    "en_us": {
        "heraldia.muestrario.inicio": "Village showcase: %s styles in a %s x %s grid, %s blocks apart. Takes about %s min. Eastwards: styles; southwards: families.",
        "heraldia.muestrario.paso": "%s/%s  %s",
        "heraldia.muestrario.terminado": "Showcase finished.",
        "heraldia.muestrario.detenido": "Showcase stopped.",
        "heraldia.familia.terminada": "Family finished.",
    },
}
for _lang, _texts in opciones.lang().items():
    LANG[_lang].update(_texts)
assert LANG["es_es"].keys() == LANG["en_us"].keys()


def tell(target, key, *args):
    """tellraw traducible con respaldo en español para clientes sin el mod."""
    comp = {"translate": key, "fallback": LANG["es_es"][key]}
    if args:
        comp["with"] = [str(a) for a in args]
    return f"tellraw {target} {json.dumps(comp, ensure_ascii=False)}"


def jdump(root, rel, obj):
    p = os.path.join(root, rel)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "w", encoding="utf-8") as f:
        json.dump(obj, f, indent=2, ensure_ascii=False)


def element(loc, proj, proc):
    if loc is None:
        return {"element_type": "minecraft:empty_pool_element"}
    return {"element_type": "minecraft:single_pool_element", "location": nsid(loc),
            "processors": proc if proc else {"processors": []}, "projection": proj}


def write(reg, out):
    if os.path.exists(out):
        shutil.rmtree(out)
    os.makedirs(out)
    # plantillas
    for t in reg.templates.values():
        t.save(out)
    # pools
    for pid, p in reg.pools.items():
        ns, path = pid.split(":")
        jdump(out, f"data/{ns}/worldgen/template_pool/{path}.json", {
            "fallback": p["fallback"],
            "elements": [{"weight": w, "element": element(loc, proj, proc)} for (loc, w, proj, proc) in p["elements"]]})
    # procesadores
    for th in THEMES:
        tid = th["id"]
        jdump(out, f"data/{NS}/worldgen/processor_list/{tid}/street.json", {"processors": [{
            "processor_type": "minecraft:rule", "rules": [
                rule(th["path"], "water", th["planks"]),
                rule(th["path2"], "water", th["planks"]),
                rule(th["path"], "lava", th["found"] if "log" not in th["found"] else "cobblestone"),
            ]}]})
        rules = []
        stone_like = {"cobblestone": "mossy_cobblestone", "stone_bricks": "mossy_stone_bricks"}
        if th["family"] in ("bosque", "oscuro", "pantano", "jungla", "llanuras", "nieve", "costa", "taiga"):
            for a, b in stone_like.items():
                rules.append({"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": f"minecraft:{a}", "probability": 0.12},
                              "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": f"minecraft:{b}"})
            rules.append({"input_predicate": {"predicate_type": "minecraft:random_block_match", "block": "minecraft:stone_bricks", "probability": 0.06},
                          "location_predicate": {"predicate_type": "minecraft:always_true"}, "output_state": "minecraft:cracked_stone_bricks"})
        jdump(out, f"data/{NS}/worldgen/processor_list/{tid}/building.json",
              {"processors": [{"processor_type": "minecraft:rule", "rules": rules}] if rules else []})
    # etiquetas de biomas
    for fam, d in FAMILIES.items():
        jdump(out, f"data/{NS}/tags/worldgen/biome/{fam}.json", {"values": [f"minecraft:{b}" for b in d["biomes"]]})
    # estructuras
    set_entries = []
    for th in THEMES:
        tid = th["id"]
        base = {"type": "minecraft:jigsaw", "biomes": f"#{NS}:{th['family']}", "step": "surface_structures",
                "spawn_overrides": {}, "terrain_adaptation": "beard_thin", "start_height": {"absolute": 0},
                "project_start_to_heightmap": "WORLD_SURFACE_WG", "use_expansion_hack": False}
        std, grande = sizes(th)
        jdump(out, f"data/{NS}/worldgen/structure/{tid}.json", dict(base, start_pool=f"{NS}:{tid}/plaza",
                                                                     size=std["size"], max_distance_from_center=std["maxdist"]))
        aliases = [{"type": "minecraft:direct", "alias": f"{NS}:villagers/{th['vtype']}/{p}",
                    "target": f"{NS}:villagers/{th['vtype']}/{p}_grande"} for p in ALL_PROFS]
        jdump(out, f"data/{NS}/worldgen/structure/{tid}_grande.json", dict(base, start_pool=f"{NS}:{tid}/plaza_grande",
                                                                            size=grande["size"], max_distance_from_center=grande["maxdist"],
                                                                            pool_aliases=aliases))
        # mismo peso: la proporción estándar/grande la decide el mod en cada casilla (aldeas.porcentaje_grandes)
        set_entries.append({"structure": f"{NS}:{tid}", "weight": 1})
        set_entries.append({"structure": f"{NS}:{tid}_grande", "weight": 1})
    # heraldia:rejilla = random_spread con separación, máximo y zona de exclusión leídos de config/heraldia.json
    jdump(out, f"data/{NS}/worldgen/structure_set/aldeas.json", {
        "structures": set_entries,
        "placement": {"type": f"{NS}:rejilla", "grupo": "aldeas", "spacing": opciones.VILLAGE_SPACING,
                      "separation": opciones.VILLAGE_SEPARATION, "salt": opciones.VILLAGE_SALT,
                      "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": opciones.VANILLA_EXCLUSION_CHUNKS}}})
    jdump(out, f"data/{NS}/tags/worldgen/structure/aldeas.json", {"values": [e["structure"] for e in set_entries]})
    jdump(out, f"{NS}/opciones.json", opciones.schema())
    # estructuras únicas
    for sid, mod in unicas.modules():
        write_unique(out, sid, mod.STRUCTURE)
    # botín
    uniques = unicas.modules()
    for name, table in loot.TABLES.items():
        if name == "epico":
            table = mapas.with_maps(table, uniques)
        jdump(out, f"data/{NS}/loot_table/cofres/{name}.json", lootr_aware(table))
    mapas.write(out, uniques, jdump)
    for sid, mod in unicas.modules():
        for name, table in getattr(mod, "LOOT", {}).items():
            jdump(out, f"data/{NS}/loot_table/unicas/{sid}/{name}.json", lootr_aware(table))
    # funciones
    fdir = os.path.join(out, "data", NS, "function")
    os.makedirs(fdir, exist_ok=True)
    files = {
        "load.mcfunction": [
            "# Aldeas enormes: inicialización",
            "scoreboard objectives add heraldia_g dummy",
            "schedule function heraldia:golems 600t replace"],
        # heraldia_cfg lo rellena el mod al arrancar desde config/heraldia.json (#limpieza 0/1, #limite_estandar, #limite_grande)
        "golems.mcfunction": [
            "# Cada 30 s revisa las aldeas cargadas y limita los gólems naturales (+25 % sobre la dotación inicial)",
            "execute if score #limpieza heraldia_cfg matches 1 as @e[type=minecraft:armor_stand,tag=heraldia_centro] at @s run function heraldia:golem_check",
            "schedule function heraldia:golems 600t replace"],
        "golem_check.mcfunction": [
            "execute store result score @s heraldia_g if entity @e[type=minecraft:iron_golem,distance=..112,nbt={PlayerCreated:0b}]",
            "execute if entity @s[tag=heraldia_std] if score @s heraldia_g >= #limite_estandar heraldia_cfg as @e[type=minecraft:iron_golem,distance=..112,nbt={PlayerCreated:0b},sort=random,limit=1] at @s run tp @s ~ -200 ~",
            "execute if entity @s[tag=heraldia_grande] if score @s heraldia_g >= #limite_grande heraldia_cfg as @e[type=minecraft:iron_golem,distance=..112,nbt={PlayerCreated:0b},sort=random,limit=1] at @s run tp @s ~ -200 ~"],
    }
    # --- muestrario: coloca los 72 estilos en una cuadrícula, uno cada 8 s, guiando al jugador
    STEP, WAIT = 300, 160
    order = []
    fams = list(dict.fromkeys(th["family"] for th in THEMES))
    for fam in fams:
        row = [th["id"] for th in THEMES if th["family"] == fam]
        order.append(row + [r + "_grande" for r in row])
    flat = [(r, c, sid) for r, row in enumerate(order) for c, sid in enumerate(row)]
    files["muestrario.mcfunction"] = [
        "# Uso: /function heraldia:muestrario  (en un mundo de prueba; parar con /function heraldia:muestrario/parar)",
        "tag @a remove heraldia_guia",
        "tag @s add heraldia_guia",
        "gamemode spectator @s",
        tell("@s", "heraldia.muestrario.inicio", len(flat), len(order[0]), len(order), STEP, len(flat) * WAIT // 20 // 60 + 1),
        "function heraldia:muestrario/p01",
    ]
    for i, (r, c, sid) in enumerate(flat):
        lines = [f"execute as @a[tag=heraldia_guia,limit=1] at @s run place structure heraldia:{sid} ~ ~ ~",
                 tell(GUIDE, "heraldia.muestrario.paso", i + 1, len(flat), f"{NS}:{sid}")]
        if i + 1 < len(flat):
            nr, nc, _ = flat[i + 1]
            dx = (nc - c) * STEP
            dz = (nr - r) * STEP
            lines.append(f"execute as @a[tag=heraldia_guia,limit=1] at @s run tp @s ~{dx} 200 ~{dz}")
            lines.append(f"schedule function heraldia:muestrario/p{i + 2:02d} {WAIT}t replace")
        else:
            lines += ["gamemode creative @a[tag=heraldia_guia]",
                      tell(GUIDE, "heraldia.muestrario.terminado"),
                      "tag @a remove heraldia_guia"]
        files[f"muestrario/p{i + 1:02d}.mcfunction"] = lines
    files["muestrario/parar.mcfunction"] = (
        [f"schedule clear heraldia:muestrario/p{i + 1:02d}" for i in range(len(flat))] +
        ["gamemode creative @a[tag=heraldia_guia]", tell(GUIDE, "heraldia.muestrario.detenido"), "tag @a remove heraldia_guia"])
    # una familia suelta (6 aldeas en fila): /function heraldia:familia/<nombre>
    for fam, row in zip(fams, order):
        files[f"familia/{fam}.mcfunction"] = (
            ["tag @a remove heraldia_guia", "tag @s add heraldia_guia", "gamemode spectator @s"] +
            [f"function heraldia:familia/{fam}_{k}" if k == 0 else "" for k in range(1)])
        for k, sid in enumerate(row):
            ls = [f"execute as @a[tag=heraldia_guia,limit=1] at @s run place structure heraldia:{sid} ~ ~ ~",
                  tell(GUIDE, "heraldia.muestrario.paso", k + 1, len(row), f"{NS}:{sid}")]
            if k + 1 < len(row):
                ls += [f"execute as @a[tag=heraldia_guia,limit=1] at @s run tp @s ~{STEP} 200 ~",
                       f"schedule function heraldia:familia/{fam}_{k + 1} {WAIT}t replace"]
            else:
                ls += ["gamemode creative @a[tag=heraldia_guia]", tell(GUIDE, "heraldia.familia.terminada"),
                       "tag @a remove heraldia_guia"]
            files[f"familia/{fam}_{k}.mcfunction"] = ls
    for fn, lines in files.items():
        os.makedirs(os.path.dirname(os.path.join(fdir, fn)), exist_ok=True)
        lines = [l for l in lines if l]
        with open(os.path.join(fdir, fn), "w", encoding="utf-8") as f:
            f.write("\n".join(lines) + "\n")
    jdump(out, "data/minecraft/tags/function/load.json", {"values": [f"{NS}:load"]})
    maps_lang = mapas.lang(uniques)
    for sid, mod in unicas.modules():
        extra = getattr(mod, "LANG", {})
        assert extra.get("es_es", {}).keys() == extra.get("en_us", {}).keys(), sid
        for lang, texts in extra.items():
            LANG[lang].update(texts)
    for lang, texts in LANG.items():
        for _, mod in unicas.modules():             # textos propios de cada estructura única
            texts = {**texts, **getattr(mod, "LANG", {}).get(lang, {})}
        jdump(out, f"assets/{NS}/lang/{lang}.json", dict(texts, **maps_lang[lang]))


def write_unique(out, sid, st):
    """JSON de una estructura única, su rejilla de colocación y su etiqueta (para mapas del tesoro)."""
    sid_full = f"{NS}:unicas/{sid}"
    structure = st.get("json") or {
        "type": "minecraft:jigsaw", "biomes": st["biomes"], "step": st.get("step", "surface_structures"),
        "spawn_overrides": st.get("spawn_overrides", {}), "terrain_adaptation": st.get("terrain_adaptation", "beard_thin"),
        "start_pool": nsid(st["start_pool"]), "size": st["size"], "max_distance_from_center": st["max_distance"],
        "start_height": st.get("start_height", {"absolute": 0}), "use_expansion_hack": False}
    if not st.get("json") and st.get("project_to", "WORLD_SURFACE_WG"):
        structure["project_start_to_heightmap"] = st.get("project_to", "WORLD_SURFACE_WG")
    jdump(out, f"data/{NS}/worldgen/structure/unicas/{sid}.json", structure)
    jdump(out, f"data/{NS}/worldgen/structure_set/unicas/{sid}.json", {
        "structures": [{"structure": sid_full, "weight": 1}],
        # colocación propia de la estructura (p. ej. la Atlántida, siempre una) o rejilla configurable heraldia:rejilla
        "placement": st.get("placement") or {
            "type": f"{NS}:rejilla", "grupo": f"unicas/{sid}", "spacing": st.get("spacing", unicas.DEFAULT_SPACING),
            "separation": st.get("separation", unicas.DEFAULT_SEPARATION), "salt": unicas.salt(sid)}})
    jdump(out, f"data/{NS}/tags/worldgen/structure/unicas/{sid}.json", {"values": [sid_full]})


def lootr_aware(table):
    """Convierte la marca "solo_sin_lootr" de cada grupo en la condición heraldia:sin_lootr."""
    pools = []
    for p in table["pools"]:
        p = dict(p)
        if p.pop("solo_sin_lootr", False):
            # 26.3: un grupo lleva una sola "condition" con "type" (varias, con all_of).
            cond = {"type": f"{NS}:sin_lootr"}
            p["condition"] = {"type": "minecraft:all_of", "terms": [p["condition"], cond]} if "condition" in p else cond
        pools.append(p)
    return dict(table, pools=pools)


def rule(inp, loc, outb):
    return {"input_predicate": {"predicate_type": "minecraft:block_match", "block": "minecraft:" + inp.split("[")[0].replace("minecraft:", "")},
            "location_predicate": {"predicate_type": "minecraft:block_match", "block": "minecraft:" + loc},
            "output_state": "minecraft:" + outb.split("[")[0].replace("minecraft:", "")}
