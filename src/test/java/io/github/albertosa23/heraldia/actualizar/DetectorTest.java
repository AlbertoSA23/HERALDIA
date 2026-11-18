package io.github.albertosa23.heraldia.actualizar;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.actualizar.Detector.Clase;
import io.github.albertosa23.heraldia.actualizar.Detector.Construccion;
import io.github.albertosa23.heraldia.actualizar.Detector.Motivo;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/**
 * Detección de construcciones con casos sintéticos, el margen de 50 bloques exactos y la clasificación de los chunks
 * vírgenes (lógica pura de {@link Detector}, sin el juego).
 */
class DetectorTest {
	private static final int MIN_Y = -64;
	private static final Detector.Parametros P = Detector.Parametros.porDefecto(50);

	/** Un chunk generado del todo, con su InhabitedTime, bloques de jugador {x, y, z} del mundo e inicios. */
	static ResumenChunk chunk(int cx, int cz, long habitado, List<int[]> jugador, Map<String, List<int[]>> inicios) {
		int[] j = new int[jugador.size()];
		for (int i = 0; i < j.length; i++) {
			int[] b = jugador.get(i);
			j[i] = ResumenChunk.empaquetar(b[0] - cx * 16, b[1], b[2] - cz * 16, MIN_Y);
		}
		return new ResumenChunk(cx, cz, true, habitado, MIN_Y, j, inicios, new int[0], new String[0]);
	}

	static ResumenChunk vacio(int cx, int cz) {
		return chunk(cx, cz, 0, List.of(), Map.of());
	}

	/** Una zona de 21 × 21 chunks (−10..10) vacía. */
	static List<ResumenChunk> mundo() {
		List<ResumenChunk> out = new ArrayList<>();
		for (int cx = -10; cx <= 10; cx++) {
			for (int cz = -10; cz <= 10; cz++) {
				out.add(vacio(cx, cz));
			}
		}
		return out;
	}

	static void poner(List<ResumenChunk> m, ResumenChunk c) {
		m.removeIf(r -> r.cx() == c.cx() && r.cz() == c.cz());
		m.add(c);
	}

	@Test
	void margenDeCincuentaBloquesExactos() {
		Construccion casa = Construccion.punto(0, 0, Motivo.BLOQUES);
		// chunk 3 (x 48..63): su borde está a 48 bloques -> protegido; chunk 4 (x 64..79): a 64 -> libre
		assertTrue(Detector.cerca(casa, 3, 0, 50));
		assertFalse(Detector.cerca(casa, 4, 0, 50));
		// el borde exacto: un punto a 50 bloques del chunk cuenta (≤ 50); a 51 no
		assertTrue(Detector.cerca(Construccion.punto(-2, 5, Motivo.BLOQUES), 3, 0, 50));    // 48 - (-2) = 50
		assertFalse(Detector.cerca(Construccion.punto(-3, 5, Motivo.BLOQUES), 3, 0, 50));   // 51
		// en diagonal se mide en línea recta: (48, 48) está a 67,9 del (0, 0)
		assertFalse(Detector.cerca(casa, 3, 3, 50));
		assertTrue(Detector.cerca(casa, 2, 2, 50));                                          // (32, 32): 45,3
		// hacia el lado negativo, igual: el chunk −4 acaba en x = −49
		assertTrue(Detector.cerca(casa, -4, 0, 50));
		assertFalse(Detector.cerca(casa, -5, 0, 50));                                        // acaba en −65
	}

	@Test
	void ningunBloqueDeUnChunkProtegidoQuedaFueraDelMargenNiAlReves() {
		Construccion casa = new Construccion(100, 200, 110, 215, Motivo.BLOQUES);
		Set<Long> prot = Detector.protegidos(List.of(casa), 50);
		for (int cx = 0; cx < 20; cx++) {
			for (int cz = 5; cz < 25; cz++) {
				double min = Double.MAX_VALUE;
				for (int x = cx * 16; x < cx * 16 + 16; x++) {
					for (int z = cz * 16; z < cz * 16 + 16; z++) {
						min = Math.min(min, Detector.distancia(casa.minX(), casa.minZ(), casa.maxX(), casa.maxZ(), x, z, x, z));
					}
				}
				assertEquals(min <= 50, prot.contains(ResumenChunk.clave(cx, cz)), "chunk " + cx + "," + cz + " a " + min);
			}
		}
	}

