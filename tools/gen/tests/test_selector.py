"""tools/test.py: selección de pruebas de servidor por rutas cambiadas (la misma que usa la CI) y reparto en grupos."""
import json, os, subprocess, sys
import pytest

TOOLS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
# tools/test.py por su ruta (el nombre «test» chocaría con el paquete test de la biblioteca estándar)
import importlib.util  # noqa: E402
_spec = importlib.util.spec_from_file_location("heraldia_test_selector", os.path.join(TOOLS, "test.py"))
sel = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(sel)

TODAS = sel.descubrir()
J = sel.JAVA
TODA_UNICA = set(sel.DE_TODA_UNICA)
COMPAT = [p for p in TODAS if sel.es_compat(p)]
SIN_COMPAT = [p for p in TODAS if not sel.es_compat(p)]


def elige(*rutas):
    return sel.seleccionar(list(rutas), TODAS)


def test_descubre_todas_las_pruebas_de_servidor():
    assert sel.HUMO not in TODAS and len(TODAS) >= 24
    assert "tools/gen/unicas/castillo/prueba_redstone.py" in TODAS and "tools/smoke/trofeos.py" in TODAS
    for sid, ps in sel.SMOKE_DE_UNICA.items():
        assert all(p in TODAS for p in ps), sid
    assert all(p in TODAS for p in sel.DE_TODA_UNICA + sel.ALDEAS)
    for p in TODAS:                                       # toda prueba conocida tiene duración medida
        assert p in sel.DURACION_S, p
    assert "tools/smoke/modrinth.py" not in TODAS and sel.COMPAT not in TODAS   # módulo común; la de compat, por grupos
    assert {p.split("::")[1] for p in COMPAT} == set(sel.grupos_compat()) and "tools/smoke/compat_mods.py::base" in COMPAT


@pytest.mark.parametrize("rutas", [
    ["docs/DESARROLLO.md"], ["README.md", "CHANGELOG.md"], ["tools/gen/tests/test_core.py"],
    ["src/test/java/io/github/albertosa23/heraldia/config/X.java"], ["src/client/java/x/ConfigScreen.java"],
    ["tools/gen/render.py"], ["tools/gen/loot.py"], [J + "comando/InfoCommand.java"],
])
def test_sin_pruebas_de_servidor(rutas):
    assert elige(*rutas) == (False, [])


@pytest.mark.parametrize("ruta", [
    "tools/gen/unicas/_comun/redstone.py", "tools/gen/unicas/__init__.py", "tools/gen/writer.py", "tools/gen/core.py",
    "tools/gen/pack.py", "tools/gen/lint.py", "tools/gen/validate.py", "tools/gen/build.py", "tools/gen/opciones.py",
    "tools/smoke/server_smoke.py", "tools/test.py", ".github/workflows/ci.yml", ".github/actions/preparar/action.yml",
    "build.gradle", "gradle.properties", "src/main/resources/fabric.mod.json", J + "Heraldia.java",
    J + "config/GridPlacement.java", J + "comun/Alturas.java", J + "loot/CofrePorJugador.java",
    J + "mixin/ChunkGeneratorMixin.java", J + "unicas/paquete_nuevo/X.java", "fichero/que/nadie/conoce.txt",
])
def test_codigo_comun_pide_la_bateria_completa(ruta):
    """La batería completa de un PR lleva las de compatibilidad solo si lo cambiado es de colocación (COMPAT_RUTAS)."""
    completa, pruebas = elige(ruta)
    de_colocacion = any(sel.fnmatch.fnmatch(ruta, p) for p in sel.COMPAT_RUTAS)
    assert completa and pruebas == (TODAS if de_colocacion else SIN_COMPAT)


@pytest.mark.parametrize("ruta", [J + "mixin/ChunkGeneratorMixin.java", J + "config/GridPlacement.java",
                                  J + "comun/ZonaAjenas.java", "gradle.properties"])
def test_colocacion_comun_arrastra_las_de_compatibilidad(ruta):
    assert elige(ruta) == (True, TODAS)


def test_compatibilidad_solo_con_sus_rutas():
    assert elige(sel.COMPAT) == (False, COMPAT)                                  # la propia prueba: todos sus grupos
    assert elige("tools/smoke/compat_mods.py::rendimiento") == (False, ["tools/smoke/compat_mods.py::rendimiento"])
    completa, p = elige("tools/smoke/modrinth.py")                               # los mods fijados: quien los descarga
    assert not completa and set(p) == set(COMPAT) | {"tools/smoke/trofeos.py", "tools/smoke/historia.py",
                                                      "tools/smoke/aldeas_vida.py", "tools/smoke/terralith_biomas.py"}
    assert set(elige("tools/gen/biomas.py")[1]) == {"tools/smoke/terralith_biomas.py"} | set(COMPAT)
    assert elige("tools/gen/writer.py") == (True, SIN_COMPAT)                    # común, pero no de colocación
    assert elige(J + "comando/InfoCommand.java") == (False, [])


def test_orden_de_una_prueba_por_grupo():
    assert sel.orden("tools/smoke/compat_mods.py::terreno")[1:] == ["--grupo", "terreno"]
    assert sel.orden("tools/smoke/compat_mods.py::terreno")[0].endswith(os.path.join("tools", "smoke", "compat_mods.py"))
    assert sel.orden("tools/smoke/trofeos.py")[1:] == []
    assert sel.nombre(["tools/smoke/compat_mods.py::base", "tools/smoke/galeon_test.py"]) == "compat base + galeon_test"


def test_una_unica_con_carpeta():
    completa, p = elige("tools/gen/unicas/castillo/planos.py")
    assert not completa and set(p) == {"tools/gen/unicas/castillo/prueba_redstone.py"} | TODA_UNICA


