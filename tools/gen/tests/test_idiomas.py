"""idiomas.py y las traducciones de tools/gen/idiomas/: claves completas y sin sobrantes, huecos de formato iguales a
los del inglés, libros (Guía, crónica, ermita, copia de la crónica) y carteles que caben en cada idioma, y el mapa de
lenguas que lee el Java (Textos.codigo).

Sin generar el datapack, los textos que las únicas solo rellenan al construirse (p. ej. los carteles de la Atlántida)
no están: aquí se comprueba que cada traducción tiene todos los demás y que todas tienen las mismas claves; la
comparación exacta con el es_es completo la hacen la generación (writer.write -> idiomas.completar) e IdiomasTest (JUnit).
"""
import json
import os
import pytest
import caminos
import guia
import idiomas
import logros
import unicas
import writer
from unicas._comun import botin
from medianas import ermita

MODS = unicas.modules()
CODIGOS = list(idiomas.TRADUCCIONES)


class _Plantilla:
    def __init__(self, sid):
        self.entities = [(0, 0, 0, {"id": "minecraft:zombie", "Tags": [f"{logros.GUARDIAN_TAG}.{sid}"]})]


class _Reg:
    """Registro mínimo: un guardián por única (todas lo tienen; los logros de guardián dependen de ello)."""
    templates = {f"unicas/{sid}/x": _Plantilla(sid) for sid, _ in MODS}


@pytest.fixture(scope="module")
def base():
    return writer.textos(_Reg)


@pytest.fixture(scope="module")
def trad():
    return {c: idiomas.cargar(c) for c in CODIGOS}


# ------------------------------------------------------------------ lógica pura
def test_marcadores():
    assert idiomas.marcadores("sin huecos") == ([], 0)
    assert idiomas.marcadores("%s de %s") == ([1, 2], 0)
    assert idiomas.marcadores("%2$s de %1$s") == ([1, 2], 0)
    assert idiomas.marcadores("%s %%") == ([1], 1)
    assert idiomas.marcadores("%d") is None


def test_formatear_como_el_juego():
    assert idiomas.formatear("%s/%s", ["1", "2"]) == "1/2"
    assert idiomas.formatear("%2$s, %1$s", ["a", "b"]) == "b, a"
    assert idiomas.formatear("%s %%", ["50"]) == "50 %"
    assert idiomas.formatear("%s %s", ["solo"]) == "solo "


def test_errores_de_claves_y_huecos():
    es = {"a": "uno %s", "b": "dos"}
    en = {"a": "one %s", "b": "two"}
    assert idiomas.errores_claves(es, {"a": "un %s", "b": "deux"}, "fr_fr") == []
    e = idiomas.errores_claves(es, {"a": "un %s", "c": "trois"}, "fr_fr")
    assert any("falta la clave b" in x for x in e) and any("sobra la clave c" in x for x in e)
    assert any("vacía" in x for x in idiomas.errores_claves(es, {"a": " ", "b": "x"}, "fr_fr"))
    assert idiomas.errores_marcadores(en, {"a": "un %1$s"}, "fr_fr") == []
    assert idiomas.errores_marcadores(en, {"a": "un"}, "fr_fr")
    assert idiomas.errores_marcadores(en, {"a": "un %s %s"}, "fr_fr")
    assert any("desconocido" in x for x in idiomas.errores_marcadores(en, {"a": "un %d"}, "fr_fr"))


def test_texto_de_un_componente():
    textos = {"k": "Hola, %s: %s", "n": "Ysolda"}
    comp = {"translate": "k", "with": [{"translate": "n"}, 3]}
    assert idiomas.texto(comp, textos) == "Hola, Ysolda: 3"
    assert idiomas.texto({"translate": "block.minecraft.stone"}, textos) == idiomas.RELLENO
    assert idiomas.texto({"text": "a", "extra": [{"text": "b"}]}, textos) == "ab"


def test_paginas_y_carteles_dentro_de_cualquier_objeto():
    libro = botin.libro([{"translate": "p1"}, {"translate": "p2"}], {"translate": "n"}, "Título", "Autor")
    atril = {"Book": {"components": {"minecraft:written_book_content": {"pages": [{"raw": {"translate": "p3"}}]}}}}
    paginas = idiomas.paginas_de_libros([("botín", {"pools": [{"entries": [libro]}]}), ("atril", atril)])
    assert [p["translate"] for _, p in paginas] == ["p1", "p2", "p3"]
    cartel = {"front_text": {"messages": [{"translate": "c1"}, {"text": ""}]}, "back_text": {"messages": [{"translate": "c2"}]}}
    assert idiomas.claves_de_carteles([cartel, {"otra": [cartel]}]) == {"c1", "c2"}


