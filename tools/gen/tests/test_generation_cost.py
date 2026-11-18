"""tools/smoke/generation_cost.py: pure functions of the generation cost test (percentiles, JFR durations,
Chunky zones, per-chunk summary, aggregate of passes, overhead, comparison with the reference and the Markdown)."""
import json, os, sys
import pytest

SMOKE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "smoke")
sys.path.insert(0, SMOKE)
import generation_cost as c  # noqa: E402


def test_percentile_interpolated():
    assert c.percentile([], 50) is None
    assert c.percentile([7], 99) == 7
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert c.percentile(v, 0) == 1 and c.percentile(v, 100) == 10
    assert c.percentile(v, 50) == pytest.approx(5.5)
    assert c.percentile(v, 90) == pytest.approx(9.1)
    assert c.percentile(list(reversed(v)), 90) == pytest.approx(9.1)      # does not depend on the order
    assert c.percentile(list(range(101)), 99) == pytest.approx(99)


def test_duration_jfr():
    assert c.duration_ms("PT0.000610953S") == pytest.approx(0.610953)
    assert c.duration_ms("PT0S") == 0
    assert c.duration_ms("PT1M2.5S") == pytest.approx(62500)
    assert c.duration_ms("PT1H") == pytest.approx(3_600_000)
    with pytest.raises(ValueError):
        c.duration_ms("0.5 ms")


def test_chunky_zone_includes_both_edges():
    # Chunky with centre 0,0 and radius 128 processes 289 chunks (17 × 17), measured on the server
    box = c.chunks_of_zone(0, 0, 128)
    assert box == (-8, -8, 8, 8) and (box[2] - box[0] + 1) ** 2 == 289
    assert c.chunks_of_zone(32, -1344, 160) == (-8, -94, 12, -74)
    assert c.side(32, 160) == 21 and c.side(0, 64) == 9
    assert c.inside((12, -74), c.chunks_of_zone(32, -1344, 160)) and not c.inside((13, -74), c.chunks_of_zone(32, -1344, 160))
    assert c.inside((13, -74), c.chunks_of_zone(32, -1344, 160), margin=1)


def test_separate_zones_far_from_warmup():
    """Each event falls in a single zone: the boxes with their margin do not touch (not even the warm-up one)."""
    all_items = c.ZONES + [c.WARMUP]
    for i, (n1, x1, z1, r1) in enumerate(all_items):
        a = c.chunks_of_zone(x1, z1, r1)
        for n2, x2, z2, r2 in all_items[i + 1:]:
            b = c.chunks_of_zone(x2, z2, r2)
            m = 2 * c.MARGIN_CHUNKS
            assert a[2] + m < b[0] or b[2] + m < a[0] or a[3] + m < b[1] or b[3] + m < a[1], (n1, n2)
    assert len({n for n, *_ in c.ZONES}) == len(c.ZONES)


def _ev(cx, cz, step, ms):
    return (cx, cz, f"minecraft:{step}", ms)


def test_summary_chunks_sums_steps_and_spreads_the_margin():
    box = (0, 0, 1, 0)                                  # 2 chunks
    ev = [_ev(0, 0, "terrain", 10), _ev(0, 0, "features", 2), _ev(1, 0, "terrain", 20),
          _ev(0, 0, "light", 100), _ev(1, 0, "initialize_light", 50),      # light: does not count in the ms per chunk
          _ev(-1, 0, "structure_starts", 4),                               # margin neighbour: counts in the mean
          _ev(50, 50, "terrain", 1000)]                                    # otra zona: no cuenta
    r = c.chunks_summary(ev, box, margin=2)
    assert r["chunks"] == 2 and r["chunks_medidos"] == 2
    assert r["media_ms"] == pytest.approx((10 + 2 + 20 + 4) / 2)
    assert r["con_luz_ms"] == pytest.approx((10 + 2 + 20 + 4 + 150) / 2)
    assert r["estructuras_ms"] == pytest.approx((2 + 4) / 2)
    assert r["max_ms"] == 20 and r["p50_ms"] == pytest.approx(16)
    assert r["pasos_ms"]["minecraft:light"] == 50 and r["pasos_ms"]["minecraft:terrain"] == 15
    assert list(r["pasos_ms"]) == sorted(r["pasos_ms"])


