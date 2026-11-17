package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Los modos de la partida (T41): pausa de cada modo, fin del contrarreloj, tiempo de partida y lo que puntúa. */
class PartidaModosTest {
	private static final UUID A = UUID.randomUUID(), B = UUID.randomUUID();

	/** Ticks hasta que empieza la oleada siguiente. */
	private static int hastaOleada(Partida p) {
		for (int i = 1; i < 10000; i++) {
			if (p.tick() == Partida.Paso.EMPIEZA_OLEADA) {
				return i;
			}
		}
		throw new AssertionError("no empieza la oleada");
	}

	/** Saca y mata a todos los enemigos de la oleada (sin pasar ticks); true si se superó. */
	private static boolean limpiar(Partida p) {
		boolean superada = false;
		while (p.estado() == Partida.Estado.OLEADA) {
			p.aparecer(20);
			int vivos = p.vivos();
			for (int i = 0; i < vivos; i++) {
				superada |= p.muere();
			}
		}
		return superada;
	}

	private static Partida empezada(Modo m, int oleadas) {
		Partida p = new Partida(50);
		assertTrue(p.empezar(m, oleadas));
		assertTrue(p.participantes(List.of(A, B)));
		assertEquals(Partida.CUENTA_TICKS, hastaOleada(p));
		return p;
	}

	@Test
	void cooperativoComoSiempre() {
		Partida p = new Partida(50);
		assertTrue(p.empezar());
		assertEquals(Modo.COOPERATIVO, p.modo());
		assertEquals(0, p.objetivo());
		p.participantes(List.of(A));
		hastaOleada(p);
		assertTrue(limpiar(p));
		assertEquals(Partida.Estado.PAUSA, p.estado());
		assertEquals(Partida.PAUSA_TICKS / 20, p.segundos());
		assertEquals(Partida.PAUSA_TICKS, hastaOleada(p));
		assertFalse(p.completada(), "el cooperativo no se acaba por oleadas");
	}

	@Test
	void contrarrelojAcabaTrasLaUltima() {
		Partida p = empezada(Modo.CONTRARRELOJ, 3);
		assertEquals(3, p.objetivo());
		for (int n = 1; n <= 3; n++) {
			assertEquals(n, p.oleada());
			for (int i = 0; i < 40; i++) {
				p.tick();                         // 2 s de lucha por oleada
			}
			assertTrue(limpiar(p));
			assertEquals(n == 3, p.completada(), "oleada " + n);
			if (n < 3) {
				assertEquals(Modo.CONTRARRELOJ.pausa(), hastaOleada(p), "pausa corta");
			}
		}
		assertEquals(3, p.superadas());
		// 3 oleadas de 40 ticks y 2 pausas de 100: lo que puntúa (los ticks al superar la última)
		assertEquals(3 * 40 + 2 * Modo.CONTRARRELOJ.pausa(), p.ticksSuperada());
		p.terminar();
		assertEquals(Modo.COOPERATIVO, p.modo(), "al terminar vuelve al de siempre");
		assertEquals(0, p.ticks());
	}

	@Test
	void contrarrelojDeAlMenosUnaOleada() {
		Partida p = new Partida(50);
		p.empezar(Modo.CONTRARRELOJ, 0);
		assertEquals(1, p.objetivo());
	}

	@Test
	void supervivenciaSinPausa() {
		Partida p = empezada(Modo.SUPERVIVENCIA, 10);
		assertEquals(0, p.objetivo(), "el número de oleadas solo es del contrarreloj");
		assertTrue(limpiar(p));
		assertEquals(Partida.Estado.PAUSA, p.estado());
		assertEquals(1, hastaOleada(p), "la siguiente oleada empieza en el tick siguiente");
		assertEquals(2, p.oleada());
		assertTrue(limpiar(p));
		assertEquals(1, hastaOleada(p));
		assertFalse(p.completada());
		assertEquals(2, p.superadas());
	}

	@Test
	void laCuentaAtrasNoCuentaParaElTiempo() {
		Partida p = new Partida(50);
		p.empezar(Modo.CONTRARRELOJ, 5);
		p.participantes(List.of(A));
		hastaOleada(p);
		assertEquals(0, p.ticks(), "la cuenta atrás no cuenta");
		for (int i = 0; i < 30; i++) {
			p.tick();
		}
		assertEquals(30, p.ticks());
		assertEquals(0, p.ticksSuperada(), "aún no ha superado ninguna");
		limpiar(p);
		assertEquals(30, p.ticksSuperada());
		hastaOleada(p);
		assertEquals(30 + Modo.CONTRARRELOJ.pausa(), p.ticks(), "la pausa sí cuenta (va contra el reloj)");
	}

	@Test
	void dosPartidasNoSeMezclan() {
		Partida p = empezada(Modo.CONTRARRELOJ, 2);
		assertFalse(p.empezar(Modo.SUPERVIVENCIA, 0), "con una partida en marcha no empieza otra");
		assertEquals(Modo.CONTRARRELOJ, p.modo());
		p.terminar();
		assertTrue(p.empezar(Modo.SUPERVIVENCIA, 0));
		assertEquals(Modo.SUPERVIVENCIA, p.modo());
		assertEquals(0, p.ticksSuperada());
	}
}