def test_pagina_o_cartel_que_no_cabe_falla():
    largo = "palabra " * 60
    assert idiomas.errores_libros([("x", {"translate": "p"})], {"p": largo}, "fr_fr")
    assert not idiomas.errores_libros([("x", {"translate": "p"})], {"p": "corta"}, "fr_fr")
    assert idiomas.errores_carteles({"c"}, {"c": "Une ligne beaucoup trop longue"}, "fr_fr")
    assert not idiomas.errores_carteles({"c"}, {"c": "Court"}, "fr_fr")


def test_cartel_de_90_px_cabe_y_de_91_no():
    exacta = "x" * 15                      # 15 × 6 px = 90 px
    assert botin.ancho(exacta) == idiomas.CARTEL_ANCHO
    assert not idiomas.errores_carteles({"c"}, {"c": exacta}, "es_es")
    assert idiomas.errores_carteles({"c"}, {"c": exacta + "!"}, "es_es")      # 92 px


def test_cartel_de_es_en_que_no_cabe_hace_fallar_la_generacion(monkeypatch):
    monkeypatch.setattr(idiomas, "cargar", lambda c: {"c": "Corto"})
    for largo in ("es_es", "en_us"):
        base = {"es_es": {"c": "Corto"}, "en_us": {"c": "Short"}}
        base[largo]["c"] = "Una línea larguísima de cartel"
        with pytest.raises(SystemExit, match=f"{largo}: la línea de cartel c no cabe"):
            idiomas.completar(base, carteles={"c"})


def test_traduccion_de_cartel_que_no_cabe_falla_aunque_es_sea_mas_ancha(monkeypatch):
    # antes se toleraba si es/en ya se pasaban; ahora el límite es siempre 90 px
    base = {"es_es": {"c": "Una línea larguísima de cartel"}, "en_us": {"c": "x"}}
    assert idiomas.errores_carteles({"c"}, {"c": "Une ligne trop longue ici"}, "fr_fr")
    monkeypatch.setattr(idiomas, "cargar", lambda c: {"c": "Une ligne trop longue ici"})
    base["es_es"]["c"] = "Corto"
    with pytest.raises(SystemExit, match="fr_fr: la línea de cartel c no cabe"):
        idiomas.completar(base, carteles={"c"})


def test_completar_falla_con_una_traduccion_incompleta(monkeypatch):
    base = {"es_es": {"a": "uno %s", "b": "dos"}, "en_us": {"a": "one %s", "b": "two"}}
    monkeypatch.setattr(idiomas, "cargar", lambda c: {"a": "x %s", "b": "y"})
    out = idiomas.completar(base)
    assert set(out) == set(idiomas.todos()) and out["fr_fr"] == {"a": "x %s", "b": "y"}
    monkeypatch.setattr(idiomas, "cargar", lambda c: {"a": "x"})
    with pytest.raises(SystemExit, match="falta la clave b"):
        idiomas.completar(base)


def test_ordenar_como_el_espanol():
    assert list(idiomas.ordenar({"b": 1, "a": 2}, {"a": "x", "b": "y"})) == ["b", "a"]


# ------------------------------------------------------------------ idiomas y lenguas (Textos.codigo en Java)
def test_lista_de_idiomas():
    assert idiomas.BASE == ("es_es", "en_us")
    assert set(CODIGOS) >= {"fr_fr", "de_de", "it_it", "pt_br", "ca_es", "gl_es"}
    assert idiomas.todos() == list(idiomas.BASE) + CODIGOS
    lenguas = [idiomas.lengua(c) for c in idiomas.todos()]
    assert len(lenguas) == len(set(lenguas)), "dos idiomas de la misma lengua: Textos.codigo no sabría cuál elegir"


def test_mapa_de_lenguas():
    m = idiomas.lenguas()
    assert m["es"] == "es_es" and m["en"] == "en_us" and m["fr"] == "fr_fr" and m["pt"] == "pt_br"
    assert m["ca"] == m["val"] == "ca_es" and m["gl"] == "gl_es" and m["esan"] == "es_es"
    assert set(m.values()) == set(idiomas.todos())


def test_cada_traduccion_existe_y_es_json_plano(trad):
    for c in CODIGOS:
        assert os.path.exists(idiomas.ruta(c)), c
        assert trad[c] and all(isinstance(k, str) and isinstance(v, str) for k, v in trad[c].items()), c


# ------------------------------------------------------------------ las traducciones reales
def test_todas_las_traducciones_tienen_las_mismas_claves(trad):
    claves = {c: set(t) for c, t in trad.items()}
    primera = claves[CODIGOS[0]]
    for c in CODIGOS[1:]:
        assert claves[c] == primera, (c, sorted(claves[c] ^ primera)[:20])


