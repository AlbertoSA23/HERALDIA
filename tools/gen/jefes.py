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
REFUERZO_MOBS = frozenset({
    "zombie", "husk", "drowned", "zombie_villager", "skeleton", "stray", "bogged", "wither_skeleton",
    "vindicator", "pillager", "witch", "guardian", "spider", "cave_spider",
})
RANURAS = ("mainhand", "offhand", "head", "chest", "legs", "feet")
PROHIBIDOS = ("netherite", "elytra")      # Decisiones de Alberto: nada de netherita en equipo ni élitros
MIN_REFUERZOS, MAX_REFUERZOS = 2, 3

# Familias: refuerzos por defecto según el tipo del guardián.
FAMILIAS = {
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
GENERICA = "generica"
MOB_FAMILIA = {
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


def _corto(mob):
    return str(mob).split(":")[-1]


def normalizar(spec):
    """Un refuerzo del contrato ("husk" o {"mob", "equipo"}) en la forma de jefes.json: {"mob": "minecraft:husk",
    "equipo": {"mainhand": "minecraft:iron_sword"}} (sin "equipo" si no lleva)."""
    if isinstance(spec, str):
        spec = {"mob": spec}
    out = {"mob": nsid(spec["mob"])}
    if spec.get("equipo"):
        out["equipo"] = {ranura: nsid(obj) for ranura, obj in spec["equipo"].items()}
    return out


def errores(sid, refuerzos):
    """Fallos de una lista REFUERZOS del contrato (vacía si cumple)."""
    pre = f"unicas/{sid}: REFUERZOS"
    if not isinstance(refuerzos, (list, tuple)):
        return [f"{pre} debe ser una lista"]
    errs = []
    if not MIN_REFUERZOS <= len(refuerzos) <= MAX_REFUERZOS:
        errs.append(f"{pre}: {len(refuerzos)} refuerzos (de {MIN_REFUERZOS} a {MAX_REFUERZOS} por fase)")
    for i, spec in enumerate(refuerzos):
        if isinstance(spec, str):
            spec = {"mob": spec}
        if not isinstance(spec, dict) or "mob" not in spec:
            errs.append(f"{pre}[{i}]: ni un id de mob ni {{'mob': ...}}")
            continue
        extra = set(spec) - {"mob", "equipo"}
        if extra:
            errs.append(f"{pre}[{i}]: claves desconocidas {sorted(extra)}")
        mob = _corto(spec["mob"])
        if mob not in REFUERZO_MOBS or not str(spec["mob"]).removeprefix("minecraft:") == mob:
            errs.append(f"{pre}[{i}]: {spec['mob']} no puede ser refuerzo (jefes.REFUERZO_MOBS)")
        for ranura, obj in (spec.get("equipo") or {}).items():
            if ranura not in RANURAS:
                errs.append(f"{pre}[{i}]: ranura {ranura} no válida ({', '.join(RANURAS)})")
            if any(p in str(obj) for p in PROHIBIDOS):
                errs.append(f"{pre}[{i}]: {obj} está prohibido (nada de netherita ni élitros)")
    return errs


def familia(mob):
    """Familia de refuerzos del tipo de un guardián (GENERICA si no tiene)."""
    return MOB_FAMILIA.get(_corto(mob), GENERICA)


def refuerzos(sid, mod, guardianes):
    """Refuerzos resueltos de una única: los de su REFUERZOS o los de la familia del tipo de su guardián
    (`guardianes`: tipos de mob de sus guardianes, de pack.tag_guardians)."""
    propios = getattr(mod, "REFUERZOS", None)
    if propios is not None:
        errs = errores(sid, propios)
        if errs:
            raise ValueError("; ".join(errs))
        return [normalizar(s) for s in propios]
    mobs = sorted(guardianes)
    return [normalizar(s) for s in FAMILIAS[familia(mobs[0]) if mobs else GENERICA]]


def schema(modules, guardianes):
    """heraldia/jefes.json: familias (para los guardianes que no se reconozcan) y refuerzos resueltos por única.
    `modules`: [(id, módulo)] de unicas; `guardianes`: {id: {tipo de mob: ...}} (reg.guardianes)."""
    for fam, specs in FAMILIAS.items():
        errs = errores(f"(familia {fam})", specs)
        assert not errs, errs
    return {
        "version": VERSION,
        "generica": GENERICA,
        "familias": {fam: [normalizar(s) for s in specs] for fam, specs in FAMILIAS.items()},
        "mob_familia": {nsid(mob): fam for mob, fam in sorted(MOB_FAMILIA.items())},
        "unicas": {sid: refuerzos(sid, mod, guardianes.get(sid, {})) for sid, mod in modules},
    }


def lang():
    assert LANG["es_es"].keys() == LANG["en_us"].keys()
    return {k: dict(v) for k, v in LANG.items()}
