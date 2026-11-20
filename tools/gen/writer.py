"""Writes the mod's data resources (data/heraldia/...) to disk."""
import json, os, shutil
from core import NS, nsid
from themes import THEMES, FAMILIES
from pack import ALL_PROFS
import loot
import uniques
import dimensions
import mediums
import mines
import shore as coast
import maps
import trades
import board
import guide
import chronicle_ending
import arena_waves
import admin
import updates
import light_profile
import quests
import caravans
import village_events
import dialogue
import wizard_huts
import roads
import options
import bosses
import biomes
import advancements
import languages
import treasure
import parallel
import herald_house
import filler_loot
import spawn_roads
from uniques._common import chest_loot

STD = dict(size=6, maxdist=92)
LARGE = dict(size=7, maxdist=116)


MAX_DIST = 116   # the game requires radius + terrain adaptation (12) <= 128


def sizes(th):
    """Themes with bulkier houses (stilts, pagoda roofs) need one more street level."""
    if th["stilts"] >= 3 or th["roof_type"] == "pagoda":
        return dict(size=7, maxdist=100), dict(size=8, maxdist=116)
    if th["roof_type"] == "flat":          # compact houses: more fit per street
        return dict(size=5, maxdist=86), dict(size=6, maxdist=104)
    return STD, LARGE


