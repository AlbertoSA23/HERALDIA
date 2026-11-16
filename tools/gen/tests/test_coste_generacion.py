"""tools/smoke/coste_generacion.py: funciones puras de la prueba de coste de generación (percentiles, duraciones de JFR,
zonas de Chunky, resumen por chunk, agregado de pasadas, sobrecoste, comparación con la referencia y el Markdown)."""
import json, os, sys
import pytest

SMOKE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "smoke")
sys.path.insert(0, SMOKE)
import coste_generacion as c  # noqa: E402


def test_percentil_interpolado():
    assert c.percentil([], 50) is None
    assert c.percentil([7], 99) == 7
    v = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
    assert c.percentil(v, 0) == 1 and c.percentil(v, 100) == 10
    assert c.percentil(v, 50) == pytest.approx(5.5)
    assert c.percentil(v, 90) == pytest.approx(9.1)
    assert c.percentil(list(reversed(v)), 90) == pytest.approx(9.1)      # no depende del orden
    assert c.percentil(list(range(101)), 99) == pytest.approx(99)


def test_duracion_jfr():
    assert c.duracion_ms("PT0.000610953S") == pytest.approx(0.610953)
    assert c.duracion_ms("PT0S") == 0
    assert c.duracion_ms("PT1M2.5S") == pytest.approx(62500)
    assert c.duracion_ms("PT1H") == pytest.approx(3_600_000)
    with pytest.raises(ValueError):
        c.duracion_ms("0.5 ms")


def test_zona_de_chunky_incluye_los_dos_bordes():
    # Chunky con centro 0,0 y radio 128 procesa 289 chunks (17 × 17), medido en el servidor
    caja = c.chunks_de_zona(0, 0, 128)
    assert caja == (-8, -8, 8, 8) and (caja[2] - caja[0] + 1) ** 2 == 289
    assert c.chunks_de_zona(32, -1344, 160) == (-8, -94, 12, -74)
    assert c.lado(32, 160) == 21 and c.lado(0, 64) == 9
    assert c.dentro((12, -74), c.chunks_de_zona(32, -1344, 160)) and not c.dentro((13, -74), c.chunks_de_zona(32, -1344, 160))
    assert c.dentro((13, -74), c.chunks_de_zona(32, -1344, 160), margen=1)


def test_zonas_separadas_y_lejos_del_calentamiento():
    """Cada evento cae en una sola zona: las cajas con su margen no se tocan (ni con la de calentamiento)."""
    todas = c.ZONAS + [c.CALENTAMIENTO]
    for i, (n1, x1, z1, r1) in enumerate(todas):
        a = c.chunks_de_zona(x1, z1, r1)
        for n2, x2, z2, r2 in todas[i + 1:]:
            b = c.chunks_de_zona(x2, z2, r2)
            m = 2 * c.MARGEN_CHUNKS
            assert a[2] + m < b[0] or b[2] + m < a[0] or a[3] + m < b[1] or b[3] + m < a[1], (n1, n2)
    assert len({n for n, *_ in c.ZONAS}) == len(c.ZONAS)


def _ev(cx, cz, paso, ms):
    return (cx, cz, f"minecraft:{paso}", ms)


def test_resumen_chunks_suma_pasos_y_reparte_el_margen():
    caja = (0, 0, 1, 0)                                  # 2 chunks
    ev = [_ev(0, 0, "terrain", 10), _ev(0, 0, "features", 2), _ev(1, 0, "terrain", 20),
          _ev(0, 0, "light", 100), _ev(1, 0, "initialize_light", 50),      # luz: no cuenta en el ms por chunk
          _ev(-1, 0, "structure_starts", 4),                               # vecino del margen: cuenta en la media
          _ev(50, 50, "terrain", 1000)]                                    # otra zona: no cuenta
    r = c.resumen_chunks(ev, caja, margen=2)
    assert r["chunks"] == 2 and r["chunks_medidos"] == 2
    assert r["media_ms"] == pytest.approx((10 + 2 + 20 + 4) / 2)
    assert r["con_luz_ms"] == pytest.approx((10 + 2 + 20 + 4 + 150) / 2)
    assert r["estructuras_ms"] == pytest.approx((2 + 4) / 2)
    assert r["max_ms"] == 20 and r["p50_ms"] == pytest.approx(16)
    assert r["pasos_ms"]["minecraft:light"] == 50 and r["pasos_ms"]["minecraft:terrain"] == 15
    assert list(r["pasos_ms"]) == sorted(r["pasos_ms"])


