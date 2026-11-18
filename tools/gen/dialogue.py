"""Villager conversations (P9a): the lines Heraldia villagers say when a player talks to them, and the texts of the chat
around them (buttons, notices). The engine is in Java (dialogue/): it picks a line by context and sends it as a literal
text in the player's language, so it works with vanilla clients and the lines never go into assets/heraldia/lang.

Line files (one folder per language, one file per group, so several sessions can write lines without touching the same
file):

    tools/gen/dialogue/<code>/<group>.json      {"<pool>": {"<id>": "<text>", ...}, ...}

* `es_es` is the reference: its pools and ids are the complete set. Every other language (`en_us` included) has, for each
  group file it ships, exactly the same pools and ids (not one more or fewer) and the same format slots in each line.
  A language may still lack a whole group file: its players then get the English line (and, failing that, the Spanish
  one). The tests (tests/test_dialogue.py) and the generation fail on any other difference.
* A pool is a context: `profession.<id>`, `family.<family>`, `time.<moment>`... (POOLS below). Ids are short and stable
  (`"1"`, `"2"`...): they are what each player's memory of recent lines stores, so a published id is never reused for
  another meaning; to remove a line, remove it in every language.
* Slots (Minecraft format, %1$s...): see SLOTS. A line may use any of its pool's slots, or none.

The generator merges each language into heraldia/dialogos/<code>.json inside the .jar (read by dialogue/Lines in Java).
How to add a line: docs/CONTENT.md, "Villager conversations".
"""
import json
import os

import languages
from themes import FAMILIES

NS = "heraldia"
K = f"{NS}.dialogos"
FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "dialogue")
REFERENCE = "es_es"
# Group files and which pools go in each (a pool belongs to exactly one group).
GROUPS = ("professions", "village")
# Vanilla professions (minecraft:<id>), as Villager.getVillagerData().profession() gives them.
PROFESSIONS = ("none", "armorer", "butcher", "cartographer", "cleric", "farmer", "fisherman", "fletcher",
               "leatherworker", "librarian", "mason", "nitwit", "shepherd", "toolsmith", "weaponsmith")
# Reputation tiers (quests/Reputation.Tier ids, published).
TIERS = ("desconocido", "conocido", "amigo", "heroe")
# Moments of the day (dialogue/Context.moment) and weather (dialogue/Context.weather).
MOMENTS = ("morning", "afternoon", "evening", "night")
WEATHERS = ("clear", "rain", "snow", "thunder")
# Kinds of hint a wayfarer can give (dialogue/Hints): a unique structure, a medium one or a mine entrance.
HINT_KINDS = ("unique", "medium", "mine")

BODY_SLOTS = {1, 2}          # %1$s player's name, %2$s village name
HINT_SLOTS = {1, 2, 3}       # %1$s the place, %2$s the direction ("north"), %3$s approximate distance in blocks


def pools():
    """{pool: (group, allowed slots)}: every pool the engine knows. A file with another pool fails."""
    out = {}
    for p in PROFESSIONS:
        out[f"profession.{p}"] = ("professions", BODY_SLOTS)
    for t in TIERS:
        out[f"greeting.{t}"] = ("village", BODY_SLOTS)
        out[f"reputation.{t}"] = ("village", BODY_SLOTS)
    for f in FAMILIES:
        out[f"family.{f}"] = ("village", BODY_SLOTS)
    for m in MOMENTS:
        out[f"time.{m}"] = ("village", BODY_SLOTS)
    for w in WEATHERS:
        out[f"weather.{w}"] = ("village", BODY_SLOTS)
    for k in HINT_KINDS:
        out[f"hint.{k}"] = ("village", HINT_SLOTS)
    for p in ("general", "rumor", "busy", "farewell", "hint.withheld", "hint.told", "hint.nothing"):
        out[p] = ("village", BODY_SLOTS)
    return out


# Pools that must have at least one line in the reference (the engine always has something to say there).
REQUIRED = ("general", "rumor", "busy", "farewell", "hint.withheld", "hint.told", "hint.nothing",
            *(f"greeting.{t}" for t in TIERS), *(f"hint.{k}" for k in HINT_KINDS))


def route(code, group):
    return os.path.join(FOLDER, code, f"{group}.json")


def load(code, group):
    """{pool: {id: text}} of a file; None if it does not exist."""
    r = route(code, group)
    if not os.path.exists(r):
        return None
    with open(r, encoding="utf-8") as f:
        return json.load(f)


def codes():
    return languages.everyone()