GUIDE = "@a[tag=heraldia_guia]"
# Texts for the player: a client with the mod translates them; a client without it sees the fallback text (es_es).
LANG = {
    "es_es": {
        "heraldia.muestrario.inicio": "Muestrario de aldeas: %s estilos en cuadrícula de %s x %s, separados %s bloques. Tarda unos %s min. Hacia el este: estilos; hacia el sur: familias.",
        "heraldia.muestrario.paso": "%s/%s  %s",
        "heraldia.muestrario.terminado": "Muestrario terminado.",
        "heraldia.muestrario.detenido": "Muestrario detenido.",
        "heraldia.familia.terminada": "Familia terminada.",
        # /heraldia key (the Java fallback texts are these same ones)
        "heraldia.llave.dada": "Entregadas %s llaves (%s) a %s jugadores",
        "heraldia.llave.desconocida": "No hay ninguna llave «%s». Opciones: %s",
        # /heraldia info (the Java takes the fallback text from this es_es)
        "heraldia.info.titulo": "Heraldia: configuración en uso",
        "heraldia.info.aldeas": "Aldeas: cada %s bloques, máximo %s, %s %% grandes, %s de %s estilos activados, a %s bloques de las vanilla",
        "heraldia.info.unicas": "Estructuras únicas activadas: %s de %s",
        "heraldia.info.unica": " - %s: cada %s bloques",
        "heraldia.info.unica.desactivada": " - %s: desactivada",
        "heraldia.info.unica.mundial": " - %s: una por mundo",
        "heraldia.info.distancia": "Distancia mínima entre únicas: %s, %s bloques",
        "heraldia.info.rejilla": "Rejilla antigua de las únicas (mundo de una versión anterior): %s",
        "heraldia.info.cofre": "Cofre premium de la Atlántida por jugador: %s; Lootr: %s",
        "heraldia.info.registradas": "Estructuras registradas: %s (%s de aldeas, %s únicas, %s medianas y %s entradas a mina)",
        "heraldia.info.minas": "Entradas a mina: %s, cada %s bloques (las pequeñas; las medianas y las grandes, en proporción); minas abandonadas vanilla: x%s en los chunks nuevos",
        "heraldia.info.medianas": "Estructuras medianas: %s; %s de %s tipos activados, frecuencia %s %%, a %s bloques de aldeas y únicas y a %s entre ellas",
        "heraldia.info.mediana": " - %s: cada %s bloques",
        "heraldia.info.si": "sí",
        "heraldia.info.no": "no",
        "heraldia.info.activada": "activada",
        "heraldia.info.desactivada": "desactivada",
        "heraldia.info.cargado": "instalado",
        "heraldia.info.no_cargado": "no instalado",
        "heraldia.info.cerca.titulo": "Estructuras Heraldia a menos de %s bloques de %s, %s (búsqueda de %s ms):",
        "heraldia.info.cerca.linea": " - %s (%s): %s bloques al %s %s, %s",
        "heraldia.info.cerca.nada": "No hay estructuras Heraldia a menos de %s bloques de %s, %s (búsqueda de %s ms).",
        "heraldia.info.generada": "generada",
        "heraldia.info.prevista": "prevista (sin generar)",
        "heraldia.info.dir.n": "norte",
        "heraldia.info.dir.ne": "noreste",
        "heraldia.info.dir.e": "este",
        "heraldia.info.dir.se": "sureste",
        "heraldia.info.dir.s": "sur",
        "heraldia.info.dir.so": "suroeste",
        "heraldia.info.dir.o": "oeste",
        "heraldia.info.dir.no": "noroeste",
        "heraldia.info.aldea": "Aldea Heraldia de %s",
        "heraldia.info.aqui.linea": "Estás en %s (%s)",
        "heraldia.info.aqui.nada": "Aquí no hay ninguna estructura Heraldia.",
        "heraldia.info.aqui.sin_cargar": "Esa posición no está cargada (para responder no se carga ni se genera nada).",
        "heraldia.info.guardian.vivo": "   Guardián: vivo, en %s, %s, %s",
        "heraldia.info.guardian.derrotado": "   Guardián: derrotado",
        "heraldia.info.guardian.desconocido": "   Guardián: no se sabe (parte de la estructura no está cargada)",
    },
    "en_us": {
        "heraldia.muestrario.inicio": "Village showcase: %s styles in a %s x %s grid, %s blocks apart. Takes about %s min. Eastwards: styles; southwards: families.",
        "heraldia.muestrario.paso": "%s/%s  %s",
        "heraldia.muestrario.terminado": "Showcase finished.",
        "heraldia.muestrario.detenido": "Showcase stopped.",
        "heraldia.familia.terminada": "Family finished.",
        "heraldia.llave.dada": "Gave %s keys (%s) to %s players",
        "heraldia.llave.desconocida": "There is no key «%s». Options: %s",
        "heraldia.info.titulo": "Heraldia: active configuration",
        "heraldia.info.aldeas": "Villages: every %s blocks, at most %s, %s %% large, %s of %s styles enabled, %s blocks from vanilla ones",
        "heraldia.info.unicas": "Unique structures enabled: %s of %s",
        "heraldia.info.unica": " - %s: every %s blocks",
        "heraldia.info.unica.desactivada": " - %s: disabled",
        "heraldia.info.unica.mundial": " - %s: one per world",
        "heraldia.info.distancia": "Minimum distance between unique structures: %s, %s blocks",
        "heraldia.info.rejilla": "Old unique-structure grid (world from an earlier version): %s",
        "heraldia.info.cofre": "Per-player Atlantis premium chest: %s; Lootr: %s",
        "heraldia.info.registradas": "Registered structures: %s (%s villages, %s unique, %s medium and %s mine entrances)",
        "heraldia.info.minas": "Mine entrances: %s, every %s blocks (small ones; medium and large ones in proportion); vanilla abandoned mineshafts: x%s in new chunks",
        "heraldia.info.medianas": "Medium structures: %s; %s of %s types enabled, frequency %s %%, %s blocks from villages and unique ones and %s from each other",
        "heraldia.info.mediana": " - %s: every %s blocks",
        "heraldia.info.si": "yes",
        "heraldia.info.no": "no",
        "heraldia.info.activada": "enabled",
        "heraldia.info.desactivada": "disabled",
        "heraldia.info.cargado": "installed",
        "heraldia.info.no_cargado": "not installed",
        "heraldia.info.cerca.titulo": "Heraldia structures within %s blocks of %s, %s (search took %s ms):",
        "heraldia.info.cerca.linea": " - %s (%s): %s blocks %s %s, %s",
        "heraldia.info.cerca.nada": "No Heraldia structures within %s blocks of %s, %s (search took %s ms).",
        "heraldia.info.generada": "generated",
        "heraldia.info.prevista": "predicted (not generated yet)",
        "heraldia.info.dir.n": "north",
        "heraldia.info.dir.ne": "northeast",
        "heraldia.info.dir.e": "east",
        "heraldia.info.dir.se": "southeast",
        "heraldia.info.dir.s": "south",
        "heraldia.info.dir.so": "southwest",
        "heraldia.info.dir.o": "west",
        "heraldia.info.dir.no": "northwest",
        "heraldia.info.aldea": "Heraldia %s village",
        "heraldia.info.aqui.linea": "You are in %s (%s)",
        "heraldia.info.aqui.nada": "There is no Heraldia structure here.",
        "heraldia.info.aqui.sin_cargar": "That position is not loaded (nothing is loaded or generated to answer).",
        "heraldia.info.guardian.vivo": "   Guardian: alive, at %s, %s, %s",
        "heraldia.info.guardian.derrotado": "   Guardian: defeated",
        "heraldia.info.guardian.desconocido": "   Guardian: unknown (part of the structure is unloaded)",
    },
}
for _lang, _texts in options.lang().items():
    LANG[_lang].update(_texts)