def test_merge_zones_weights_by_chunks(monkeypatch):
    monkeypatch.setattr(c, "ZONES", [("a", 8, 8, 0), ("b", 1608, 8, 16)])      # 1 chunk and 3 × 3 chunks
    ev = [_ev(0, 0, "terrain", 90)] + [_ev(cx, cz, "terrain", 10) for cx in range(99, 102) for cz in range(-1, 2)]
    zones = {n: c.chunks_summary(ev, c.chunks_of_zone(x, z, r), margin=0) for n, x, z, r in c.ZONES}
    assert zones["a"]["chunks"] == 1 and zones["b"]["chunks"] == 9
    j = c.join_zones(ev, zones)
    assert j["media_ms"] == pytest.approx((90 + 9 * 10) / 10)
    assert j["max_ms"] == 90 and j["p50_ms"] == 10
    assert j["pasos_ms"] == {"minecraft:terrain": pytest.approx(18)}


def test_events_of_jfr_print_json():
    dataset = {"recording": {"events": [
        {"type": "minecraft.ChunkGeneration", "values": {"duration": "PT0.002S", "chunkPosX": 3, "chunkPosZ": -2,
                                                         "status": "minecraft:features", "level": "minecraft:overworld"}},
        {"type": "minecraft.ChunkGeneration", "values": {"duration": "PT0.5S", "chunkPosX": 0, "chunkPosZ": 0,
                                                         "status": "minecraft:terrain", "level": "minecraft:the_nether"}},
        {"type": "minecraft.ServerTickTime", "values": {"averageTickDuration": "PT0.003S"}}]}}
    assert c.jfr_chunk_events(dataset) == [(3, -2, "minecraft:features", pytest.approx(2.0))]


def test_mspt_memory_and_profile():
    summary = {"serverTick": {"minMs": 0.4, "averageMs": 8.9, "maxMs": 69.5, "p99": 64.2, "p90": 16.9, "p75": 2.3, "p50": 1.1}}
    assert c.mspt_of(summary) == {"media": 8.9, "p50": 1.1, "p90": 16.9, "p99": 64.2, "max": 69.5}
    assert c.mspt_of({})["media"] is None
    heap = [{"values": {"when": "Before GC", "heapUsed": 900 * 2 ** 20}}, {"values": {"when": "After GC", "heapUsed": 300 * 2 ** 20}},
            {"values": {"when": "After GC", "heapUsed": 350 * 2 ** 20}}]
    assert c.memory_of(heap) == 350 and c.memory_of([]) is None
    log = ("[x] Heraldia: perfil: {\"ladera\":{\"n\":1,\"total_ms\":2.0,\"media_us\":2000.0,\"max_us\":2000.0}}\n"
           "otra línea\n[y] Heraldia: perfil: {\"ladera\":{\"n\":3,\"total_ms\":6.0,\"media_us\":2000.0,\"max_us\":2500.0}}\n")
    assert c.last_profile(log) == {"ladera": {"n": 3, "total_ms": 6.0, "media_us": 2000.0, "max_us": 2500.0}}
    assert c.last_profile("nada") is None
    m = c.medium_profile([{"ladera": {"n": 1, "total_ms": 1, "media_us": 1, "max_us": 1}},
                          {"ladera": {"n": 3, "total_ms": 3, "media_us": 3, "max_us": 3}, "orilla": {"n": 1, "total_ms": 9, "media_us": 9, "max_us": 9}}])
    assert m == {"ladera": {"n": 2, "total_ms": 2, "media_us": 2, "max_us": 2}, "orilla": {"n": 1, "total_ms": 9, "media_us": 9, "max_us": 9}}


def _pass(mean, seconds=10.0, locate=None, chunks=800):
    return {"chunks": chunks, "segundos": seconds, "mspt": {"media": 1.0, "p50": 1.0, "p90": 2.0, "p99": 3.0, "max": 4.0},
            "memoria_mb": 400.0, "locate_ms": locate or {},
            "ms_por_chunk": {"media_ms": mean, "p50_ms": mean / 2, "p90_ms": mean, "p99_ms": 2 * mean, "max_ms": 3 * mean,
                             "estructuras_ms": 1.0, "con_luz_ms": mean + 40, "pasos_ms": {"minecraft:terrain": mean}},
            "zonas": {"aldea": {"media_ms": mean + 5}, "origen": {"media_ms": mean - 5}}}


