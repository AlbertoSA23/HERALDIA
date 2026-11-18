"""Inhabitants of the medium structures (mediums/_inhabitants.py): who lives where, and the contract that makes them
settle (a bed and a workstation each, walkable without ladders, no free bed to breed)."""
import copy

import pytest

import mediums
from mediums import _inhabitants as inh
from pack import Registry

# Who lives in each variant (professions of the inhabitant villagers, and their animals): the brief's choice, kind by kind.
EXPECTED = {
    "posada": {"a": (["butcher"], ["pig", "pig"]), "b": (["butcher", "farmer"], [])},
    "pescador": {"a": (["fisherman"], []), "b": (["fisherman"], [])},
    "cazadores": {"a": (["leatherworker", "fletcher"], []), "b": (["leatherworker"], [])},
    "molino": {"a": (["farmer"], []), "b": (["farmer"], [])},
    "torre_vigia": {"a": ([], []), "b": (["fletcher"], [])},
    "ermita": {"a": (["librarian"], []), "b": (["librarian"], [])},
}


@pytest.fixture(scope="module")
def reg():
    r = Registry()
    for mid, _ in mediums.modules():
        mediums.build(r, mid)
    assert not r.warnings, r.warnings
    return r


def _living(t):
    vs = [n["VillagerData"]["profession"].split(":")[1] for *_, n in t.entities
          if inh.is_inhabitant(n) and n["id"] == "minecraft:villager"]
    animals = [n["id"].split(":")[1] for *_, n in t.entities if inh.is_inhabitant(n) and n["id"] != "minecraft:villager"]
    return sorted(vs), sorted(animals)


def test_who_lives_where(reg):
    for name, t in reg.templates.items():
        _, mid, style, variant = name.split("/")
        want = EXPECTED.get(mid, {}).get(variant, ([], []))
        assert _living(t) == (sorted(want[0]), sorted(want[1])), name


def test_hostile_and_other_dimensions_have_no_inhabitants(reg):
    """Camps, shrines, the wizard's hut (its own Java) and the Nether and End kinds keep what they had."""
    for name, t in reg.templates.items():
        mid = name.split("/")[1]
        if mid not in EXPECTED:
            assert _living(t) == ([], []), name


def test_one_to_four_per_inhabited_structure(reg):
    for name, t in reg.templates.items():
        vs, animals = _living(t)
        if vs or animals:
            assert 1 <= len(t.entities) <= mediums.MAX_ENTITIES, name
            assert len(vs) <= inh.MAX_VILLAGERS, name


def test_every_template_meets_the_contract(reg):
    for name, t in reg.templates.items():
        assert inh.issues(t) == [], name


def test_villagers_live_with_ai_and_keep_their_trades(reg):
    for name, t in reg.templates.items():
        for *_, n in t.entities:
            if inh.is_inhabitant(n) and n["id"] == "minecraft:villager":
                assert "NoAI" not in n and n["Invulnerable"] == 1 and n["PersistenceRequired"] == 1, name
                assert n["Xp"] > 0, name                       # locked profession: it keeps the template's trades
                assert n["Offers"]["Recipes"], name
                assert n["CustomName"]["translate"].startswith("heraldia.medianas."), name


def test_old_figures_are_marked_still_before(reg):
    """The traders that were still figures before carry STILL_BEFORE (still again with the option off); the new ones do not."""
    before = {("posada", "butcher"), ("pescador", "fisherman"), ("cazadores", "leatherworker"), ("molino", "farmer")}
    for name, t in reg.templates.items():
        _, mid, _, variant = name.split("/")
        for *_, n in t.entities:
            if inh.is_inhabitant(n) and n["id"] == "minecraft:villager":
                prof = n["VillagerData"]["profession"].split(":")[1]
                was = (mid, prof) in before and (variant == "a" or mid == "posada")
                assert (inh.STILL_BEFORE in n["Tags"]) == was, (name, prof)
                assert inh.SEEN not in n["Tags"], name           # only the mod sets it


def test_animals_without_name_or_anchor(reg):
    import core
    for name, t in reg.templates.items():
        for *_, n in t.entities:
            if inh.is_inhabitant(n) and n["id"] != "minecraft:villager":
                assert "CustomName" not in n and core.ANCHORED_TAG not in n["Tags"], name


def _tower(reg):
    return copy.deepcopy(reg.templates["medianas/torre_vigia/colinas/b"])


def test_bed_only_by_ladder_does_not_count(reg):
    t = _tower(reg)
    for p, (st, _) in list(t.blocks.items()):
        if "_bed" in st and p[1] == 1:
            t.blocks[p] = ("minecraft:air", None)
    errs = inh.issues(t)
    assert any("without ladders" in e for e in errs), errs      # the upstairs bed (y = 6) is only reached by the ladder


def test_missing_workstation(reg):
    t = _tower(reg)
    for p, (st, _) in list(t.blocks.items()):
        if "fletching_table" in st:
            t.blocks[p] = ("minecraft:air", None)
    assert any("fletching_table" in e for e in inh.issues(t))


def test_two_villagers_one_workstation(reg):
    t = copy.deepcopy(reg.templates["medianas/cazadores/nieve/a"])
    for p, (st, _) in list(t.blocks.items()):
        if "fletching_table" in st:
            t.blocks[p] = ("minecraft:air", None)
    assert any("fletcher" in e for e in inh.issues(t))


def test_free_bed_for_two_lets_them_breed(reg):
    t = copy.deepcopy(reg.templates["medianas/cazadores/nieve/a"])
    t.blocks[(12, 1, 9)] = ("minecraft:white_bed[facing=west,occupied=false,part=head]", None)
    t.blocks[(13, 1, 9)] = ("minecraft:white_bed[facing=west,occupied=false,part=foot]", None)
    assert any("breed" in e for e in inh.issues(t))


def test_too_many_villagers(reg):
    t = copy.deepcopy(reg.templates["medianas/posada/llanura/b"])
    x, y, z, n = t.entities[0]
    t.entities.append((x, y, z, copy.deepcopy(n)))
    assert any("maximum" in e for e in inh.issues(t))


def test_inhabitant_without_ai_or_villager_with_ai_untagged(reg):
    t = copy.deepcopy(reg.templates["medianas/molino/llanura/a"])
    (x, y, z, n) = next(e for e in t.entities if e[3]["id"] == "minecraft:villager")
    n["NoAI"] = 1
    assert any("NoAI" in e for e in inh.issues(t))
    del n["NoAI"]
    n["Tags"] = [g for g in n["Tags"] if g != inh.TAG]
    assert any("without" in e and inh.TAG in e for e in inh.issues(t))


def test_named_animal_would_be_anchored(reg):
    t = copy.deepcopy(reg.templates["medianas/posada/llanura/a"])
    pig = next(n for *_, n in t.entities if n["id"] == "minecraft:pig")
    pig["CustomName"] = {"translate": "heraldia.medianas.posada.cerdo"}
    assert any("anchor" in e for e in inh.issues(t))


def test_workstations_match_vanilla():
    """Each profession used here has its 26.3 workstation (PoiTypes)."""
    assert inh.WORKSTATION["butcher"] == ("smoker",) and inh.WORKSTATION["farmer"] == ("composter",)
    assert inh.WORKSTATION["fisherman"] == ("barrel",) and inh.WORKSTATION["fletcher"] == ("fletching_table",)
    assert "cauldron" in inh.WORKSTATION["leatherworker"] and inh.WORKSTATION["librarian"] == ("lectern",)
