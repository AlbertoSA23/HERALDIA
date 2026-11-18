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
    assert c.CONFIG == {"arena": {"generar_en_mundos_nuevos": False}}
