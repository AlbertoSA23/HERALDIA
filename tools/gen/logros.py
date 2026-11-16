"""Logros de Heraldia (pestaña «Heraldia»): solo datos, generados recorriendo las aldeas y el registro de únicas.

Árbol (ids heraldia:<ruta>, textos advancements.heraldia.<ruta con puntos>.title/.description):
  raiz                         entrar en una aldea Heraldia o en una estructura única
  aldeas/<familia>             entrar en una aldea de esa familia (etiqueta de estructuras heraldia:aldeas/<familia>)
  aldeas/todas                 (desafío) las 12 familias
  unicas/<id>/descubrir        entrar en la estructura (minecraft:location con structures heraldia:unicas/<id>)
  unicas/<id>/guardian         matar a su guardián: Tags heraldia_guardian.<id> (pack.tag_guardians) y su tipo de mob
                               (predicado minecraft:entity_tags de 26.3)
  unicas/<id>/tesoro           abrir el cofre del tesoro (player_generates_container_loot de sus tablas) o conseguir
                               un objeto que solo hay en él (cofres de contenido fijo)
  unicas/<id>/<extra>          logros propios del módulo
  unicas/todas                 (desafío) descubrir todas las únicas
  unicas/trofeos               (desafío) conseguir el trofeo de cada guardián (TROFEO de cada módulo, custom_data
                               heraldia_trofeo; un criterio inventory_changed por trofeo, todos requeridos)
  medianas/descubrir           entrar en una estructura mediana cualquiera; medianas/todas: una de cada tipo
  medianas/<id>/<extra>        logros propios de un tipo de mediana (LOGROS del módulo: abrir uno de sus contenedores o
                               criterios propios)
  unicas/cronista              (desafío) reunir los pliegos de la Crónica de los Heraldos (HISTORIA de cada módulo,
                               custom_data heraldia_historia; un criterio inventory_changed por pliego, todos requeridos)
Contrato opcional en cada módulo de unicas/ (ver unicas/__init__.py): LOGRO = {"icono", "tesoro", "tesoro_objeto", "extra"}.
Recompensas: solo experiencia (Decisiones de Alberto: nada que rompa la progresión).
"""
from themes import FAMILIES, THEMES
from unicas._comun.piezas import GUARDIAN_TAG
from unicas._comun import botin

NS = "heraldia"
BACKGROUND = "minecraft:gui/advancements/backgrounds/adventure"
ROOT_ICON, VILLAGES_ICON, UNIQUES_ICON = "minecraft:filled_map", "minecraft:bell", "minecraft:compass"
DEFAULT_ICON, GUARDIAN_ICON, TREASURE_ICON = "minecraft:filled_map", "minecraft:iron_sword", "minecraft:chest"
# Experiencia (moderada): una aldea vale lo que un logro vanilla sencillo, los desafíos lo que uno vanilla grande.
XP = {"familia": 20, "aldeas": 250, "descubrir": 50, "guardian": 100, "tesoro": 50, "extra": 30, "unicas": 500,
      "trofeos": 500, "cronista": 500, "mediana": 10, "medianas": 150, "mediana_extra": 20}
MEDIANAS_ICON = "minecraft:oak_sign"
TROPHIES_ICON, CHRONICLE_ICON = "minecraft:armor_stand", "minecraft:written_book"
DEFAULT_TREASURE_TABLES = ("premium",)
TREASURE_MARK = "heraldia_tesoro"   # custom_data de los objetos de un cofre de contenido fijo (tesoro_objeto)

