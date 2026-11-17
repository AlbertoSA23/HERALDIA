package io.github.albertosa23.heraldia.tesoro;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** La elección de la cadena: determinista, con tipos válidos, dentro del radio, sin repetir y prefiriendo lo generado. */
class PlanificadorTest {
	static final Planificador.Biomas BIOMAS = (x, z) -> x < 0 ? "minecraft:desert" : "minecraft:plains";

	/** Un mundo de mentira: medianas y minas repartidas al azar (con su semilla) en ±5000 bloques. */
	record Mundo(List<Planificador.Candidata> todas) implements Planificador.Buscador {
		static Mundo azar(long seed, int n) {
			Random r = new Random(seed);
			List<Planificador.Candidata> l = new ArrayList<>();
			for (int i = 0; i < n; i++) {
				Destino.Tipo t = r.nextBoolean() ? Destino.Tipo.MEDIANA : Destino.Tipo.MINA;
				l.add(new Planificador.Candidata(t, "heraldia:" + t.id() + "/" + i, r.nextInt(10000) - 5000, r.nextInt(10000) - 5000,
						r.nextInt(3) > 0));
			}
			return new Mundo(l);
		}

		@Override
		public List<Planificador.Candidata> buscar(Destino.Tipo tipo, int x, int z, int radio) {
			List<Planificador.Candidata> out = new ArrayList<>();
			for (Planificador.Candidata c : todas) {   // devuelve de más (otro tipo, fuera del radio): el planificador filtra
				if (Planificador.dist(c.x() - x, c.z() - z) <= 4L * radio * radio) {
					out.add(c);
				}
			}
			return out;
		}
	}

	@Test
	void mismaSemillaMismaCadena() {
		Mundo m = Mundo.azar(7, 400);
		for (long s = 0; s < 50; s++) {
			assertEquals(Planificador.planificar(s, 100, 200, 1500, m, BIOMAS), Planificador.planificar(s, 100, 200, 1500, m, BIOMAS));
		}
	}

	@Test
	void elOrdenDeLasCandidatasNoImporta() {
		Mundo m = Mundo.azar(11, 300);
		List<Planificador.Candidata> al = new ArrayList<>(m.todas());
		java.util.Collections.reverse(al);
		Mundo inverso = new Mundo(al);
		for (long s = 0; s < 30; s++) {
			assertEquals(Planificador.planificar(s, 0, 0, 1500, m, BIOMAS), Planificador.planificar(s, 0, 0, 1500, inverso, BIOMAS));
		}
	}

	@Test
	void semillasDistintasDanCadenasDistintas() {
		Mundo m = Mundo.azar(3, 600);
		Set<List<Destino>> distintas = new HashSet<>();
		for (long s = 0; s < 40; s++) {
			Planificador.planificar(s, 0, 0, 1500, m, BIOMAS).ifPresent(distintas::add);
		}
		assertTrue(distintas.size() > 20, "casi todas distintas: " + distintas.size());
	}

	@Test
	void tiposRadioYSinRepetir() {
		for (long mundo = 0; mundo < 20; mundo++) {
			Mundo m = Mundo.azar(mundo, 500);
			for (long s = 0; s < 20; s++) {
				int radio = 600 + (int) (s * 50);
				Optional<List<Destino>> o = Planificador.planificar(s, 0, 0, radio, m, BIOMAS);
				if (o.isEmpty()) {
					continue;
				}
				List<Destino> d = o.get();
				assertTrue(d.size() == 2 || d.size() == 3, d.toString());
				assertEquals(Destino.Tipo.TESORO, d.getLast().tipo());
				assertTrue(d.subList(0, d.size() - 1).stream().allMatch(x -> x.tipo() != Destino.Tipo.TESORO));
				int px = 0, pz = 0;
				for (int i = 0; i < d.size() - 1; i++) {
					Destino x = d.get(i);
					long dist = x.distanciaSq(px, pz);
					assertTrue(dist <= (long) radio * radio && dist >= (long) Planificador.DISTANCIA_MIN * Planificador.DISTANCIA_MIN,
							"marca " + i + " a " + Math.sqrt(dist) + " de la anterior (radio " + radio + ")");
					assertTrue(m.todas().stream().anyMatch(c -> c.x() == x.x() && c.z() == x.z() && c.tipo() == x.tipo()
							&& c.estructura().equals(x.estructura())), "estructura real: " + x);
					px = x.x();
					pz = x.z();
				}
				for (int i = 0; i < d.size(); i++) {
					for (int j = i + 1; j < d.size() - 1; j++) {
						assertTrue(d.get(i).distanciaSq(d.get(j).x(), d.get(j).z()) >= (long) Planificador.DISTANCIA_MIN * Planificador.DISTANCIA_MIN);
					}
				}
				long t = d.getLast().distanciaSq(px, pz);
				assertTrue(t >= (long) (Planificador.TESORO_MIN - 1) * (Planificador.TESORO_MIN - 1)
						&& t <= (long) (Planificador.TESORO_MAX + 1) * (Planificador.TESORO_MAX + 1), "tesoro a " + Math.sqrt(t));
			}
		}
	}

	@Test
	void medianaLuegoMinaLuegoTesoro() {
		Mundo m = new Mundo(List.of(
				new Planificador.Candidata(Destino.Tipo.MEDIANA, "heraldia:medianas/posada/a", 500, 0, true),
				new Planificador.Candidata(Destino.Tipo.MINA, "heraldia:minas/pequena/a/a", 900, 0, true)));
		List<Destino> d = Planificador.planificar(1, 0, 0, 1500, m, BIOMAS).orElseThrow();
		assertEquals(List.of(Destino.Tipo.MEDIANA, Destino.Tipo.MINA, Destino.Tipo.TESORO), d.stream().map(Destino::tipo).toList());
		assertEquals("minecraft:plains", d.getFirst().bioma());
	}

