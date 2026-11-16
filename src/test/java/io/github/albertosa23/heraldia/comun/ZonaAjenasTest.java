package io.github.albertosa23.heraldia.comun;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Random;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicInteger;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.GenerationStep;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * ZonaAjenas sin servidor: qué estructuras cuentan como ajenas, qué candidatas de Heraldia están cerca (frente a un
 * recorrido de todas las casillas a mano), que solo se excluye si la de Heraldia sale de verdad, la memoria por
 * candidata y semilla, y que varios hilos a la vez (la generación, también con C2ME) dan lo mismo que uno solo.
 * Las rejillas son random_spread corrientes (como las de las aldeas y las únicas sin desfase); la viabilidad, falsa.
 */
class ZonaAjenasTest {
	private static final int DISTANCE = 224;
	private static final long SEED = 123456789L;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static RandomSpreadStructurePlacement grid(int spacing, int separation, int salt) {
		return new RandomSpreadStructurePlacement(spacing, separation, RandomSpreadType.LINEAR, salt);
	}

	/** Dos únicas de rejilla y una de colocación propia (la Atlántida, que ZonaAjenas no mira). */
	private static UniqueSeparation uniques() {
		List<Identifier> ids = List.of(Identifier.parse("heraldia:unicas/a"), Identifier.parse("heraldia:unicas/b"),
				Identifier.parse("heraldia:unicas/atlantida"));
		List<Structure> none = new ArrayList<>(Collections.nCopies(3, (Structure) null));
		return new UniqueSeparation("prueba", ids, none, List.of(grid(40, 10, 11), grid(55, 20, 22), grid(4096, 0, 33)),
				List.of(false, false, true), true, 1000);
	}

	private static ZonaAjenas zona(int distance) {
		return new ZonaAjenas("prueba", distance, grid(24, 16, 261112013), List.of(), List.of());
	}

	/** Viabilidad falsa y determinista: «sale» la mitad de las candidatas (también las aldeas, tipo -1). */
	private static boolean sale(int tipo, int x, int z, long seed) {
		return Long.hashCode(ZonaAjenas.clave(tipo, x, z) * 0x9E3779B97F4A7C15L ^ seed) % 2 == 0;
	}

	@Test
	void ajenasSonLasDeOtrosModsQueAsoman() {
		assertFalse(ZonaAjenas.deOtroMod(Identifier.parse("heraldia:castellana")));
		assertFalse(ZonaAjenas.deOtroMod(Identifier.parse("minecraft:village_plains")));
		assertTrue(ZonaAjenas.deOtroMod(Identifier.parse("towns_and_towers:village_forest")));
		assertTrue(ZonaAjenas.visible(GenerationStep.Decoration.SURFACE_STRUCTURES));
		assertTrue(ZonaAjenas.visible(GenerationStep.Decoration.RAW_GENERATION));
		for (GenerationStep.Decoration d : List.of(GenerationStep.Decoration.UNDERGROUND_STRUCTURES, GenerationStep.Decoration.STRONGHOLDS,
				GenerationStep.Decoration.UNDERGROUND_DECORATION, GenerationStep.Decoration.UNDERGROUND_ORES)) {
			assertFalse(ZonaAjenas.visible(d), d.toString());
		}
	}

	@Test
	void soloEnElMundoPrincipalYConDistancia() {
		assertTrue(zona(DISTANCE).activa(Level.OVERWORLD));
		assertFalse(zona(DISTANCE).activa(Level.NETHER));
		assertFalse(zona(0).activa(Level.OVERWORLD));
	}

	/** Todas las candidatas a menos de la distancia, recorriendo a mano una ventana amplia de casillas. */
	private static Set<List<Long>> aMano(UniqueSeparation sep, RandomSpreadStructurePlacement aldeas, int cx, int cz) {
		Set<List<Long>> out = new HashSet<>();
		for (int i = -1; i < sep.size(); i++) {
			if (i >= 0 && sep.fixed(i)) {
				continue;
			}
			RandomSpreadStructurePlacement p = i < 0 ? aldeas : sep.placement(i);
			int s = p.spacing();
			for (int gx = Math.floorDiv(cx, s) - 3; gx <= Math.floorDiv(cx, s) + 3; gx++) {
				for (int gz = Math.floorDiv(cz, s) - 3; gz <= Math.floorDiv(cz, s) + 3; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(SEED, gx * s, gz * s);
					long dx = (c.x() - (long) cx) * 16, dz = (c.z() - (long) cz) * 16;
					if (dx * dx + dz * dz <= (long) DISTANCE * DISTANCE) {
						out.add(List.of((long) (i < 0 ? ZonaAjenas.ALDEA : i), (long) c.x(), (long) c.z()));
					}
				}
			}
		}
		return out;
	}

	private static Set<List<Long>> triples(long[] t) {
		Set<List<Long>> out = new HashSet<>();
		if (t != null) {
			assertEquals(0, t.length % 3);
			for (int k = 0; k < t.length; k += 3) {
				assertTrue(out.add(List.of(t[k], t[k + 1], t[k + 2])), "candidata repetida");
			}
		}
		return out;
	}

	@Test
	void cercanasSonTodasLasDeDentroYNingunaMas() {
		UniqueSeparation sep = uniques();
		ZonaAjenas z = zona(DISTANCE);
		RandomSpreadStructurePlacement aldeas = grid(24, 16, 261112013);
		Random r = new Random(7);
		int conAlguna = 0;
		for (int n = 0; n < 2000; n++) {
			int cx = r.nextInt(4000) - 2000, cz = r.nextInt(4000) - 2000;
			long[] t = z.cercanas(sep, SEED, cx, cz);
			Set<List<Long>> esperadas = aMano(sep, aldeas, cx, cz);
			assertEquals(esperadas, triples(t), "chunk " + cx + ", " + cz);
			if (t == null) {
				assertTrue(esperadas.isEmpty());
			} else {
				conAlguna++;
			}
		}
		assertTrue(conAlguna > 200 && conAlguna < 2000, "la prueba debe ver chunks con y sin candidatas cerca: " + conAlguna);
	}

