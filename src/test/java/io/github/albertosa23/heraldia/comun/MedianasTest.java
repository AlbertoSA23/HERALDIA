package io.github.albertosa23.heraldia.comun;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
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
 * Estructuras medianas sin servidor: la rejilla heraldia:rejilla del grupo medianas/&lt;tipo&gt; (lo que lee de la
 * configuración) y la regla de {@link Medianas} con la zona y los estilos inyectados (lógica pura): ninguna superviviente
 * en la zona de una aldea o una única, dos supervivientes nunca a menos de la distancia mínima, toda candidata descartada
 * por otra mediana tiene cerca una superviviente, y el resultado no depende del orden de las consultas.
 */
class MedianasTest {
	private static final String[] TIPOS = {"torre_vigia", "posada", "campamento", "ermita"};

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

	static GridPlacement grid(String tipo, int spacing, int salt) {
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(
				"{\"grupo\": \"medianas/" + tipo + "\", \"spacing\": " + spacing + ", \"separation\": " + spacing / 3
						+ ", \"salt\": " + salt + "}")).getOrThrow();
	}

	private static Medianas medianas(int distancia) {
		List<Identifier> tipos = new ArrayList<>();
		List<List<Identifier>> ids = new ArrayList<>();
		List<List<Structure>> estilos = new ArrayList<>();
		List<RandomSpreadStructurePlacement> placements = new ArrayList<>();
		for (int i = 0; i < TIPOS.length; i++) {
			Identifier t = Identifier.fromNamespaceAndPath("heraldia", "medianas/" + TIPOS[i]);
			tipos.add(t);
			ids.add(List.of(Identifier.fromNamespaceAndPath("heraldia", "medianas/" + TIPOS[i] + "/a")));
			estilos.add(List.of());
			placements.add(grid(TIPOS[i], 44, 1000 + i));
		}
		return new Medianas(new Object(), tipos, ids, estilos, placements, null, distancia);
	}

	@Test
	void rejillaLeeSeparacionFrecuenciaYDistancia() throws IOException {
		config("{\"medianas\": {\"posada\": {\"separacion_bloques\": 800}, \"frecuencia_porcentaje\": 400, "
				+ "\"distancia_minima\": {\"bloques\": 160}}}");
		GridPlacement g = grid("posada", 48, 7);
		assertEquals(Math.round(800 / 2.0F / 16), g.spacing(), "400 % = la mitad de separación (cuatro veces más densas)");
		assertEquals(10, g.separation());
		assertTrue(g.offsetX() >= 0 && g.offsetX() < g.spacing() && g.offsetZ() < g.spacing());
		config("{\"medianas\": {\"posada\": {\"separacion_bloques\": 800}, \"distancia_minima\": {\"bloques\": 1024}}}");
		GridPlacement h = grid("posada", 48, 7);
		assertEquals(50, h.spacing());
		assertEquals(25, h.separation(), "la interna, como mucho media casilla");
	}

	@Test
	void desactivadasNoDejanNinguna() throws IOException {
		for (String cfg : new String[]{"{\"medianas\": {\"activadas\": false}}", "{\"medianas\": {\"ermita\": {\"activada\": false}}}"}) {
			config(cfg);
			GridPlacement g = grid("ermita", 56, 3);
			for (int k = -3; k <= 3; k++) {
				ChunkPos c = g.getPotentialStructureChunk(11, k * g.spacing() + g.offsetX(), g.offsetZ());
				assertFalse(g.applyAdditionalChunkRestrictions(c.x(), c.z(), 11), cfg);
			}
		}
		config("{}");
		GridPlacement g = grid("ermita", 56, 3);
		ChunkPos c = g.getPotentialStructureChunk(11, g.offsetX(), g.offsetZ());
		assertTrue(g.applyAdditionalChunkRestrictions(c.x(), c.z(), 11));
	}

	private record Candidata(int tipo, int x, int z) {
	}

	private static List<Candidata> candidatas(Medianas m, long seed, int radio) {
		List<Candidata> out = new ArrayList<>();
		for (int i = 0; i < m.tipos(); i++) {
			RandomSpreadStructurePlacement p = m.placement(i);
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
	void separacionCoherenteEntreMedianas() throws IOException {
		config("{}");
		int distancia = 400; // más que la de por defecto: más choques que comprobar
		long d2 = (long) distancia * distancia;
		Medianas.Zona libre = (x, z) -> false;
		for (long seed : new long[]{1, 42, -9}) {
			Medianas m = medianas(distancia);
			Medianas.Estilos todos = (j, x, z) -> true;
			List<Candidata> all = candidatas(m, seed, 600);
			List<Candidata> vivas = new ArrayList<>();
			for (Candidata c : all) {
				if (!m.rechaza(c.tipo, c.x, c.z, seed, libre, todos, libre)) {
					vivas.add(c);
				}
			}
			assertTrue(vivas.size() > all.size() / 3 && vivas.size() < all.size(), "supervivientes " + vivas.size() + " de " + all.size());
			for (Candidata a : vivas) {
				for (Candidata b : vivas) {
					if (a != b && a.tipo != b.tipo) {
						long dx = (a.x - b.x) * 16L, dz = (a.z - b.z) * 16L;
						assertTrue(dx * dx + dz * dz >= d2, a + " y " + b + " sobreviven las dos a menos de " + distancia);
					}
				}
			}
			int borde = 600 - distancia / 16 - 64;   // lejos del borde de lo enumerado (la que la descarta puede estar fuera)
			for (Candidata c : all) {
				if (vivas.contains(c) || Math.abs(c.x) > borde || Math.abs(c.z) > borde) {
					continue;
				}
				boolean cerca = vivas.stream().anyMatch(v -> v.tipo != c.tipo && Math.pow((v.x - c.x) * 16.0, 2) + Math.pow((v.z - c.z) * 16.0, 2) < d2);
				assertTrue(cerca, c + " descartada sin ninguna superviviente cerca");
			}
			// otra instancia, otro orden: mismo resultado (sin estado que dependa de quién pregunta primero)
			Medianas m2 = medianas(distancia);
			for (int k = all.size() - 1; k >= 0; k--) {
				Candidata c = all.get(k);
				assertEquals(vivas.contains(c), !m2.rechaza(c.tipo, c.x, c.z, seed, libre, todos, libre), c.toString());
			}
		}
	}

	@Test
	void cedenElSitioAEstructurasAjenas() throws IOException {
		config("{}");
		GridPlacement rejilla = grid("posada", 48, 9);   // una rejilla cualquiera hace de estructura vanilla
		Medianas m = new Medianas(new Object(), List.of(), List.of(), List.of(), List.of(), null, 192,
				List.of(new Medianas.Ajena(rejilla, new Structure[]{null}, Medianas.AJENAS_BLOQUES)));
		ChunkPos c = rejilla.getPotentialStructureChunk(3, rejilla.offsetX(), rejilla.offsetZ());
		int cerca = (Medianas.AJENAS_BLOQUES - 16) / 16, lejos = Medianas.AJENAS_BLOQUES / 16 + 2;
		assertTrue(m.cedeAjena(c.x() + cerca, c.z(), 3, (st, x, z) -> true), "sale a menos de la distancia: cede");
		assertFalse(m.cedeAjena(c.x() + lejos, c.z(), 3, (st, x, z) -> true), "más lejos: no");
		Medianas n = new Medianas(new Object(), List.of(), List.of(), List.of(), List.of(), null, 192,
				List.of(new Medianas.Ajena(rejilla, new Structure[]{null}, Medianas.AJENAS_BLOQUES)));
		assertFalse(n.cedeAjena(c.x() + cerca, c.z(), 3, (st, x, z) -> false), "si no sale (bioma), no cede");
	}

	@Test
	void soloLasQueLoPidenCedenALasMinas() throws IOException {
		config("{}");
		GridPlacement mina = grid("posada", 48, 11);    // hace de rejilla de una entrada a mina
		List<Identifier> tipos = List.of(Identifier.fromNamespaceAndPath("heraldia", "medianas/choza_mago"),
				Identifier.fromNamespaceAndPath("heraldia", "medianas/ermita"));
		Medianas m = new Medianas(new Object(), tipos, List.of(List.of(), List.of()), List.of(List.of(), List.of()),
				List.of(grid("choza_mago", 64, 1), grid("ermita", 48, 2)), null, 192, List.of(), new boolean[]{true, false},
				List.of(new Medianas.Ajena(mina, new Structure[]{null}, 192)));
		ChunkPos c = mina.getPotentialStructureChunk(5, mina.offsetX(), mina.offsetZ());
		int cerca = (192 - 16) / 16, lejos = 192 / 16 + 2;
		assertTrue(m.cedeMina(0, c.x() + cerca, c.z(), 5, (st, x, z) -> true), "la choza cede a una mina que sale cerca");
		assertFalse(m.cedeMina(1, c.x() + cerca, c.z(), 5, (st, x, z) -> true), "la ermita no lo pide: no cede");
		assertFalse(m.cedeMina(0, c.x() + lejos, c.z(), 5, (st, x, z) -> true), "más lejos que la distancia mínima: no");
		assertFalse(m.cedeMina(-1, c.x(), c.z(), 5, (st, x, z) -> true), "tipo desconocido: no");
		Medianas n = new Medianas(new Object(), tipos, List.of(List.of(), List.of()), List.of(List.of(), List.of()),
				List.of(grid("choza_mago", 64, 1), grid("ermita", 48, 2)), null, 192, List.of(), new boolean[]{true, false},
				List.of(new Medianas.Ajena(mina, new Structure[]{null}, 192)));
		assertFalse(n.cedeMina(0, c.x() + cerca, c.z(), 5, (st, x, z) -> false), "si la mina no sale (bioma o ladera), no cede");
		// sin la lista de las que ceden (el constructor de siempre), ninguna cede
		Medianas o = new Medianas(new Object(), tipos, List.of(List.of(), List.of()), List.of(List.of(), List.of()),
				List.of(grid("choza_mago", 64, 1), grid("ermita", 48, 2)), null, 192, List.of());
		assertFalse(o.cedeMina(0, c.x() + cerca, c.z(), 5, (st, x, z) -> true));
	}

	@Test
	void zonaYEstilosDescartan() throws IOException {
		config("{}");
		Medianas m = medianas(192);
		Medianas.Zona libre = (x, z) -> false;
		Medianas.Estilos todos = (j, x, z) -> true;
		List<Candidata> all = candidatas(m, 5, 300);
		Candidata c = all.getFirst();
		assertTrue(m.rechaza(c.tipo, c.x, c.z, 77, (x, z) -> x == c.x && z == c.z, todos, libre), "en la zona de una aldea o una única");
		// una vecina que no sale (bioma) o que cae en la Atlántida no descarta a nadie
		Medianas sola = medianas(2000);
		int vivas = 0;
		for (Candidata o : candidatas(sola, 6, 300)) {
			vivas += sola.rechaza(o.tipo, o.x, o.z, 6, libre, (j, x, z) -> j == 0, libre) ? 0 : 1;
		}
		assertTrue(vivas > 1, "con un solo tipo que sale, sus candidatas no las descarta nadie: " + vivas);
		Medianas atl = medianas(2000);
		int vivasAtl = 0;
		for (Candidata o : candidatas(atl, 6, 300)) {
			vivasAtl += atl.rechaza(o.tipo, o.x, o.z, 6, libre, todos, (x, z) -> true) ? 0 : 1;
		}
		assertEquals(candidatas(atl, 6, 300).size(), vivasAtl, "las de la Atlántida no salen, así que no descartan");
	}
}
