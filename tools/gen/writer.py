"""Escribe los recursos de datos del mod (data/heraldia/...) en disco."""
import json, os, shutil
from core import NS, nsid
from themes import THEMES, FAMILIES
from pack import ALL_PROFS
import loot
import unicas
import medianas
import mapas
import tratos
import tablon
import opciones
import biomas
import logros
import paralelo
from unicas._comun import botin

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
        # /heraldia llave (los textos de respaldo del Java son estos mismos)
        "heraldia.llave.dada": "Entregadas %s llaves (%s) a %s jugadores",
        "heraldia.llave.desconocida": "No hay ninguna llave «%s». Opciones: %s",
        # /heraldia info (el Java toma el texto de respaldo de este es_es)
        "heraldia.info.titulo": "Heraldia: configuración en uso",
        "heraldia.info.aldeas": "Aldeas: cada %s bloques, máximo %s, %s %% grandes, %s de %s estilos activados, a %s bloques de las vanilla",
        "heraldia.info.unicas": "Estructuras únicas activadas: %s de %s",
        "heraldia.info.unica": " - %s: cada %s bloques",
        "heraldia.info.unica.desactivada": " - %s: desactivada",
        "heraldia.info.unica.mundial": " - %s: una por mundo",
        "heraldia.info.distancia": "Distancia mínima entre únicas: %s, %s bloques",
        "heraldia.info.rejilla": "Rejilla antigua de las únicas (mundo de una versión anterior): %s",
        "heraldia.info.cofre": "Cofre premium de la Atlántida por jugador: %s; Lootr: %s",
        "heraldia.info.registradas": "Estructuras registradas: %s (%s de aldeas, %s únicas y %s medianas)",
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
        "heraldia.info.registradas": "Registered structures: %s (%s villages, %s unique and %s medium)",
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
    # plantillas (en paralelo: cada una en su fichero, el resultado no depende del orden)
    paralelo.mapa(lambda t: t.save(out), reg.templates.values(), chunksize=16)
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
        jdump(out, f"data/{NS}/worldgen/processor_list/{tid}/building.json", {"processors": procs + [cimientos(th)]})
        if th["family"] == "costa":
            jdump(out, f"data/{NS}/worldgen/processor_list/{tid}/pier.json", {"processors": [
                hasta_el_suelo([log_block(th["pier"]["log"])], PILOTES_MAX)]})
    # etiquetas de biomas
    for fam, d in FAMILIES.items():
        biomas.etiqueta(out, fam, d["biomes"])
    # estructuras
    set_entries = []
    for th in THEMES:
        tid = th["id"]
        base = {"type": "minecraft:jigsaw", "biomes": f"#{NS}:{th['family']}", "step": "surface_structures",
                "spawn_overrides": {}, "terrain_adaptation": "beard_thin", "start_height": {"absolute": 0},
                "project_start_to_heightmap": "WORLD_SURFACE_WG", "use_expansion_hack": False}
        std, grande = sizes(th)
        aliases = [{"type": "minecraft:direct", "alias": f"{NS}:villagers/{th['vtype']}/{p}",
                    "target": f"{NS}:villagers/{th['vtype']}/{p}_grande"} for p in ALL_PROFS]
        for suffix, pool, sz, al in (("", "plaza", std, []), ("_grande", "plaza_grande", grande, aliases)):
            jig = dict(base, start_pool=f"{NS}:{tid}/{pool}", size=sz["size"], max_distance_from_center=sz["maxdist"])
            if al:
                jig["pool_aliases"] = al
            jig = village_with_port(reg, th, jig) if th["family"] == "costa" else village(jig)
            jdump(out, f"data/{NS}/worldgen/structure/{tid}{suffix}.json", jig)
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
    # estructuras medianas (medianas/): estructuras, etiquetas, structure_sets y botín
    medianas_lang = medianas.write(out, jdump)
    # botín
    uniques = unicas.modules()
    for name, table in loot.TABLES.items():
        if name == "epico":
            table = mapas.with_maps(table, uniques)
        jdump(out, f"data/{NS}/loot_table/cofres/{name}.json", lootr_aware(table))
    mapas.write(out, uniques, jdump)
    tratos.write(out, uniques, jdump)
    for sid, mod in unicas.modules():
        for name, table in getattr(mod, "LOOT", {}).items():
            if name == mod.HISTORIA["cofre"]:
                table = botin.con_historia(table, sid)   # su pliego de la Crónica de los Heraldos
            jdump(out, f"data/{NS}/loot_table/unicas/{sid}/{name}.json", lootr_aware(table))
    history_lang = write_history(out, uniques)
    jdump(out, f"{NS}/llaves.json", write_keys(out))
    trophy_lang = write_trophies(out, reg)
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
    adv_lang = logros.write(out, reg, uniques, jdump)
    for extra in (tratos.lang(), tablon.write(out, jdump), medianas_lang):
        for lang, texts in extra.items():
            adv_lang[lang].update(texts)
    for sid, mod in unicas.modules():
        extra = getattr(mod, "LANG", {})
        assert extra.get("es_es", {}).keys() == extra.get("en_us", {}).keys(), sid
        for lang, texts in extra.items():
            LANG[lang].update(texts)
    for lang, texts in LANG.items():
        jdump(out, f"assets/{NS}/lang/{lang}.json", dict(texts, **maps_lang[lang], **adv_lang[lang], **trophy_lang[lang], **history_lang[lang]))