def test_aggregate_takes_the_median_of_the_passes():
    a = c.add_entry([_pass(60, 12, {"mina": 900}), _pass(70, 10, {"mina": 1000}), _pass(100, 30, {"mina": 5000, "aldea": 7})])
    assert a["pasadas"] == 3 and a["chunks"] == 800
    assert a["ms_por_chunk"]["media_ms"] == 70 and a["ms_por_chunk"]["p99_ms"] == 140
    assert a["segundos"] == 12 and a["chunks_por_s"] == pytest.approx(800 / 12)
    assert a["locate_ms"] == {"aldea": 7, "mina": 1000}                    # the one missing in a pass does not count
    assert a["pasos_ms"] == {"minecraft:terrain": 70} and a["zonas_ms"] == {"aldea": 75, "origen": 65}
    assert a["mspt"]["p99"] == 3.0 and a["memoria_mb"] == 400
    assert c.add_entry([]) is None


def test_overcost():
    with_it, sin = c.add_entry([_pass(66)]), c.add_entry([_pass(60)])
    assert c.overcost(with_it, sin) == pytest.approx(0.1)
    assert c.overcost(sin, with_it) == pytest.approx(60 / 66 - 1)
    assert c.overcost(None, sin) is None and c.overcost(with_it, c.add_entry([_pass(0)])) is None


@pytest.mark.parametrize("current, ok", [(0.10, True), (0.15, True), (0.1749, True), (0.1751, False), (0.5, False), (-0.2, True)])
def test_compare_with_threshold_and_margin(current, ok):
    ref = {"sobrecoste": 0.10, "umbral_relativo": 0.25, "margen_absoluto": 0.05}     # limit 0.10 × 1.25 + 0.05 = 0.175
    r = c.compare(current, ref)
    assert r[0] is ok and r[1] == pytest.approx(0.175)
    assert ("REGRESIÓN" in r[2]) is (not ok)


def test_compare_cases_limit():
    assert c.compare(None, {"sobrecoste": 0.1})[0] is False                     # without a measurement: fails
    ok, limit, text = c.compare(0.9, None)                                   # without a reference: passes and says so
    assert ok and limit is None and "sin referencia" in text
    # negative reference (noise: Heraldia came out faster): the limit starts from 0, not from a negative value
    assert c.compare(0.04, {"sobrecoste": -0.03})[1] == pytest.approx(0.08)
    assert c.compare(0.09, {"sobrecoste": -0.03})[0] is False
    # default values if the reference does not bring them
    assert c.compare(0.0, {"sobrecoste": 0.2})[1] == pytest.approx(0.2 * 1.25 + 0.08)


def _result():
    sin, with_it = c.add_entry([_pass(60, locate={"aldea_vanilla": 180})]), c.add_entry([_pass(66, locate={"mina": 4800, "aldea_vanilla": 175})])
    return {"semilla": "heraldia", "zonas": ["aldea (32, -1344) 21×21 chunks"], "maquina": "4 núcleos, Linux", "fecha": "2026-11-16",
            "commit": "abc1234", "sin": sin, "con": with_it, "sobrecoste": c.overcost(with_it, sin),
            "perfil": {"ladera": {"n": 4, "total_ms": 90.0, "media_us": 22500.0, "max_us": 38000.0},
                       "reglas": {"n": 100, "total_ms": 30.0, "media_us": 300.0, "max_us": 14000.0}}}


def test_new_reference_keeps_threshold_and_margin():
    r = _result()
    new_one = c.new_reference(r, {"sobrecoste": 0.3, "umbral_relativo": 0.4, "margen_absoluto": 0.02})
    assert new_one["sobrecoste"] == pytest.approx(0.1) and new_one["umbral_relativo"] == 0.4 and new_one["margen_absoluto"] == 0.02
    assert new_one["ms_por_chunk_con"] == 66 and new_one["ms_por_chunk_sin"] == 60 and new_one["pasadas"] == 1
    assert new_one["commit"] == "abc1234"
    default = c.new_reference(r)
    assert default["umbral_relativo"] == 0.25 and default["margen_absoluto"] == 0.08
    json.dumps(new_one)                                                       # it can be saved as is


