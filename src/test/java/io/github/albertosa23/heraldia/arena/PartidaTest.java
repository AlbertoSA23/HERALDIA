package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** La partida: cuenta atrás, oleadas por tandas, pausa, mini-jefe, fin y reinicio. */
class PartidaTest {
	private static final UUID A = UUID.randomUUID(), B = UUID.randomUUID();

	/** Avanza ticks hasta que empiece la oleada siguiente; devuelve cuántos segundos se anunciaron. */
	private static int hastaOleada(Partida p) {
		int segundos = 0;
		for (int i = 0; i < 10000; i++) {
			Partida.Paso paso = p.tick();
			if (paso == Partida.Paso.EMPIEZA_OLEADA) {
				return segundos;
			}
			if (paso == Partida.Paso.SEGUNDO) {
				segundos++;
			}
		}
		throw new AssertionError("no empieza la oleada");
	}

	/** Mata a todos los enemigos de la oleada saliendo en tandas de como mucho `max`; devuelve las tandas. */
	private static int limpiar(Partida p, int max) {
		int tandas = 0;
		while (p.estado() == Partida.Estado.OLEADA) {
			int n = p.aparecer(max);
			assertTrue(p.vivos() <= max, "más vivos que el límite");
			if (n > 0) {
				tandas++;
			}
			int vivos = p.vivos();
			for (int i = 0; i < vivos; i++) {
				p.muere();
			}
		}
		return tandas;
	}

	@Test
	void cuentaAtrasYPrimeraOleada() {
		Partida p = new Partida(50);
		assertEquals(Partida.Estado.LIBRE, p.estado());
		assertTrue(p.empezar());
		assertFalse(p.empezar(), "dos campanas no empiezan dos partidas");
		assertEquals(Partida.Estado.CUENTA_ATRAS, p.estado());
		assertEquals(5, p.segundos());
		assertTrue(p.participantes(List.of(A, B)));
		assertEquals(4, hastaOleada(p));          // 4, 3, 2, 1 y luego empieza
		assertEquals(Partida.Estado.OLEADA, p.estado());
		assertEquals(1, p.oleada());
		assertEquals(4, p.total());
		assertEquals(4, p.restantes());
		assertEquals(0, p.superadas());
	}

	@Test
	void tandasConElLimite() {
		Partida p = new Partida(50);
		p.empezar();
		p.participantes(List.of(A));
		hastaOleada(p);
		for (int i = 1; i < 10; i++) {          // a la oleada 10: 22 enemigos y el mini-jefe
			limpiar(p, 100);
			hastaOleada(p);
		}
		assertEquals(10, p.oleada());
		assertEquals(23, p.total());
		assertEquals(5, p.aparecer(5));
		assertEquals(0, p.aparecer(5), "con 5 vivos y el límite en 5 no sale nadie más");
		p.muere();
		p.muere();
		assertEquals(2, p.aparecer(5));
		assertEquals(23 - 7, p.pendientes());
		assertTrue(limpiar(p, 5) >= 4, "16 que faltan y 5 vivos a la vez: al menos 4 tandas");
		assertEquals(Partida.Estado.PAUSA, p.estado());
	}

	@Test
	void oleadaSuperadaYPausa() {
		Partida p = new Partida(50);
		p.empezar();
		p.participantes(List.of(A));
		hastaOleada(p);
		assertEquals(4, p.aparecer(20));
		assertFalse(p.muere());
		assertFalse(p.muere());
		assertFalse(p.muere());
		assertTrue(p.muere(), "el último enemigo supera la oleada");
		assertEquals(Partida.Estado.PAUSA, p.estado());
		assertEquals(1, p.superadas());
		assertFalse(p.muere(), "en la pausa no hay enemigos");
		assertEquals(9, hastaOleada(p));          // 10 s de pausa: 9 avisos y empieza
		assertEquals(2, p.oleada());
		assertEquals(6, p.total());
	}

	@Test
	void miniJefeUnaVez() {
		Partida p = new Partida(50);
		p.empezar();
		p.participantes(List.of(A));
		for (int n = 1; n <= 5; n++) {
			hastaOleada(p);
			boolean jefe = p.tomarJefe();
			assertEquals(n == 5, jefe, "oleada " + n);
			assertFalse(p.tomarJefe(), "el mini-jefe sale una sola vez");
			if (n < 5) {
				limpiar(p, 20);
			}
		}
		assertEquals(Oleadas.mobs(5, 50) + 1, p.total());
	}

	@Test
	void falloYRefuerzos() {
		Partida p = new Partida(50);
		p.empezar();
		p.participantes(List.of(A));
		hastaOleada(p);
		p.aparecer(20);
		p.fallo();
		assertEquals(3, p.vivos());
		assertEquals(1, p.pendientes());
		p.extra();
		assertEquals(5, p.total());
		assertEquals(5, p.restantes());
	}

	@Test
	void finCuandoSalenTodosYReinicioLimpio() {
		Partida p = new Partida(50);
		p.empezar();
		p.participantes(List.of(A, B));
		hastaOleada(p);
		p.aparecer(20);
		assertFalse(p.sale(A), "queda B");
		assertTrue(p.participa(B));
		assertFalse(p.participa(A));
		assertTrue(p.sale(B), "sin participantes la partida acaba");
		p.terminar();
		assertEquals(Partida.Estado.LIBRE, p.estado());
		assertEquals(0, p.oleada());
		assertEquals(0, p.restantes());
		assertTrue(p.participantes().isEmpty());
		// otra partida empieza de cero
		assertTrue(p.empezar());
		p.participantes(List.of(A));
		hastaOleada(p);
		assertEquals(1, p.oleada());
		assertEquals(4, p.total());
	}

	@Test
	void sinParticipantes() {
		Partida p = new Partida(50);
		p.empezar();
		assertFalse(p.participantes(List.of()));
		assertFalse(p.sale(A), "en la cuenta atrás no se acaba por salir");
	}

	@Test
	void libreNoHaceNada() {
		Partida p = new Partida(50);
		assertEquals(Partida.Paso.NADA, p.tick());
		assertEquals(0, p.aparecer(20));
		assertFalse(p.muere());
	}
}