for _lang, _texts in bosses.lang().items():
    LANG[_lang].update(_texts)
assert LANG["es_es"].keys() == LANG["en_us"].keys()


def tell(target, key, *args):
    """Translatable tellraw with a Spanish fallback for clients without the mod."""
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
    # templates (in parallel: each in its own file, the result does not depend on the order)
    parallel.map_obj(lambda t: t.save(out), reg.templates.values(), chunksize=16)
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
        procs = [{"processor_type": "minecraft:rule", "rules": rules}] if rules else []
        jdump(out, f"data/{NS}/worldgen/processor_list/{tid}/building.json", {"processors": procs + [foundations(th)]})
        if th["family"] == "costa":
            jdump(out, f"data/{NS}/worldgen/processor_list/{tid}/pier.json", {"processors": [
                down_to_floor([log_block(th["pier"]["log"])], PILES_MAX)]})
    # etiquetas de biomas
    for fam, d in FAMILIES.items():
        biomes.tag(out, fam, d["biomes"])
    # estructuras
    set_entries = []
    for th in THEMES:
        tid = th["id"]
        base = {"type": "minecraft:jigsaw", "biomes": f"#{NS}:{th['family']}", "step": "surface_structures",
                "spawn_overrides": {}, "terrain_adaptation": "beard_thin", "start_height": {"absolute": 0},
                "project_start_to_heightmap": "WORLD_SURFACE_WG", "use_expansion_hack": False}
        std, large = sizes(th)
        aliases = [{"type": "minecraft:direct", "alias": f"{NS}:villagers/{th['vtype']}/{p}",
                    "target": f"{NS}:villagers/{th['vtype']}/{p}_grande"} for p in ALL_PROFS]
        for suffix, pool, sz, al in (("", "plaza", std, []), ("_grande", "plaza_grande", large, aliases)):
            jig = dict(base, start_pool=f"{NS}:{tid}/{pool}", size=sz["size"], max_distance_from_center=sz["maxdist"])
            if al:
                jig["pool_aliases"] = al
            jig = village_with_port(reg, th, jig) if th["family"] == "costa" else village(jig)
            jdump(out, f"data/{NS}/worldgen/structure/{tid}{suffix}.json", jig)
        # same weight: the standard/large ratio is decided by the mod in each cell (aldeas.porcentaje_grandes)
        set_entries.append({"structure": f"{NS}:{tid}", "weight": 1})
        set_entries.append({"structure": f"{NS}:{tid}_grande", "weight": 1})
    # heraldia:rejilla = random_spread with spacing, maximum and exclusion zone read from config/heraldia.json
    jdump(out, f"data/{NS}/worldgen/structure_set/aldeas.json", {
        "structures": set_entries,
        "placement": {"type": f"{NS}:rejilla", "grupo": "aldeas", "spacing": options.VILLAGE_SPACING,
                      "separation": options.VILLAGE_SEPARATION, "salt": options.VILLAGE_SALT,
                      "exclusion_zone": {"other_set": "minecraft:villages", "chunk_count": options.VANILLA_EXCLUSION_CHUNKS}}})
    jdump(out, f"data/{NS}/tags/worldgen/structure/aldeas.json", {"values": [e["structure"] for e in set_entries]})
    jdump(out, f"{NS}/opciones.json", options.schema())
    # unique structures
    for sid, mod in uniques.modules():
        write_unique(out, sid, mod.STRUCTURE)
    # medium structures (medianas/): structures, tags, structure_sets and loot
    mediums.write(out, jdump)
    # mine entrances (minas/) and the placement of vanilla abandoned mines
    mines.write(out, jdump)
    # coastal lighthouses and shipwrecks (costa/)
    coast.write(out, jdump)
    # loot
    unique_mods = uniques.modules()
    with_map = dimensions.overworld_only(unique_mods)   # an exploration map only searches in its own dimension
    for name, table in loot.TABLES.items():
        if name == "epico":
            table = maps.with_maps(table, with_map)
        jdump(out, f"data/{NS}/loot_table/cofres/{name}.json", lootr_aware(table))
    filler_loot.write(out, jdump)                         # the poor filler of every container without a table of its own
    maps.write(out, with_map, jdump)
    trades.write(out, unique_mods, jdump)
    with_hint = treasure.tables_in_containers(reg)       # the treasure fragment, only in chests, barrels and pots
    for sid, mod in uniques.modules():
        for name, table in getattr(mod, "LOOT", {}).items():
            if name == mod.STORY["cofre"]:
                table = chest_loot.with_story(table, sid)   # its sheet of the Chronicle of the Heralds
            if f"{NS}:unicas/{sid}/{name}" in with_hint:
                table = treasure.with_hint(table, "unicas")
            jdump(out, f"data/{NS}/loot_table/unicas/{sid}/{name}.json", lootr_aware(table))
    jdump(out, f"data/{NS}/loot_table/{chest_loot.CLEARED_PREMIUM_ID.split(':')[1]}.json", chest_loot.cleared_premium())
    write_history(out, unique_mods)
    treasure.write(out, jdump)                            # treasure hunt: fragment, final chest and advancements
    jdump(out, f"{NS}/llaves.json", write_keys(out))
    write_trophies(out, reg)
    # guardian phases and reinforcements (comun/jefes in Java)
    jdump(out, f"{NS}/jefes.json", bosses.schema(uniques.modules(), reg.guardians))
    # funciones
    fdir = os.path.join(out, "data", NS, "function")
    os.makedirs(fdir, exist_ok=True)
    files = {
        "load.mcfunction": [
            "# Aldeas enormes: inicialización",
            "scoreboard objectives add heraldia_g dummy",
            "schedule function heraldia:golems 600t replace"],
        # heraldia_cfg is filled in by the mod at startup from config/heraldia.json (#limpieza 0/1, #limite_estandar, #limite_grande)
        "golems.mcfunction": [
            "# Cada 30 s revisa las aldeas cargadas y limita los gólems naturales (+25 % sobre la dotación inicial)",
            "execute if score #limpieza heraldia_cfg matches 1 as @e[type=minecraft:armor_stand,tag=heraldia_centro] at @s run function heraldia:golem_check",
            "schedule function heraldia:golems 600t replace"],
        "golem_check.mcfunction": [
            "execute store result score @s heraldia_g if entity @e[type=minecraft:iron_golem,distance=..112,nbt={PlayerCreated:0b}]",
            "execute if entity @s[tag=heraldia_std] if score @s heraldia_g >= #limite_estandar heraldia_cfg as @e[type=minecraft:iron_golem,distance=..112,nbt={PlayerCreated:0b},sort=random,limit=1] at @s run tp @s ~ -200 ~",
            "execute if entity @s[tag=heraldia_grande] if score @s heraldia_g >= #limite_grande heraldia_cfg as @e[type=minecraft:iron_golem,distance=..112,nbt={PlayerCreated:0b},sort=random,limit=1] at @s run tp @s ~ -200 ~"],
    }
    # --- showcase: places the 72 styles on a grid, one every 8 s, guiding the player
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
    # a single family (6 villages in a row): /function heraldia:familia/<name>
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
    advancements.write(out, reg, unique_mods, jdump)
    for writes in (board.write, roads.write, arena_waves.write, quests.write, caravans.write,
                    wizard_huts.write, chronicle_ending.write, dialogue.write, herald_house.write, spawn_roads.write):
        writes(out, jdump)
    translated = languages.complete(texts(reg), book_pages(reg, out),
                                   languages.sign_keys(nbt for t in reg.templates.values() for _, nbt in t.blocks.values() if nbt))
    guide.write(out, unique_mods, jdump, {c: t for c, t in translated.items() if c not in languages.BASE})
    e = treasure.errors({c: t for c, t in translated.items() if c not in languages.BASE})
    e += chronicle_ending.errors({c: t for c, t in translated.items() if c not in languages.BASE})
    e += herald_house.text_errors({c: t for c, t in translated.items() if c not in languages.BASE})
    e += spawn_roads.text_errors({c: t for c, t in translated.items() if c not in languages.BASE})
    if e:
        raise SystemExit("\n".join(e))
    jdump(out, f"{NS}/idiomas.json", {"lenguas": languages.mc_locales()})
    for lang, lang_texts in translated.items():
        jdump(out, f"assets/{NS}/lang/{lang}.json", lang_texts)