def test_juntar_zonas_pondera_por_chunks(monkeypatch):
    monkeypatch.setattr(c, "ZONAS", [("a", 8, 8, 0), ("b", 1608, 8, 16)])      # 1 chunk y 3 × 3 chunks
    ev = [_ev(0, 0, "terrain", 90)] + [_ev(cx, cz, "terrain", 10) for cx in range(99, 102) for cz in range(-1, 2)]
    zonas = {n: c.resumen_chunks(ev, c.chunks_de_zona(x, z, r), margen=0) for n, x, z, r in c.ZONAS}
    assert zonas["a"]["chunks"] == 1 and zonas["b"]["chunks"] == 9
    j = c.juntar_zonas(ev, zonas)
    assert j["media_ms"] == pytest.approx((90 + 9 * 10) / 10)
    assert j["max_ms"] == 90 and j["p50_ms"] == 10
    assert j["pasos_ms"] == {"minecraft:terrain": pytest.approx(18)}


def test_eventos_de_jfr_print_json():
    datos = {"recording": {"events": [
        {"type": "minecraft.ChunkGeneration", "values": {"duration": "PT0.002S", "chunkPosX": 3, "chunkPosZ": -2,
                                                         "status": "minecraft:features", "level": "minecraft:overworld"}},
        {"type": "minecraft.ChunkGeneration", "values": {"duration": "PT0.5S", "chunkPosX": 0, "chunkPosZ": 0,
                                                         "status": "minecraft:terrain", "level": "minecraft:the_nether"}},
        {"type": "minecraft.ServerTickTime", "values": {"averageTickDuration": "PT0.003S"}}]}}
    assert c.eventos_jfr(datos) == [(3, -2, "minecraft:features", pytest.approx(2.0))]


def test_mspt_memoria_y_perfil():
    resumen = {"serverTick": {"minMs": 0.4, "averageMs": 8.9, "maxMs": 69.5, "p99": 64.2, "p90": 16.9, "p75": 2.3, "p50": 1.1}}
    assert c.mspt_de(resumen) == {"media": 8.9, "p50": 1.1, "p90": 16.9, "p99": 64.2, "max": 69.5}
    assert c.mspt_de({})["media"] is None
    heap = [{"values": {"when": "Before GC", "heapUsed": 900 * 2 ** 20}}, {"values": {"when": "After GC", "heapUsed": 300 * 2 ** 20}},
            {"values": {"when": "After GC", "heapUsed": 350 * 2 ** 20}}]
    assert c.memoria_de(heap) == 350 and c.memoria_de([]) is None
    log = ("[x] Heraldia: perfil: {\"ladera\":{\"n\":1,\"total_ms\":2.0,\"media_us\":2000.0,\"max_us\":2000.0}}\n"
           "otra línea\n[y] Heraldia: perfil: {\"ladera\":{\"n\":3,\"total_ms\":6.0,\"media_us\":2000.0,\"max_us\":2500.0}}\n")
    assert c.ultimo_perfil(log) == {"ladera": {"n": 3, "total_ms": 6.0, "media_us": 2000.0, "max_us": 2500.0}}
    assert c.ultimo_perfil("nada") is None
    m = c.perfil_mediano([{"ladera": {"n": 1, "total_ms": 1, "media_us": 1, "max_us": 1}},
                          {"ladera": {"n": 3, "total_ms": 3, "media_us": 3, "max_us": 3}, "orilla": {"n": 1, "total_ms": 9, "media_us": 9, "max_us": 9}}])
    assert m == {"ladera": {"n": 2, "total_ms": 2, "media_us": 2, "max_us": 2}, "orilla": {"n": 1, "total_ms": 9, "media_us": 9, "max_us": 9}}


def _pasada(media, segundos=10.0, locate=None, chunks=800):
    return {"chunks": chunks, "segundos": segundos, "mspt": {"media": 1.0, "p50": 1.0, "p90": 2.0, "p99": 3.0, "max": 4.0},
            "memoria_mb": 400.0, "locate_ms": locate or {},
            "ms_por_chunk": {"media_ms": media, "p50_ms": media / 2, "p90_ms": media, "p99_ms": 2 * media, "max_ms": 3 * media,
                             "estructuras_ms": 1.0, "con_luz_ms": media + 40, "pasos_ms": {"minecraft:terrain": media}},
            "zonas": {"aldea": {"media_ms": media + 5}, "origen": {"media_ms": media - 5}}}


