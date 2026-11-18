"""Contract of the guardians' reinforcements (jefes.py, REFUERZOS of each unique structure) and the schema heraldia/jefes.json
read by the Java (comun/jefes). Without generating the datapack."""
import types
import pytest
import bosses
import options
import uniques
import writer

MODS = uniques.modules()
IDS = [sid for sid, _ in MODS]
# Mob type of the final guardian of each unique structure (what pack.tag_guardians leaves in reg.guardianes), for the schema.
GUARDIANS = {sid: {"minecraft:zombie": "minecraft:entities/zombie"} for sid in IDS}


def mod(**kw):
    return types.SimpleNamespace(**kw)


@pytest.mark.parametrize("sid, m", MODS, ids=IDS)
def test_reinforcements_of_each_unique_comply(sid, m):
    own_items = getattr(m, "REINFORCEMENTS", None)
    if own_items is not None:
        assert bosses.errors(sid, own_items) == []
    out = bosses.reinforcements(sid, m, GUARDIANS[sid])
    assert bosses.MIN_REINFORCEMENTS <= len(out) <= bosses.MAX_REINFORCEMENTS
    for r in out:
        assert r["mob"].startswith("minecraft:") and r["mob"].split(":")[1] in bosses.REINFORCEMENT_MOBS


def test_families_meet_and_cover_the_guardians():
    for fam, specs in bosses.FAMILIES.items():
        assert bosses.errors(fam, specs) == [], fam
    assert set(bosses.MOB_FAMILY.values()) <= set(bosses.FAMILIES)
    assert bosses.GENERIC in bosses.FAMILIES
    # the guardian types of today (piezas.guardian and the Atlantis boss) have their own family
    for mob in ("zombie", "husk", "drowned", "skeleton", "stray", "bogged", "wither_skeleton", "evoker",
                "vindicator", "elder_guardian"):
        assert bosses.family(mob) != bosses.GENERIC, mob
        assert bosses.family("minecraft:" + mob) == bosses.family(mob)


def test_family_unknown_es_the_generic():
    assert bosses.family("minecraft:creeper") == bosses.GENERIC
    out = bosses.reinforcements("x", mod(), {"minecraft:creeper": "t"})
    assert out == [bosses.normalize(s) for s in bosses.FAMILIES[bosses.GENERIC]]
    assert bosses.reinforcements("x", mod(), {}) == out       # without a known guardian, too


def test_without_own_reinforcements_uses_the_guardian_family():
    assert bosses.reinforcements("x", mod(), {"minecraft:husk": "t"}) == [{"mob": "minecraft:husk"}] * 2
    assert bosses.reinforcements("x", mod(), {"minecraft:elder_guardian": "t"}) == [{"mob": "minecraft:guardian"}] * 2
    assert [r["mob"] for r in bosses.reinforcements("x", mod(), {"minecraft:evoker": "t"})] == ["minecraft:vindicator",
                                                                                       "minecraft:pillager"]


def test_own_reinforcements_override_the_family():
    m = mod(REINFORCEMENTS=["witch", {"mob": "minecraft:vindicator", "equipo": {"mainhand": "iron_axe"}}])
    assert bosses.reinforcements("x", m, {"minecraft:husk": "t"}) == [
        {"mob": "minecraft:witch"}, {"mob": "minecraft:vindicator", "equipo": {"mainhand": "minecraft:iron_axe"}}]


@pytest.mark.parametrize("bad, fragment", [
    (["zombie"], "1 reinforcements"),
    (["zombie"] * 4, "4 reinforcements"),
    (["zombie", "hoglin"], "hoglin cannot be a reinforcement"),
    (["zombie", "wither"], "wither cannot be a reinforcement"),
    (["zombie", "vex"], "vex cannot be a reinforcement"),
    (["zombie", "heraldia:zombie"], "heraldia:zombie cannot be a reinforcement"),
    (["zombie", {"mob": "zombie", "equipo": {"mainhand": "netherite_sword"}}], "is forbidden"),
    (["zombie", {"mob": "zombie", "equipo": {"chest": "elytra"}}], "is forbidden"),
    (["zombie", {"mob": "zombie", "equipo": {"espalda": "stick"}}], "slot espalda is not valid"),
    (["zombie", {"mob": "zombie", "nombre": "x"}], "claves desconocidas"),
    (["zombie", {"equipo": {}}], "ni un id"),
    ("zombie", "debe ser una lista"),
])
def test_errors_of_the_contract(bad, fragment):
    errs = bosses.errors("x", bad)
    assert any(fragment in e for e in errs), errs
    if isinstance(bad, list):
        with pytest.raises(ValueError):
            bosses.reinforcements("x", mod(REINFORCEMENTS=bad), {})


def test_normalize():
    assert bosses.normalize("husk") == {"mob": "minecraft:husk"}
    assert bosses.normalize({"mob": "minecraft:husk", "equipo": {}}) == {"mob": "minecraft:husk"}
    assert bosses.normalize({"mob": "husk", "equipo": {"offhand": "shield"}}) == {
        "mob": "minecraft:husk", "equipo": {"offhand": "minecraft:shield"}}


def test_schema():
    s = bosses.schema(MODS, GUARDIANS)
    assert s["version"] == bosses.VERSION and s["generica"] == bosses.GENERIC
    assert sorted(s["unicas"]) == IDS
    assert set(s["familias"]) == set(bosses.FAMILIES)
    assert all(k.startswith("minecraft:") and v in s["familias"] for k, v in s["mob_familia"].items())
    for specs in list(s["unicas"].values()) + list(s["familias"].values()):
        assert all(set(r) <= {"mob", "equipo"} for r in specs)
    # a unique structure with its own REFUERZOS carries them as they are, without looking at its guardian
    with_it = [sid for sid, m in MODS if hasattr(m, "REINFORCEMENTS")]
    assert with_it, "no unique structure with its own REFUERZOS"
    for sid in with_it:
        assert s["unicas"][sid] == [bosses.normalize(r) for r in dict(MODS)[sid].REINFORCEMENTS]


def test_texts_and_options():
    lang = bosses.lang()
    assert lang["es_es"].keys() == lang["en_us"].keys()
    for phase in (2, 3):
        for suf in ("", ".refuerzos"):
            k = f"heraldia.jefes.fase.{phase}{suf}"
            assert lang["es_es"][k].count("%s") == 1 and lang["en_us"][k].count("%s") == 1
    assert "heraldia.jefes.refuerzos" in lang["es_es"]
    # in the mod's language (and so in the Spanish fallback of clients without the mod)
    assert all(writer.LANG["es_es"][k] == v for k, v in lang["es_es"].items())
    keys = {o["clave"]: o for o in options.schema()["opciones"]}
    for k in ("jefes.fases.activado", "jefes.refuerzos.activado", "jefes.barra.activado"):
        assert keys[k]["defecto"] is True and keys[k]["seccion"] == "jefes"