@pytest.mark.parametrize("codigo", CODIGOS)
def test_traduccion_completa(codigo, base, trad):
    faltan = [k for k in base["es_es"] if k not in trad[codigo]]
    assert faltan == [], faltan[:20]
    assert all(v.strip() for v in trad[codigo].values())


@pytest.mark.parametrize("codigo", CODIGOS)
def test_mismos_huecos_que_el_ingles(codigo, base, trad):
    assert idiomas.errores_marcadores(base["en_us"], trad[codigo], codigo) == []


def test_las_claves_de_mas_son_de_las_unicas(base, trad):
    """Las que no salen sin construir son textos de módulos de unicas/ que se rellenan en build()."""
    prefijos = tuple(f"heraldia.{sid}." for sid, _ in MODS) + tuple(f"heraldia.unicas.{sid}." for sid, _ in MODS)
    extra = [k for k in trad[CODIGOS[0]] if k not in base["es_es"]]
    assert all(k.startswith(prefijos) for k in extra), [k for k in extra if not k.startswith(prefijos)][:20]


@pytest.mark.parametrize("codigo", CODIGOS)
def test_la_guia_cabe(codigo, trad):
    assert guia.errores(MODS, {codigo: trad[codigo]}) == []


def test_la_guia_cuenta_las_entradas_con_el_peor_idioma(trad):
    solo_base, todos = guia.datos(MODS), guia.datos(MODS, trad)
    assert todos["nombres_por_pagina"] <= solo_base["nombres_por_pagina"]
    assert todos["pistas_por_pagina"] <= solo_base["pistas_por_pagina"]
    for c in CODIGOS:
        assert todos["pistas_por_pagina"] <= guia.datos(MODS, {c: trad[c]})["pistas_por_pagina"]


def _libros():
    """Los libros del botín que salen sin construir: los pliegos de la crónica, el diario de la ermita y las copias de la
    crónica de los tratos (los de los atriles de las plantillas los mide la generación)."""
    objetos = [(sid, t) for sid, t in writer.history_tables(MODS).items()]
    objetos += [("ermita", ermita.LOOT)]
    import tratos
    objetos += [("tratos", tratos.objetos(MODS))]
    return idiomas.paginas_de_libros(objetos)


def test_hay_libros_que_medir():
    paginas = _libros()
    assert len(paginas) >= 3 * len(MODS)
    assert any(p.get("translate") == "heraldia.historia.final" for _, p in paginas)


@pytest.mark.parametrize("codigo", CODIGOS)
def test_libros_caben(codigo, base, trad):
    assert idiomas.errores_libros(_libros(), {**base["en_us"], **trad[codigo]}, codigo) == []


@pytest.mark.parametrize("codigo", CODIGOS)
def test_tablon_cabe(codigo, trad):
    import tablon
    for k in tablon.TEXTOS:
        if k.startswith("p"):
            t = idiomas.formatear(trad[codigo][f"{tablon.K}.{k}"], [idiomas.RELLENO] * 4)
            assert botin.lineas_libro(t) <= botin.LIBRO_LINEAS, (k, t)


@pytest.mark.parametrize("codigo", CODIGOS)
def test_carteles_caben(codigo, base, trad):
    carteles = {k for k in trad[codigo] if ".cartel." in k and k in base["es_es"]}
    assert carteles
    assert idiomas.errores_carteles(carteles, trad[codigo], codigo) == []
    for c in idiomas.BASE:
        assert idiomas.errores_carteles(carteles, base[c], c) == []


@pytest.mark.parametrize("codigo", CODIGOS)
def test_carteles_de_los_caminos(codigo, trad):
    for k in caminos.LANG["es_es"]:
        t = trad[codigo][k]
        assert idiomas.marcadores(t) == ([1], 0), (k, t)
        assert len(idiomas.formatear(t, ["1999"])) <= 15, (k, t)      # cabe en una línea de cartel


@pytest.mark.parametrize("codigo", CODIGOS)
def test_comandos_sin_traducir(codigo, base, trad):
    """Un comando que sale en un texto (/heraldia guia, /heraldia arena...) sigue igual en la traducción."""
    import re
    for k, es in base["es_es"].items():
        for cmd in re.findall(r"/heraldia(?: \w+)?", es):
            assert cmd in trad[codigo][k], (k, cmd, trad[codigo][k])


def test_ficheros_de_traduccion_en_su_formato():
    """JSON con sangría 2 y sin escapar los acentos, como los escribe idiomas (diffs legibles)."""
    for c in CODIGOS:
        with open(idiomas.ruta(c), encoding="utf-8") as f:
            texto = f.read()
        assert texto == json.dumps(json.loads(texto), indent=2, ensure_ascii=False) + "\n", c