def test_una_unica_de_un_solo_modulo_y_su_prueba_en_smoke():
    completa, p = elige("tools/gen/unicas/observatorio.py")
    assert not completa and set(p) == {"tools/smoke/observatorio_smoke.py"} | TODA_UNICA


def test_unica_sin_prueba_propia():
    completa, p = elige("tools/gen/unicas/acueducto/obra.py")
    assert not completa and set(p) == TODA_UNICA


def test_java_de_una_unica():
    assert set(elige(J + "unicas/isla/IslaStructure.java")[1]) == {"tools/gen/unicas/isla_corsario/prueba_servidor.py"} | TODA_UNICA
    # la zona de la isla también decide qué estructuras ajenas nacen cerca: arrastra las de compatibilidad
    assert set(elige(J + "unicas/isla/IslaZona.java")[1]) == {"tools/gen/unicas/isla_corsario/prueba_servidor.py"} | TODA_UNICA | set(COMPAT)
    assert set(elige(J + "unicas/galeon/GaleonStructure.java")[1]) == {"tools/smoke/galeon_test.py"} | TODA_UNICA
    assert set(elige(J + "unicas/mina/Mina.java")[1]) == {"tools/gen/unicas/mina_perdida/prueba_servidor.py"} | TODA_UNICA


def test_cambiar_una_prueba_solo_ejecuta_esa():
    assert elige("tools/smoke/palacio_redstone.py") == (False, ["tools/smoke/palacio_redstone.py"])
    assert elige("tools/gen/unicas/piramide/prueba_servidor.py") == (False, ["tools/gen/unicas/piramide/prueba_servidor.py"])


def test_aldeas_y_datos():
    assert set(elige("tools/gen/houses.py")[1]) == set(sel.ALDEAS)
    assert set(elige(J + "aldeas/AldeaStructure.java")[1]) == set(sel.ALDEAS)
    assert elige("tools/gen/tablon.py")[1] == ["tools/smoke/aldeas_vida.py"]
    assert "tools/smoke/terralith_biomas.py" in elige("tools/gen/biomas.py")[1]
    assert elige(J + "mixin/ZombieMixin.java")[1] == ["tools/smoke/guardianes_adultos.py"]
    assert elige(J + "comun/Anclaje.java")[1] == ["tools/smoke/guardianes_anclados.py"]
    assert elige(J + "comun/HastaElSueloProcessor.java")[0]          # el resto de comun/: batería completa
    assert set(elige("tools/gen/logros.py")[1]) == {"tools/smoke/trofeos.py", "tools/smoke/historia.py", "tools/smoke/aldeas_vida.py"}


def test_union_de_varios_cambios_y_uno_comun_lo_arrastra_todo():
    completa, p = elige("tools/gen/unicas/palacio/plano.py", "tools/gen/tablon.py", "docs/x.md")
    assert not completa and set(p) == {"tools/smoke/palacio_redstone.py", "tools/smoke/aldeas_vida.py"} | TODA_UNICA
    assert elige("tools/gen/unicas/palacio/plano.py", "tools/gen/writer.py") == (True, SIN_COMPAT)
    assert elige("tools/gen/writer.py", J + "config/UniqueSeparation.java") == (True, TODAS)


def test_grupos_reparten_sin_pasar_del_tope():
    g = sel.grupos(TODAS)
    assert sorted(p for x in g for p in x) == TODAS                       # cada prueba una vez
    largo = max(sel.DURACION_S.values())
    tope = max(sel.TOPE_GRUPO_S, largo)
    assert all(sum(sel.DURACION_S[p] for p in x) <= tope for x in g)
    assert len(g) <= 18                     # con la compilación y la de humo, en una tanda de 20 jobs gratis
    assert len(sel.grupos(SIN_COMPAT)) <= 12  # un PR con cambios comunes (sin las de compatibilidad) deja máquinas libres
    assert sel.grupos([]) == [] and sel.grupos(TODAS) == g                # determinista
    assert sel.grupos(["x/nueva.py"]) == [["x/nueva.py"]]                  # sin duración medida: DEFECTO_S


def test_matriz_y_nombres():
    m = sel.matriz(False, ["tools/smoke/galeon_test.py", "tools/gen/unicas/piramide/prueba_servidor.py"])
    assert m["include"] == [{"nombre": "piramide + galeon_test",
                             "pruebas": "tools/gen/unicas/piramide/prueba_servidor.py tools/smoke/galeon_test.py"}]
    assert sel.matriz(False, []) == {"include": []}


def test_ci_matriz_por_linea_de_ordenes():
    """--ci-matriz --completa da todas las pruebas en grupos, como en push a develop."""
    out = subprocess.run([sys.executable, os.path.join(TOOLS, "test.py"), "--ci-matriz", "--completa"],
                         capture_output=True, text=True, check=True).stdout
    m = json.loads(out)
    assert m["completa"] is True
    assert sorted(p for g in m["include"] for p in g["pruebas"].split()) == TODAS


def test_medianas():
    mobs = ["tools/smoke/estructuras_medianas.py", "tools/smoke/guardianes_adultos.py", "tools/smoke/guardianes_anclados.py"]
    assert elige("tools/gen/medianas/posada.py") == (False, mobs)       # sus mobs entran en las pruebas de anclados
    assert elige("tools/gen/medianas/__init__.py") == (False, mobs)
    assert elige("tools/smoke/estructuras_medianas.py") == (False, ["tools/smoke/estructuras_medianas.py"])
    completa, p = elige(J + "comun/Medianas.java")      # decide dónde salen: también las de compatibilidad
    assert not completa and set(p) == {"tools/smoke/estructuras_medianas.py"} | set(COMPAT)