# Textos comunes; %s es el nombre de la familia, de la estructura o del guardián.
TEXTS = {
    "raiz": (("Heraldia", "Heraldia"),
             ("Entra en una aldea Heraldia, una estructura única o una mediana",
              "Enter a Heraldia village, a unique structure or a medium structure")),
    "familia": (("%s", "%s"), ("Entra en una aldea Heraldia de la familia %s", "Enter a Heraldia village of the %s family")),
    "aldeas": (("Trotamundos de Heraldia", "Heraldia Globetrotter"),
               ("Entra en una aldea de cada una de las 12 familias", "Enter a village of each of the 12 families")),
    "descubrir": (("%s", "%s"), ("Descubre la estructura única «%s»", "Discover the unique structure “%s”")),
    "guardian": (("%s", "%s"), ("Derrota al guardián de «%s»", "Defeat the guardian of “%s”")),
    "tesoro": (("Tesoro: %s", "Treasure: %s"), ("Abre la cámara del tesoro de «%s»", "Open the treasure chamber of “%s”")),
    "unicas": (("Cartógrafo de leyendas", "Cartographer of Legends"),
               ("Descubre todas las estructuras únicas", "Discover every unique structure")),
    "trofeos": (("Sala de trofeos", "Hall of Trophies"),
                ("Consigue el trofeo de cada guardián de las estructuras únicas",
                 "Collect the trophy of every unique structure's guardian")),
    "mediana": (("Al borde del camino", "By the Wayside"),
                ("Encuentra una estructura mediana: una torre de vigía, una posada, un campamento, una ermita...",
                 "Find a medium structure: a watchtower, an inn, a camp, a hermitage...")),
    "medianas": (("Caminante", "Wayfarer"),
                 ("Encuentra una estructura mediana de cada tipo", "Find a medium structure of every type")),
    "cronista": (("Cronista", "Chronicler"),
                 ("Reúne todos los pliegos de la Crónica de los Heraldos",
                  "Gather every leaf of the Chronicle of the Heralds")),
}


def key(path, part):
    return f"advancements.{NS}.{path.replace('/', '.')}.{part}"


def comp(k, fallback, *args):
    c = {"translate": k, "fallback": fallback}
    if args:
        c["with"] = list(args)
    return c


def name_key(sid):
    return f"{NS}.unicas.{sid}.nombre"


def unique_name(sid, mod):
    n = getattr(mod, "NOMBRE", None) or {}
    fallback = sid.replace("_", " ").capitalize()
    return n.get("es_es", fallback), n.get("en_us", n.get("es_es", fallback))


def location(structures):
    return {"trigger": "minecraft:location", "conditions": {"player": {
        "type": "minecraft:entity_properties", "entity": "this", "predicate": {"minecraft:location": {"structures": structures}}}}}


def advancement(parent, icon, title, desc, criteria, frame="task", xp=0, requirements=None, **display):
    """Logro de 26.3; sin `requirements` basta cualquiera de los criterios."""
    adv = {"criteria": criteria,
           "display": dict({"icon": {"id": icon}, "title": title, "description": desc, "frame": frame}, **display),
           "requirements": requirements or [sorted(criteria)]}
    if parent:
        adv["parent"] = f"{NS}:{parent}"
    if xp:
        adv["rewards"] = {"experience": xp}
    return adv


def guardians(reg, sid):
    """[(tipo de mob, CustomName)] de los guardianes de la única, sin repetir tipo (pack.tag_guardians los marca)."""
    found = {}
    for name, t in reg.templates.items():
        if name.startswith(f"unicas/{sid}/"):
            for *_, n in t.entities:
                if f"{GUARDIAN_TAG}.{sid}" in (n.get("Tags") or []):
                    found.setdefault(str(n["id"]), n.get("CustomName"))
    return sorted(found.items())


