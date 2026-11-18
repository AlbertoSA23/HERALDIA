"""Jefes: fases y refuerzos de los guardianes finales de las estructuras únicas (lado servidor, comun/jefes en Java).

El Java pasa de fase a un guardián (etiqueta heraldia_guardian) al bajar del 66 % y del 33 % de vida y llama a sus
refuerzos una vez por fase. Qué refuerzos llama cada guardián sale de aquí, en heraldia/jefes.json (dentro del .jar):

Contrato (opcional) de cada módulo de unicas/:
  REFUERZOS = ["husk", {"mob": "husk", "equipo": {"mainhand": "iron_sword"}}]   # 2 o 3 mobs de REFUERZO_MOBS
Sin REFUERZOS, los de la familia del tipo de su guardián (MOB_FAMILIA -> FAMILIAS); un tipo sin familia, GENERICA.
Los guardianes de un mundo ya generado que no se reconozcan (sin heraldia_guardian.<id>) usan también la familia de su
tipo: por eso jefes.json lleva las familias además de lo ya resuelto por única.

Reglas (falla la generación): 2-3 refuerzos, mobs hostiles de REFUERZO_MOBS (sin jefes, ni hoglins ni zoglins, que
salen bebés; ni vex, que mueren solos), equipo en ranuras válidas y sin netherita ni élitros.
"""

VERSION = 1
# Mobs que pueden ser refuerzos: hostiles, adultos garantizados (los zombis con heraldia_adulto) y sin jefes.
REINFORCEMENT_MOBS = frozenset({
    "zombie", "husk", "drowned", "zombie_villager", "skeleton", "stray", "bogged", "wither_skeleton",
    "vindicator", "pillager", "witch", "guardian", "spider", "cave_spider",
})
SLOTS = ("mainhand", "offhand", "head", "chest", "legs", "feet")
FORBIDDEN_ITEMS = ("netherite", "elytra")      # Decisiones del dueño: nada de netherita en equipo ni élitros
MIN_REINFORCEMENTS, MAX_REINFORCEMENTS = 2, 3

# Familias: refuerzos por defecto según el tipo del guardián.
FAMILIES = {
    "zombi": ["zombie", "zombie"],
    "momia": ["husk", "husk"],
    "ahogado": ["drowned", "drowned"],
    "esqueleto": ["skeleton", "skeleton"],
    "escarcha": ["stray", "stray"],
    "pantano": ["bogged", "bogged"],
    "inframundo": ["skeleton", "wither_skeleton"],
    "illager": ["vindicator", "pillager"],
    "abisal": ["guardian", "guardian"],
    "generica": ["zombie", "skeleton"],
}
GENERIC = "generica"
MOB_FAMILY = {
    "zombie": "zombi", "zombie_villager": "zombi", "husk": "momia", "drowned": "ahogado",
    "skeleton": "esqueleto", "stray": "escarcha", "bogged": "pantano", "wither_skeleton": "inframundo",
    "vindicator": "illager", "evoker": "illager", "pillager": "illager", "illusioner": "illager",
    "guardian": "abisal", "elder_guardian": "abisal",
}

LANG = {
    "es_es": {
        "heraldia.jefes.fase.2": "%s se enfurece",
        "heraldia.jefes.fase.2.refuerzos": "%s se enfurece y llama a sus refuerzos",
        "heraldia.jefes.fase.3": "%s, malherido, lucha a la desesperada",
        "heraldia.jefes.fase.3.refuerzos": "%s, malherido, llama a sus últimos refuerzos",
        "heraldia.jefes.refuerzos": "%s llama a sus refuerzos",
    },
    "en_us": {
        "heraldia.jefes.fase.2": "%s is enraged",
        "heraldia.jefes.fase.2.refuerzos": "%s is enraged and calls for reinforcements",
        "heraldia.jefes.fase.3": "%s, badly wounded, fights desperately",
        "heraldia.jefes.fase.3.refuerzos": "%s, badly wounded, calls its last reinforcements",
        "heraldia.jefes.refuerzos": "%s calls for reinforcements",
    },
}


def nsid(s):
    """Id con espacio de nombres (minecraft: si no lo lleva): los refuerzos y su equipo son siempre vanilla."""
    s = str(s)
    return s if ":" in s else "minecraft:" + s


