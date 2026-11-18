package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotSame;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Recarga en caliente (/heraldia reload): qué opciones se aplican sin reiniciar, la mezcla con lo que está en uso y
 * {@link HeraldiaConfig#reload} con un fichero real (sin reescribirlo).
 */
class ReloadTest {
	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private Path file(Map<String, JsonPrimitive> changes) throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.putAll(changes);
		HeraldiaConfig.save(file, v);
		return file;
	}

	@Test
	void optionClassification() {
		for (String k : List.of("dificultad.nivel", "dificultad.escalar_por_jugadores", "dificultad.escalar_botin", "jefes.fases.activado",
				"jefes.refuerzos.activado", "jefes.barra.activado", "botin.reponer.activado", "botin.reponer.dias", "arena.activado",
				"arena.oleada.mobs_incremento", "arena.max_mobs_vivos", "arena.experiencia_porcentaje", "guia.entregar_al_entrar",
				"golems.limpieza", "golems.limite_estandar", "aldeas.vida.tratos_estilo", "aldeas.vida.asedios",
				"unicas.atlantida.cofre_unico_por_jugador")) {
			assertTrue(Reload.reloadable(k), k);
		}
		for (String k : List.of("aldeas.separacion_bloques", "aldeas.maximo", "aldeas.porcentaje_grandes", "aldeas.vida.tablon",
				"aldeas.caminos.activado", "aldeas.caminos.ancho", "aldeas.estilos.llanuras_castellana", "aldeas.familias.llanuras",
				"unicas.castillo.activada", "unicas.castillo.separacion_bloques", "unicas.rejilla_compatible",
				"unicas.distancia_minima.bloques", "compatibilidad.zona_estructuras_ajenas_bloques", "medianas.activadas",
				"medianas.posada.separacion_bloques", "minas.entradas.activado", "minas.vanilla.multiplicador",
				"arena.generar_en_mundos_nuevos", "una.opcion.nueva")) {
			assertFalse(Reload.reloadable(k), k);
		}
		// un prefijo con punto no casa con otra palabra que empiece igual
		assertFalse(Reload.reloadable("dificultades.nivel"));
		assertFalse(Reload.reloadable("aldeas.vida.asedios_extra"));
	}

	@Test
	void allSchemaOptionsAreClassifiedAndMostDoNotReload() {
		int reloadables = 0;
		for (ConfigOption o : HeraldiaConfig.options()) {
			if (Reload.reloadable(o.key())) {
				reloadables++;
			}
		}
		assertTrue(reloadables >= 18, "recargables: " + reloadables);
		assertTrue(reloadables < HeraldiaConfig.options().size() / 2, "la generación es la mayor parte");
	}

	@Test
	void mergeTakesNewOnlyFromReloadables() {
		Map<String, JsonPrimitive> inUse = new LinkedHashMap<>();
		inUse.put("aldeas.separacion_bloques", new JsonPrimitive(1500));
		inUse.put("dificultad.nivel", new JsonPrimitive("normal"));
		inUse.put("jefes.barra.activado", new JsonPrimitive(true));
		inUse.put("minas.vanilla.multiplicador", new JsonPrimitive(2.0));
		Map<String, JsonPrimitive> loaded = new LinkedHashMap<>(inUse);
		loaded.put("aldeas.separacion_bloques", new JsonPrimitive(3000));
		loaded.put("dificultad.nivel", new JsonPrimitive("heroica"));
		loaded.put("minas.vanilla.multiplicador", new JsonPrimitive(2));   // el mismo número escrito sin decimales
		loaded.remove("jefes.barra.activado");                              // si falta, se conserva

		Reload.Result r = Reload.merge(inUse, loaded);
		assertEquals(List.of("dificultad.nivel"), r.applied());
		assertEquals(1, r.pending().size());
		Reload.Pending p = r.pending().getFirst();
		assertEquals("aldeas.separacion_bloques", p.key());
		assertEquals(1500, p.inUse().getAsInt());
		assertEquals(3000, p.read().getAsInt());
		assertEquals(List.copyOf(inUse.keySet()), List.copyOf(r.optionValues().keySet()), "mismas claves y orden");
		assertEquals("heroica", r.optionValues().get("dificultad.nivel").getAsString());
		assertEquals(1500, r.optionValues().get("aldeas.separacion_bloques").getAsInt());
		assertTrue(r.optionValues().get("jefes.barra.activado").getAsBoolean());
		assertTrue(r.changes());
		assertFalse(Reload.merge(inUse, inUse).changes());
		assertTrue(Reload.merge(inUse, inUse).pending().isEmpty());
	}

	@Test
	void reloadAppliesReloadableAndLeavesGenerationUntilRestart() throws IOException {
		Path file = file(Map.of());
		HeraldiaConfig.load(file);
		HeraldiaConfig before = HeraldiaConfig.get();
		VillageRules villages = before.villages();

		file(Map.of("dificultad.nivel", new JsonPrimitive("dificil"), "botin.reponer.activado", new JsonPrimitive(true),
				"aldeas.separacion_bloques", new JsonPrimitive(4000), "aldeas.estilos.llanuras_castellana", new JsonPrimitive(false),
				"arena.generar_en_mundos_nuevos", new JsonPrimitive(false)));
		String written = Files.readString(file);
		Reload.Result r = HeraldiaConfig.reload(file);

		assertEquals(List.of("botin.reponer.activado", "dificultad.nivel"), r.applied().stream().sorted().toList());
		assertEquals(List.of("aldeas.estilos.llanuras_castellana", "aldeas.separacion_bloques", "arena.generar_en_mundos_nuevos"),
				r.pending().stream().map(Reload.Pending::key).sorted().toList());
		HeraldiaConfig now = HeraldiaConfig.get();
		assertNotSame(before, now, "se sustituye entera (inmutable)");
		assertEquals("dificil", now.getString("dificultad.nivel"));
		assertTrue(now.getBool("botin.reponer.activado"));
		assertEquals(1500, now.getInt("aldeas.separacion_bloques"), "la generación conserva el valor en uso");
		assertTrue(now.getBool("aldeas.estilos.llanuras_castellana"));
		assertTrue(now.getBool("arena.generar_en_mundos_nuevos"));
		assertEquals(villages.enabledStyles(), now.villages().enabledStyles(), "las reglas de las aldeas no cambian");
		assertEquals(written, Files.readString(file), "recargar no reescribe el fichero");
		// lo que espera al reinicio se sigue avisando en cada recarga, y sin cambios no se sustituye nada
		Reload.Result other = HeraldiaConfig.reload(file);
		assertTrue(other.applied().isEmpty());
		assertEquals(3, other.pending().size());
		assertSame(now, HeraldiaConfig.get());
	}

	@Test
	void invalidValueKeepsFactoryDefaultLikeAtStartup() throws IOException {
		Path file = dir.resolve("heraldia.json");
		HeraldiaConfig.load(file(Map.of("botin.reponer.dias", new JsonPrimitive(10))));
		Files.writeString(file, "{\"version\": 1, \"botin\": {\"reponer\": {\"dias\": 999}}, \"dificultad\": {\"nivel\": \"imposible\"}}");
		Reload.Result r = HeraldiaConfig.reload(file);
		assertEquals(7, HeraldiaConfig.get().getInt("botin.reponer.dias"), "fuera de rango: el de por defecto");
		assertEquals("normal", HeraldiaConfig.get().getString("dificultad.nivel"));
		assertTrue(r.applied().contains("botin.reponer.dias"));
	}
}
