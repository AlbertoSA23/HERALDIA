"""village_events.py, the events' spoken lines and options: the texts the Java side (events/) asks for exist, in every
language, with the arguments it passes; the kinds and the roles agree with the Java; the light profile turns events off."""
import os
import re

import dialogue
import languages
import options
import village_events as ev

JAVA = os.path.join(os.path.dirname(__file__), "..", "..", "..", "src", "main", "java", "io", "github", "albertosa23",
                    "heraldia", "events")


def _java(name):
    with open(os.path.join(JAVA, name), encoding="utf-8") as f:
        return f.read()


def test_kinds_match_the_java():
    ids = re.findall(r'^\t([A-Z]+)\("([a-z]+)"', _java("Kind.java"), re.M)
    assert [i for _, i in ids] == list(ev.KINDS)
    assert set(dialogue.EVENT_POOLS) == set(ev.KINDS)


def test_every_kind_has_its_texts():
    lang = ev.lang()
    for k in ev.KINDS:
        for part in ("nombre", "anuncio", "fin", "dispersa"):
            key = f"{ev.K}.{k}.{part}"
            assert key in lang["es_es"] and key in lang["en_us"], key
            if part != "nombre":
                # the Java passes one argument: the village's name
                assert lang["es_es"][key].count("%s") == 1 and lang["en_us"][key].count("%s") == 1, key
    for k in ("wedding", "funeral"):
        assert f"{ev.K}.{k}.regalo" in lang["en_us"]


def test_named_figures_match_the_roles():
    java = _java("VillageEvents.java")
    named = re.search(r"case (MERCHANT, CLERIC[A-Z, ]+) -> f\.role\(\)", java).group(1)
    roles = [r.strip().lower() for r in named.split(",")]
    assert roles == ["merchant", "cleric", "bride", "groom", "widow", "musician", "host"]
    for r in roles:
        assert f"{ev.K}.figura.{r}" in ev.lang()["es_es"], r
    all_roles = re.search(r"enum Role \{\s*([A-Z, ]+)\s*\}", _java("Layout.java")).group(1)
    assert set(roles) <= {x.strip().lower() for x in all_roles.split(",")}


def test_the_java_asks_only_for_existing_keys():
    """Every literal "heraldia.eventos." key and every K + "..." suffix the Java uses exists in the texts."""
    java = _java("VillageEvents.java")
    have = set(ev.lang()["es_es"])
    for suffix in re.findall(r'K \+ "([a-z_.]+)"', java):
        if suffix.endswith("."):
            continue                                   # a prefix completed in the Java (figura.<role>): checked above
        assert f"{ev.K}.{suffix}" in have, suffix
    for why in re.findall(r'return "([a-z_]+)";', java):
        assert f"{ev.K}.{why}" in have, why
    for part in re.findall(r'K \+ e\.kind\.id \+ "\.([a-z]+)"', java) + re.findall(r'"\.(fin|dispersa)"', java):
        for k in ev.KINDS:
            if part != "regalo" or k in ("wedding", "funeral"):
                assert f"{ev.K}.{k}.{part}" in have, (k, part)


def test_every_language_has_the_texts():
    for code in languages.TRANSLATIONS:
        data = languages.load_data(code)
        for key, es in ev.lang()["es_es"].items():
            assert key in data, (code, key)
            assert data[key].count("%s") == es.count("%s"), (code, key)


def test_lines_of_every_pool_in_every_language():
    pools = dialogue.pools()
    for code in dialogue.codes():
        data = dialogue.load(code, "events")
        assert data is not None, f"{code}/events.json"
        for kind, moments in dialogue.EVENT_POOLS.items():
            for m in moments:
                pool = f"event.{kind}.{m}"
                assert pools[pool][0] == "events"
                assert len(data[pool]) >= 3, (code, pool)
        for pool in dialogue.EVENT_SEQUENCES:
            assert sorted(data[pool]) == ["1", "2", "3"], (code, pool)


def test_options_and_the_light_profile():
    fixed = {k: (d, lo, hi) for k, d, lo, hi, *_ in options._FIXED}
    assert fixed["eventos.activado"][0] is True, "on by default"
    assert fixed["eventos.frecuencia"][1] == 0, "0: only with the command"
    assert fixed["eventos.espera_minutos"][2] >= 120, "a way to make them much rarer"
    assert fixed["eventos.max_activos"][2] <= 4
    light = options.profiles()["ligero"]
    assert light["eventos.activado"] is False, "the light profile has no events"
    assert not options.is_generation("eventos.activado")
    java = _java("VillageEvents.java")
    for k in ("eventos.activado", "eventos.frecuencia", "eventos.espera_minutos", "eventos.max_activos"):
        assert f'"{k}"' in java, k