	@Test
	void unaCasaProtegeSuMargenYLoDemasEsVirgen() {
		List<ResumenChunk> m = mundo();
		poner(m, chunk(0, 0, 0, List.of(new int[] {5, 70, 5}, new int[] {6, 70, 5}), Map.of()));   // cama y cofre en (5, 5)
		Detector.Resultado r = Detector.clasificar(m, Map.of(), List.of(), P);
		assertEquals(Clase.CONSTRUCCION, r.clase(0, 0));
		assertEquals(Clase.PROTEGIDO, r.clase(3, 0));          // x 48 - 6 = 42
		assertEquals(Clase.PROTEGIDO, r.clase(-3, 0));         // 5 - (-33) = 38
		assertEquals(Clase.NORMAL, r.clase(4, 0));             // a 58 bloques, pero junto a un chunk protegido: no se regenera
		assertEquals(Clase.VIRGEN, r.clase(5, 0));
		assertEquals(Clase.VIRGEN, r.clase(10, 10));
		assertEquals(2, r.porMotivo().get(Motivo.BLOQUES));
		// nada virgen a 50 bloques o menos de la casa, ni junto a un chunk protegido (sus rasgos escribirían en él)
		r.clases().forEach((k, c) -> {
			if (c == Clase.VIRGEN) {
				int cx = ResumenChunk.cx(k), cz = ResumenChunk.cz(k);
				assertFalse(Detector.cerca(Construccion.punto(5, 5, Motivo.BLOQUES), cx, cz, 50));
				for (int dx = -1; dx <= 1; dx++) {
					for (int dz = -1; dz <= 1; dz++) {
						assertFalse(r.protegidos().contains(ResumenChunk.clave(cx + dx, cz + dz)), cx + "," + cz);
					}
				}
			}
		});
	}

	@Test
	void losBloquesDentroDeUnaEstructuraNoSonConstruccion() {
		List<ResumenChunk> m = mundo();
		int[] pieza = {0, 60, 0, 40, 80, 40};                    // una aldea con camas y cofres dentro
		poner(m, chunk(0, 0, 0, List.of(new int[] {5, 70, 5}), Map.of("minecraft:village_plains", List.of(pieza))));
		poner(m, chunk(1, 1, 0, List.of(new int[] {20, 70, 20}), Map.of()));          // dentro de la pieza (de otro chunk)
		Detector.Resultado r = Detector.clasificar(m, Map.of(), List.of(), P);
		assertEquals(Clase.VIRGEN, r.clase(0, 0));
		assertEquals(Clase.VIRGEN, r.clase(1, 1));
		assertTrue(r.construcciones().isEmpty());
		// fuera de la pieza (y = 90), sí
		poner(m, chunk(1, 1, 0, List.of(new int[] {20, 90, 20}), Map.of()));
		assertEquals(Clase.CONSTRUCCION, Detector.clasificar(m, Map.of(), List.of(), P).clase(1, 1));
	}