def test_agregar_toma_la_mediana_de_las_pasadas():
    a = c.agregar([_pasada(60, 12, {"mina": 900}), _pasada(70, 10, {"mina": 1000}), _pasada(100, 30, {"mina": 5000, "aldea": 7})])
    assert a["pasadas"] == 3 and a["chunks"] == 800
    assert a["ms_por_chunk"]["media_ms"] == 70 and a["ms_por_chunk"]["p99_ms"] == 140
    assert a["segundos"] == 12 and a["chunks_por_s"] == pytest.approx(800 / 12)
    assert a["locate_ms"] == {"aldea": 7, "mina": 1000}                    # la que falta en una pasada no cuenta
    assert a["pasos_ms"] == {"minecraft:terrain": 70} and a["zonas_ms"] == {"aldea": 75, "origen": 65}
    assert a["mspt"]["p99"] == 3.0 and a["memoria_mb"] == 400
    assert c.agregar([]) is None


def test_sobrecoste():
    con, sin = c.agregar([_pasada(66)]), c.agregar([_pasada(60)])
    assert c.sobrecoste(con, sin) == pytest.approx(0.1)
    assert c.sobrecoste(sin, con) == pytest.approx(60 / 66 - 1)
    assert c.sobrecoste(None, sin) is None and c.sobrecoste(con, c.agregar([_pasada(0)])) is None


@pytest.mark.parametrize("actual, ok", [(0.10, True), (0.15, True), (0.1749, True), (0.1751, False), (0.5, False), (-0.2, True)])
def test_comparar_con_umbral_y_margen(actual, ok):
    ref = {"sobrecoste": 0.10, "umbral_relativo": 0.25, "margen_absoluto": 0.05}     # límite 0,10 × 1,25 + 0,05 = 0,175
    r = c.comparar(actual, ref)
    assert r[0] is ok and r[1] == pytest.approx(0.175)
    assert ("REGRESIÓN" in r[2]) is (not ok)


def test_comparar_casos_limite():
    assert c.comparar(None, {"sobrecoste": 0.1})[0] is False                     # sin medida: falla
    ok, limite, texto = c.comparar(0.9, None)                                   # sin referencia: pasa y lo dice
    assert ok and limite is None and "sin referencia" in texto
    # referencia negativa (ruido: Heraldia salió más rápida): el límite parte de 0, no de un valor negativo
    assert c.comparar(0.04, {"sobrecoste": -0.03})[1] == pytest.approx(0.08)
    assert c.comparar(0.09, {"sobrecoste": -0.03})[0] is False
    # valores por defecto si la referencia no los trae
    assert c.comparar(0.0, {"sobrecoste": 0.2})[1] == pytest.approx(0.2 * 1.25 + 0.08)


def _resultado():
    sin, con = c.agregar([_pasada(60, locate={"aldea_vanilla": 180})]), c.agregar([_pasada(66, locate={"mina": 4800, "aldea_vanilla": 175})])
    return {"semilla": "heraldia", "zonas": ["aldea (32, -1344) 21×21 chunks"], "maquina": "4 núcleos, Linux", "fecha": "2026-11-16",
            "commit": "abc1234", "sin": sin, "con": con, "sobrecoste": c.sobrecoste(con, sin),
            "perfil": {"ladera": {"n": 4, "total_ms": 90.0, "media_us": 22500.0, "max_us": 38000.0},
                       "reglas": {"n": 100, "total_ms": 30.0, "media_us": 300.0, "max_us": 14000.0}}}


def test_referencia_nueva_conserva_umbral_y_margen():
    r = _resultado()
    nueva = c.referencia_nueva(r, {"sobrecoste": 0.3, "umbral_relativo": 0.4, "margen_absoluto": 0.02})
    assert nueva["sobrecoste"] == pytest.approx(0.1) and nueva["umbral_relativo"] == 0.4 and nueva["margen_absoluto"] == 0.02
    assert nueva["ms_por_chunk_con"] == 66 and nueva["ms_por_chunk_sin"] == 60 and nueva["pasadas"] == 1
    assert nueva["commit"] == "abc1234"
    defecto = c.referencia_nueva(r)
    assert defecto["umbral_relativo"] == 0.25 and defecto["margen_absoluto"] == 0.08
    json.dumps(nueva)                                                       # se puede guardar tal cual