def test_summary_markdown():
    r = _result()
    md = c.markdown(r, c.compare(r["sobrecoste"], {"sobrecoste": 0.08}))
    assert md.startswith("## Coste de generación de Heraldia ✅")
    assert "| ms por chunk (media, sin luz) | 60.0 | 66.0 | +10% |" in md
    assert "| mina | — | 4800 |" in md and "| aldea_vanilla | 180 | 175 |" in md
    assert md.index("| ladera |") < md.index("| reglas |")                 # profile sorted by total time
    assert "| aldea | 65.0 | 71.0 | +9% |" in md                              # per zone
    assert "tools/smoke/cost_reference.json" in md
    bad = c.markdown(r, c.compare(0.9, {"sobrecoste": 0.08}))
    assert bad.startswith("## Coste de generación de Heraldia ❌") and "REGRESIÓN" in bad


def test_write_json_markdown_and_summary_of_the_job(tmp_path, monkeypatch):
    summary = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(summary))
    r = _result()
    md = c.write(r, c.compare(r["sobrecoste"], None), str(tmp_path / "salida"))
    saved = json.loads((tmp_path / "salida" / "coste_generacion.json").read_text(encoding="utf-8"))
    assert saved["sobrecoste"] == pytest.approx(0.1) and saved["comparacion"]["ok"] is True
    assert (tmp_path / "salida" / "coste_generacion.md").read_text(encoding="utf-8") == md == summary.read_text(encoding="utf-8")


def test_from_a_json_and_update_the_reference(tmp_path, monkeypatch):
    """--from-json rebuilds the summary of a saved measurement (the CI artifact) without a server, and with
    --update-reference saves it; without --no-threshold, a regression gives exit code 1."""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    r = _result()
    gauged = tmp_path / "coste_generacion.json"
    gauged.write_text(json.dumps(r), encoding="utf-8")
    ref = tmp_path / "ref.json"
    ref.write_text(json.dumps({"sobrecoste": 0.01, "umbral_relativo": 0.25, "margen_absoluto": 0.05}), encoding="utf-8")
    base = ["--from-json", str(gauged), "--reference", str(ref), "--output", str(tmp_path / "s")]
    assert c.main(base) == 1                                                # 0,10 > 0,01 × 1,25 + 0,05
    assert c.main(base + ["--no-threshold"]) == 0
    assert c.main(base + ["--update-reference"]) == 0
    new_one = json.loads(ref.read_text(encoding="utf-8"))
    assert new_one["sobrecoste"] == pytest.approx(0.1) and new_one["umbral_relativo"] == 0.25
    assert c.main(base) == 0


def test_repository_reference():
    ref = c.read_reference()
    assert ref is not None, "tools/smoke/cost_reference.json is missing"
    assert -0.5 < ref["sobrecoste"] < 1.0
    assert 0 < ref["umbral_relativo"] <= 1 and 0 <= ref["margen_absoluto"] <= 0.25
    assert ref["ms_por_chunk_con"] > 0 and ref["ms_por_chunk_sin"] > 0 and ref["pasadas"] >= 1


def test_cpu_of_proc_stat():
    # /proc/<pid>/stat with a name containing spaces and parentheses: utime (14) and stime (15) in clock ticks
    line = "4242 (java (x) y) S 1 4242 4242 0 -1 4194560 1000 0 0 0 1234 566 0 0 20 0 60 0 100 0 0"
    assert c.cpu_of_stat(line) == pytest.approx(18.0)
    assert c.cpu_of_stat(line, hz=1000) == pytest.approx(1.8)
    assert c.process_cpu(-1) is None                                         # without a process: None, not an exception
    if os.path.isfile(f"/proc/{os.getpid()}/stat"):
        assert c.process_cpu(os.getpid()) >= 0


def test_cpu_decides_if_in_both():
    with_it, sin = c.add_entry([_pass(66)]), c.add_entry([_pass(60)])
    with_it["cpu_ms_por_chunk"], sin["cpu_ms_por_chunk"] = 33.0, 30.0
    assert c.overcost(with_it, sin) == pytest.approx(0.1) and c.metric(with_it) == 33
    sin["cpu_ms_por_chunk"] = None                                           # missing in one: the JFR steps
    assert c.overcost(with_it, sin) == pytest.approx(0.1) and c.metric(sin) == 60
    r = {"con": with_it, "sin": dict(sin, cpu_ms_por_chunk=30.0), "sobrecoste": 0.1}
    assert c.new_reference(r)["medida"] == "cpu" and c.new_reference(r)["ms_por_chunk_con"] == 33


