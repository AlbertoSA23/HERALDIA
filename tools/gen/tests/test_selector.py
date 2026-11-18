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
    ["tools/gen/render.py"], ["tools/gen/loot.py"], [J + "command/KeyCommand.java"],
])
def test_sin_pruebas_de_servidor(rutas):
    assert elige(*rutas) == (False, [])


@pytest.mark.parametrize("ruta", [
    "tools/gen/unicas/_comun/redstone.py", "tools/gen/unicas/__init__.py", "tools/gen/writer.py", "tools/gen/core.py",
    "tools/gen/pack.py", "tools/gen/lint.py", "tools/gen/validate.py", "tools/gen/build.py", "tools/gen/opciones.py",
    "tools/smoke/server_smoke.py", "tools/test.py", ".github/workflows/ci.yml", ".github/actions/preparar/action.yml",
    "build.gradle", "gradle.properties", "src/main/resources/fabric.mod.json", J + "Heraldia.java",
    J + "config/GridPlacement.java", J + "common/Heights.java", J + "loot/PerPlayerChest.java",
    J + "mixin/ChunkGeneratorMixin.java", J + "unicas/paquete_nuevo/X.java", "fichero/que/nadie/conoce.txt",
])
def test_codigo_comun_pide_la_bateria_completa(ruta):
    """La batería completa de un PR lleva las de compatibilidad solo si lo cambiado es de colocación (COMPAT_RUTAS)."""
    completa, pruebas = elige(ruta)
    de_colocacion = any(sel.fnmatch.fnmatch(ruta, p) for p in sel.COMPAT_RUTAS)
    assert completa and pruebas == (TODAS if de_colocacion else SIN_COMPAT)


@pytest.mark.parametrize("ruta", [J + "mixin/ChunkGeneratorMixin.java", J + "config/GridPlacement.java",
                                  J + "common/ForeignZone.java", "gradle.properties"])
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
    assert elige(J + "command/InfoCommand.java") == (False, ["tools/smoke/admin.py"])   # no es de colocación


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
    assert set(elige(J + "uniques/island/IslandStructure.java")[1]) == {"tools/gen/unicas/isla_corsario/prueba_servidor.py"} | TODA_UNICA
    # la zona de la isla también decide qué estructuras ajenas nacen cerca: arrastra las de compatibilidad
    assert set(elige(J + "uniques/island/IslandZone.java")[1]) == {"tools/gen/unicas/isla_corsario/prueba_servidor.py"} | TODA_UNICA | set(COMPAT)
    assert set(elige(J + "uniques/galleon/GalleonStructure.java")[1]) == {"tools/smoke/galeon_test.py"} | TODA_UNICA
    assert set(elige(J + "uniques/mine/Mine.java")[1]) == {"tools/gen/unicas/mina_perdida/prueba_servidor.py"} | TODA_UNICA


def test_cambiar_una_prueba_solo_ejecuta_esa():
    assert elige("tools/smoke/palacio_redstone.py") == (False, ["tools/smoke/palacio_redstone.py"])
    assert elige("tools/gen/unicas/piramide/prueba_servidor.py") == (False, ["tools/gen/unicas/piramide/prueba_servidor.py"])


def test_aldeas_y_datos():
    assert set(elige("tools/gen/houses.py")[1]) == set(sel.ALDEAS)
    assert set(elige(J + "villages/VillageStructure.java")[1]) == set(sel.ALDEAS)
    assert elige("tools/gen/tablon.py")[1] == ["tools/smoke/aldeas_vida.py"]
    assert "tools/smoke/terralith_biomas.py" in elige("tools/gen/biomas.py")[1]
    assert elige(J + "mixin/ZombieMixin.java")[1] == ["tools/smoke/guardianes_adultos.py"]
    assert elige(J + "common/Anchoring.java")[1] == ["tools/smoke/guardianes_anclados.py"]
    assert elige(J + "common/ToGroundProcessor.java")[0]          # el resto de comun/: batería completa
    assert set(elige("tools/gen/logros.py")[1]) == {"tools/smoke/trofeos.py", "tools/smoke/historia.py", "tools/smoke/aldeas_vida.py"}
    assert elige(J + "roads/RoadLayout.java") == (False, ["tools/smoke/caminos.py"])
    assert elige("tools/gen/caminos.py") == (False, ["tools/smoke/caminos.py"])


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
    assert len(sel.grupos(SIN_COMPAT)) <= 14  # un PR con cambios comunes (sin las de compatibilidad) deja máquinas libres (14 con T46: + compilación, humo, JUnit largas, coste y selección = 19 de 20)
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
    mobs = ["tools/smoke/estructuras_medianas.py", "tools/smoke/guardianes_adultos.py", "tools/smoke/guardianes_anclados.py",
            "tools/smoke/nether_end.py"]
    assert elige("tools/gen/medianas/posada.py") == (False, mobs)       # sus mobs entran en las pruebas de anclados
    assert elige("tools/gen/medianas/__init__.py") == (False, mobs)
    assert elige("tools/smoke/estructuras_medianas.py") == (False, ["tools/smoke/estructuras_medianas.py"])
    completa, p = elige(J + "common/MediumStructures.java")      # decide dónde salen: también las de compatibilidad
    assert not completa and set(p) == {"tools/smoke/estructuras_medianas.py", "tools/smoke/nether_end.py"} | set(COMPAT)