def write_keys(out):
    """Llaves de los cofres cerrados de las únicas (LLAVES de cada módulo): una tabla de botín por llave,
    heraldia:llaves/<id>/<llave>, que da exactamente el objeto que pide la cerradura, y el índice que lee el comando
    /heraldia llave al arrancar el servidor: {"<id>.<llave>": {"tabla": "heraldia:llaves/<id>/<llave>", "cerradura": lock}}
    (la cerradura la usa la prueba de humo para comprobar que la llave la abre)."""
    index = {}
    for sid, mod in unicas.modules():
        for key, d in getattr(mod, "LLAVES", {}).items():
            jdump(out, f"data/{NS}/loot_table/llaves/{sid}/{key}.json", d["tabla"])
            index[f"{sid}.{key}"] = {"tabla": f"{NS}:llaves/{sid}/{key}", "cerradura": d["cerradura"]}
    return {"llaves": index}


def write_trophies(out, reg):
    """Trofeos de los guardianes (TROFEO de cada módulo, _comun/botin): heraldia:trofeos/<id> (el trofeo solo) y
    heraldia:guardianes/<id>/<mob> (DeathLootTable que pack.tag_guardians pone a cada guardián). Devuelve los textos."""
    texts = {"es_es": {}, "en_us": {}}
    for sid, mod in unicas.modules():
        d = mod.TROFEO
        jdump(out, f"data/{NS}/loot_table/trofeos/{sid}.json", botin.trofeo(sid, d))
        for mob, original in reg.guardianes.get(sid, {}).items():
            jdump(out, f"data/{NS}/loot_table/{botin.guardian_tabla_id(sid, mob).split(':')[1]}.json",
                  botin.guardian_tabla(sid, original))
        for lang, t in botin.trofeo_lang(sid, d).items():
            texts[lang].update(t)
    return texts


def history_tables(modules):
    """{id: tabla heraldia:historia/<id>} de la Crónica de los Heraldos (HISTORIA de cada módulo, _comun/botin): el
    pliego de cada única señala la siguiente de la cadena (botin.historia_cadena) y a veces trae su mapa del tesoro."""
    mods = dict(modules)
    chain = botin.historia_cadena(modules)
    out = {}
    for i, sid in enumerate(chain):
        nxt = chain[(i + 1) % len(chain)]
        name = {"translate": logros.name_key(sid), "fallback": logros.unique_name(sid, mods[sid])[0]}
        book = botin.historia_libro(sid, mods[sid].HISTORIA, i + 1, len(chain), nxt, mods[nxt].HISTORIA, name)
        out[sid] = botin.historia_tabla(book, mapas.map_entry(nxt, mods[nxt], 1))
    return out


def write_history(out, modules):
    """Escribe heraldia:historia/<id> y devuelve los textos de la crónica."""
    for sid, table in history_tables(modules).items():
        jdump(out, f"data/{NS}/loot_table/{botin.historia_tabla_id(sid).split(':')[1]}.json", table)
    return botin.historia_lang(modules)