def texts(reg):
    """{"es_es": {...}, "en_us": {...}} with all the mod's texts (what write writes to assets/heraldia/lang),
    without writing anything: the single source of the keys of each language (languages.complete). It only depends on `reg` for the
    unique structures' guardians (advancements.guardians)."""
    unique_mods = uniques.modules()
    out = {lang: dict(lang_texts) for lang, lang_texts in LANG.items()}
    for sid, mod in unique_mods:
        extra = getattr(mod, "LANG", {})
        assert extra.get("es_es", {}).keys() == extra.get("en_us", {}).keys(), sid
        for lang, lang_texts in extra.items():
            out[lang].update(lang_texts)
    parts = [maps.lang(dimensions.overworld_only(unique_mods)), advancements.build(reg, unique_mods, mediums.modules(), mines, coast)[1], trades.lang(),
              board.lang(), roads.LANG, mediums.lang(), mines.lang(), coast.lang(), guide.lang(), arena_waves.lang(), admin.lang(), updates.lang(), light_profile.lang(), quests.lang(), caravans.lang(), wizard_huts.lang(),
              trophies_lang(), chest_loot.story_lang(unique_mods), treasure.lang(), chronicle_ending.lang(), dialogue.lang(), herald_house.lang(), spawn_roads.lang(), village_events.lang()]
    for part in parts:
        assert part["es_es"].keys() == part["en_us"].keys()
        for lang, lang_texts in part.items():
            out[lang].update(lang_texts)
    return out