def errors():
    """Everything wrong in the line files (empty if all is well)."""
    e = []
    known = pools()
    ref = {}
    for g in GROUPS:
        data = load(REFERENCE, g)
        if data is None:
            e.append(f"{REFERENCE}: falta el archivo de frases {g}.json")
            continue
        ref[g] = data
    for code in codes():
        for g in GROUPS:
            data = load(code, g)
            if data is None:
                continue
            for pool, lines in data.items():
                if pool not in known:
                    e.append(f"{code}/{g}: el grupo de frases {pool} no existe (dialogue.pools)")
                    continue
                if known[pool][0] != g:
                    e.append(f"{code}/{g}: el grupo de frases {pool} va en {known[pool][0]}.json")
                if not isinstance(lines, dict):
                    e.append(f"{code}/{g}: {pool} debe ser un objeto {{id: frase}}")
                    continue
                for lid, text in lines.items():
                    if not isinstance(text, str) or not text.strip():
                        e.append(f"{code}/{g}: {pool}.{lid} está vacía")
                        continue
                    m = languages.markers(text)
                    if m is None:
                        e.append(f"{code}/{g}: {pool}.{lid} tiene un marcador desconocido: {text!r}")
                    elif not set(m[0]) <= known[pool][1]:
                        e.append(f"{code}/{g}: {pool}.{lid} usa los huecos {m[0]}; en {pool} solo valen {sorted(known[pool][1])}")
            if code == REFERENCE or g not in ref:
                continue
            e += _compare(ref[g], data, f"{code}/{g}")
    for pool in REQUIRED:
        g = known[pool][0]
        if g in ref and not ref[g].get(pool):
            e.append(f"{REFERENCE}/{g}: {pool} necesita al menos una frase")
    return e


def _compare(ref, data, where):
    """Same pools, same ids and the same slots as the reference (the Spanish)."""
    e = []
    for pool, lines in ref.items():
        got = data.get(pool)
        if got is None:
            e.append(f"{where}: falta el grupo de frases {pool} ({len(lines)} frases)")
            continue
        for lid, text in lines.items():
            if lid not in got:
                e.append(f"{where}: falta la frase {pool}.{lid}: {text[:50]!r}")
            elif isinstance(got[lid], str) and languages.markers(got[lid]) != languages.markers(text):
                e.append(f"{where}: {pool}.{lid} usa los huecos {languages.markers(got[lid])}, el español "
                         f"{languages.markers(text)}: {got[lid]!r}")
        for lid in got if isinstance(got, dict) else ():
            if lid not in lines:
                e.append(f"{where}: sobra la frase {pool}.{lid} (no está en el español)")
    for pool in data:
        if pool not in ref:
            e.append(f"{where}: sobra el grupo de frases {pool} (no está en el español)")
    return e


def missing_files():
    """[(code, group)] of the languages that do not ship a group file yet (their players get the English line)."""
    return [(c, g) for c in codes() if c != REFERENCE for g in GROUPS if load(c, g) is None]


def merged(code):
    """{pool: {id: text}} of a language, all its group files together."""
    out = {}
    for g in GROUPS:
        out.update(load(code, g) or {})
    return out


def counts(code=REFERENCE):
    """{pool: number of lines} (for the documentation and the report)."""
    return {p: len(v) for p, v in sorted(merged(code).items())}


# Texts of the chat around the lines (heraldia.dialogos.<key>): (es_es, en_us). The arguments come from the Java
# (dialogue/Dialogue): do not change their order without changing it there.
TEXTS = {
    "linea": ("%s: «%s»", "%s: “%s”"),
    "boton.mas": ("[Seguir hablando]", "[Keep talking]"),
    "boton.rumores": ("[¿Qué se cuenta?]", "[Any news?]"),
    "boton.tratar": ("[Comerciar]", "[Trade]"),
    "boton.adios": ("[Adiós]", "[Goodbye]"),
    "pista.mas": ("Tu brújula y el sol te dirán el resto: es una pista, no un mapa.",
                  "Your compass and the sun will tell you the rest: it is a hint, not a map."),
    "sin_charla": ("No estás hablando con ningún aldeano: haz clic derecho sobre uno de una aldea de Heraldia.",
                   "You are not talking to any villager: right-click one in a Heraldia village."),
    "lejos": ("Te has alejado demasiado: vuelve a hablarle.", "You have walked too far away: talk to them again."),
    "desactivados": ("Las conversaciones con los aldeanos están desactivadas en este servidor.",
                     "Conversations with villagers are disabled on this server."),
    "no_habla": ("Ese no es un aldeano de Heraldia dentro de su aldea: no tiene conversación.",
                 "That is not a Heraldia villager inside its village: it has no conversation."),
    "agacharse": ("Agáchate y haz clic derecho para comerciar directamente.",
                  "Sneak and right-click to trade directly."),
}


def lang():
    out = {"es_es": {}, "en_us": {}}
    for k, (es, en) in TEXTS.items():
        out["es_es"][f"{K}.{k}"], out["en_us"][f"{K}.{k}"] = es, en
    return out


def write(out, jdump):
    """heraldia/dialogos/<code>.json for every language that has lines; fails if any file is wrong."""
    e = errors()
    if e:
        raise SystemExit("Frases de los aldeanos:\n" + "\n".join(e))
    for code in codes():
        data = merged(code)
        if data:
            jdump(out, f"{NS}/dialogos/{code}.json", data)