def test_nether_end():
    """T44: el contenido del Nether y el End pasa su prueba de servidor."""
    ne = "tools/smoke/nether_end.py"
    assert elige(J + "dimensions/DimensionStructure.java") == (False, [ne])
    completa, p = elige("tools/gen/dimensiones.py")
    assert not completa and ne in p and "tools/smoke/estructuras_medianas.py" in p
    completa, p = elige("tools/gen/unicas/ciudadela_ceniza.py")
    assert not completa and ne in p and "tools/smoke/trofeos.py" in p
    assert elige(ne) == (False, [ne])


def test_minas():
    m = ["tools/smoke/entradas_mina.py"]
    assert elige("tools/gen/minas/planos.py") == (False, m)
    assert elige("tools/gen/minas/__init__.py") == (False, m)
    assert elige(J + "mines/Hillside.java") == (False, sorted(m + ["tools/smoke/costa.py"])), "la regla de la costa es la de las minas"
    assert elige("tools/smoke/entradas_mina.py") == (False, m)
    # T36: la caché compartida de alturas y el /locate en paralelo (solo los usan las minas)
    assert elige(J + "common/HeightCache.java") == (False, m)
    assert elige(J + "mixin/ChunkGeneratorLocateMixin.java") == (False, m)
    assert elige(J + "mines/ParallelLocate.java") == (False, sorted(m + ["tools/smoke/costa.py"]))


def test_costa():
    c = ["tools/smoke/costa.py"]
    mobs = c + ["tools/smoke/guardianes_adultos.py", "tools/smoke/guardianes_anclados.py"]
    assert elige("tools/gen/litoral/obras.py") == (False, mobs), "el ahogado del semihundido"
    assert elige("tools/gen/litoral/__init__.py") == (False, mobs)
    assert elige(J + "coast/Shoreline.java") == (False, c)
    assert elige("tools/smoke/costa.py") == (False, c)
    assert sel.coste([J + "coast/Shoreline.java"]) and sel.coste(["tools/gen/litoral/obras.py"])


def test_perfiles():
    p = ["tools/smoke/perfiles.py"]
    assert elige(J + "config/Profiles.java") == (False, p)
    assert elige(J + "command/ProfileCommand.java") == (False, p)
    assert elige("tools/smoke/perfiles.py") == (False, p)
    assert elige(J + "config/HeraldiaConfig.java")[0]          # el resto de la configuración: común, batería completa
    assert elige("tools/gen/opciones.py")[0]


def test_guia_del_heraldo():
    assert elige(J + "command/Guide.java") == (False, ["tools/smoke/guia.py"])
    assert elige(J + "command/Texts.java") == (False, ["tools/smoke/guia.py"])
    assert elige("tools/gen/guia.py") == (False, ["tools/smoke/guia.py"])
    assert elige("tools/smoke/guia.py") == (False, ["tools/smoke/guia.py"])
    # idiomas: las traducciones y su comprobación solo pasan la de la Guía (el respaldo en el idioma del cliente)
    assert elige("tools/gen/idiomas.py") == (False, ["tools/smoke/guia.py"])
    assert elige("tools/gen/idiomas/fr_fr.json", "tools/gen/idiomas/gl_es.json") == (False, ["tools/smoke/guia.py"])
    assert elige("README.fr.md", "docs/CONFIGURACION.md", "tools/gen/tests/test_readme.py") == (False, [])
    assert elige(J + "command/KeyCommand.java") == (False, [])       # el resto de comando/: solo la de humo


def test_herramientas_de_administracion():
    admin = (False, ["tools/smoke/admin.py"])
    for r in ("command/ReviewCommand.java", "command/Revision.java", "command/SafeSpot.java",
              "command/State.java", "command/StatusCommand.java", "command/ReloadCommand.java",
              "command/InfoCommand.java", "config/Reload.java"):
        assert elige(J + r) == admin, r
    assert elige("tools/gen/admin.py") == admin
    assert elige("tools/smoke/admin.py") == admin
    assert elige(J + "config/HeraldiaConfig.java")[0]           # el resto de config/: común, batería completa


def test_comandos_en_ingles_y_aviso_de_version():
    update = (False, ["tools/smoke/update_check.py"])
    for r in ("command/VersionNotice.java", "version/Version.java", "version/Releases.java", "version/Notified.java"):
        assert elige(J + r) == update, r
    assert elige("tools/smoke/update_check.py") == update
    comandos = (False, sorted(["tools/smoke/update_check.py", "tools/smoke/admin.py", "tools/smoke/guia.py", "tools/smoke/arena.py",
                               "tools/smoke/arena_modos.py"]))
    for r in (J + "command/HeraldiaCommands.java", J + "command/Alias.java", J + "mixin/CommandsMixin.java", "tools/gen/comandos.py"):
        assert (elige(r)[0], sorted(elige(r)[1])) == comandos, r


