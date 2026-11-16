package io.github.albertosa23.heraldia.minas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import io.github.albertosa23.heraldia.comun.Medianas;
import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
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
 * Entradas a mina sin servidor: la rejilla heraldia:rejilla del grupo minas/&lt;tamaño&gt; (activación y separación de la
 * configuración, en proporción entre tamaños) y la regla de {@link Minas} con todo inyectado: ninguna superviviente en
 * la zona de una aldea o una única ni junto a una mediana que sale, dos de distinto tamaño nunca a menos de la distancia
 * mínima, toda descartada por otra mina tiene cerca una superviviente, y el resultado no depende del orden; y
 * {@link Medianas#cerca} (la mediana más cercana que sale, la que hace ceder a una mina).
 */
class MinasTest {
	private static final String[] TAMANOS = {"pequena", "mediana", "grande"};
	private static final int[] SPACING = {48, 72, 120};

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

	private static Minas minas(int distancia) {
		List<Identifier> tipos = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> estilos = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		for (int i = 0; i < TAMANOS.length; i++) {
			tipos.add(Identifier.fromNamespaceAndPath("heraldia", "minas/" + TAMANOS[i]));
			ids.add(List.of(Identifier.fromNamespaceAndPath("heraldia", "minas/" + TAMANOS[i] + "/montana/a")));
			estilos.add(List.of());
			placements.add(grid("minas/" + TAMANOS[i], SPACING[i], 1907261101 + i));
		}
		return new Minas(new Object(), tipos, ids, estilos, placements, distancia);
	}

	@Test
	void rejillaEscalaLosTresTamanosConLaOpcion() throws IOException {
		config("{}");
		for (int i = 0; i < 3; i++) {
			GridPlacement g = grid("minas/" + TAMANOS[i], SPACING[i], 5);
			assertEquals(SPACING[i], g.spacing(), "por defecto, la del datapack");
			assertEquals(12, g.separation(), "la interna: medianas.distancia_minima.bloques (192)");
			assertTrue(g.offsetX() >= 0 && g.offsetX() < g.spacing(), "origen desplazado por la sal");
		}
		config("{\"minas\": {\"entradas\": {\"separacion_bloques\": 1536}}, \"medianas\": {\"distancia_minima\": {\"bloques\": 320}}}");
		assertEquals(96, grid("minas/pequena", 48, 5).spacing(), "el doble de la de por defecto (768)");
		assertEquals(144, grid("minas/mediana", 72, 5).spacing(), "y las otras en proporción");
		assertEquals(240, grid("minas/grande", 120, 5).spacing());
		assertEquals(20, grid("minas/grande", 120, 5).separation());
		config("{\"minas\": {\"entradas\": {\"separacion_bloques\": 256}}, \"medianas\": {\"distancia_minima\": {\"bloques\": 1024}}}");
		GridPlacement p = grid("minas/pequena", 48, 5);
		assertEquals(16, p.spacing());
		assertEquals(8, p.separation(), "la interna, como mucho media casilla");
	}

	@Test
	void desactivadasNoDejanNinguna() throws IOException {
		config("{\"minas\": {\"entradas\": {\"activado\": false}}}");
		for (int i = 0; i < 3; i++) {
			GridPlacement g = grid("minas/" + TAMANOS[i], SPACING[i], 3);
			for (int k = -3; k <= 3; k++) {
				ChunkPos c = g.getPotentialStructureChunk(11, k * g.spacing() + g.offsetX(), g.offsetZ());
				assertFalse(g.applyAdditionalChunkRestrictions(c.x(), c.z(), 11));
			}
		}
		config("{}");
		GridPlacement g = grid("minas/grande", 120, 3);
		ChunkPos c = g.getPotentialStructureChunk(11, g.offsetX(), g.offsetZ());
		assertTrue(g.applyAdditionalChunkRestrictions(c.x(), c.z(), 11));
	}

	private record Candidata(int tipo, int x, int z) {
	}

	private static List<Candidata> candidatas(Minas m, List<RandomSpreadStructurePlacement> ps, long seed, int radio) {
		List<Candidata> out = new ArrayList<>();
		for (int i = 0; i < m.tipos(); i++) {
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

	private static List<RandomSpreadStructurePlacement> rejillas() {
		List<RandomSpreadStructurePlacement> ps = new ArrayList<>();
		for (int i = 0; i < 3; i++) {
			ps.add(grid("minas/" + TAMANOS[i], SPACING[i], 1907261101 + i));
		}
		return ps;
	}

	@Test
	void separacionCoherenteEntreTamanos() throws IOException {
		config("{}");
		int distancia = 900;                    // mucho más que la de por defecto: muchos choques que comprobar
		long d2 = (long) distancia * distancia;
		Medianas.Zona libre = (x, z) -> false;
		Medianas.Estilos todos = (j, x, z) -> true;
		List<RandomSpreadStructurePlacement> ps = rejillas();
		for (long seed : new long[] {1, 42, -9}) {
			Minas m = minas(distancia);
			List<Candidata> all = candidatas(m, ps, seed, 900);
			List<Candidata> vivas = new ArrayList<>();
			for (Candidata c : all) {
				if (!m.rechaza(c.tipo, c.x, c.z, seed, libre, todos, libre, libre)) {
					vivas.add(c);
				}
			}
			assertTrue(vivas.size() > all.size() / 4 && vivas.size() < all.size(), "supervivientes " + vivas.size() + " de " + all.size());
			for (Candidata a : vivas) {
				for (Candidata b : vivas) {
					if (a != b && a.tipo != b.tipo) {
						long dx = (a.x - b.x) * 16L, dz = (a.z - b.z) * 16L;
						assertTrue(dx * dx + dz * dz >= d2, a + " y " + b + " sobreviven las dos a menos de " + distancia);
					}
				}
			}
			int borde = 900 - distancia / 16 - 140;
			for (Candidata c : all) {
				if (vivas.contains(c) || Math.abs(c.x) > borde || Math.abs(c.z) > borde) {
					continue;
				}
				boolean cerca = vivas.stream().anyMatch(v -> v.tipo != c.tipo && Math.pow((v.x - c.x) * 16.0, 2) + Math.pow((v.z - c.z) * 16.0, 2) < d2);
				assertTrue(cerca, c + " descartada sin ninguna superviviente cerca");
			}
			Minas m2 = minas(distancia);
			for (int k = all.size() - 1; k >= 0; k--) {
				Candidata c = all.get(k);
				assertEquals(vivas.contains(c), !m2.rechaza(c.tipo, c.x, c.z, seed, libre, todos, libre, libre), c.toString());
			}
		}
	}

	@Test
	void cedenAAldeasUnicasMedianasYAtlantida() throws IOException {
		config("{}");
		Medianas.Zona libre = (x, z) -> false;
		Medianas.Estilos todos = (j, x, z) -> true;
		List<Candidata> all = candidatas(minas(192), rejillas(), 5, 400);
		Candidata c = all.getFirst();
		Medianas.Zona aqui = (x, z) -> x == c.x && z == c.z;
		assertTrue(minas(192).rechaza(c.tipo, c.x, c.z, 77, aqui, todos, libre, libre), "en la zona de una aldea o una única");
		assertTrue(minas(192).rechaza(c.tipo, c.x, c.z, 77, libre, todos, libre, aqui), "junto a una mediana que sale");
		// vecinas que no salen (bioma o ladera), en la Atlántida o junto a una mediana no descartan a nadie
		int distancia = 3000;
		for (String caso : new String[] {"estilos", "atlantida", "medianas"}) {
			Minas m = minas(distancia);
			int vivas = 0;
			List<Candidata> todas = candidatas(m, rejillas(), 6, 400);
			for (Candidata o : todas) {
				boolean propia = caso.equals("medianas");
				Medianas.Zona med = propia ? (x, z) -> !(x == o.x && z == o.z) : libre;
				boolean rechazada = m.rechaza(o.tipo, o.x, o.z, 6, libre, caso.equals("estilos") ? (j, x, z) -> j == o.tipo && x == o.x && z == o.z : todos,
						caso.equals("atlantida") ? (x, z) -> !(x == o.x && z == o.z) : libre, med);
				vivas += rechazada ? 0 : 1;
			}
			assertEquals(todas.size(), vivas, caso + ": las que no salen no descartan");
		}
	}

	@Test
	void medianaCercaSoloSiSale() throws IOException {
		config("{}");
		GridPlacement posada = grid("medianas/posada", 44, 1001);
		java.util.function.Supplier<Medianas> nueva = () -> new Medianas(new Object(),
				List.of(Identifier.fromNamespaceAndPath("heraldia", "medianas/posada")),
				List.of(List.of(Identifier.fromNamespaceAndPath("heraldia", "medianas/posada/a"))), List.of(List.of()), List.of(posada), null, 192);
		Medianas med = nueva.get();          // una por contexto: la decisión de cada mediana queda en su memoria
		ChunkPos p = posada.getPotentialStructureChunk(8, posada.offsetX(), posada.offsetZ());
		Medianas.Zona libre = (x, z) -> false;
		Medianas.Contexto sale = new Medianas.Contexto(libre, (j, x, z) -> true, libre);
		assertTrue(med.cerca(p.x() + 5, p.z(), 192, 8, sale), "a 80 bloques de una mediana que sale");
		assertFalse(med.cerca(p.x() + 14, p.z(), 192, 8, sale), "a 224 bloques, no");
		assertFalse(nueva.get().cerca(p.x() + 5, p.z(), 192, 8, new Medianas.Contexto(libre, (j, x, z) -> false, libre)), "si no sale, no cuenta");
		assertFalse(nueva.get().cerca(p.x() + 5, p.z(), 192, 8, new Medianas.Contexto((x, z) -> true, (j, x, z) -> true, libre)),
				"tampoco la que cae en la zona de una aldea (no sale)");
	}

	@Test
	void susCofresSeReponenComoLosDeHeraldia() {
		for (String t : new String[] {"galeria", "boca", "capataz", "fundicion", "filon", "vagoneta"}) {
			assertTrue(io.github.albertosa23.heraldia.loot.Reposicion.tablaRepone("heraldia:minas/" + t), t);
		}
		assertFalse(io.github.albertosa23.heraldia.loot.Reposicion.tablaRepone("heraldia:minas/"));
	}

	@Test
	void claveDistingueTipoYChunk() {
		assertTrue(Minas.clave(0, 1, 2) != Minas.clave(1, 1, 2));
		assertTrue(Minas.clave(0, -1, 2) != Minas.clave(0, 1, 2));
		assertTrue(Minas.clave(2, 5, -7) != Minas.clave(2, -7, 5));
		assertTrue(Minas.esMina(Identifier.parse("heraldia:minas/grande/picos/b")));
		assertFalse(Minas.esMina(Identifier.parse("heraldia:medianas/posada/a")));
		assertFalse(Minas.esMina(Identifier.parse("minecraft:mineshaft")));
		assertFalse(Minas.esMina(Identifier.parse("heraldia:unicas/mina_perdida")));
	}
}
