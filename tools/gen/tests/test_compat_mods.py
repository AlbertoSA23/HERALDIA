"""tools/smoke/compat_mods.py y tools/smoke/modrinth.py: grupos, catálogo de mods fijados y las funciones puras de la prueba
de compatibilidad (solapes entre inicios de estructura, lectura de regiones, excepciones de Heraldia, «Can't keep up!»)."""
import io, json, os, struct, sys, zipfile, zlib
import nbtlib
import pytest

SMOKE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "smoke")
sys.path.insert(0, SMOKE)
import compat_mods as c  # noqa: E402
import modrinth  # noqa: E402


def test_catalog_pinned():
    for slug, m in modrinth.MODS.items():
        assert m.slug == slug
        assert len(m.sha512) == 128 and int(m.sha512, 16) >= 0, slug
        assert m.url.startswith("https://cdn.modrinth.com/data/") and m.file.endswith(".jar"), slug
    assert not set(modrinth.NO_VERSION) & set(modrinth.MODS)


def test_groups_only_with_mods_pinned_and_chunky():
    assert "base" in c.GROUPS and c.GROUPS["base"] == []
    for g in c.GROUPS:
        mods = c.mods_of(g)
        assert (mods[-1] == "chunky") == (g not in c.NO_CHUNKY) and len(mods) == len(set(mods)), g
        assert "chunky" not in mods[:-1], g
        assert all(p in modrinth.MODS for p in mods), g
    # Tectonic 3 y Terralith no cargan juntos; Distant Horizons y Chunky se cuelgan al arrancar: grupos distintos
    assert not any({"tectonic", "terralith"} <= set(c.mods_of(g)) for g in c.GROUPS)
    assert not any({"distanthorizons", "chunky"} <= set(c.mods_of(g)) for g in c.GROUPS)


def test_fetch_checks_the_sha512(tmp_path, monkeypatch):
    dataset = b"jar de prueba"
    def fake(url, dest):          # como server_smoke.download: no descarga si ya está
        if not os.path.isfile(dest):
            with open(dest, "wb") as f:
                f.write(dataset)
    monkeypatch.setattr(modrinth.s, "download", fake)
    import hashlib
    good = hashlib.sha512(dataset).hexdigest()
    p = modrinth.fetch(str(tmp_path), "x.jar", "https://x", good)
    assert p == os.path.join(str(tmp_path), "modrinth", "x.jar") and open(p, "rb").read() == dataset
    with pytest.raises(SystemExit):
        modrinth.fetch(str(tmp_path), "y.jar", "https://x", "0" * 128)
    assert not os.path.exists(os.path.join(str(tmp_path), "modrinth", "y.jar"))   # la mala no se queda en caché
    # una copia vieja con otro contenido (caché de la CI) se descarga otra vez en vez de fallar
    with open(os.path.join(str(tmp_path), "modrinth", "z.jar"), "wb") as f:
        f.write(b"vieja")
    assert open(modrinth.fetch(str(tmp_path), "z.jar", "https://x", good), "rb").read() == dataset


def box(x0, z0, x1, z1, y0=60, y1=80):
    return (x0, y0, z0, x1, y1, z1)


def test_overlaps_only_heraldia_with_other_visible_mods():
    lst = [
        ("heraldia:castellana", (0, 0), [box(0, 0, 50, 50)]),
        ("towns_and_towers:village_plains", (2, 2), [box(40, 40, 90, 90)]),        # cruza: solape
        ("minecraft:village_plains", (1, 1), [box(10, 10, 30, 30)]),               # vanilla: no cuenta
        ("dungeons_and_taverns:mazmorra", (0, 1), [box(0, 0, 50, 50, 0, 20)]),    # sin cruzarse en altura
        ("explorify:cripta", (1, 0), [box(0, 0, 50, 50)]),                         # subterránea por su paso
        ("structory:ruina", (9, 9), [box(100, 100, 120, 120)]),                    # lejos
        ("otro:a", (5, 5), [box(51, 0, 60, 50)]),                                  # justo al lado
    ]
    got = c.overlaps(lst, {"explorify:cripta": "underground_structures"})
    assert got == [("heraldia:castellana", (0, 0), "towns_and_towers:village_plains", (2, 2))]
    assert c.overlaps([x for x in lst if x[0] != "towns_and_towers:village_plains"]) == \
        [("heraldia:castellana", (0, 0), "explorify:cripta", (1, 0))]   # sin saber el paso, cuenta


