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
    ["tools/gen/render.py"], ["tools/gen/loot.py"], [J + "comando/LlaveCommand.java"],
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
    assert elige(J + "comando/InfoCommand.java") == (False, ["tools/smoke/admin.py"])   # no es de colocación


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
    assert elige(J + "caminos/Trazado.java") == (False, ["tools/smoke/caminos.py"])
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


def test_minas():
    m = ["tools/smoke/entradas_mina.py"]
    assert elige("tools/gen/minas/planos.py") == (False, m)
    assert elige("tools/gen/minas/__init__.py") == (False, m)
    assert elige(J + "minas/Ladera.java") == (False, sorted(m + ["tools/smoke/costa.py"])), "la regla de la costa es la de las minas"
    assert elige("tools/smoke/entradas_mina.py") == (False, m)
    # T36: la caché compartida de alturas y el /locate en paralelo (solo los usan las minas)
    assert elige(J + "comun/CacheAlturas.java") == (False, m)
    assert elige(J + "mixin/ChunkGeneratorLocateMixin.java") == (False, m)
    assert elige(J + "minas/LocateParalelo.java") == (False, sorted(m + ["tools/smoke/costa.py"]))


def test_costa():
    c = ["tools/smoke/costa.py"]
    mobs = c + ["tools/smoke/guardianes_adultos.py", "tools/smoke/guardianes_anclados.py"]
    assert elige("tools/gen/litoral/obras.py") == (False, mobs), "el ahogado del semihundido"
    assert elige("tools/gen/litoral/__init__.py") == (False, mobs)
    assert elige(J + "costa/Orilla.java") == (False, c)
    assert elige("tools/smoke/costa.py") == (False, c)
    assert sel.coste([J + "costa/Orilla.java"]) and sel.coste(["tools/gen/litoral/obras.py"])


def test_perfiles():
    p = ["tools/smoke/perfiles.py"]
    assert elige(J + "config/Perfiles.java") == (False, p)
    assert elige(J + "comando/ProfileCommand.java") == (False, p)
    assert elige("tools/smoke/perfiles.py") == (False, p)
    assert elige(J + "config/HeraldiaConfig.java")[0]          # el resto de la configuración: común, batería completa
    assert elige("tools/gen/opciones.py")[0]


def test_guia_del_heraldo():
    assert elige(J + "comando/Guia.java") == (False, ["tools/smoke/guia.py"])
    assert elige(J + "comando/Textos.java") == (False, ["tools/smoke/guia.py"])
    assert elige("tools/gen/guia.py") == (False, ["tools/smoke/guia.py"])
    assert elige("tools/smoke/guia.py") == (False, ["tools/smoke/guia.py"])
    # idiomas: las traducciones y su comprobación solo pasan la de la Guía (el respaldo en el idioma del cliente)
    assert elige("tools/gen/idiomas.py") == (False, ["tools/smoke/guia.py"])
    assert elige("tools/gen/idiomas/fr_fr.json", "tools/gen/idiomas/gl_es.json") == (False, ["tools/smoke/guia.py"])
    assert elige("README.fr.md", "docs/CONFIGURACION.md", "tools/gen/tests/test_readme.py") == (False, [])
    assert elige(J + "comando/LlaveCommand.java") == (False, [])       # el resto de comando/: solo la de humo


def test_herramientas_de_administracion():
    admin = (False, ["tools/smoke/admin.py"])
    for r in ("comando/RevisarCommand.java", "comando/Revision.java", "comando/Seguro.java",
              "comando/Estado.java", "comando/EstadoCommand.java", "comando/RecargarCommand.java",
              "comando/InfoCommand.java", "config/Recarga.java"):
        assert elige(J + r) == admin, r
    assert elige("tools/gen/admin.py") == admin
    assert elige("tools/smoke/admin.py") == admin
    assert elige(J + "config/HeraldiaConfig.java")[0]           # el resto de config/: común, batería completa


def test_comandos_en_ingles_y_aviso_de_version():
    update = (False, ["tools/smoke/update_check.py"])
    for r in ("comando/AvisoVersion.java", "version/Version.java", "version/Publicaciones.java", "version/Avisados.java"):
        assert elige(J + r) == update, r
    assert elige("tools/smoke/update_check.py") == update
    comandos = (False, sorted(["tools/smoke/update_check.py", "tools/smoke/admin.py", "tools/smoke/guia.py", "tools/smoke/arena.py"]))
    for r in (J + "comando/Comandos.java", J + "comando/Alias.java", J + "mixin/CommandsMixin.java", "tools/gen/comandos.py"):
        assert (elige(r)[0], sorted(elige(r)[1])) == comandos, r