	@Test
	void losBloquesAmbiguosSoloCuentanConJugadoresCerca() {
		List<ResumenChunk> m = mundo();
		// tablones de los puentes de una mina abandonada (fuera de su caja) o un cofre de mazmorra, sin nadie que haya pasado
		int[] tablon = {ResumenChunk.empaquetar(3, 20, 3, MIN_Y) | ResumenChunk.AMBIGUO};
		poner(m, new ResumenChunk(6, 6, true, 0, MIN_Y, tablon, Map.of(), new int[0], new String[0]));
		assertEquals(Clase.VIRGEN, Detector.clasificar(m, Map.of(), List.of(), P).clase(6, 6));
		// el mismo bloque donde ha estado un jugador: construcción
		poner(m, new ResumenChunk(6, 6, true, 40, MIN_Y, tablon, Map.of(), new int[0], new String[0]));
		assertEquals(Clase.CONSTRUCCION, Detector.clasificar(m, Map.of(), List.of(), P).clase(6, 6));
		assertTrue(BloquesJugador.ambiguo("minecraft:oak_planks") && BloquesJugador.ambiguo("minecraft:chest"));
		assertFalse(BloquesJugador.ambiguo("minecraft:red_bed") || BloquesJugador.ambiguo("minecraft:crafting_table"));
		assertTrue(BloquesJugador.deJugador("minecraft:red_bed") && BloquesJugador.deJugador("minecraft:oak_sign"));
		assertFalse(BloquesJugador.deJugador("minecraft:stone") || BloquesJugador.deJugador("minecraft:oak_log")
				|| BloquesJugador.deJugador("othermod:fancy_bed"));
		assertTrue(BloquesJugador.cimaNatural("minecraft:oak_leaves") && !BloquesJugador.cimaNatural("minecraft:cobblestone"));
	}

	@Test
	void inhabitedTimeDecideVirgenYBase() {
		List<ResumenChunk> m = mundo();
		poner(m, chunk(5, 5, 1199, List.of(), Map.of()));
		poner(m, chunk(6, 6, 1200, List.of(), Map.of()));
		poner(m, chunk(-8, -8, 72_000, List.of(), Map.of()));      // una hora de jugadores: cuenta como construcción
		Detector.Resultado r = Detector.clasificar(m, Map.of(), List.of(), P);
		assertEquals(Clase.VIRGEN, r.clase(5, 5));
		assertEquals(Clase.NORMAL, r.clase(6, 6));
		assertEquals(Clase.CONSTRUCCION, r.clase(-8, -8));
		assertEquals(Clase.PROTEGIDO, r.clase(-5, -8));            // a 33 bloques del chunk habitado
	}

	@Test
	void lasDiferenciasConLaRegeneracionCuentanDesdeTresColumnas() {
		List<ResumenChunk> m = mundo();
		long k = ResumenChunk.clave(2, 2);
		Map<Long, List<int[]>> dos = Map.of(k, List.of(new int[] {34, 34}, new int[] {38, 34}));
		assertEquals(Clase.VIRGEN, Detector.clasificar(m, dos, List.of(), P).clase(2, 2));
		Map<Long, List<int[]>> tres = Map.of(k, List.of(new int[] {34, 34}, new int[] {38, 34}, new int[] {42, 34}));
		Detector.Resultado r = Detector.clasificar(m, tres, List.of(), P);
		assertEquals(Clase.CONSTRUCCION, r.clase(2, 2));
		assertEquals(3, r.porMotivo().get(Motivo.DIFERENCIA));
	}

	@Test
	void spawnCamasYJugadoresProtegen() {
		List<ResumenChunk> m = mundo();
		List<Construccion> extra = List.of(Construccion.punto(0, 0, Motivo.SPAWN), Construccion.punto(150, 150, Motivo.REAPARICION),
				Construccion.punto(-150, 100, Motivo.JUGADOR));
		Detector.Resultado r = Detector.clasificar(m, Map.of(), extra, P);
		assertEquals(Clase.CONSTRUCCION, r.clase(0, 0));
		assertEquals(Clase.CONSTRUCCION, r.clase(9, 9));
		assertEquals(Clase.CONSTRUCCION, r.clase(-10, 6));
		assertEquals(Clase.PROTEGIDO, r.clase(7, 9));
		assertEquals(Clase.VIRGEN, r.clase(5, -5));
	}

	@Test
	void unChunkAMedioGenerarNoEsVirgen() {
		List<ResumenChunk> m = mundo();
		poner(m, new ResumenChunk(8, 8, false, 0, MIN_Y, new int[0], Map.of(), new int[0], new String[0]));
		assertEquals(Clase.INCOMPLETO, Detector.clasificar(m, Map.of(), List.of(), P).clase(8, 8));
	}

	@Test
	void otroMargenConfigurable() {
		Construccion casa = Construccion.punto(0, 0, Motivo.BLOQUES);
		assertFalse(Detector.protegidos(List.of(casa), 16).contains(ResumenChunk.clave(2, 0)));   // 32 > 16
		assertTrue(Detector.protegidos(List.of(casa), 100).contains(ResumenChunk.clave(6, 0)));   // 96 ≤ 100
	}