	@Test
	void sinMinaOtraMedianaYSinMedianaUnaMina() {
		Mundo soloMedianas = new Mundo(List.of(
				new Planificador.Candidata(Destino.Tipo.MEDIANA, "heraldia:medianas/posada/a", 500, 0, true),
				new Planificador.Candidata(Destino.Tipo.MEDIANA, "heraldia:medianas/ermita/a", 900, 0, false)));
		assertEquals(List.of(Destino.Tipo.MEDIANA, Destino.Tipo.MEDIANA, Destino.Tipo.TESORO),
				Planificador.planificar(1, 0, 0, 1500, soloMedianas, BIOMAS).orElseThrow().stream().map(Destino::tipo).toList());
		Mundo soloUnaMina = new Mundo(List.of(new Planificador.Candidata(Destino.Tipo.MINA, "heraldia:minas/grande/a/a", -400, 0, true)));
		List<Destino> d = Planificador.planificar(1, 0, 0, 1500, soloUnaMina, BIOMAS).orElseThrow();
		assertEquals(List.of(Destino.Tipo.MINA, Destino.Tipo.TESORO), d.stream().map(Destino::tipo).toList());
		assertEquals("minecraft:desert", d.getFirst().bioma());
	}

	@Test
	void sinEstructurasNoHayCadena() {
		assertTrue(Planificador.planificar(1, 0, 0, 1500, new Mundo(List.of()), BIOMAS).isEmpty());
		Mundo lejos = new Mundo(List.of(new Planificador.Candidata(Destino.Tipo.MEDIANA, "heraldia:medianas/a", 3000, 0, true)));
		assertTrue(Planificador.planificar(1, 0, 0, 1500, lejos, BIOMAS).isEmpty(), "fuera del radio");
		Mundo cerca = new Mundo(List.of(new Planificador.Candidata(Destino.Tipo.MEDIANA, "heraldia:medianas/a", 50, 0, true)));
		assertTrue(Planificador.planificar(1, 0, 0, 1500, cerca, BIOMAS).isEmpty(), "demasiado cerca del origen");
	}

	@Test
	void prefiereLasGeneradas() {
		List<Planificador.Candidata> l = new ArrayList<>();
		for (int i = 0; i < 6; i++) {   // previstas más cerca, generadas más lejos
			l.add(new Planificador.Candidata(Destino.Tipo.MEDIANA, "heraldia:medianas/prevista" + i, 150 + i * 20, 0, false));
		}
		for (int i = 0; i < 3; i++) {
			l.add(new Planificador.Candidata(Destino.Tipo.MEDIANA, "heraldia:medianas/generada" + i, -800 - i * 20, 0, true));
		}
		Mundo m = new Mundo(l);
		for (long s = 0; s < 30; s++) {
			assertTrue(Planificador.planificar(s, 0, 0, 1500, m, BIOMAS).orElseThrow().getFirst().generada());
		}
	}

	@Test
	void sorteaEntreLasMasCercanas() {
		List<Planificador.Candidata> l = new ArrayList<>();
		for (int i = 0; i < 10; i++) {
			l.add(new Planificador.Candidata(Destino.Tipo.MEDIANA, "heraldia:medianas/" + i, 200 + i * 100, 0, true));
		}
		Mundo m = new Mundo(l);
		Set<Integer> primeras = new HashSet<>();
		for (long s = 0; s < 60; s++) {
			primeras.add(Planificador.planificar(s, 0, 0, 1500, m, BIOMAS).orElseThrow().getFirst().x());
		}
		assertEquals(Set.of(200, 300, 400), primeras, "solo las " + Planificador.ELEGIBLES + " más cercanas, y todas salen");
	}

	@Test
	void semillaPorMundoJugadorYNumero() {
		UUID a = UUID.fromString("00000000-0000-0000-0000-000000000001"), b = UUID.fromString("00000000-0000-0000-0000-000000000002");
		assertEquals(Planificador.semilla(5, a, 0), Planificador.semilla(5, a, 0));
		assertNotEquals(Planificador.semilla(5, a, 0), Planificador.semilla(5, a, 1));
		assertNotEquals(Planificador.semilla(5, a, 0), Planificador.semilla(5, b, 0));
		assertNotEquals(Planificador.semilla(5, a, 0), Planificador.semilla(6, a, 0));
		Set<Long> s = new HashSet<>();
		for (int n = 0; n < 1000; n++) {
			s.add(Planificador.semilla(42, a, n));
		}
		assertEquals(1000, s.size());
	}

	@Test
	void moverElTesoroEsDeterministaYCerca() {
		Cadena c = CadenaTest.cadena().avanzar().avanzar();
		Destino t1 = Planificador.moverTesoro(c, BIOMAS);
		assertEquals(t1, Planificador.moverTesoro(c, BIOMAS));
		long d = t1.distanciaSq(CadenaTest.TESORO.x(), CadenaTest.TESORO.z());
		assertTrue(d >= 31 * 31 && d <= 65 * 65, "a " + Math.sqrt(d));
		Cadena movida = c.conTesoro(t1);
		assertNotEquals(t1, Planificador.moverTesoro(movida, BIOMAS), "el segundo intento va a otro sitio");
		assertFalse(movida.completada());
	}
}
