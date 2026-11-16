"""tools/smoke/server_smoke.py: descargas del servidor de prueba (una descarga cortada no se queda en la caché) y las
funciones puras de tools/smoke/mundo_existente.py (lectura de secciones y comparación de chunks guardados)."""
import io, os, sys, zipfile
import pytest

SMOKE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "smoke")
sys.path.insert(0, SMOKE)
import server_smoke as s  # noqa: E402
import mundo_existente as me  # noqa: E402


def _jar():
    b = io.BytesIO()
    with zipfile.ZipFile(b, "w") as z:
        z.writestr("fabric.mod.json", "{}" * 2000)
    return b.getvalue()


class _Resp(io.BytesIO):
    def __init__(self, data, largo):
        super().__init__(data)
        self.headers = {"Content-Length": str(largo)}

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def test_jar_valido(tmp_path):
    bueno, cortado = tmp_path / "a.jar", tmp_path / "b.jar"
    bueno.write_bytes(_jar())
    cortado.write_bytes(_jar()[:200])
    assert s.jar_valido(str(bueno))
    assert not s.jar_valido(str(cortado))
    assert not s.jar_valido(str(tmp_path / "no.jar"))


def test_descarga_cortada_se_repite(tmp_path, monkeypatch):
    jar = _jar()
    respuestas = [_Resp(jar[:300], len(jar)), _Resp(jar, len(jar))]       # la primera, cortada por la red
    monkeypatch.setattr(s.urllib.request, "urlopen", lambda url: respuestas.pop(0))
    monkeypatch.setattr(s.time, "sleep", lambda t: None)
    dest = tmp_path / "fabric-api.jar"
    s.download("https://ejemplo/fabric-api.jar", str(dest))
    assert dest.read_bytes() == jar and not respuestas


def test_jar_corrupto_en_cache_se_vuelve_a_descargar(tmp_path, monkeypatch):
    jar = _jar()
    dest = tmp_path / "fabric-api.jar"
    dest.write_bytes(jar[:300])                       # lo que dejó una ejecución anterior
    monkeypatch.setattr(s.urllib.request, "urlopen", lambda url: _Resp(jar, len(jar)))
    s.download("https://ejemplo/fabric-api.jar", str(dest))
    assert dest.read_bytes() == jar


def test_descarga_siempre_cortada_falla(tmp_path, monkeypatch):
    jar = _jar()
    monkeypatch.setattr(s.urllib.request, "urlopen", lambda url: _Resp(jar[:300], len(jar)))
    monkeypatch.setattr(s.time, "sleep", lambda t: None)
    with pytest.raises(SystemExit):
        s.download("https://ejemplo/fabric-api.jar", str(tmp_path / "x.jar"), intentos=2)
    assert not (tmp_path / "x.jar").exists()


# ------------------------------------------------------------------ mundo_existente.py
def _seccion(paleta, indices):
    """block_states de una sección con `paleta` (nombres) e `indices` (4096), empaquetados como el juego."""
    bits = max(4, (len(paleta) - 1).bit_length())
    por, data = 64 // bits, []
    for i in range(0, 4096, por):
        v = 0
        for k, idx in enumerate(indices[i:i + por]):
            v |= idx << (k * bits)
        data.append(v - (1 << 64) if v >= 1 << 63 else v)
    return {"palette": [{"Name": n} for n in paleta], "data": data}


def test_estados_de_una_seccion():
    assert me.estados(None) is None
    assert me.estados({"palette": [{"Name": "minecraft:air"}]}) == [("minecraft:air", ())] * 4096
    ind = [i % 3 for i in range(4096)]
    est = me.estados(_seccion(["minecraft:air", "minecraft:stone", "minecraft:dirt"], ind))
    assert len(est) == 4096 and est[0][0] == "minecraft:air" and est[4095][0] == ["minecraft:air", "minecraft:stone", "minecraft:dirt"][4095 % 3]
    # 17 estados: 5 bits, 12 por long (sin repartir entre dos)
    pal = [f"minecraft:b{i}" for i in range(17)]
    ind = [(i * 7) % 17 for i in range(4096)]
    assert [e[0] for e in me.estados(_seccion(pal, ind))] == [pal[i] for i in ind]


def _huella(paleta, indices, be=None):
    return me.huella({"sections": [{"Y": 0, "block_states": _seccion(paleta, indices), "biomes": {"palette": ["minecraft:plains"]}}],
                      "block_entities": be or [], "Heightmaps": {}, "structures": {"References": {}, "starts": {}},
                      "LastUpdate": 5, "InhabitedTime": 9, "Status": "minecraft:full"})


def test_misma_seccion_con_otra_paleta_no_cambia():
    ind = [i % 2 for i in range(4096)]
    a = _huella(["minecraft:air", "minecraft:stone"], ind)
    b = _huella(["minecraft:stone", "minecraft:air"], [1 - i for i in ind])
    assert me.diferencias(a, b) == []


def test_un_bloque_cambiado_se_detecta():
    ind = [0] * 4096
    a = _huella(["minecraft:air", "minecraft:stone"], ind)
    ind2 = list(ind)
    ind2[(5 << 8) | (3 << 4) | 2] = 1                  # x=2, y=5, z=3
    d = me.diferencias(a, _huella(["minecraft:air", "minecraft:stone"], ind2))
    assert len(d) == 1 and "1 bloques cambian" in d[0] and "x=2 y=5 z=3" in d[0] and "minecraft:stone" in d[0]


def test_bloques_con_datos_y_campos_volatiles():
    ind = [0] * 4096
    cofre = {"id": "minecraft:chest", "x": 1, "y": 2, "z": 3, "LootTable": "heraldia:unicas/x"}
    a = _huella(["minecraft:air"], ind, [cofre])
    assert me.diferencias(a, _huella(["minecraft:air"], ind, [dict(cofre, keepPacked=1)])) == []
    d = me.diferencias(a, _huella(["minecraft:air"], ind, [dict(cofre, LootTable="heraldia:otra")]))
    assert len(d) == 1 and "LootTable" in d[0]
    assert me.diferencias(a, _huella(["minecraft:air"], ind)) != []


def test_paleta_de_cadenas_de_26_3():
    ind = [i % 2 for i in range(4096)]
    sec = _seccion(["minecraft:air", "minecraft:stone"], ind)
    sec["palette"] = ["minecraft:air", "minecraft:stone"]               # como lo guarda 26.3
    assert [e[0] for e in me.estados(sec)] == [["minecraft:air", "minecraft:stone"][i] for i in ind]


def test_lista_mixta_de_26_3():
    mixta = [{"": "minecraft:air"}, {"id": "minecraft:oak_log", "properties": {"axis": "y"}}]
    assert me._plano(mixta) == ["minecraft:air", {"id": "minecraft:oak_log", "properties": {"axis": "y"}}]
    sec = {"palette": me._plano(mixta), "data": [0x10]}                 # índice 0 y luego 1
    est = me.estados(sec)
    assert est[0] == ("minecraft:air", ()) and est[1] == ("minecraft:oak_log", (("axis", "y"),))