def build(reg, modules, medianas_mods=None):
    """{ruta: advancement} y textos {"es_es": {...}, "en_us": {...}} (claves con el texto propio; los %s del título y
    la descripción se rellenan con "with")."""
    advs, lang = {}, {"es_es": {}, "en_us": {}}

    def text(path, kind, *args):
        """(título, descripción) traducibles de un logro con los textos comunes de TEXTS[kind]."""
        (tes, ten), (des, den) = TEXTS[kind]
        for part, es, en in (("title", tes, ten), ("description", des, den)):
            lang["es_es"][key(path, part)], lang["en_us"][key(path, part)] = es, en
        fb = lambda s: s % tuple(a.get("fallback", "") for a in args) if args else s
        return comp(key(path, "title"), fb(tes), *([args[0]] if "%s" in tes else [])), \
            comp(key(path, "description"), fb(des), *([args[0]] if "%s" in des else []))

    title, desc = text("raiz", "raiz")
    raiz = {"aldea": location(f"#{NS}:aldeas"), "unica": location(f"#{NS}:unicas")}
    if medianas_mods:
        raiz["mediana"] = location(f"#{NS}:medianas")
    advs["raiz"] = advancement(None, ROOT_ICON, title, desc, raiz, requirements=[sorted(raiz)], background=BACKGROUND,
                               announce_to_chat=False, show_toast=False)
    if medianas_mods:   # estructuras medianas (medianas/): una cualquiera y una de cada tipo
        title, desc = text("medianas/descubrir", "mediana")
        advs["medianas/descubrir"] = advancement("raiz", MEDIANAS_ICON, title, desc,
                                                 {"mediana": location(f"#{NS}:medianas")}, xp=XP["mediana"])
        crit = {mid: location(f"#{NS}:medianas/{mid}") for mid, _ in medianas_mods}
        title, desc = text("medianas/todas", "medianas")
        advs["medianas/todas"] = advancement("medianas/descubrir", MEDIANAS_ICON, title, desc, crit,
                                             requirements=[[mid] for mid in sorted(crit)], frame="goal", xp=XP["medianas"])
        for mid, mod in medianas_mods:      # logros propios de cada tipo (LOGROS, opcional; ver medianas/__init__.py)
            for ex in getattr(mod, "LOGROS", ()):
                path = f"medianas/{mid}/{ex['id']}"
                for part, field in (("title", "titulo"), ("description", "descripcion")):
                    lang["es_es"][key(path, part)], lang["en_us"][key(path, part)] = ex[field]
                crit = ex.get("criterios") or {ex["tabla"]: {"trigger": "minecraft:player_generates_container_loot",
                                                             "conditions": {"loot_tables": f"{NS}:medianas/{mid}/{ex['tabla']}"}}}
                advs[path] = advancement("medianas/descubrir", ex["icono"], comp(key(path, "title"), ex["titulo"][0]),
                                         comp(key(path, "description"), ex["descripcion"][0]), crit,
                                         xp=ex.get("xp", XP["mediana_extra"]), requirements=[sorted(crit)])
    # aldeas por familia
    for fam, d in FAMILIES.items():
        es, en = d["nombre"]
        lang["es_es"][f"{NS}.familia.{fam}"], lang["en_us"][f"{NS}.familia.{fam}"] = es, en
        title, desc = text(f"aldeas/{fam}", "familia", comp(f"{NS}.familia.{fam}", es))
        advs[f"aldeas/{fam}"] = advancement("raiz", d["icono"], title, desc, {fam: location(f"#{NS}:aldeas/{fam}")},
                                            xp=XP["familia"])
    title, desc = text("aldeas/todas", "aldeas")
    advs["aldeas/todas"] = advancement("raiz", VILLAGES_ICON, title, desc,
                                       {fam: location(f"#{NS}:aldeas/{fam}") for fam in FAMILIES},
                                       requirements=[[fam] for fam in FAMILIES], frame="challenge", xp=XP["aldeas"])
    # estructuras únicas: todo sale del registro, una única nueva tiene sus logros sin tocar este módulo
    for sid, mod in modules:
        es, en = unique_name(sid, mod)
        lang["es_es"][name_key(sid)], lang["en_us"][name_key(sid)] = es, en
        uname = comp(name_key(sid), es)
        logro = getattr(mod, "LOGRO", None) or {}
        base = f"unicas/{sid}"
        title, desc = text(f"{base}/descubrir", "descubrir", uname)
        advs[f"{base}/descubrir"] = advancement("raiz", logro.get("icono", DEFAULT_ICON), title, desc,
                                                {"descubrir": location(f"{NS}:{base}")}, xp=XP["descubrir"])
        gs = guardians(reg, sid)
        if gs:
            gname = gs[0][1] or uname
            gname = {k: v for k, v in gname.items() if k in ("translate", "fallback")}
            _, desc = text(f"{base}/guardian", "guardian", uname)
            crit = {mob.split(":")[-1]: {"trigger": "minecraft:player_killed_entity", "conditions": {"entity": {
                "type": "minecraft:entity_properties", "entity": "this",
                # entity_tags lee las Tags sin serializar el mob (más barato que nbt); el tipo se mira antes
                "predicate": {"minecraft:entity_type": mob, "minecraft:entity_tags": {"all_of": [f"{GUARDIAN_TAG}.{sid}"]}}}}}
                for mob, _ in gs}
            advs[f"{base}/guardian"] = advancement(f"{base}/descubrir", GUARDIAN_ICON, gname, desc, crit,
                                                   frame="goal", xp=XP["guardian"], requirements=[sorted(crit)])
        loot = getattr(mod, "LOOT", {})
        tables = [t for t in logro.get("tesoro", DEFAULT_TREASURE_TABLES) if t in loot]
        crit = {t: {"trigger": "minecraft:player_generates_container_loot",
                    "conditions": {"loot_tables": f"{NS}:{base}/{t}"}} for t in tables}
        if logro.get("tesoro_objeto"):
            crit["objeto"] = {"trigger": "minecraft:inventory_changed", "conditions": {"items": [logro["tesoro_objeto"]]}}
        if crit:
            title, desc = text(f"{base}/tesoro", "tesoro", uname)
            advs[f"{base}/tesoro"] = advancement(f"{base}/descubrir", TREASURE_ICON, title, desc, crit, frame="goal",
                                                 xp=XP["tesoro"], requirements=[sorted(crit)])
        for ex in logro.get("extra", ()):
            path = f"{base}/{ex['id']}"
            for part, field in (("title", "titulo"), ("description", "descripcion")):
                lang["es_es"][key(path, part)], lang["en_us"][key(path, part)] = ex[field]
            advs[path] = advancement(f"{base}/{ex.get('padre', 'descubrir')}", ex["icono"],
                                     comp(key(path, "title"), ex["titulo"][0]), comp(key(path, "description"), ex["descripcion"][0]),
                                     ex["criterios"], frame=ex.get("marco", "task"), xp=ex.get("xp", XP["extra"]),
                                     requirements=ex.get("requisitos"))
    title, desc = text("unicas/todas", "unicas")
    advs["unicas/todas"] = advancement("raiz", UNIQUES_ICON, title, desc,
                                       {sid: location(f"{NS}:unicas/{sid}") for sid, _ in modules},
                                       requirements=[[sid] for sid, _ in modules], frame="challenge", xp=XP["unicas"])
    # trofeos: uno por única (TROFEO es obligatorio, pack.build_all lo comprueba), todos requeridos
    crit = {sid: {"trigger": "minecraft:inventory_changed",
                  "conditions": {"items": [botin.trofeo_predicado(sid, mod.TROFEO)]}} for sid, mod in modules}
    title, desc = text("unicas/trofeos", "trofeos")
    advs["unicas/trofeos"] = advancement("raiz", TROPHIES_ICON, title, desc, crit,
                                         requirements=[[sid] for sid in sorted(crit)], frame="challenge", xp=XP["trofeos"])
    # crónica: un pliego por única (HISTORIA es obligatorio, pack.build_all lo comprueba), todos requeridos
    crit = {sid: {"trigger": "minecraft:inventory_changed", "conditions": {"items": [botin.historia_predicado(sid)]}}
            for sid, mod in modules}
    title, desc = text("unicas/cronista", "cronista")
    advs["unicas/cronista"] = advancement("raiz", CHRONICLE_ICON, title, desc, crit,
                                          requirements=[[sid] for sid in sorted(crit)], frame="challenge", xp=XP["cronista"])
    return advs, lang


def structure_tags(modules):
    """Etiquetas de estructuras que usan los logros: heraldia:aldeas/<familia> y heraldia:unicas (todas)."""
    tags = {f"aldeas/{fam}": [f"{NS}:{th['id']}{suf}" for th in THEMES if th["family"] == fam for suf in ("", "_grande")]
            for fam in FAMILIES}
    tags["unicas"] = [f"{NS}:unicas/{sid}" for sid, _ in modules]
    return tags


def write(out, reg, modules, jdump):
    """Escribe los logros y sus etiquetas; devuelve los textos para sumarlos a los idiomas del mod."""
    for path, values in structure_tags(modules).items():
        jdump(out, f"data/{NS}/tags/worldgen/structure/{path}.json", {"values": values})
    import medianas
    advs, lang = build(reg, modules, medianas.modules())
    for path, adv in advs.items():
        jdump(out, f"data/{NS}/advancement/{path}.json", adv)
    return lang
