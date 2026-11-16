package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonParser;
import com.mojang.serialization.JsonOps;
import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadType;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Lo que consultan a la vez los hilos de generación (con C2ME, muchos más que en vanilla): la candidata con búsqueda de
 * bioma de GridPlacement (memoria compartida por casilla) y la distancia mínima entre únicas (UniqueSeparation, con su
 * recursión y su memoria por consulta). Varios hilos sobre la misma instancia deben dar lo mismo que uno solo, y una
 * búsqueda que aún corre con el mundo anterior no puede dejar su resultado en la memoria del nuevo.
 */
class ConcurrenciaTest {
	private static final long SEED = 42L;
	private static final int HILOS = 8;
	private static final String MICELIO = "{\"grupo\": \"unicas/laboratorio_micelio\", \"spacing\": 250, \"separation\": 190,"
			+ " \"salt\": 98765, \"bioma\": \"minecraft:is_ocean\"}";

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		GridPlacement.testContext(0, null);
		HeraldiaConfig.load(null);
	}

	private static GridPlacement micelio() {
		return GridPlacement.CODEC.codec().parse(JsonOps.INSTANCE, JsonParser.parseString(MICELIO)).getOrThrow();
	}

	/** Bioma falso: franjas de 32 chunks (cuartos de bloque / 4 = bloques / 16 = chunks). */
	private static boolean franjas(int qx, int qz) {
		return Math.floorMod(Math.floorDiv(qx, 4 * 32), 2) == 0 && Math.floorMod(Math.floorDiv(qz, 4 * 48), 3) != 1;
	}

	private static long[] candidatas(GridPlacement g, int casillas) {
		long[] out = new long[casillas * casillas];
		int s = g.spacing(), k = 0;
		for (int gx = 0; gx < casillas; gx++) {
			for (int gz = 0; gz < casillas; gz++) {
				ChunkPos c = g.getPotentialStructureChunk(SEED, (gx - casillas / 2) * s + g.offsetX(), (gz - casillas / 2) * s + g.offsetZ());
				out[k++] = ChunkPos.pack(c.x(), c.z());
			}
		}
		return out;
	}

	@Test
	void busquedaDeBiomaEnVariosHilosIgualQueEnSerie() throws Exception {
		GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> franjas(qx, qz));
		long[] esperado = candidatas(micelio(), 12);
		GridPlacement compartida = micelio();
		ExecutorService pool = Executors.newFixedThreadPool(HILOS);
		try {
			List<Future<long[]>> futuros = new ArrayList<>();
			for (int h = 0; h < HILOS; h++) {
				futuros.add(pool.submit(() -> candidatas(compartida, 12)));
			}
			for (Future<long[]> f : futuros) {
				assertArrayEquals(esperado, f.get(60, TimeUnit.SECONDS));
			}
		} finally {
			pool.shutdownNow();
		}
	}

	/**
	 * Cambio de mundo con búsquedas en marcha: los hilos buscan con un contexto lento (otro mundo) mientras se pasa al
	 * nuevo; acabada la carrera, toda candidata debe ser la del nuevo contexto. Con una sola memoria por instancia (lo de
	 * antes), una búsqueda vieja que terminaba después del cambio dejaba su candidata para siempre.
	 */
	@Test
	void unaBusquedaDelMundoAnteriorNoQuedaEnElNuevo() throws Exception {
		GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> franjas(qx, qz));
		long[] nuevo = candidatas(micelio(), 6);
		GridPlacement g = micelio();
		CountDownLatch empezadas = new CountDownLatch(HILOS);
		AtomicBoolean lento = new AtomicBoolean(true);
		GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> {
			if (lento.get()) {
				empezadas.countDown();
				long fin = System.nanoTime() + 20_000;
				while (System.nanoTime() < fin) {
					Thread.onSpinWait();
				}
			}
			return true; // el mundo anterior: todo es del bioma (otra candidata en cada casilla)
		});
		ExecutorService pool = Executors.newFixedThreadPool(HILOS);
		try {
			List<Future<long[]>> futuros = new ArrayList<>();
			for (int h = 0; h < HILOS; h++) {
				futuros.add(pool.submit(() -> candidatas(g, 6)));
			}
			assertTrue(empezadas.await(30, TimeUnit.SECONDS));
			GridPlacement.testContext(SEED, (tag, qx, qy, qz) -> franjas(qx, qz)); // el mundo nuevo (misma semilla)
			candidatas(g, 6); // primeras consultas del mundo nuevo mientras las viejas siguen (lentas)
			lento.set(false); // ahora terminan las viejas: su resultado no debe pisar el del mundo nuevo
			for (Future<long[]> f : futuros) {
				f.get(120, TimeUnit.SECONDS);
			}
		} finally {
			pool.shutdownNow();
		}
		assertArrayEquals(nuevo, candidatas(g, 6));
	}

	@Test
	void distanciaMinimaEnVariosHilosIgualQueEnSerie() throws Exception {
		int n = 6;
		List<Identifier> ids = new ArrayList<>();
		List<RandomSpreadStructurePlacement> grids = new ArrayList<>();
		for (int i = 0; i < n; i++) {
			ids.add(Identifier.fromNamespaceAndPath("heraldia", "unicas/u" + i));
			grids.add(new RandomSpreadStructurePlacement(40 + 3 * i, 20, RandomSpreadType.LINEAR, 1000 + 7919 * i));
		}
		List<Structure> none = new ArrayList<>(Collections.nCopies(n, (Structure) null));
		UniqueSeparation sep = new UniqueSeparation("prueba", ids, none, grids, Collections.nCopies(n, false), true, 1000);
		UniqueSeparation.Viability v = (j, x, z) -> Long.hashCode(UniqueSeparation.mix(ChunkPos.pack(x, z) * 31 + j)) % 3 != 0;
		int casillas = 30;
		boolean[] esperado = new boolean[n * casillas * casillas];
		int[][] pos = new int[esperado.length][];
		int k = 0;
		for (int i = 0; i < n; i++) {
			int s = grids.get(i).spacing();
			for (int gx = 0; gx < casillas; gx++) {
				for (int gz = 0; gz < casillas; gz++) {
					ChunkPos c = grids.get(i).getPotentialStructureChunk(SEED, gx * s, gz * s);
					pos[k] = new int[]{i, c.x(), c.z()};
					esperado[k] = sep.blocked(i, c.x(), c.z(), SEED, v);
					k++;
				}
			}
		}
		int descartadas = 0;
		for (boolean b : esperado) {
			descartadas += b ? 1 : 0;
		}
		assertTrue(descartadas > 0 && descartadas < esperado.length, "la prueba debe tener de las dos: " + descartadas);
		ExecutorService pool = Executors.newFixedThreadPool(HILOS);
		try {
			List<Future<boolean[]>> futuros = new ArrayList<>();
			for (int h = 0; h < HILOS; h++) {
				int desde = h;
				futuros.add(pool.submit(() -> {
					boolean[] got = new boolean[esperado.length];
					for (int m = 0; m < got.length; m++) {
						int q = (m * 13 + desde * 977) % got.length;
						got[q] = sep.blocked(pos[q][0], pos[q][1], pos[q][2], SEED, v);
					}
					return got;
				}));
			}
			for (Future<boolean[]> f : futuros) {
				assertArrayEquals(esperado, f.get(120, TimeUnit.SECONDS));
			}
		} finally {
			pool.shutdownNow();
		}
		assertEquals(esperado.length, pos.length);
	}
}