def book_pages(reg, out):
    """[(where, page)] of all the written books in the datapack (loot and trades already written to `out`, and those on the
    lecterns of the templates), to measure them in each language (languages.complete)."""
    items = []
    for d, _, fs in os.walk(os.path.join(out, "data", NS)):
        for f in fs:
            if f.endswith(".json"):
                with open(os.path.join(d, f), encoding="utf-8") as fh:
                    text = fh.read()
                if "written_book_content" in text:
                    items.append((os.path.relpath(os.path.join(d, f), out), json.loads(text)))
    for name, t in reg.templates.items():
        for _, nbt in t.blocks.values():
            if nbt and "Book" in nbt:
                items.append((name, nbt))
    return languages.book_pages(items)


def write_keys(out):
    """Keys for the unique structures' locked chests (KEYS of each module): one loot table per key,
    heraldia:llaves/<id>/<llave>, which gives exactly the item the lock asks for, and the index read by the command
    /heraldia key when the server starts: {"<id>.<llave>": {"tabla": "heraldia:llaves/<id>/<llave>", "cerradura": lock}}
    (the lock is used by the smoke test to check that the key opens it)."""
    index = {}
    for sid, mod in uniques.modules():
        for key, d in getattr(mod, "KEYS", {}).items():
            jdump(out, f"data/{NS}/loot_table/llaves/{sid}/{key}.json", d["tabla"])
            index[f"{sid}.{key}"] = {"tabla": f"{NS}:llaves/{sid}/{key}", "cerradura": d["cerradura"]}
    return {"llaves": index}


