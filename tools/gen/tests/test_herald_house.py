"""The Herald's House (herald_house.py): the template keeps what casa_heraldo.json promises, it fits the brief (96 x 96,
a bell, the job board reused, beds and workstations for every villager, eight empty stalls, return barrels, an unlit
portal frame, gates on every side), nothing burns, the generic audit passes and the sign lines fit."""
import pytest

import board
import herald_house as h
import lint


@pytest.fixture(scope="module")
def t():
    return h.construct()


def test_template_keeps_its_promises(t):
    assert h.errors(t) == []


def test_size_is_96_by_96(t):
    sx, sy, sz = t.size()
    assert (sx, sz) == (96, 96)
    assert h.dataset(t)["tamano"] == [sx, sy, sz]


def test_generic_audit(t):
    assert lint.template_issues(t) == []


def test_portal_is_not_lit(t):
    names = {h._name(st) for st, _ in t.blocks.values()}
    assert "nether_portal" not in names and "fire" not in names
    assert "obsidian" in names


def test_job_board_is_the_villages_one(t):
    b = board.piece(h.THEME, "x")
    lectern = next(st for st, nbt in b.blocks.values() if st.startswith("minecraft:lectern"))
    bx, by, bz = h.BOARD
    assert t.get(bx, by, bz) == lectern
    assert any(n.get("Tags") and board.TAG_CONSTABLE in n["Tags"] for *_, n in t.entities)


def test_every_villager_is_a_heraldia_villager_with_its_own_trade(t):
    villagers = [n for *_, n in t.entities if n["id"] == "minecraft:villager" and board.TAG_CONSTABLE not in n["Tags"]]
    assert len(villagers) == len(t.villagers) == 11
    assert all("heraldia" in n["Tags"] for n in villagers)
    assert len({n["VillagerData"]["profession"] for n in villagers}) == len(villagers)


def test_house_entities_are_tagged(t):
    # Building.finish keeps the house's own entities (HeraldHouse.HOUSE_TAG) where the template puts them
    assert t.entities and all(h.HOUSE_TAG in n.get("Tags", []) for *_, n in t.entities)


def test_stalls_are_empty_boxes_with_a_sign(t):
    d = h.dataset(t)
    assert [s["id"] for s in d["puestos"]] == list(range(1, 9))
    for s in d["puestos"]:
        (x0, y0, z0), (x1, y1, z1) = s["caja"]
        assert (x1 - x0, y1 - y0, z1 - z0) == (2, 2, 2)


def test_dock_template():
    dk = h.dock()
    w, length = h.DOCK_SIZE
    assert dk.size()[0] == w and dk.size()[2] == length


def test_sign_texts_fit():
    assert h.text_errors() == []


def test_texts_are_paired():
    out = h.lang()
    assert out["es_es"].keys() == out["en_us"].keys()
    assert out["en_us"]["heraldia.casa_heraldo.nombre"] == "The Herald's House"
    assert out["es_es"]["heraldia.casa_heraldo.nombre"] == "La Casa del Heraldo"
