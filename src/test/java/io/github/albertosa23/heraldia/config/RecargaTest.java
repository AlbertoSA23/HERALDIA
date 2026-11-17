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
 * {@link HeraldiaConfig#recargar} con un fichero real (sin reescribirlo).
 */
class RecargaTest {
	@TempDir
	Path dir;

	@AfterEach
	void restaurar() {
		HeraldiaConfig.load(null);
	}

	private Path fichero(Map<String, JsonPrimitive> cambios) throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.putAll(cambios);
		HeraldiaConfig.save(file, v);
		return file;
	}

	@Test
	void clasificacionDeLasOpciones() {
		for (String k : List.of("dificultad.nivel", "dificultad.escalar_por_jugadores", "dificultad.escalar_botin", "jefes.fases.activado",
				"jefes.refuerzos.activado", "jefes.barra.activado", "botin.reponer.activado", "botin.reponer.dias", "arena.activado",
				"arena.oleada.mobs_incremento", "arena.max_mobs_vivos", "arena.experiencia_porcentaje", "guia.entregar_al_entrar",
				"golems.limpieza", "golems.limite_estandar", "aldeas.vida.tratos_estilo", "aldeas.vida.asedios",
				"unicas.atlantida.cofre_unico_por_jugador")) {
			assertTrue(Recarga.recargable(k), k);
		}
		for (String k : List.of("aldeas.separacion_bloques", "aldeas.maximo", "aldeas.porcentaje_grandes", "aldeas.vida.tablon",
				"aldeas.caminos.activado", "aldeas.caminos.ancho", "aldeas.estilos.llanuras_castellana", "aldeas.familias.llanuras",
				"unicas.castillo.activada", "unicas.castillo.separacion_bloques", "unicas.rejilla_compatible",
				"unicas.distancia_minima.bloques", "compatibilidad.zona_estructuras_ajenas_bloques", "medianas.activadas",
				"medianas.posada.separacion_bloques", "minas.entradas.activado", "minas.vanilla.multiplicador",
				"arena.generar_en_mundos_nuevos", "una.opcion.nueva")) {
			assertFalse(Recarga.recargable(k), k);
		}
		// un prefijo con punto no casa con otra palabra que empiece igual
		assertFalse(Recarga.recargable("dificultades.nivel"));
		assertFalse(Recarga.recargable("aldeas.vida.asedios_extra"));
	}

	@Test
	void todasLasOpcionesDelEsquemaEstanClasificadasYLaMayoriaNoSeRecarga() {
		int recargables = 0;
		for (ConfigOption o : HeraldiaConfig.options()) {
			if (Recarga.recargable(o.key())) {
				recargables++;
			}
		}
		assertTrue(recargables >= 18, "recargables: " + recargables);
		assertTrue(recargables < HeraldiaConfig.options().size() / 2, "la generación es la mayor parte");
	}

	@Test
	void mezclarTomaLoNuevoSoloDeLasRecargables() {
		Map<String, JsonPrimitive> enUso = new LinkedHashMap<>();
		enUso.put("aldeas.separacion_bloques", new JsonPrimitive(1500));
		enUso.put("dificultad.nivel", new JsonPrimitive("normal"));
		enUso.put("jefes.barra.activado", new JsonPrimitive(true));
		enUso.put("minas.vanilla.multiplicador", new JsonPrimitive(2.0));
		Map<String, JsonPrimitive> leidos = new LinkedHashMap<>(enUso);
		leidos.put("aldeas.separacion_bloques", new JsonPrimitive(3000));
		leidos.put("dificultad.nivel", new JsonPrimitive("heroica"));
		leidos.put("minas.vanilla.multiplicador", new JsonPrimitive(2));   // el mismo número escrito sin decimales
		leidos.remove("jefes.barra.activado");                              // si falta, se conserva

		Recarga.Resultado r = Recarga.mezclar(enUso, leidos);
		assertEquals(List.of("dificultad.nivel"), r.aplicadas());
		assertEquals(1, r.pendientes().size());
		Recarga.Pendiente p = r.pendientes().getFirst();
		assertEquals("aldeas.separacion_bloques", p.clave());
		assertEquals(1500, p.enUso().getAsInt());
		assertEquals(3000, p.leido().getAsInt());
		assertEquals(List.copyOf(enUso.keySet()), List.copyOf(r.valores().keySet()), "mismas claves y orden");
		assertEquals("heroica", r.valores().get("dificultad.nivel").getAsString());
		assertEquals(1500, r.valores().get("aldeas.separacion_bloques").getAsInt());
		assertTrue(r.valores().get("jefes.barra.activado").getAsBoolean());
		assertTrue(r.cambia());
		assertFalse(Recarga.mezclar(enUso, enUso).cambia());
		assertTrue(Recarga.mezclar(enUso, enUso).pendientes().isEmpty());
	}

	@Test
	void recargarAplicaLoRecargableYDejaLaGeneracionHastaElReinicio() throws IOException {
		Path file = fichero(Map.of());
		HeraldiaConfig.load(file);
		HeraldiaConfig antes = HeraldiaConfig.get();
		VillageRules aldeas = antes.villages();

		fichero(Map.of("dificultad.nivel", new JsonPrimitive("dificil"), "botin.reponer.activado", new JsonPrimitive(true),
				"aldeas.separacion_bloques", new JsonPrimitive(4000), "aldeas.estilos.llanuras_castellana", new JsonPrimitive(false),
				"arena.generar_en_mundos_nuevos", new JsonPrimitive(false)));
		String escrito = Files.readString(file);
		Recarga.Resultado r = HeraldiaConfig.recargar(file);

		assertEquals(List.of("botin.reponer.activado", "dificultad.nivel"), r.aplicadas().stream().sorted().toList());
		assertEquals(List.of("aldeas.estilos.llanuras_castellana", "aldeas.separacion_bloques", "arena.generar_en_mundos_nuevos"),
				r.pendientes().stream().map(Recarga.Pendiente::clave).sorted().toList());
		HeraldiaConfig ahora = HeraldiaConfig.get();
		assertNotSame(antes, ahora, "se sustituye entera (inmutable)");
		assertEquals("dificil", ahora.getString("dificultad.nivel"));
		assertTrue(ahora.getBool("botin.reponer.activado"));
		assertEquals(1500, ahora.getInt("aldeas.separacion_bloques"), "la generación conserva el valor en uso");
		assertTrue(ahora.getBool("aldeas.estilos.llanuras_castellana"));
		assertTrue(ahora.getBool("arena.generar_en_mundos_nuevos"));
		assertEquals(aldeas.enabledStyles(), ahora.villages().enabledStyles(), "las reglas de las aldeas no cambian");
		assertEquals(escrito, Files.readString(file), "recargar no reescribe el fichero");
		// lo que espera al reinicio se sigue avisando en cada recarga, y sin cambios no se sustituye nada
		Recarga.Resultado otra = HeraldiaConfig.recargar(file);
		assertTrue(otra.aplicadas().isEmpty());
		assertEquals(3, otra.pendientes().size());
		assertSame(ahora, HeraldiaConfig.get());
	}

	@Test
	void unValorNoValidoSeQuedaConElDeFabricaComoAlArrancar() throws IOException {
		Path file = dir.resolve("heraldia.json");
		HeraldiaConfig.load(fichero(Map.of("botin.reponer.dias", new JsonPrimitive(10))));
		Files.writeString(file, "{\"version\": 1, \"botin\": {\"reponer\": {\"dias\": 999}}, \"dificultad\": {\"nivel\": \"imposible\"}}");
		Recarga.Resultado r = HeraldiaConfig.recargar(file);
		assertEquals(7, HeraldiaConfig.get().getInt("botin.reponer.dias"), "fuera de rango: el de por defecto");
		assertEquals("normal", HeraldiaConfig.get().getString("dificultad.nivel"));
		assertTrue(r.aplicadas().contains("botin.reponer.dias"));
	}
}