def _short_name(mob):
    return str(mob).split(":")[-1]


def normalize(spec):
    """Un refuerzo del contrato ("husk" o {"mob", "equipo"}) en la forma de jefes.json: {"mob": "minecraft:husk",
    "equipo": {"mainhand": "minecraft:iron_sword"}} (sin "equipo" si no lleva)."""
    if isinstance(spec, str):
        spec = {"mob": spec}
    out = {"mob": nsid(spec["mob"])}
    if spec.get("equipo"):
        out["equipo"] = {slot: nsid(obj) for slot, obj in spec["equipo"].items()}
    return out


def errors(sid, reinforcements):
    """Fallos de una lista REFUERZOS del contrato (vacía si cumple)."""
    pre = f"unicas/{sid}: REFUERZOS"
    if not isinstance(reinforcements, (list, tuple)):
        return [f"{pre} debe ser una lista"]
    errs = []
    if not MIN_REINFORCEMENTS <= len(reinforcements) <= MAX_REINFORCEMENTS:
        errs.append(f"{pre}: {len(reinforcements)} refuerzos (de {MIN_REINFORCEMENTS} a {MAX_REINFORCEMENTS} por fase)")
    for i, spec in enumerate(reinforcements):
        if isinstance(spec, str):
            spec = {"mob": spec}
        if not isinstance(spec, dict) or "mob" not in spec:
            errs.append(f"{pre}[{i}]: ni un id de mob ni {{'mob': ...}}")
            continue
        extra = set(spec) - {"mob", "equipo"}
        if extra:
            errs.append(f"{pre}[{i}]: claves desconocidas {sorted(extra)}")
        mob = _short_name(spec["mob"])
        if mob not in REINFORCEMENT_MOBS or not str(spec["mob"]).removeprefix("minecraft:") == mob:
            errs.append(f"{pre}[{i}]: {spec['mob']} no puede ser refuerzo (jefes.REFUERZO_MOBS)")
        for slot, obj in (spec.get("equipo") or {}).items():
            if slot not in SLOTS:
                errs.append(f"{pre}[{i}]: ranura {slot} no válida ({', '.join(SLOTS)})")
            if any(p in str(obj) for p in FORBIDDEN_ITEMS):
                errs.append(f"{pre}[{i}]: {obj} está prohibido (nada de netherita ni élitros)")
    return errs


def family(mob):
    """Familia de refuerzos del tipo de un guardián (GENERICA si no tiene)."""
    return MOB_FAMILY.get(_short_name(mob), GENERIC)


def reinforcements(sid, mod, guardians):
    """Refuerzos resueltos de una única: los de su REFUERZOS o los de la familia del tipo de su guardián
    (`guardianes`: tipos de mob de sus guardianes, de pack.tag_guardians)."""
    own_items = getattr(mod, "REINFORCEMENTS", None)
    if own_items is not None:
        errs = errors(sid, own_items)
        if errs:
            raise ValueError("; ".join(errs))
        return [normalize(s) for s in own_items]
    mobs = sorted(guardians)
    return [normalize(s) for s in FAMILIES[family(mobs[0]) if mobs else GENERIC]]


def schema(modules, guardians):
    """heraldia/jefes.json: familias (para los guardianes que no se reconozcan) y refuerzos resueltos por única.
    `modules`: [(id, módulo)] de unicas; `guardianes`: {id: {tipo de mob: ...}} (reg.guardianes)."""
    for fam, specs in FAMILIES.items():
        errs = errors(f"(familia {fam})", specs)
        assert not errs, errs
    return {
        "version": VERSION,
        "generica": GENERIC,
        "familias": {fam: [normalize(s) for s in specs] for fam, specs in FAMILIES.items()},
        "mob_familia": {nsid(mob): fam for mob, fam in sorted(MOB_FAMILY.items())},
        "unicas": {sid: reinforcements(sid, mod, guardians.get(sid, {})) for sid, mod in modules},
    }


def lang():
    assert LANG["es_es"].keys() == LANG["en_us"].keys()
    return {k: dict(v) for k, v in LANG.items()}
