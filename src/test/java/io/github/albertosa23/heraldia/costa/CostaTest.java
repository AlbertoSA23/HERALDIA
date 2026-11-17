package io.github.albertosa23.heraldia.costa;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.comun.Medianas;
import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.loot.Reposicion;
import io.github.albertosa23.heraldia.minas.Minas;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Faros y naufragios sin servidor: la rejilla heraldia:rejilla de los grupos costa/faro y costa/naufragio (activación y
 * separación de faros.* y naufragios.*: la frecuencia configurable), la regla de {@link Costa} (la de las minas con su
 * familia, {@link Minas#familia}) con todo inyectado: ninguna superviviente en la zona de una aldea o una única, junto a
 * una mediana o una entrada a mina que sale, ni un faro a menos de la distancia mínima de un naufragio; y
 * {@link Minas#cerca} (la mina más cercana que sale, la que hace ceder a la costa).
 */
class CostaTest {
	private static final String[] TIPOS = {"faro", "naufragio"};
	private static final int[] SPACING = {64, 48};

	@TempDir
	Path dir;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private void config(String json) throws IOException {
		Path file = dir.resolve("heraldia.json");
		Files.writeString(file, json);
		HeraldiaConfig.load(file);
	}

	static GridPlacement grid(String grupo, int spacing, int salt) {
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(
				"{\"grupo\": \"" + grupo + "\", \"spacing\": " + spacing + ", \"separation\": " + spacing / 3
						+ ", \"salt\": " + salt + "}")).getOrThrow();
	}

	private static List<RandomSpreadStructurePlacement> rejillas() {
		List<RandomSpreadStructurePlacement> ps = new ArrayList<>();
		for (int i = 0; i < TIPOS.length; i++) {
			ps.add(grid("costa/" + TIPOS[i], SPACING[i], 1907261201 + i));
		}
		return ps;
	}

	/** La regla de la costa tal y como la arma Costa.of: la familia de las minas con los dos tipos de la costa. */
	private static Minas familia(int distancia) {
		List<Identifier> tipos = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> estilos = new ArrayList<>();
		for (String t : TIPOS) {
			tipos.add(Identifier.fromNamespaceAndPath("heraldia", "costa/" + t));
			ids.add(List.of(Identifier.fromNamespaceAndPath("heraldia", "costa/" + t + "/templada/a")));
			estilos.add(List.of());
		}
		return new Minas(new Object(), tipos, ids, estilos, rejillas(), distancia);
	}

	@Test
	void rejillaConSusOpciones() throws IOException {
		config("{}");
		for (int i = 0; i < TIPOS.length; i++) {
			GridPlacement g = grid("costa/" + TIPOS[i], SPACING[i], 5);
			assertEquals(SPACING[i], g.spacing(), "por defecto (1024 y 768 bloques), la del datapack");
			assertEquals(12, g.separation(), "la interna: medianas.distancia_minima.bloques (192)");
			assertTrue(g.offsetX() >= 0 && g.offsetX() < g.spacing(), "origen desplazado por la sal");
		}
		config("{\"faros\": {\"separacion_bloques\": 2048}, \"naufragios\": {\"separacion_bloques\": 320}, "
				+ "\"medianas\": {\"distancia_minima\": {\"bloques\": 256}}}");
		assertEquals(128, grid("costa/faro", 64, 5).spacing());
		assertEquals(20, grid("costa/naufragio", 48, 5).spacing(), "cada tipo con su opción");
		assertEquals(10, grid("costa/naufragio", 48, 5).separation(), "la interna, como mucho media casilla");
		assertEquals(16, grid("costa/faro", 64, 5).separation());
	}

	@Test
	void frecuenciaSegunLaSeparacion() throws IOException {
		// candidatas en un cuadrado de 400 x 400 chunks: una por casilla, así que con la mitad de separación, unas 4 veces más
		int[] cuantas = new int[2];
		String[] cfg = {"{}", "{\"faros\": {\"separacion_bloques\": 512}}"};
		for (int k = 0; k < 2; k++) {
			config(cfg[k]);
			GridPlacement g = grid("costa/faro", 64, 7);
			for (int gx = -200 / g.spacing(); gx < 200 / g.spacing(); gx++) {
				for (int gz = -200 / g.spacing(); gz < 200 / g.spacing(); gz++) {
					ChunkPos c = g.getPotentialStructureChunk(3, gx * g.spacing() + g.offsetX(), gz * g.spacing() + g.offsetZ());
					if (g.applyAdditionalChunkRestrictions(c.x(), c.z(), 3)) {
						cuantas[k]++;
					}
				}
			}
		}
		assertTrue(cuantas[1] >= 3.5 * cuantas[0] && cuantas[1] <= 4.5 * cuantas[0], cuantas[0] + " -> " + cuantas[1]);
	}

	@Test
	void desactivadosNoDejanNinguno() throws IOException {
		config("{\"faros\": {\"activado\": false}}");
		GridPlacement faro = grid("costa/faro", 64, 3), naufragio = grid("costa/naufragio", 48, 4);
		for (int k = -3; k <= 3; k++) {
			ChunkPos c = faro.getPotentialStructureChunk(11, k * faro.spacing() + faro.offsetX(), faro.offsetZ());
			assertFalse(faro.applyAdditionalChunkRestrictions(c.x(), c.z(), 11), "faros desactivados");
			ChunkPos n = naufragio.getPotentialStructureChunk(11, k * naufragio.spacing() + naufragio.offsetX(), naufragio.offsetZ());
			assertTrue(naufragio.applyAdditionalChunkRestrictions(n.x(), n.z(), 11), "los naufragios, por su cuenta");
		}
		config("{\"naufragios\": {\"activado\": false}}");
		assertFalse(Costa.activado(HeraldiaConfig.get(), "naufragio"));
		assertTrue(Costa.activado(HeraldiaConfig.get(), "faro"));
	}

	private record Candidata(int tipo, int x, int z) {
	}

	private static List<Candidata> candidatas(List<RandomSpreadStructurePlacement> ps, long seed, int radio) {
		List<Candidata> out = new ArrayList<>();
		for (int i = 0; i < ps.size(); i++) {
			RandomSpreadStructurePlacement p = ps.get(i);
			int s = p.spacing(), ox = ((GridPlacement) p).offsetX(), oz = ((GridPlacement) p).offsetZ();
			for (int gx = -radio / s - 1; gx <= radio / s + 1; gx++) {
				for (int gz = -radio / s - 1; gz <= radio / s + 1; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					out.add(new Candidata(i, c.x(), c.z()));
				}
			}
		}
		return out;
	}

	@Test
	void faroYNaufragioNuncaJuntos() throws IOException {
		config("{}");
		int distancia = 1200;
		long d2 = (long) distancia * distancia;
		Medianas.Zona libre = (x, z) -> false;
		Medianas.Estilos todos = (j, x, z) -> true;
		for (long seed : new long[] {2, 77, -5}) {
			Minas m = familia(distancia);
			List<Candidata> all = candidatas(rejillas(), seed, 900);
			List<Candidata> vivas = all.stream().filter(c -> !m.rechaza(c.tipo, c.x, c.z, seed, libre, todos, libre, libre)).toList();
			assertTrue(vivas.size() > all.size() / 4 && vivas.size() < all.size(), "supervivientes " + vivas.size() + " de " + all.size());
			for (Candidata a : vivas) {
				for (Candidata b : vivas) {
					if (a != b && a.tipo != b.tipo) {
						long dx = (a.x - b.x) * 16L, dz = (a.z - b.z) * 16L;
						assertTrue(dx * dx + dz * dz >= d2, a + " y " + b + " a menos de " + distancia);
					}
				}
			}
			Minas otra = familia(distancia);              // el mismo resultado en cualquier orden
			for (int k = all.size() - 1; k >= 0; k--) {
				Candidata c = all.get(k);
				assertEquals(vivas.contains(c), !otra.rechaza(c.tipo, c.x, c.z, seed, libre, todos, libre, libre), c.toString());
			}
		}
	}

	@Test
	void cedenAAldeasUnicasMedianasMinasYAtlantida() throws IOException {
		config("{}");
		Medianas.Zona libre = (x, z) -> false;
		Medianas.Estilos todos = (j, x, z) -> true;
		Candidata c = candidatas(rejillas(), 5, 400).getFirst();
		Medianas.Zona aqui = (x, z) -> x == c.x && z == c.z;
		assertTrue(familia(192).rechaza(c.tipo, c.x, c.z, 77, aqui, todos, libre, libre), "en la zona de una aldea o una única");
		assertTrue(familia(192).rechaza(c.tipo, c.x, c.z, 77, libre, todos, libre, aqui), "junto a una mediana o una mina");
		// una entrada a mina que sale a 80 bloques: Costa compone la zona con Minas.cerca, como en el juego
		GridPlacement boca = MinasRejilla.grid();
		Minas minas = MinasRejilla.minas(boca);
		ChunkPos m = boca.getPotentialStructureChunk(8, boca.offsetX(), boca.offsetZ());
		Medianas.Zona cercaMina = (x, z) -> minas.cerca(x, z, 192, 8, libre, todos, libre, libre);
		assertTrue(cercaMina.ocupada(m.x() + 5, m.z()), "a 80 bloques de una mina que sale");
		assertFalse(cercaMina.ocupada(m.x() + 14, m.z()), "a 224, no");
		assertFalse(MinasRejilla.minas(boca).cerca(m.x() + 5, m.z(), 192, 8, libre, (j, x, z) -> false, libre, libre),
				"si la mina no sale (sin ladera), no cuenta");
		assertFalse(MinasRejilla.minas(boca).cerca(m.x() + 5, m.z(), 192, 8, (x, z) -> true, todos, libre, libre),
				"ni la que cae en la zona de una aldea");
		assertTrue(familia(192).rechaza(c.tipo, m.x() + 5, m.z(), 8, libre, todos, libre, cercaMina), "el faro cede a la mina");
	}

	/** Una rejilla de entradas a mina pequeñas (la del datapack) para probar Minas.cerca. */
	private static final class MinasRejilla {
		static GridPlacement grid() {
			return CostaTest.grid("minas/pequena", 48, 1907261101);
		}

		static Minas minas(GridPlacement g) {
			return new Minas(new Object(), List.of(Identifier.fromNamespaceAndPath("heraldia", "minas/pequena")),
					List.of(List.of(Identifier.fromNamespaceAndPath("heraldia", "minas/pequena/montana/a"))), List.of(List.of()), List.of(g), 192);
		}
	}

	@Test
	void idsOpcionesYBotin() {
		assertTrue(Costa.esCosta(Identifier.parse("heraldia:costa/faro/templada/a")));
		assertTrue(Costa.esCosta(Identifier.parse("heraldia:costa/naufragio/nevada/b")));
		assertFalse(Costa.esCosta(Identifier.parse("heraldia:aldea_costa")));
		assertFalse(Costa.esCosta(Identifier.parse("heraldia:unicas/faro")), "el faro único es otra cosa");
		assertFalse(Costa.esCosta(Identifier.parse("minecraft:shipwreck")));
		assertEquals("faro", Costa.tipo(Identifier.parse("heraldia:costa/faro/fria/b")));
		assertEquals("faros", Costa.opcion("faro"));
		assertEquals("naufragios", Costa.opcion("naufragio"));
		assertNull(Costa.opcion("muelle"));
		for (String t : new String[] {"faro", "bodega", "camarote"}) {
			assertTrue(Reposicion.tablaRepone("heraldia:costa/" + t), "se repone: " + t);
		}
		assertFalse(Reposicion.tablaRepone("heraldia:costa/"));
	}
}