def write_trophies(out, reg):
    """Guardian trophies (TROPHY of each module, _comun/botin): heraldia:trofeos/<id> (the trophy alone) and
    heraldia:guardianes/<id>/<mob> (DeathLootTable that pack.tag_guardians gives to each guardian). Returns the texts."""
    for sid, mod in uniques.modules():
        d = mod.TROPHY
        jdump(out, f"data/{NS}/loot_table/trofeos/{sid}.json", chest_loot.trophy(sid, d))
        for mob, original in reg.guardians.get(sid, {}).items():
            jdump(out, f"data/{NS}/loot_table/{chest_loot.guardian_table_id(sid, mob).split(':')[1]}.json",
                  chest_loot.guardian_table(sid, original))
    return trophies_lang()


def trophies_lang():
    """Texts of the guardian trophies."""
    lang_texts = {"es_es": {}, "en_us": {}}
    for sid, mod in uniques.modules():
        for lang, t in chest_loot.trophy_lang(sid, mod.TROPHY).items():
            lang_texts[lang].update(t)
    return lang_texts


def history_tables(modules):
    """{id: table heraldia:historia/<id>} of the Chronicle of the Heralds (STORY of each module, _comun/botin): the
    sheet of each unique structure points to the next one in the chain (chest_loot.story_chain) and sometimes carries its treasure map."""
    mods = dict(modules)
    chain = chest_loot.story_chain(modules)
    out = {}
    for i, sid in enumerate(chain):
        nxt = chain[(i + 1) % len(chain)]
        name = {"translate": advancements.name_key(sid), "fallback": advancements.unique_name(sid, mods[sid])[0]}
        book = chest_loot.story_book(sid, mods[sid].STORY, i + 1, len(chain), nxt, mods[nxt].STORY, name)
        # the next one's map, only if both are in the overworld (a map searches in the chest's dimension)
        map_obj = maps.map_entry(nxt, mods[nxt], 1) if dimensions.dimension_of(mods[sid]) == dimensions.dimension_of(mods[nxt]) == dimensions.MAIN else None
        out[sid] = chest_loot.story_table(book, map_obj)
    return out


def write_history(out, modules):
    """Writes heraldia:historia/<id> and returns the chronicle texts."""
    for sid, table in history_tables(modules).items():
        jdump(out, f"data/{NS}/loot_table/{chest_loot.story_table_id(sid).split(':')[1]}.json", table)
    return chest_loot.story_lang(modules)


def write_unique(out, sid, st):
    """JSON of a unique structure, its placement grid and its tag (for treasure maps)."""
    sid_full = f"{NS}:unicas/{sid}"
    structure = st.get("json") or {
        "type": "minecraft:jigsaw", "biomes": st["biomes"], "step": st.get("step", "surface_structures"),
        "spawn_overrides": st.get("spawn_overrides", {}), "terrain_adaptation": st.get("terrain_adaptation", "beard_thin"),
        "start_pool": nsid(st["start_pool"]), "size": st["size"], "max_distance_from_center": st["max_distance"],
        "start_height": st.get("start_height", {"absolute": 0}), "use_expansion_hack": False}
    structure = dict(structure, biomes=biomes.for_unique(out, sid, structure["biomes"]))     # lista vanilla -> #heraldia:unicas/<id>
    if not st.get("json") and st.get("project_to", "WORLD_SURFACE_WG"):
        structure["project_start_to_heightmap"] = st.get("project_to", "WORLD_SURFACE_WG")
    jdump(out, f"data/{NS}/worldgen/structure/unicas/{sid}.json", structure)
    placement = st.get("placement") or {
        "type": f"{NS}:rejilla", "grupo": f"unicas/{sid}", "spacing": st.get("spacing", uniques.DEFAULT_SPACING),
        "separation": st.get("separation", uniques.DEFAULT_SEPARATION), "salt": uniques.salt(sid)}
    if sid in uniques.OLD_GRID:    # it was already in 0.1.0: with uniques.rejilla_compatible, its grid from back then
        assert placement["type"] == f"{NS}:rejilla" and not st.get("candidata_en_bioma"), f"{sid}: old grid without the one from back then"
        placement = dict(placement, rejilla_antigua=True)
    if st.get("candidata_en_bioma"):     # rare biome: each cell's candidate is searched for in its biomes (GridPlacement)
        assert placement["type"] == f"{NS}:rejilla", f"{sid}: candidata_en_bioma only with the heraldia:rejilla grid"
        placement = dict(placement, bioma=structure["biomes"].lstrip("#"))
        if st.get("candidata_y") is not None:   # underground biomes: the candidate is searched for at that height (GridPlacement)
            placement["bioma_y"] = st["candidata_y"]
    jdump(out, f"data/{NS}/worldgen/structure_set/unicas/{sid}.json", {
        "structures": [{"structure": sid_full, "weight": 1}],
        # the structure's own placement (e.g. Atlantis, always unique) or configurable grid heraldia:rejilla
        "placement": placement})
    jdump(out, f"data/{NS}/tags/worldgen/structure/unicas/{sid}.json", {"values": [sid_full]})


