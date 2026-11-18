"""Bosses: phases and reinforcements of the final guardians of the unique structures (server side, comun/jefes in Java).

The Java side moves a guardian (tag heraldia_guardian) to the next phase when it drops below 66 % and 33 % health and calls its
reinforcements once per phase. Which reinforcements each guardian calls comes from here, in heraldia/bosses.json (inside the .jar):

(Optional) contract of each unicas/ module:
  REINFORCEMENTS = ["husk", {"mob": "husk", "equipo": {"mainhand": "iron_sword"}}]   # 2 or 3 mobs from REINFORCEMENT_MOBS
Without REINFORCEMENTS, those of the family of its guardian's type (MOB_FAMILY -> FAMILIES); a type with no family, GENERIC.
Guardians in an already generated world that are not recognized (without heraldia_guardian.<id>) also use the family of their
type: that is why bosses.json carries the families in addition to what is already resolved per unique structure.

Rules (generation fails): 2-3 reinforcements, hostile mobs from REINFORCEMENT_MOBS (no bosses, nor hoglins or zoglins, which
spawn as babies; nor vex, which die on their own), equipment in valid slots and no netherite or elytra.
"""

VERSION = 1
# Mobs that can be reinforcements: hostile, guaranteed adults (zombies with heraldia_adulto) and no bosses.
REINFORCEMENT_MOBS = frozenset({
    "zombie", "husk", "drowned", "zombie_villager", "skeleton", "stray", "bogged", "wither_skeleton",
    "vindicator", "pillager", "witch", "guardian", "spider", "cave_spider",
})
SLOTS = ("mainhand", "offhand", "head", "chest", "legs", "feet")
FORBIDDEN_ITEMS = ("netherite", "elytra")      # Owner's decisions: no netherite in equipment or elytra
MIN_REINFORCEMENTS, MAX_REINFORCEMENTS = 2, 3

# Families: default reinforcements according to the guardian's type.
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
    """Namespaced id (minecraft: if it has none): reinforcements and their equipment are always vanilla."""
    s = str(s)
    return s if ":" in s else "minecraft:" + s


def _short_name(mob):
    return str(mob).split(":")[-1]


def normalize(spec):
    """A contract reinforcement ("husk" or {"mob", "equipo"}) in the bosses.json form: {"mob": "minecraft:husk",
    "equipo": {"mainhand": "minecraft:iron_sword"}} (without "equipo" if it has none)."""
    if isinstance(spec, str):
        spec = {"mob": spec}
    out = {"mob": nsid(spec["mob"])}
    if spec.get("equipo"):
        out["equipo"] = {slot: nsid(obj) for slot, obj in spec["equipo"].items()}
    return out


def errors(sid, reinforcements):
    """Failures of a contract REINFORCEMENTS list (empty if it complies)."""
    pre = f"unicas/{sid}: REFUERZOS"
    if not isinstance(reinforcements, (list, tuple)):
        return [f"{pre} debe ser una lista"]
    errs = []
    if not MIN_REINFORCEMENTS <= len(reinforcements) <= MAX_REINFORCEMENTS:
        errs.append(f"{pre}: {len(reinforcements)} reinforcements ({MIN_REINFORCEMENTS} to {MAX_REINFORCEMENTS} per phase)")
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
            errs.append(f"{pre}[{i}]: {spec['mob']} cannot be a reinforcement (jefes.REFUERZO_MOBS)")
        for slot, obj in (spec.get("equipo") or {}).items():
            if slot not in SLOTS:
                errs.append(f"{pre}[{i}]: slot {slot} is not valid ({', '.join(SLOTS)})")
            if any(p in str(obj) for p in FORBIDDEN_ITEMS):
                errs.append(f"{pre}[{i}]: {obj} is forbidden (no netherite or elytra)")
    return errs


def family(mob):
    """Reinforcement family of a guardian's type (GENERIC if it has none)."""
    return MOB_FAMILY.get(_short_name(mob), GENERIC)


def reinforcements(sid, mod, guardians):
    """Resolved reinforcements of a unique structure: those from its REINFORCEMENTS or those of the family of its guardian's type
    (`guardians`: mob types of its guardians, from pack.tag_guardians)."""
    own_items = getattr(mod, "REINFORCEMENTS", None)
    if own_items is not None:
        errs = errors(sid, own_items)
        if errs:
            raise ValueError("; ".join(errs))
        return [normalize(s) for s in own_items]
    mobs = sorted(guardians)
    return [normalize(s) for s in FAMILIES[family(mobs[0]) if mobs else GENERIC]]


def schema(modules, guardians):
    """heraldia/bosses.json: families (for guardians that are not recognized) and reinforcements resolved per unique structure.
    `modules`: [(id, module)] of unicas; `guardians`: {id: {mob type: ...}} (reg.guardianes)."""
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