	@Test
	void excluyeSoloSiLaDeHeraldiaSaleDeVerdad() {
		UniqueSeparation sep = uniques();
		ZonaAjenas z = zona(DISTANCE);
		Random r = new Random(11);
		int excluidas = 0, libres = 0;
		for (int n = 0; n < 2000; n++) {
			int cx = r.nextInt(4000) - 2000, cz = r.nextInt(4000) - 2000;
			long[] t = z.cercanas(sep, SEED, cx, cz);
			if (t == null) {
				continue;
			}
			boolean alguna = false;
			for (int k = 0; k < t.length; k += 3) {
				alguna |= sale((int) t[k], (int) t[k + 1], (int) t[k + 2], SEED);
			}
			// una única cuenta si es viable y no la descarta la distancia mínima entre únicas (la misma regla que la generación)
			boolean esperado = false;
			for (int k = 0; k < t.length; k += 3) {
				int tipo = (int) t[k], x = (int) t[k + 1], zz = (int) t[k + 2];
				esperado |= tipo == ZonaAjenas.ALDEA ? sale(tipo, x, zz, SEED)
						: sale(tipo, x, zz, SEED) && !sep.blocked(tipo, x, zz, SEED, (j, a, b) -> sale(j, a, b, SEED));
			}
			boolean got = z.ocupada(t, sep, SEED, (j, a, b) -> sale(j, a, b, SEED), (a, b) -> sale(ZonaAjenas.ALDEA, a, b, SEED));
			assertEquals(esperado, got, "chunk " + cx + ", " + cz);
			if (got) {
				excluidas++;
			} else {
				libres++;
			}
			assertTrue(alguna || !got, "excluida sin ninguna candidata viable");
		}
		assertTrue(excluidas > 0 && libres > 0, "excluidas " + excluidas + ", libres " + libres);
	}

	@Test
	void laViabilidadSeCalculaUnaVezPorCandidataYSemilla() {
		UniqueSeparation sep = uniques();
		ZonaAjenas z = zona(DISTANCE);
		long[] cerca = {ZonaAjenas.ALDEA, 5, 7};
		AtomicInteger llamadas = new AtomicInteger();
		for (int n = 0; n < 50; n++) {
			assertTrue(z.ocupada(cerca, sep, SEED, (j, a, b) -> false, (a, b) -> llamadas.incrementAndGet() > 0));
		}
		assertEquals(1, llamadas.get());
		// otra semilla (otro mundo): memoria nueva, no se reutiliza el resultado de la anterior
		assertFalse(z.ocupada(cerca, sep, SEED + 1, (j, a, b) -> false, (a, b) -> false));
		assertEquals(1, llamadas.get());
	}

	@Test
	void clavesDistintasParaCandidatasDistintas() {
		Set<Long> vistas = new HashSet<>();
		int[] coords = {-1_900_000, -65536, -1, 0, 1, 65535, 1_900_000};
		for (int tipo = -1; tipo < 20; tipo++) {
			for (int x : coords) {
				for (int z : coords) {
					assertTrue(vistas.add(ZonaAjenas.clave(tipo, x, z)), tipo + " " + x + " " + z);
				}
			}
		}
	}

	/** Varios hilos a la vez (como los de generación, también con C2ME) sobre la misma instancia dan lo mismo que uno. */
	@Test
	void concurrenteIgualQueEnSerie() throws Exception {
		UniqueSeparation sep = uniques();
		Random r = new Random(3);
		int n = 4000;
		int[] xs = new int[n], zs = new int[n];
		for (int k = 0; k < n; k++) {
			xs[k] = r.nextInt(3000) - 1500;
			zs[k] = r.nextInt(3000) - 1500;
		}
		ZonaAjenas serie = zona(DISTANCE);
		boolean[] esperado = new boolean[n];
		for (int k = 0; k < n; k++) {
			long[] t = serie.cercanas(sep, SEED, xs[k], zs[k]);
			esperado[k] = t != null && serie.ocupada(t, sep, SEED, (j, a, b) -> sale(j, a, b, SEED), (a, b) -> sale(ZonaAjenas.ALDEA, a, b, SEED));
		}
		ZonaAjenas compartida = zona(DISTANCE);
		AtomicInteger viabilidades = new AtomicInteger();
		ExecutorService pool = Executors.newFixedThreadPool(8);
		try {
			List<Future<boolean[]>> futuros = new ArrayList<>();
			for (int h = 0; h < 8; h++) {
				int desde = h;
				futuros.add(pool.submit(() -> {
					boolean[] got = new boolean[n];
					for (int i = 0; i < n; i++) {
						int k = (i * 7 + desde * 131) % n; // cada hilo en otro orden: se pisan en la memoria
						long[] t = compartida.cercanas(sep, SEED, xs[k], zs[k]);
						got[k] = t != null && compartida.ocupada(t, sep, SEED, (j, a, b) -> {
							viabilidades.incrementAndGet();
							return sale(j, a, b, SEED);
						}, (a, b) -> {
							viabilidades.incrementAndGet();
							return sale(ZonaAjenas.ALDEA, a, b, SEED);
						});
					}
					return got;
				}));
			}
			for (Future<boolean[]> f : futuros) {
				assertArrayEquals(esperado, f.get(60, TimeUnit.SECONDS));
			}
		} finally {
			pool.shutdownNow();
		}
		assertTrue(viabilidades.get() > 0);
	}
}