def write_unique(out, sid, st):
    """JSON de una estructura única, su rejilla de colocación y su etiqueta (para mapas del tesoro)."""
    sid_full = f"{NS}:unicas/{sid}"
    structure = st.get("json") or {
        "type": "minecraft:jigsaw", "biomes": st["biomes"], "step": st.get("step", "surface_structures"),
        "spawn_overrides": st.get("spawn_overrides", {}), "terrain_adaptation": st.get("terrain_adaptation", "beard_thin"),
        "start_pool": nsid(st["start_pool"]), "size": st["size"], "max_distance_from_center": st["max_distance"],
        "start_height": st.get("start_height", {"absolute": 0}), "use_expansion_hack": False}
    structure = dict(structure, biomes=biomas.de_unica(out, sid, structure["biomes"]))     # lista vanilla -> #heraldia:unicas/<id>
    if not st.get("json") and st.get("project_to", "WORLD_SURFACE_WG"):
        structure["project_start_to_heightmap"] = st.get("project_to", "WORLD_SURFACE_WG")
    jdump(out, f"data/{NS}/worldgen/structure/unicas/{sid}.json", structure)
    placement = st.get("placement") or {
        "type": f"{NS}:rejilla", "grupo": f"unicas/{sid}", "spacing": st.get("spacing", unicas.DEFAULT_SPACING),
        "separation": st.get("separation", unicas.DEFAULT_SEPARATION), "salt": unicas.salt(sid)}
    if sid in unicas.REJILLA_ANTIGUA:    # ya estaba en la 0.1.0: con unicas.rejilla_compatible, su rejilla de entonces
        assert placement["type"] == f"{NS}:rejilla" and not st.get("candidata_en_bioma"), f"{sid}: rejilla antigua sin la de entonces"
        placement = dict(placement, rejilla_antigua=True)
    if st.get("candidata_en_bioma"):     # bioma raro: la candidata de cada casilla se busca en sus biomas (GridPlacement)
        assert placement["type"] == f"{NS}:rejilla", f"{sid}: candidata_en_bioma solo con la rejilla heraldia:rejilla"
        placement = dict(placement, bioma=structure["biomes"].lstrip("#"))
        if st.get("candidata_y") is not None:   # biomas subterráneos: la candidata se busca a esa altura (GridPlacement)
            placement["bioma_y"] = st["candidata_y"]
    jdump(out, f"data/{NS}/worldgen/structure_set/unicas/{sid}.json", {
        "structures": [{"structure": sid_full, "weight": 1}],
        # colocación propia de la estructura (p. ej. la Atlántida, siempre una) o rejilla configurable heraldia:rejilla
        "placement": placement})
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


# ---------------------------------------------------------------- cimientos y puerto (aldeas)
CIMIENTOS_MAX = 16     # bloques que puede bajar un cimiento (con /place en un barranco no se hace una torre)
PILOTES_MAX = 24       # pilotes del muelle hasta el fondo del mar


def log_block(state):
    return "minecraft:" + state.split("[")[0].replace("minecraft:", "")


def hasta_el_suelo(blocks, depth):
    """Procesador heraldia:acueducto_hasta_el_suelo (Java comun/HastaElSueloProcessor): alarga hasta el suelo firme los
    bloques de la lista que estén en la fila inferior de la plantilla."""
    return {"processor_type": f"{NS}:acueducto_hasta_el_suelo", "bloques": sorted(set(blocks)), "profundidad_maxima": depth}


def cimientos(th):
    """Cimientos de los edificios de la aldea en ladera: la fila inferior de cimiento (th["found"]) y, en los estilos de
    pilotes, los pilotes y la barandilla de la escalera bajan hasta el terreno con el material del estilo, en vez de
    quedar al aire (con /place) o sobre un talud de tierra suelto."""
    blocks = [log_block(th["found"])]
    if th["stilts"]:
        blocks += [log_block(th["log"]), log_block(th["fence"])]
    return hasta_el_suelo(blocks, CIMIENTOS_MAX)


PORT_REACH = 96        # bloques desde el centro de la plaza en que se busca la orilla (el Java descarta lo que salga de los 8 chunks)


def jigsaw_pos(t, name):
    return next(list(j["pos"]) for j in t.jigsaws if j["name"] == name)


def village(jig, **extra):
    """Aldea de tipo heraldia:aldea (Java aldeas/AldeaStructure): el jigsaw de siempre en `aldea`; el Java quita el
    tablón de encargos si está desactivado (aldeas.vida.tablon) y, con `puerto`, pone el de la costa."""
    settings = {k: jig[k] for k in ("biomes", "step", "spawn_overrides", "terrain_adaptation")}
    return dict({"type": f"{NS}:aldea"}, **settings, aldea={k: v for k, v in jig.items() if k != "type"}, **extra)


def village_with_port(reg, th, jig):
    """Aldea de la costa: además pone la caseta y el muelle del puerto (pools special/port y port_pier) en la orilla
    más cercana a la plaza, con el muelle hacia el mar."""
    from specials import PIER_L
    tid = th["id"]
    return village(jig, puerto={
        "caseta": f"{NS}:{tid}/special/port", "muelle": f"{NS}:{tid}/port_pier",
        "union_caseta": jigsaw_pos(reg.templates[f"{tid}/specials/port"], f"{NS}:pier"),
        "union_muelle": jigsaw_pos(reg.templates[f"{tid}/specials/port_pier"], f"{NS}:pier"),
        "largo": PIER_L, "alcance": PORT_REACH})
