"""Inhabitants of the medium structures: villagers who live there (AI on, a bed and a workstation each) and their animals.

The medium structures used to hold, at most, a still villager (NoAI) with fixed trades: a figure behind the counter. Now
the innkeeper, the miller, the fisherman, the hunters, the lookout and the hermit live in their building: they sleep in
their bed, go to their workstation in the morning and wander about it during the day, with vanilla AI and nothing of
Heraldia running every tick. What the game needs for that (and what `issues` checks on every template):
- a bed and a workstation of the villager's profession per villager, inside the template, that the villager can walk to
  from where it spawns WITHOUT ladders (the villagers' path-finder does not climb them) and close together
  (BED_JOB_MAX blocks: the game looks for them among the 5 nearest free ones within 48 blocks);
- at most MAX_VILLAGERS villagers and no more beds within their reach than villagers: no free bed, no breeding, and
  under the iron golem summoning count, so the population never grows on its own (the cost stays fixed);
- the profession is locked (Xp > 0) and the trades are the template's fixed ones, as before; Invulnerable stays on (alone in
  the wild, the first night's zombies would empty the building).
Every inhabitant carries TAG (and the villagers that were already in the structure before, as still figures, STILL_BEFORE
too): with medianas.habitantes off (and in the light profile) the mod (inhabitants/Inhabitants.java) removes the new
ones and leaves the old ones still, as before, when they first load. An inhabitant that has loaded once carries SEEN and is
never touched again: changing the option does not change what a world already has.
update/MobFixes skips TAG: its "marcas" fix anchors any persistent mob with a heraldia.* name, and an anchored farmer
could not pick up the seeds it needs to replant."""
from core import B, F, NS

TAG = "heraldia_habitante"
STILL_BEFORE = "heraldia_habitante.quieto_antes"     # was a still figure (NoAI) before: still again with the option off
SEEN = "heraldia_habitante.visto"                  # set by the mod on first load (never by the generator)
MAX_VILLAGERS = 2
BED_JOB_MAX = 12                                   # blocks between the villager's spawn, its bed and its workstation

# Workstation of each profession (vanilla PoiTypes, 26.3).
WORKSTATION = {
    "armorer": ("blast_furnace",), "butcher": ("smoker",), "cartographer": ("cartography_table",),
    "cleric": ("brewing_stand",), "farmer": ("composter",), "fisherman": ("barrel",), "fletcher": ("fletching_table",),
    "leatherworker": ("cauldron", "water_cauldron", "lava_cauldron", "powder_snow_cauldron"), "librarian": ("lectern",),
    "mason": ("stonecutter",), "shepherd": ("loom",), "toolsmith": ("smithing_table",), "weaponsmith": ("grindstone",),
}


def villager(mid, key, fallback, profession, kind, offers, rot=0.0, still_before=False):
    """A villager who lives in the structure: like _common.villager (name, fixed trades, invulnerable) but with AI."""
    from . import _common as c
    tags = [TAG] + ([STILL_BEFORE] if still_before else [])
    return {"id": "minecraft:villager", "PersistenceRequired": B(1), "Invulnerable": B(1),
            "CustomName": c.text(mid, key, fallback), "CustomNameVisible": B(1),
            "VillagerData": {"profession": f"minecraft:{profession}", "level": 2, "type": f"minecraft:{kind}"},
            "Xp": 10, "Rotation": [F(rot), F(0.0)], "Offers": {"Recipes": offers}, "Tags": tags}


def animal(kind, rot=0.0, **extra):
    """A farm animal of the structure, free to move inside its pen: persistent, without a name (a heraldia.* name would make
    update/MobFixes anchor it) and with TAG."""
    n = {"id": f"minecraft:{kind}", "PersistenceRequired": B(1), "Rotation": [F(rot), F(0.0)], "Tags": [TAG]}
    n.update(extra)
    return n


def is_inhabitant(n):
    return TAG in (n.get("Tags") or [])


def _name(st):
    return st.split("[")[0].replace("minecraft:", "")


def _cell(p):
    return tuple(int(v // 1) for v in p)


def _no_ladders(t):
    """A copy of the template without ladders: what a villager can walk (the path-finder does not climb)."""
    from core import Template
    u = Template(t.name + "#sin_escaleras")
    u.blocks = {p: (("minecraft:air", None) if _name(st) == "ladder" else (st, nbt)) for p, (st, nbt) in t.blocks.items()}
    u.jigsaws, u.entities = t.jigsaws, []
    return u


def _beside(cells, x, y, z):
    """Is there a walkable cell next to the block (x, y, z), at its height or one below/above (a bed, a counter)?"""
    return any((x + dx, y + dy, z + dz) in cells for dx, dz in ((1, 0), (-1, 0), (0, 1), (0, -1)) for dy in (0, -1, 1))


def issues(t):
    """Contract of the inhabitants of a template (empty list = fine)."""
    import lint
    errs = []
    villagers = [((x, y, z), n) for x, y, z, n in t.entities if n["id"] == "minecraft:villager"]
    living = [(p, n) for p, n in villagers if is_inhabitant(n)]
    for p, n in villagers:
        if not is_inhabitant(n) and not n.get("NoAI"):
            errs.append(f"villager at {p} with AI and without {TAG}: it would not be counted or switched off with the option")
    for p, n in villagers:
        if is_inhabitant(n) and n.get("NoAI"):
            errs.append(f"inhabitant at {p} with NoAI: an inhabitant lives there (AI on)")
    for *_, n in t.entities:
        if is_inhabitant(n) and n.get("CustomName") and n["id"] != "minecraft:villager":
            errs.append(f"{n['id']} inhabitant with a name: update/MobFixes would anchor it")
    if len(living) > MAX_VILLAGERS:
        errs.append(f"{len(living)} inhabitant villagers (maximum {MAX_VILLAGERS})")
    if not living:
        return errs
    cells = set(lint.walk(_no_ladders(t)))
    beds = [p for p, (st, _) in t.blocks.items() if _name(st).endswith("_bed") and "part=head" in st]
    reach_beds = [b for b in beds if _beside(cells, *b)]
    if len(reach_beds) < len(living):
        errs.append(f"{len(living)} inhabitant villagers and {len(reach_beds)} beds they can walk to without ladders")
    if len(reach_beds) > len(living) and len(living) > 1:
        errs.append(f"{len(reach_beds)} reachable beds for {len(living)} villagers: a free bed lets them breed")
    used_jobs = set()
    for p, n in living:
        prof = n["VillagerData"]["profession"].split(":")[1]
        x, y, z = _cell(p)
        if not any((x, yy, z) in cells for yy in (y, y + 1)):
            errs.append(f"inhabitant {prof} at {p}: it spawns where it cannot walk")
            continue
        jobs = [q for q, (st, _) in t.blocks.items() if _name(st) in WORKSTATION.get(prof, ()) and q not in used_jobs
                and _beside(cells, *q)]
        near = [q for q in jobs if max(abs(q[0] - x), abs(q[2] - z)) <= BED_JOB_MAX]
        if not near:
            errs.append(f"inhabitant {prof} at {p}: no {WORKSTATION.get(prof)} it can walk to within {BED_JOB_MAX} blocks")
        else:
            used_jobs.add(min(near, key=lambda q: abs(q[0] - x) + abs(q[2] - z)))
        if not any(max(abs(b[0] - x), abs(b[2] - z)) <= BED_JOB_MAX for b in reach_beds):
            errs.append(f"inhabitant {prof} at {p}: no bed it can walk to within {BED_JOB_MAX} blocks")
    return errs
