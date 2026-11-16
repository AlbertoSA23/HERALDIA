package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Curva de oleadas, tandas con el límite de vivos, rotación de tipos y mini-jefe, experiencia y recompensas. */
class OleadasTest {
	private static final int MOBS = 50, STATS = 10;

	@Test
	void porDefectoCincuentaYDiez() {
		assertEquals(List.of(4, 6, 8, 10, 12, 14), List.of(Oleadas.mobs(1, MOBS), Oleadas.mobs(2, MOBS), Oleadas.mobs(3, MOBS),
				Oleadas.mobs(4, MOBS), Oleadas.mobs(5, MOBS), Oleadas.mobs(6, MOBS)));
		assertEquals(1.0, Oleadas.stats(1, STATS), 1e-9);
		assertEquals(1.1, Oleadas.stats(2, STATS), 1e-9);
		assertEquals(1.2, Oleadas.stats(3, STATS), 1e-9);
		assertEquals(0.0, Oleadas.modificador(1, STATS), 1e-9);
		assertEquals(0.5, Oleadas.modificador(6, STATS), 1e-9);
	}

	@Test
	void siempreSubenLasDosCosas() {
		for (int mobs = 10; mobs <= 200; mobs += 5) {
			for (int stats = 1; stats <= 100; stats += 3) {
				int s = Oleadas.statsEfectivo(mobs, stats);
				for (int n = 1; n < 60; n++) {
					assertTrue(Oleadas.mobs(n + 1, mobs) > Oleadas.mobs(n, mobs), "mobs " + mobs + " oleada " + n);
					assertTrue(Oleadas.stats(n + 1, s) > Oleadas.stats(n, s), "stats " + s + " oleada " + n);
				}
			}
		}
	}

	@Test
	void losMobsCrecenProporcionalmenteMas() {
		for (int mobs = 10; mobs <= 200; mobs += 5) {
			for (int stats = 1; stats <= 100; stats += 3) {
				int s = Oleadas.statsEfectivo(mobs, stats);
				assertTrue(s <= mobs, "stats efectivo " + s + " > mobs " + mobs);
				for (int n = 2; n < 60; n++) {
					double crecMobs = (double) Oleadas.mobs(n, mobs) / Oleadas.mobs(1, mobs);
					assertTrue(crecMobs + 1e-9 >= Oleadas.stats(n, s), "mobs " + mobs + " stats " + s + " oleada " + n);
				}
			}
		}
		// por defecto, estrictamente más
		for (int n = 2; n < 60; n++) {
			assertTrue((double) Oleadas.mobs(n, MOBS) / Oleadas.mobs(1, MOBS) > Oleadas.stats(n, STATS));
		}
	}

	@Test
	void statsEfectivoRecortaAlDeMobs() {
		assertEquals(10, Oleadas.statsEfectivo(50, 10));
		assertEquals(30, Oleadas.statsEfectivo(30, 80));
		assertEquals(1, Oleadas.statsEfectivo(50, 0));
	}

	@Test
	void oleadasFueraDeRango() {
		assertEquals(Oleadas.BASE, Oleadas.mobs(0, MOBS));
		assertEquals(Oleadas.BASE, Oleadas.mobs(-5, MOBS));
		assertEquals(Oleadas.mobs(Oleadas.MAX_OLEADA, MOBS), Oleadas.mobs(Oleadas.MAX_OLEADA + 50, MOBS));
	}

	@Test
	void tandasConElLimiteDeVivos() {
		assertEquals(14, Oleadas.aparecen(0, 14, 20));
		assertEquals(20, Oleadas.aparecen(0, 30, 20));
		assertEquals(5, Oleadas.aparecen(15, 30, 20));
		assertEquals(0, Oleadas.aparecen(20, 30, 20));
		assertEquals(0, Oleadas.aparecen(25, 30, 20));
		assertEquals(0, Oleadas.aparecen(3, 0, 20));
	}