def test_markdown_del_resumen():
    r = _resultado()
    md = c.markdown(r, c.comparar(r["sobrecoste"], {"sobrecoste": 0.08}))
    assert md.startswith("## Coste de generación de Heraldia ✅")
    assert "| ms por chunk (media, sin luz) | 60.0 | 66.0 | +10% |" in md
    assert "| mina | — | 4800 |" in md and "| aldea_vanilla | 180 | 175 |" in md
    assert md.index("| ladera |") < md.index("| reglas |")                 # perfil ordenado por tiempo total
    assert "| aldea | 65.0 | 71.0 | +9% |" in md                              # por zona
    assert "tools/smoke/coste_referencia.json" in md
    malo = c.markdown(r, c.comparar(0.9, {"sobrecoste": 0.08}))
    assert malo.startswith("## Coste de generación de Heraldia ❌") and "REGRESIÓN" in malo


def test_escribir_json_markdown_y_resumen_del_job(tmp_path, monkeypatch):
    resumen = tmp_path / "summary.md"
    monkeypatch.setenv("GITHUB_STEP_SUMMARY", str(resumen))
    r = _resultado()
    md = c.escribir(r, c.comparar(r["sobrecoste"], None), str(tmp_path / "salida"))
    guardado = json.loads((tmp_path / "salida" / "coste_generacion.json").read_text(encoding="utf-8"))
    assert guardado["sobrecoste"] == pytest.approx(0.1) and guardado["comparacion"]["ok"] is True
    assert (tmp_path / "salida" / "coste_generacion.md").read_text(encoding="utf-8") == md == resumen.read_text(encoding="utf-8")


def test_desde_un_json_y_actualizar_la_referencia(tmp_path, monkeypatch):
    """--desde rehace el resumen de una medición guardada (el artefacto de la CI) sin servidor, y con
    --actualizar-referencia la guarda; sin --sin-umbral, una regresión da código 1."""
    monkeypatch.delenv("GITHUB_STEP_SUMMARY", raising=False)
    r = _resultado()
    medido = tmp_path / "coste_generacion.json"
    medido.write_text(json.dumps(r), encoding="utf-8")
    ref = tmp_path / "ref.json"
    ref.write_text(json.dumps({"sobrecoste": 0.01, "umbral_relativo": 0.25, "margen_absoluto": 0.05}), encoding="utf-8")
    base = ["--desde", str(medido), "--referencia", str(ref), "--salida", str(tmp_path / "s")]
    assert c.main(base) == 1                                                # 0,10 > 0,01 × 1,25 + 0,05
    assert c.main(base + ["--sin-umbral"]) == 0
    assert c.main(base + ["--actualizar-referencia"]) == 0
    nueva = json.loads(ref.read_text(encoding="utf-8"))
    assert nueva["sobrecoste"] == pytest.approx(0.1) and nueva["umbral_relativo"] == 0.25
    assert c.main(base) == 0


def test_referencia_del_repositorio():
    ref = c.leer_referencia()
    assert ref is not None, "falta tools/smoke/coste_referencia.json"
    assert -0.5 < ref["sobrecoste"] < 1.0
    assert 0 < ref["umbral_relativo"] <= 1 and 0 <= ref["margen_absoluto"] <= 0.25
    assert ref["ms_por_chunk_con"] > 0 and ref["ms_por_chunk_sin"] > 0 and ref["pasadas"] >= 1


def test_cpu_de_proc_stat():
    # /proc/<pid>/stat con un nombre con espacios y paréntesis: utime (14) y stime (15) en ticks de reloj
    linea = "4242 (java (x) y) S 1 4242 4242 0 -1 4194560 1000 0 0 0 1234 566 0 0 20 0 60 0 100 0 0"
    assert c.cpu_de_stat(linea) == pytest.approx(18.0)
    assert c.cpu_de_stat(linea, hz=1000) == pytest.approx(1.8)
    assert c.cpu_proceso(-1) is None                                         # sin proceso: None, no excepción
    if os.path.isfile(f"/proc/{os.getpid()}/stat"):
        assert c.cpu_proceso(os.getpid()) >= 0


def test_la_cpu_decide_si_esta_en_las_dos():
    con, sin = c.agregar([_pasada(66)]), c.agregar([_pasada(60)])
    con["cpu_ms_por_chunk"], sin["cpu_ms_por_chunk"] = 33.0, 30.0
    assert c.sobrecoste(con, sin) == pytest.approx(0.1) and c.metrica(con) == 33
    sin["cpu_ms_por_chunk"] = None                                           # falta en una: los pasos de JFR
    assert c.sobrecoste(con, sin) == pytest.approx(0.1) and c.metrica(sin) == 60
    r = {"con": con, "sin": dict(sin, cpu_ms_por_chunk=30.0), "sobrecoste": 0.1}
    assert c.referencia_nueva(r)["medida"] == "cpu" and c.referencia_nueva(r)["ms_por_chunk_con"] == 33