def test_mod_steps(tmp_path):
    jar = tmp_path / "m.jar"
    with zipfile.ZipFile(jar, "w") as z:
        z.writestr("data/otro/worldgen/structure/torre.json", json.dumps({"step": "surface_structures"}))
        z.writestr("data/otro/worldgen/structure/sub/mina.json", json.dumps({"step": "minecraft:underground_structures"}))
        z.writestr("data/otro/worldgen/structure/rota.json", "{no es json")
        z.writestr("data/otro/loot_table/x.json", "{}")
    assert c.mod_steps([str(jar)]) == {"otro:torre": "surface_structures", "otro:sub/mina": "underground_structures"}


def test_delays():
    log = ("[10:00:00] [Server thread/WARN]: Can't keep up! Is the server overloaded? Running 2504ms or 50 ticks behind\n"
           "otra línea\n[10:00:09] [Server thread/WARN]: Can't keep up! Is the server overloaded? Running 61000ms or 1220 ticks behind\n")
    assert c.lags(log) == [2504, 61000] and c.lags("") == []


def test_errors_heraldia():
    log = "\n".join([
        "[10:00:00] [Worker/ERROR]: Fallo de otro mod",
        "java.lang.IllegalStateException: algo",
        "\tat com.otro.Mod.run(Mod.java:1)",
        "[10:00:01] [Worker/ERROR]: Couldn't generate",
        "java.lang.NullPointerException: null",
        "\tat net.minecraft.world.level.chunk.ChunkGenerator.handler$zzz000$heraldia$villageRules(ChunkGenerator.java:1)",
        "\tat net.minecraft.Util.run(Util.java:2)",
        "Caused by: java.lang.RuntimeException",
        "\tat io.github.albertosa23.heraldia.common.ForeignZone.occupied(ForeignZone.java:3)",
        "[10:00:02] [Server thread/INFO]: Done",
    ])
    got = c.heraldia_errors(log)
    assert len(got) == 1 and "NullPointerException" in got[0] and "ForeignZone" in got[0]
    assert c.heraldia_errors("[x] [main/INFO]: Heraldia: 87 estructuras registradas") == []


def _region(path, chunks):
    """Región .mca mínima: {(i): nbt} con i = índice del chunk en la región."""
    header, body, sector = bytearray(8192), bytearray(), 2
    for i, nbt in chunks.items():
        buf = io.BytesIO()
        nbt.write(buf)
        dataset = zlib.compress(buf.getvalue())
        block = struct.pack(">IB", len(dataset) + 1, 2) + dataset
        block += b"\0" * (-len(block) % 4096)
        header[i * 4:i * 4 + 4] = (sector << 8 | len(block) // 4096).to_bytes(4, "big")
        body += block
        sector += len(block) // 4096
    with open(path, "wb") as f:
        f.write(bytes(header) + bytes(body))


def test_starts_read_from_regions(tmp_path):
    reg = tmp_path / "world" / "dimensions" / "minecraft" / "overworld" / "region"
    reg.mkdir(parents=True)
    C, L, I = nbtlib.Compound, nbtlib.List, nbtlib.Int
    def start(sid, x, z, bbs):
        return C({"id": nbtlib.String(sid), "ChunkX": I(x), "ChunkZ": I(z),
                  "Children": L[C]([C({"BB": nbtlib.IntArray(bb)}) for bb in bbs])})
    chunk0 = nbtlib.File(C({"structures": C({"starts": C({
        "heraldia:castellana": start("heraldia:castellana", 0, 0, [[0, 60, 0, 30, 80, 30], [31, 60, 0, 50, 70, 10]]),
        "otro:torre": C({"id": nbtlib.String("INVALID")})})})}))
    chunk5 = nbtlib.File(C({"structures": C({"starts": C({"otro:torre": start("otro:torre", 5, 0, [[80, 60, 0, 90, 90, 10]])})})}))
    _region(str(reg / "r.0.0.mca"), {0: chunk0, 5: chunk5, 7: nbtlib.File(C({"Status": nbtlib.String("full")}))})
    got = sorted(c.structure_starts(str(tmp_path / "world")))
    assert got == [("heraldia:castellana", (0, 0), [(0, 60, 0, 30, 80, 30), (31, 60, 0, 50, 70, 10)]),
                   ("otro:torre", (5, 0), [(80, 60, 0, 90, 90, 10)])]
    assert c.overlaps(got) == []