def test_configuration_by_default_without_the_arena():
    """What is measured is the default configuration, except the wave arena (a unique build next to the spawn of a
    new world, not generation); the option exists and is enabled by default."""
    import options                                   # tools/gen is on sys.path (conftest)
    fixed_opts = {o[0]: o[1] for o in options._FIXED}
    assert fixed_opts["arena.generar_en_mundos_nuevos"] is True
    assert fixed_opts["casa_heraldo.generar_en_mundos_nuevos"] is True     # the Herald's House, likewise
    assert c.CONFIG == {"arena": {"generar_en_mundos_nuevos": False}, "casa_heraldo": {"generar_en_mundos_nuevos": False}}


# ---------------------------------------------------------------- peaks and the continuous strip

def test_strip_far_from_the_zones_and_its_rectangle():
    name, x, z, rx, rz = c.STRIP
    box = c.chunks_of_rect(x, z, rx, rz)
    assert box == ((x - rx) >> 4, (z - rz) >> 4, (x + rx) >> 4, (z + rz) >> 4)
    assert c.box_chunks(box) == (box[2] - box[0] + 1) * (box[3] - box[1] + 1)
    assert box[2] - box[0] + 1 > 8 * (box[3] - box[1] + 1), "long and narrow: like flying over it"
    m = 2 * c.MARGIN_CHUNKS
    for n, zx, zz, r in c.ZONES + [c.WARMUP]:
        b = c.chunks_of_zone(zx, zz, r)
        assert box[2] + m < b[0] or b[2] + m < box[0] or box[3] + m < b[1] or b[3] + m < box[1], n
    assert box[2] - box[0] + 1 > c.LEAD_IN_CHUNKS + 4 * c.STRETCH_CHUNKS


def test_peaks_tail_worst_chunk_and_slow_ones():
    ev = [_ev(0, 0, "terrain", 30), _ev(0, 0, "features", 30), _ev(1, 0, "terrain", 10), _ev(2, 0, "terrain", 200),
          _ev(2, 0, "light", 900), _ev(9, 9, "terrain", 999)]
    pc = c.per_chunk_ms(ev, [(0, 0, 2, 0)])
    assert pc == {(0, 0): 60, (1, 0): 10, (2, 0): 200}                 # without light; outside the box, nothing
    p = c.peaks(pc)
    assert p["chunks"] == 3 and p["max_ms"] == 200 and p["peor_chunk"] == [2, 0]
    assert p["lentos"] == 2 and p["lentos_fraccion"] == pytest.approx(2 / 3)       # more than a tick (50 ms)
    assert p["p50_ms"] == 60 and p["p95_ms"] == pytest.approx(186) and p["p99_ms"] == pytest.approx(197.2)
    assert c.peaks({})["max_ms"] is None and c.peaks({})["lentos_fraccion"] is None