	@Test
	void noSeRegeneraLoQueCortariaUnaEstructura() {
		Set<Long> generados = new HashSet<>(), virgenes = new HashSet<>();
		for (int cx = 0; cx < 6; cx++) {
			for (int cz = 0; cz < 6; cz++) {
				generados.add(ResumenChunk.clave(cx, cz));
				virgenes.add(ResumenChunk.clave(cx, cz));
			}
		}
		virgenes.remove(ResumenChunk.clave(3, 0));                  // uno que se queda (no virgen)
		Map<Long, List<int[]>> req = new HashMap<>();
		req.put(ResumenChunk.clave(2, 0), List.of(new int[] {32, 0, 0, 63, 50, 15}));   // pisaría el chunk 3,0
		req.put(ResumenChunk.clave(0, 4), List.of(new int[] {0, 0, 64, 31, 50, 79}));   // cae en vírgenes: vale
		req.put(ResumenChunk.clave(5, 5), List.of(new int[] {80, 0, 80, 120, 50, 120})); // sale a chunks sin generar: vale
		req.put(ResumenChunk.clave(1, 0), List.of(new int[] {16, 0, 0, 47, 50, 15}));   // pisa el 2,0, que no se borra
		Set<Long> r = Detector.regenerables(virgenes, generados, req);
		assertFalse(r.contains(ResumenChunk.clave(2, 0)));
		assertFalse(r.contains(ResumenChunk.clave(1, 0)));          // en cadena
		assertTrue(r.contains(ResumenChunk.clave(0, 4)));
		assertTrue(r.contains(ResumenChunk.clave(5, 5)));
		assertTrue(r.contains(ResumenChunk.clave(4, 4)));
		assertEquals(virgenes.size() - 2, r.size());
	}

	@Test
	void unaEstructuraNuevaSoloSeColocaLejosDeLasConstrucciones() {
		List<ResumenChunk> m = mundo();
		poner(m, chunk(0, 0, 0, List.of(new int[] {5, 70, 5}), Map.of()));
		for (int cx = 5; cx <= 10; cx++) {
			poner(m, chunk(cx, 0, 5000, List.of(), Map.of()));     // normales (habitados un poco)
		}
		poner(m, chunk(8, 3, 0, List.of(), Map.of("minecraft:pillager_outpost", List.of(new int[] {130, 60, 50, 140, 80, 60}))));
		Detector.Resultado r = Detector.clasificar(m, Map.of(), List.of(), P);
		Map<Long, List<int[]>> piezas = Detector.piezasPorChunk(m);
		List<int[]> elegidas = new ArrayList<>();
		// a 5 chunks de la casa (80 bloques) y su caja de 2 × 2 chunks: lejos del margen
		assertTrue(Detector.colocable(new int[] {80, 60, 0, 111, 80, 31}, ResumenChunk.clave(5, 0), r, Set.of(), piezas, elegidas));
		// una caja que se acerca a la casa (x desde 40): no
		assertFalse(Detector.colocable(new int[] {40, 60, 0, 111, 80, 31}, ResumenChunk.clave(5, 0), r, Set.of(), piezas, elegidas));
		// encima de otra estructura guardada: no
		assertFalse(Detector.colocable(new int[] {120, 60, 40, 150, 80, 70}, ResumenChunk.clave(8, 0), r, Set.of(), piezas, elegidas));
		// encima de una ya elegida: no
		elegidas.add(new int[] {80, 60, 0, 111, 80, 31});
		assertFalse(Detector.colocable(new int[] {100, 60, 0, 130, 80, 20}, ResumenChunk.clave(6, 0), r, Set.of(), piezas, elegidas));
		// en un chunk que se va a regenerar: no
		assertFalse(Detector.colocable(new int[] {160, 60, 0, 175, 80, 15}, ResumenChunk.clave(10, 0), r,
				Set.of(ResumenChunk.clave(10, 0)), piezas, List.of()));
	}
}