	@Test
	void rotacionDeTipos() {
		assertEquals(Oleadas.Tanda.ZOMBIS, Oleadas.tanda(1));
		assertEquals(Oleadas.Tanda.ESQUELETOS_ARANAS, Oleadas.tanda(2));
		assertEquals(Oleadas.Tanda.MEZCLA, Oleadas.tanda(3));
		assertEquals(Oleadas.Tanda.MEZCLA_DURA, Oleadas.tanda(4));
		assertEquals(Oleadas.Tanda.ZOMBIS, Oleadas.tanda(5));
		assertTrue(Set.copyOf(Oleadas.tipos(1, MOBS)).stream().allMatch(t -> t.contains("zombie") || t.contains("husk")));
		assertEquals(Set.of("minecraft:skeleton", "minecraft:spider"), Set.copyOf(Oleadas.tipos(2, MOBS)));
		for (int n = 1; n < 30; n++) {
			List<String> t = Oleadas.tipos(n, MOBS);
			assertEquals(Oleadas.mobs(n, MOBS), t.size());
			assertTrue(Oleadas.tanda(n).mobs().containsAll(t));
			// repartidos por turnos: con mobs de sobra salen todos los tipos de la tanda
			if (t.size() >= Oleadas.tanda(n).mobs().size()) {
				assertEquals(new HashSet<>(Oleadas.tanda(n).mobs()), new HashSet<>(t));
			}
		}
	}

	@Test
	void miniJefeCadaCinco() {
		for (int n = 1; n <= 40; n++) {
			assertEquals(n % 5 == 0, Oleadas.conJefe(n), "oleada " + n);
			assertEquals(Oleadas.mobs(n, MOBS) + (n % 5 == 0 ? 1 : 0), Oleadas.total(n, MOBS));
		}
		assertEquals(0, Oleadas.jefe(5).indice());
		assertEquals(1, Oleadas.jefe(10).indice());
		assertEquals(2, Oleadas.jefe(15).indice());
		assertEquals(3, Oleadas.jefe(20).indice());
		assertEquals(0, Oleadas.jefe(25).indice());
		assertFalse(Oleadas.conJefe(0));
	}

	@Test
	void experienciaAlQuincePorCiento() {
		// 15 % de 5 (un zombi) = 0,75: 1 con azar < 0,75, 0 si no
		assertEquals(1, Oleadas.experiencia(5, 15, 0.0));
		assertEquals(1, Oleadas.experiencia(5, 15, 0.74));
		assertEquals(0, Oleadas.experiencia(5, 15, 0.75));
		assertEquals(3, Oleadas.experiencia(20, 15, 0.5));
		assertEquals(0, Oleadas.experiencia(5, 0, 0.0));
		assertEquals(5, Oleadas.experiencia(5, 100, 0.99));
		assertEquals(0, Oleadas.experiencia(0, 15, 0.0));
		// de media, exactamente el porcentaje
		double suma = 0;
		int n = 10000;
		for (int i = 0; i < n; i++) {
			suma += Oleadas.experiencia(5, 15, (i + 0.5) / n);
		}
		assertEquals(0.75, suma / n, 1e-3);
	}

	@Test
	void recompensasYLogros() {
		assertEquals(0, Oleadas.recompensa(4));
		assertEquals(1, Oleadas.recompensa(5));
		assertEquals(2, Oleadas.recompensa(10));
		assertEquals(3, Oleadas.recompensa(15));
		assertEquals(4, Oleadas.recompensa(20));
		assertEquals(4, Oleadas.recompensa(35));
		assertEquals(0, Oleadas.recompensa(21));
		assertTrue(Oleadas.logro(5) && Oleadas.logro(10) && Oleadas.logro(20));
		assertFalse(Oleadas.logro(15) || Oleadas.logro(1) || Oleadas.logro(25));
	}
}