def test_structure_events_summary_and_blame():
    dataset = {"recording": {"events": [
        {"type": "minecraft.StructureGeneration", "values": {"duration": "PT0.230S", "chunkPosX": 2, "chunkPosZ": -84,
                                                             "structure": "heraldia:pantano_brujas", "success": True,
                                                             "level": "minecraft:overworld"}},
        {"type": "minecraft.StructureGeneration", "values": {"duration": "PT0.001S", "chunkPosX": 2, "chunkPosZ": -84,
                                                             "structure": "heraldia:nieve_pastores", "success": False,
                                                             "level": "minecraft:overworld"}},
        {"type": "minecraft.StructureGeneration", "values": {"duration": "PT0.030S", "chunkPosX": 5, "chunkPosZ": -80,
                                                             "structure": "heraldia:unicas/castillo", "success": True,
                                                             "level": "minecraft:overworld"}},
        {"type": "minecraft.StructureGeneration", "values": {"duration": "PT9S", "chunkPosX": 0, "chunkPosZ": 0,
                                                             "structure": "minecraft:fortress", "success": True,
                                                             "level": "minecraft:the_nether"}}]}}
    se = c.jfr_structure_events(dataset)
    assert se == [(2, -84, "heraldia:pantano_brujas", pytest.approx(230), True), (2, -84, "heraldia:nieve_pastores", pytest.approx(1), False),
                  (5, -80, "heraldia:unicas/castillo", pytest.approx(30), True)]
    s = c.structures_summary(se, [(0, -90, 10, -78)], margin=0)
    assert list(s) == ["heraldia:pantano_brujas", "heraldia:unicas/castillo", "heraldia:nieve_pastores"]   # slowest first
    assert s["heraldia:pantano_brujas"] == {"intentos": 1, "generadas": 1, "total_ms": pytest.approx(230), "max_ms": pytest.approx(230),
                                            "max_chunk": [2, -84]}
    assert s["heraldia:nieve_pastores"]["generadas"] == 0
    ev = [_ev(2, -84, "structure_starts", 231), _ev(2, -84, "terrain", 20), _ev(2, -84, "light", 99), _ev(6, -80, "features", 40)]
    b = c.blame((2, -84), ev, se)
    assert b["chunk"] == [2, -84] and b["bloque"] == [40, -1336]
    assert list(b["pasos_ms"]) == ["minecraft:structure_starts", "minecraft:terrain"]            # without light, slowest first
    assert b["iniciadas"] == [{"estructura": "heraldia:pantano_brujas", "ms": pytest.approx(230)}]
    near = c.blame((6, -80), ev, se)
    assert near["iniciadas"] == [] and near["cercana"]["estructura"] == "heraldia:unicas/castillo" and near["cercana"]["distancia_chunks"] == 1
    assert c.blame((60, 60), ev, se)["cercana"] is None
    assert "pantano_brujas" in c._blame_text(dict(b, max_ms=251)) and "castillo" in c._blame_text(dict(near, max_ms=40))


def test_stretches_of_the_strip():
    box = (0, 0, 9, 1)                                                 # 10 columns, 2 chunks wide
    ev = [_ev(x, z, "terrain", 10) for x in range(10) for z in range(2)]
    ev += [_ev(7, 0, "features", 100), _ev(8, 5, "structure_starts", 60)]   # a neighbour across the strip (margin) counts
    ev += [_ev(7, 0, "light", 1000), _ev(20, 0, "terrain", 1000)]      # light and outside, not
    t = c.stretches(ev, box, width=3, margin=4)
    assert t["chunks_por_tramo"] == 6 and t["bloques_por_tramo"] == 48 and t["tramos"] == 8
    assert t["peor_columnas"] == [6, 8] and t["peor_desde_x"] == 96 and t["peor_hasta_x"] == 143
    assert t["peor_ms"] == pytest.approx(60 + 100 + 60) and t["peor_ms_por_chunk"] == pytest.approx(220 / 6)
    assert c.stretches([], (0, 0, 1, 0), width=3) is None


def _peak_pass(slow, stretch, mspt_p99=4.0, worst=300.0):
    p = _pass(60)
    p["mspt"]["p99"] = mspt_p99
    p["picos"] = {"chunks": 100, "p50_ms": 30, "p95_ms": 90, "p99_ms": 200, "max_ms": worst, "peor_chunk": [1, 2],
                  "lentos": int(slow * 100), "lentos_fraccion": slow}
    p["peor_chunk"] = {"chunk": [1, 2], "bloque": [24, 40], "pasos_ms": {"minecraft:structure_starts": worst}, "iniciadas": [], "cercana": None}
    p["estructuras"] = {"heraldia:pantano_brujas": {"intentos": 1, "generadas": 1, "total_ms": 230.0, "max_ms": 230.0, "max_chunk": [1, 2]}}
    p["franja"] = {"chunks": 1067, "segundos": 20.0, "chunks_por_s": 53.0, "cpu_ms_por_chunk": 52.0,
                   "picos": dict(p["picos"]), "peor_chunk": dict(p["peor_chunk"]),
                   "tramos": {"chunks_por_tramo": 88, "bloques_por_tramo": 128, "tramos": 80, "media_ms_por_chunk": 50.0,
                              "peor_ms": stretch * 88, "peor_ms_por_chunk": stretch, "peor_desde_x": -5000, "peor_hasta_x": -4873}}
    return p


