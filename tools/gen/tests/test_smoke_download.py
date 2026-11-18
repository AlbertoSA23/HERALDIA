"""tools/smoke/server_smoke.py: test server downloads (a cut-off download is not left in the cache) and the pure
functions of tools/smoke/existing_world.py (reading sections and comparing saved chunks)."""
import io, os, sys, zipfile
import pytest

SMOKE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "smoke")
_path = list(sys.path)      # tools/smoke only while importing (see test_compat_mods.py)
sys.path.insert(0, SMOKE)
import server_smoke as s  # noqa: E402
import existing_world as me  # noqa: E402
sys.path[:] = _path


def _jar():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("fabric.mod.json", "{}" * 2000)
    return b.getvalue()


class _Resp(io.BytesIO):
    def __init__(self, data, length):
        super().__init__(data)
        self.headers = {"Content-Length": str(length)}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_valid_jar(tmp_path):
    good, truncated = tmp_path / "a.jar", tmp_path / "b.jar"
    good.write_bytes(_jar())
    truncated.write_bytes(_jar()[:200])
    assert s.valid_jar(str(good))
    assert not s.valid_jar(str(truncated))
    assert not s.valid_jar(str(tmp_path / "no.jar"))


def test_download_cut_gets_repeats(tmp_path, monkeypatch):
    jar = _jar()
    answers = [_Resp(jar[:300], len(jar)), _Resp(jar, len(jar))]       # the first one, cut by the network
    monkeypatch.setattr(s.urllib.request, "urlopen", lambda url: answers.pop(0))
    monkeypatch.setattr(s.time, "sleep", lambda t: None)
    dest = tmp_path / "fabric-api.jar"
    s.download("https://ejemplo/fabric-api.jar", str(dest))
    assert dest.read_bytes() == jar and not answers


def test_corrupt_jar_in_cache_is_redownloaded(tmp_path, monkeypatch):
    jar = _jar()
    dest = tmp_path / "fabric-api.jar"
    dest.write_bytes(jar[:300])                       # what an earlier run left
    monkeypatch.setattr(s.urllib.request, "urlopen", lambda url: _Resp(jar, len(jar)))
    s.download("https://ejemplo/fabric-api.jar", str(dest))
    assert dest.read_bytes() == jar


def test_download_always_cut_fails(tmp_path, monkeypatch):
    jar = _jar()
    monkeypatch.setattr(s.urllib.request, "urlopen", lambda url: _Resp(jar[:300], len(jar)))
    monkeypatch.setattr(s.time, "sleep", lambda t: None)
    with pytest.raises(SystemExit):
        s.download("https://ejemplo/fabric-api.jar", str(tmp_path / "x.jar"), attempts=2)
    assert not (tmp_path / "x.jar").exists()


# ------------------------------------------------------------------ mundo_existente.py
def _build_section(palette, indices):
    """block_states of a section with `paleta` (names) and `indices` (4096), packed like the game."""
    bits = max(4, (len(palette) - 1).bit_length())
    per, data = 64 // bits, []
    for i in range(0, 4096, per):
        v = 0
        for k, idx in enumerate(indices[i:i + per]):
            v |= idx << (k * bits)
        data.append(v - (1 << 64) if v >= 1 << 63 else v)
    return {"palette": [{"Name": n} for n in palette], "data": data}


def test_states_of_a_section():
    assert me.states(None) is None
    assert me.states({"palette": [{"Name": "minecraft:air"}]}) == [("minecraft:air", ())] * 4096
    ind = [i % 3 for i in range(4096)]
    sty = me.states(_build_section(["minecraft:air", "minecraft:stone", "minecraft:dirt"], ind))
    assert len(sty) == 4096 and sty[0][0] == "minecraft:air" and sty[4095][0] == ["minecraft:air", "minecraft:stone", "minecraft:dirt"][4095 % 3]
    # 17 states: 5 bits, 12 per long (not split across two)
    pal = [f"minecraft:b{i}" for i in range(17)]
    ind = [(i * 7) % 17 for i in range(4096)]
    assert [e[0] for e in me.states(_build_section(pal, ind))] == [pal[i] for i in ind]


def _footprint(palette, indices, be=None):
    return me.footprint({"sections": [{"Y": 0, "block_states": _build_section(palette, indices), "biomes": {"palette": ["minecraft:plains"]}}],
                      "block_entities": be or [], "Heightmaps": {}, "structures": {"References": {}, "starts": {}},
                      "LastUpdate": 5, "InhabitedTime": 9, "Status": "minecraft:full"})


def test_same_section_with_another_palette_does_not_change():
    ind = [i % 2 for i in range(4096)]
    a = _footprint(["minecraft:air", "minecraft:stone"], ind)
    b = _footprint(["minecraft:stone", "minecraft:air"], [1 - i for i in ind])
    assert me.differences(a, b) == []


def test_a_changed_block_is_detected():
    ind = [0] * 4096
    a = _footprint(["minecraft:air", "minecraft:stone"], ind)
    ind2 = list(ind)
    ind2[(5 << 8) | (3 << 4) | 2] = 1                  # x=2, y=5, z=3
    d = me.differences(a, _footprint(["minecraft:air", "minecraft:stone"], ind2))
    assert len(d) == 1 and "1 bloques cambian" in d[0] and "x=2 y=5 z=3" in d[0] and "minecraft:stone" in d[0]


def test_blocks_with_data_and_fields_volatile():
    ind = [0] * 4096
    place_chest = {"id": "minecraft:chest", "x": 1, "y": 2, "z": 3, "LootTable": "heraldia:unicas/x"}
    a = _footprint(["minecraft:air"], ind, [place_chest])
    assert me.differences(a, _footprint(["minecraft:air"], ind, [dict(place_chest, keepPacked=1)])) == []
    d = me.differences(a, _footprint(["minecraft:air"], ind, [dict(place_chest, LootTable="heraldia:otra")]))
    assert len(d) == 1 and "LootTable" in d[0]
    assert me.differences(a, _footprint(["minecraft:air"], ind)) != []


def test_chain_palette_of_26_3():
    ind = [i % 2 for i in range(4096)]
    sec = _build_section(["minecraft:air", "minecraft:stone"], ind)
    sec["palette"] = ["minecraft:air", "minecraft:stone"]               # as 26.3 stores it
    assert [e[0] for e in me.states(sec)] == [["minecraft:air", "minecraft:stone"][i] for i in ind]


def test_mixed_list_of_26_3():
    mixed = [{"": "minecraft:air"}, {"id": "minecraft:oak_log", "properties": {"axis": "y"}}]
    assert me._blueprint(mixed) == ["minecraft:air", {"id": "minecraft:oak_log", "properties": {"axis": "y"}}]
    sec = {"palette": me._blueprint(mixed), "data": [0x10]}                 # index 0 and then 1
    sty = me.states(sec)
    assert sty[0] == ("minecraft:air", ()) and sty[1] == ("minecraft:oak_log", (("axis", "y"),))


def test_forceload_pieces_of_256_chunks():
    C = {(x, z) for x in range(-10, 12) for z in range(-90, -68)}         # 22 x 22 = 484 chunks
    t = me.fragments(C)
    assert all(((x1 - x0 + 1) // 16) * ((z1 - z0 + 1) // 16) <= 256 for x0, z0, x1, z1 in t)
    roofed_set = {(x // 16, z // 16) for x0, z0, x1, z1 in t for x in range(x0, x1 + 1, 16) for z in range(z0, z1 + 1, 16)}
    assert roofed_set == C