def test_botin_que_se_repone_y_dificultad():
    assert elige(J + "loot/BotinRepuesto.java") == (False, ["tools/smoke/botin_reponer.py"])
    assert elige(J + "loot/Reposicion.java") == (False, ["tools/smoke/botin_reponer.py"])
    assert elige(J + "dificultad/DificultadMobs.java") == (False, ["tools/smoke/dificultad.py"])
    assert elige(J + "dificultad/Dificultad.java", "tools/smoke/botin_reponer.py") == \
        (False, ["tools/smoke/botin_reponer.py", "tools/smoke/dificultad.py"])
    assert elige(J + "loot/CofrePorJugador.java")[0]         # el resto de loot/: común, batería completa


def test_arena_de_oleadas():
    arena = (False, ["tools/smoke/arena.py"])
    assert elige(J + "arena/Juego.java") == arena
    assert elige(J + "arena/Oleadas.java") == arena
    assert elige(J + "mixin/ArenaExplosionMixin.java") == arena
    assert elige("tools/gen/arena_oleadas.py") == arena
    assert elige("tools/smoke/arena.py") == arena
    assert elige(J + "mixin/ArenaPistonMixin.java", "tools/gen/guia.py") == \
        (False, ["tools/smoke/arena.py", "tools/smoke/guia.py"])


def test_coste_de_generacion_por_rutas():
    """La prueba de coste (job propio de la CI) va en un PR si cambia el Java de la generación, el generador o la propia
    prueba; no con documentación, tests, comandos ni mobs. No entra en los grupos de servidor."""
    assert sel.COSTE not in TODAS and "tools/smoke/coste_generacion.py" in [sel.rel(p) for p in
                                                                            sel.glob.glob(os.path.join(sel.ROOT, "tools", "smoke", "*.py"))]
    for r in [J + "mixin/ChunkGeneratorMixin.java", J + "mixin/StructureCheckMixin.java", J + "comun/Medianas.java",
              J + "caminos/Trazado.java", J + "minas/Ladera.java", J + "aldeas/Orilla.java", J + "unicas/isla/IslaZona.java",
              J + "config/GridPlacement.java", "tools/gen/houses.py", "tools/gen/medianas/posada.py", "tools/gen/unicas/castillo.py",
              "tools/smoke/coste_generacion.py", "tools/smoke/coste_referencia.json", "gradle.properties"]:
        assert sel.coste([r]), r
    for r in ["docs/DESARROLLO.md", "CHANGELOG.md", "tools/gen/tests/test_core.py", "tools/gen/LEEME.md", "tools/gen/render.py",
              J + "comando/Guia.java", J + "mixin/ZombieMixin.java", J + "jefes/Fases.java", J + "loot/BotinRepuesto.java",
              "src/test/java/io/github/albertosa23/heraldia/comun/PerfilTest.java", "tools/smoke/trofeos.py", ".github/workflows/ci.yml"]:
        assert not sel.coste([r]), r
    assert sel.coste(["docs/DESARROLLO.md", J + "minas/Ladera.java"]) and not sel.coste([])


def test_ci_matriz_dice_si_va_el_coste():
    out = subprocess.run([sys.executable, os.path.join(TOOLS, "test.py"), "--ci-matriz", "--completa"],
                         capture_output=True, text=True, check=True).stdout
    assert json.loads(out)["coste"] is True
    out = subprocess.run([sys.executable, os.path.join(TOOLS, "test.py"), "--listar", "--completa"],
                         capture_output=True, text=True, check=True).stdout.split()
    assert out[-1] == sel.COSTE and sorted(out[:-1]) == TODAS


def test_caravanas():
    p = ["tools/smoke/caravanas.py"]
    assert elige(J + "caravanas/Caravanas.java") == (False, p)
    assert elige(J + "caravanas/Viaje.java") == (False, p)
    assert elige("tools/gen/caravanas.py") == (False, p)
    assert elige("tools/smoke/caravanas.py") == (False, p)
    assert sel.DURACION_S["tools/smoke/caravanas.py"] > 0