def test_aggregate_of_the_peaks_takes_the_median_and_the_worst_chunk():
    a = c.add_entry([_peak_pass(0.20, 100, worst=300), _peak_pass(0.30, 140, worst=700), _peak_pass(0.25, 120, worst=400)])
    assert a["picos"]["lentos_fraccion"] == pytest.approx(0.25) and a["picos"]["max_ms"] == 400
    assert a["peor_chunk"]["max_ms"] == 700 and a["peor_chunk"]["mismo_en_todas"] is True
    assert a["franja"]["tramos"]["peor_ms_por_chunk"] == 120 and a["franja"]["chunks"] == 1067
    assert a["estructuras"]["heraldia:pantano_brujas"]["max_ms"] == 230
    old = c.add_entry([_pass(60)])                                     # a measurement from before: without peaks
    assert "picos" not in old


@pytest.mark.parametrize("slow, stretch, mspt, ok", [(0.245, 125, 10.5, True), (0.30, 125, 10.5, False), (0.245, 190, 10.5, False),
                                                       (0.245, 125, 60.0, False), (0.235, 90, 4.0, True)])
def test_compare_peaks(slow, stretch, mspt, ok):
    r = {"sin": c.add_entry([_peak_pass(0.235, 142)]), "con": c.add_entry([_peak_pass(slow, stretch, mspt)])}
    got, text = c.compare_peaks(r)
    assert got is ok, text
    assert ("REGRESIÓN" in text) is (not ok)
    # limits from the reference
    assert c.compare_peaks(r, {"picos": {"lentos_pp": 0.2, "peor_tramo": 1.0, "mspt_p99_ms": 100}})[0] is True
    assert c.compare_peaks({"sin": c.add_entry([_pass(60)]), "con": c.add_entry([_pass(66)])})[0] is True   # without peaks


def test_peaks_markdown_and_main_exit_code(tmp_path, monkeypatch):
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    r = _result()
    r["sin"], r["con"] = c.add_entry([_peak_pass(0.235, 142)]), c.add_entry([_peak_pass(0.246, 125)])
    r["sobrecoste"] = 0.04
    comp = c.compare(r["sobrecoste"], {"sobrecoste": 0.09}) + c.compare_peaks(r)
    md = c.markdown(r, comp)
    assert "**Picos: la cola del tiempo por chunk**" in md and "**Recorrido continuo**" in md
    assert "| chunks de más de 50 ms (%) | 23.50 | 24.60 | +5% |" in md
    assert "| peor tramo, ms por chunk | 142.0 | 125.0 | -12% |" in md
    assert "heraldia:pantano_brujas" in md and md.startswith("## Coste de generación de Heraldia ✅")
    gauged = tmp_path / "coste_generacion.json"
    import json as _json
    bad = dict(r, con=c.add_entry([_peak_pass(0.40, 125)]))
    gauged.write_text(_json.dumps(bad), encoding="utf-8")
    ref = tmp_path / "ref.json"
    ref.write_text(_json.dumps({"sobrecoste": 0.09}), encoding="utf-8")
    base = ["--from-json", str(gauged), "--reference", str(ref), "--output", str(tmp_path / "s")]
    assert c.main(base) == 1, "the median passes, the peaks do not"
    assert c.main(base + ["--no-threshold"]) == 0
    saved = _json.loads((tmp_path / "s" / "coste_generacion.json").read_text(encoding="utf-8"))
    assert saved["comparacion_picos"]["ok"] is False


def test_new_reference_keeps_the_peak_limits():
    r = _result()
    assert c.new_reference(r)["picos"] == c.PEAK_LIMITS
    assert c.new_reference(r, {"picos": {"lentos_pp": 0.05}})["picos"]["lentos_pp"] == 0.05


def test_repository_reference_has_peak_limits():
    ref = c.read_reference()
    assert set(ref["picos"]) >= set(c.PEAK_LIMITS)
    assert 0 < ref["picos"]["lentos_pp"] <= 0.1 and 0 < ref["picos"]["peor_tramo"] <= 0.5
    assert ref["picos"]["mspt_p99_ms"] == c.TICK_MS