def lootr_aware(table):
    """Converts each group's "solo_sin_lootr" mark into the heraldia:sin_lootr condition."""
    pools = []
    for p in table["pools"]:
        p = dict(p)
        if p.pop("solo_sin_lootr", False):
            # 26.3: a group carries a single "condition" with "type" (several, with all_of).
            cond = {"type": f"{NS}:sin_lootr"}
            p["condition"] = {"type": "minecraft:all_of", "terms": [p["condition"], cond]} if "condition" in p else cond
        pools.append(p)
    return dict(table, pools=pools)


def rule(inp, loc, outb):
    return {"input_predicate": {"predicate_type": "minecraft:block_match", "block": "minecraft:" + inp.split("[")[0].replace("minecraft:", "")},
            "location_predicate": {"predicate_type": "minecraft:block_match", "block": "minecraft:" + loc},
            "output_state": "minecraft:" + outb.split("[")[0].replace("minecraft:", "")}


# ---------------------------------------------------------------- foundations and harbor (villages)
FOUNDATION_MAX = 16     # blocks a foundation may descend (with /place in a ravine a tower is not built)
PILES_MAX = 24       # dock piles down to the sea floor


def log_block(state):
    return "minecraft:" + state.split("[")[0].replace("minecraft:", "")


def down_to_floor(blocks, depth):
    """Processor heraldia:acueducto_hasta_el_suelo (Java comun/HastaElSueloProcessor): extends the blocks in the list
    that are in the template's bottom row down to firm ground."""
    return {"processor_type": f"{NS}:acueducto_hasta_el_suelo", "bloques": sorted(set(blocks)), "profundidad_maxima": depth}


def foundations(th):
    """Foundations of the village buildings on a hillside: the bottom foundation row (th["found"]) and, in the stilt
    styles, the stilts and the staircase railing go down to the terrain with the style's material, instead of
    hanging in the air (with /place) or resting on a loose dirt slope."""
    blocks = [log_block(th["found"])]
    if th["stilts"]:
        blocks += [log_block(th["log"]), log_block(th["fence"])]
    return down_to_floor(blocks, FOUNDATION_MAX)


PORT_REACH = 96        # blocks from the plaza center within which the shore is searched for (the Java code discards anything outside the 8 chunks)


def jigsaw_pos(t, name):
    return next(list(j["pos"]) for j in t.jigsaws if j["name"] == name)


def village(jig, **extra):
    """Village of type heraldia:aldea (Java aldeas/AldeaStructure): the usual jigsaw in `village`; the Java code removes the
    quest board if disabled (aldeas.vida.tablon) and, with `harbor`, adds the coastal one."""
    settings = {k: jig[k] for k in ("biomes", "step", "spawn_overrides", "terrain_adaptation")}
    return dict({"type": f"{NS}:aldea"}, **settings, aldea={k: v for k, v in jig.items() if k != "type"}, **extra)


def village_with_port(reg, th, jig):
    """Coastal village: also places the harbor hut and pier (pools special/port and port_pier) on the shore
    closest to the plaza, with the pier facing the sea."""
    from specials import PIER_L
    tid = th["id"]
    return village(jig, puerto={   # key of the Java config: stays in Spanish
        "caseta": f"{NS}:{tid}/special/port", "muelle": f"{NS}:{tid}/port_pier",
        "union_caseta": jigsaw_pos(reg.templates[f"{tid}/specials/port"], f"{NS}:pier"),
        "union_muelle": jigsaw_pos(reg.templates[f"{tid}/specials/port_pier"], f"{NS}:pier"),
        "largo": PIER_L, "alcance": PORT_REACH})