def test_botin_que_se_repone_y_dificultad():
    assert elige(J + "loot/RestockedLoot.java") == (False, ["tools/smoke/botin_reponer.py"])
    assert elige(J + "loot/Restock.java") == (False, ["tools/smoke/botin_reponer.py"])
    assert elige(J + "difficulty/MobDifficulty.java") == (False, ["tools/smoke/dificultad.py"])
    assert elige(J + "difficulty/ModDifficulty.java", "tools/smoke/botin_reponer.py") == \
        (False, ["tools/smoke/botin_reponer.py", "tools/smoke/dificultad.py"])
    assert elige(J + "loot/PerPlayerChest.java")[0]         # el resto de loot/: común, batería completa


def test_arena_de_oleadas():
    arena = (False, ["tools/smoke/arena.py", "tools/smoke/arena_modos.py"])
    assert elige(J + "arena/Game.java") == arena
    assert elige(J + "arena/Waves.java") == arena
    assert elige(J + "arena/Fame.java") == arena                  # T41: modos, clasificación y salón de la fama
    assert elige(J + "mixin/ArenaExplosionMixin.java") == arena
    assert elige("tools/gen/arena_oleadas.py") == arena
    assert elige("tools/smoke/arena.py") == (False, ["tools/smoke/arena.py"])
    assert elige("tools/smoke/arena_modos.py") == (False, ["tools/smoke/arena_modos.py"])
    assert elige(J + "mixin/ArenaPistonMixin.java", "tools/gen/guia.py") == \
        (False, ["tools/smoke/arena.py", "tools/smoke/arena_modos.py", "tools/smoke/guia.py"])


def test_coste_de_generacion_por_rutas():
    """La prueba de coste (job propio de la CI) va en un PR si cambia el Java de la generación, el generador o la propia
    prueba; no con documentación, tests, comandos ni mobs. No entra en los grupos de servidor."""
    assert sel.COSTE not in TODAS and "tools/smoke/coste_generacion.py" in [sel.rel(p) for p in
                                                                            sel.glob.glob(os.path.join(sel.ROOT, "tools", "smoke", "*.py"))]
    for r in [J + "mixin/ChunkGeneratorMixin.java", J + "mixin/StructureCheckMixin.java", J + "common/MediumStructures.java",
              J + "roads/RoadLayout.java", J + "mines/Hillside.java", J + "villages/Shoreline.java", J + "uniques/island/IslandZone.java",
              J + "config/GridPlacement.java", "tools/gen/houses.py", "tools/gen/medianas/posada.py", "tools/gen/unicas/castillo.py",
              "tools/smoke/coste_generacion.py", "tools/smoke/coste_referencia.json", "gradle.properties"]:
        assert sel.coste([r]), r
    for r in ["docs/DESARROLLO.md", "CHANGELOG.md", "tools/gen/tests/test_core.py", "tools/gen/LEEME.md", "tools/gen/render.py",
              J + "command/Guide.java", J + "mixin/ZombieMixin.java", J + "bosses/Phases.java", J + "loot/RestockedLoot.java",
              "src/test/java/io/github/albertosa23/heraldia/common/ProfilerTest.java", "tools/smoke/trofeos.py", ".github/workflows/ci.yml"]:
        assert not sel.coste([r]), r
    assert sel.coste(["docs/DESARROLLO.md", J + "mines/Hillside.java"]) and not sel.coste([])


def test_ci_matriz_dice_si_va_el_coste():
    out = subprocess.run([sys.executable, os.path.join(TOOLS, "test.py"), "--ci-matriz", "--completa"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["coste"] is True
    out = subprocess.run([sys.executable, os.path.join(TOOLS, "test.py"), "--listar", "--completa"],
                         capture_output=True, text=True, check=True).stdout.split()
    assert out[-1] == sel.COSTE and sorted(out[:-1]) == TODAS


def test_caravanas():
    p = ["tools/smoke/caravanas.py"]
    assert elige(J + "caravans/Caravans.java") == (False, p)
    assert elige(J + "caravans/Journey.java") == (False, p)
    assert elige("tools/gen/caravanas.py") == (False, p)
    assert elige("tools/smoke/caravanas.py") == (False, p)
    assert sel.DURACION_S["tools/smoke/caravanas.py"] > 0


def test_chozas_mago():
    p = ["tools/smoke/chozas_mago.py"]
    assert elige(J + "huts/Wizards.java") == (False, p)
    assert elige(J + "huts/Decision.java") == (False, p)
    assert elige("tools/gen/chozas_mago.py") == (False, p)
    assert elige("tools/smoke/chozas_mago.py") == (False, p)
    completo, pruebas = elige("tools/gen/medianas/choza_mago.py")
    assert not completo and set(p) <= set(pruebas) and "tools/smoke/estructuras_medianas.py" in pruebas
    assert sel.DURACION_S["tools/smoke/chozas_mago.py"] > 0