# ---------------------------------------------------------------- variants (comparing configurations, e.g. medium density)

def test_parse_variant_reads_json_values():
    assert c.parse_variant("medianas.frecuencia_porcentaje=70") == {"medianas.frecuencia_porcentaje": 70}
    assert c.parse_variant("a=true, b=1.5,c=texto") == {"a": True, "b": 1.5, "c": "texto"}
    with pytest.raises(ValueError):
        c.parse_variant("sin_igual")


def test_config_of_nests_the_options_over_the_base_configuration():
    cfg = c.config_of("ligero", {"medianas.frecuencia_porcentaje": 100, "medianas.distancia_minima.bloques": 192})
    assert cfg == {"arena": {"generar_en_mundos_nuevos": False}, "casa_heraldo": {"generar_en_mundos_nuevos": False},
                   "perfil": "ligero",
                   "medianas": {"frecuencia_porcentaje": 100, "distancia_minima": {"bloques": 192}}}
    assert c.config_of() == c.CONFIG and c.config_of() is not c.CONFIG
    assert c.CONFIG == {"arena": {"generar_en_mundos_nuevos": False},
                        "casa_heraldo": {"generar_en_mundos_nuevos": False}}, "the base is not modified"


def test_medium_starts_counts_only_medium_structures():
    st = {"heraldia:medianas/posada/llanura": {"generadas": 2, "total_ms": 10.0},
          "heraldia:medianas/molino/taiga": {"generadas": 1, "total_ms": 4.5},
          "heraldia:unicas/castillo": {"generadas": 1, "total_ms": 30.0}, "minecraft:village_plains": {"generadas": 3, "total_ms": 900.0}}
    assert c.medium_starts(st) == (3, 14.5)
    assert c.medium_starts({}) == (0, 0.0)


def test_medium_zones_are_large_separate_and_far_from_the_strip():
    """The medium layout: four large squares that do not touch each other, the warm-up or the strip."""
    zones = c.LAYOUTS["medianas"]
    assert c.LAYOUTS["estandar"] is c.ZONES
    m = 2 * c.MARGIN_CHUNKS
    name, x, z, rx, rz = c.STRIP
    boxes = [(n, c.chunks_of_zone(zx, zz, r)) for n, zx, zz, r in zones + [c.WARMUP]] + [(name, c.chunks_of_rect(x, z, rx, rz))]
    for i, (n1, a) in enumerate(boxes):
        for n2, b in boxes[i + 1:]:
            assert a[2] + m < b[0] or b[2] + m < a[0] or a[3] + m < b[1] or b[3] + m < a[1], (n1, n2)
    assert sum(c.box_chunks(c.chunks_of_zone(zx, zz, r)) for _, zx, zz, r in zones) >= 10000, "enough land to hold several mediums"


def test_variants_markdown_has_one_row_per_configuration():
    def entry(cpu, slow, starts):
        return {"cpu_ms_por_chunk": cpu, "picos": {"p95_ms": 100.0, "p99_ms": 200.0, "lentos_fraccion": slow},
                "franja": {"tramos": {"peor_ms_por_chunk": 60.0}}, "mspt": {"p99": 9.0}, "locate_ms": {"mediana": 50},
                "estructuras": {"heraldia:medianas/posada/llanura": {"generadas": starts, "total_ms": 3.0 * starts}}}
    sin = entry(50.0, 0.25, 0)
    sin.pop("estructuras")
    rows = [({"medianas.frecuencia_porcentaje": 100}, {"sin": sin, "con": entry(55.0, 0.30, 8), "sobrecoste": 0.10}),
            ({"medianas.frecuencia_porcentaje": 70}, {"sin": sin, "con": entry(53.0, 0.28, 5), "sobrecoste": 0.06})]
    md = c.variants_markdown(rows)
    lines = [l for l in md.splitlines() if l.startswith("| ")]
    assert len(lines) == 4, md                    # header, without Heraldia and the two variants
    assert "| sin Heraldia | — | 50.0 |" in md
    assert "| medianas.frecuencia_porcentaje=100 | +10.0% | 55.0 |" in md and "| 30.0 % |" in md
    assert "| medianas.frecuencia_porcentaje=70 | +6.0% | 53.0 |" in md and "| 5 | 15.0 | 50.0 |" in md
