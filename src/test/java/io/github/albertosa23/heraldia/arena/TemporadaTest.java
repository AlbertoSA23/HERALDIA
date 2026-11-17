package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonElement;
import com.mojang.serialization.JsonOps;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/**
 * La clasificación semanal de la arena: orden y desempates de cada modo, una marca por jugador, récords, cierre de la
 * semana (también con el servidor apagado en el reinicio), histórico acotado, campeones, reinicio forzado, migración del
 * marcador vanilla y lo que se guarda.
 */
class TemporadaTest {
	private static final UUID A = UUID.nameUUIDFromBytes("a".getBytes()), B = UUID.nameUUIDFromBytes("b".getBytes()),
			C = UUID.nameUUIDFromBytes("c".getBytes());
	private static final LocalDate L16 = LocalDate.of(2026, 11, 16), L23 = LocalDate.of(2026, 11, 23), L30 = LocalDate.of(2026, 11, 30),
			L7 = LocalDate.of(2026, 12, 7);
	private static final DayOfWeek LUNES = DayOfWeek.MONDAY;

	private static Temporada.Entrada e(UUID u, String n, int oleadas, long ticks, long fecha) {
		return new Temporada.Entrada(u, n, oleadas, ticks, fecha, 0);
	}

	private static Temporada.Entrada ta(UUID u, String n, int oleadas, long ticks, long fecha, int objetivo) {
		return new Temporada.Entrada(u, n, oleadas, ticks, fecha, objetivo);
	}

	private static Temporada empezada(LocalDate ini) {
		return Temporada.VACIA.avanzar(ini, LUNES, 8).temporada();
	}

	@Test
	void ordenYDesempates() {
		// más oleadas gana; con las mismas, menos tiempo; con el mismo, antes; y luego por nombre
		Temporada.Entrada a10 = e(A, "Ana", 10, 5000, 3), b12 = e(B, "Bea", 12, 9000, 2), c10 = e(C, "Cid", 10, 4000, 9);
		Temporada t = empezada(L16).registrar(Modo.COOPERATIVO, a10).registrar(Modo.COOPERATIVO, b12).registrar(Modo.COOPERATIVO, c10);
		assertEquals(List.of(b12, c10, a10), t.clasificacion(Modo.COOPERATIVO));
		Temporada.Entrada x = e(A, "Ana", 7, 100, 5), y = e(B, "Bea", 7, 100, 4);
		assertTrue(Temporada.mejor(y, x), "a igual marca, el que la hizo antes");
		assertTrue(Temporada.mejor(e(A, "Ana", 7, 100, 4), e(B, "Bea", 7, 100, 4)), "y por nombre");
		assertTrue(Temporada.mejor(x, null));
		// tiempo desconocido (migrado): detrás de cualquiera con tiempo y las mismas oleadas
		assertTrue(Temporada.mejor(e(A, "Ana", 7, 99999, 9), e(Temporada.SIN_JUGADOR, "Viejo", 7, -1, 0)));
		assertTrue(Temporada.mejor(e(Temporada.SIN_JUGADOR, "Viejo", 8, -1, 0), e(A, "Ana", 7, 1, 9)));
	}

	@Test
	void contrarrelojPuntuaElTiempo() {
		// acabado (10 de 10): decide el tiempo; a medias va detrás de cualquiera acabado
		Temporada.Entrada rapido = ta(A, "Ana", 10, 12000, 5, 10), lento = ta(B, "Bea", 10, 15000, 1, 10),
				medias = ta(C, "Cid", 7, 3000, 1, 10);
		Temporada t = empezada(L16);
		for (Temporada.Entrada x : List.of(medias, lento, rapido)) {
			t = t.registrar(Modo.CONTRARRELOJ, x);
		}
		assertEquals(List.of(rapido, lento, medias), t.clasificacion(Modo.CONTRARRELOJ));
		assertTrue(rapido.completa() && !medias.completa());
		assertFalse(e(A, "Ana", 10, 1, 1).completa(), "fuera del contrarreloj no hay «completa»");
		assertEquals(rapido, t.record(Modo.CONTRARRELOJ).orElseThrow());
		// los modos no se mezclan
		assertTrue(t.clasificacion(Modo.SUPERVIVENCIA).isEmpty());
		assertTrue(t.record(Modo.COOPERATIVO).isEmpty());
	}

	@Test
	void supervivenciaPuntuaLaOleada() {
		Temporada t = empezada(L16).registrar(Modo.SUPERVIVENCIA, e(A, "Ana", 14, 90000, 1))
				.registrar(Modo.SUPERVIVENCIA, e(B, "Bea", 16, 120000, 2));
		assertEquals("Bea", t.clasificacion(Modo.SUPERVIVENCIA).get(0).nombre());
	}

	@Test
	void unaMarcaPorJugadorLaMejor() {
		Temporada t = empezada(L16).registrar(Modo.COOPERATIVO, e(A, "Ana", 5, 100, 1))
				.registrar(Modo.COOPERATIVO, e(A, "Ana", 8, 900, 2))
				.registrar(Modo.COOPERATIVO, e(A, "Ana", 6, 50, 3));
		assertEquals(List.of(e(A, "Ana", 8, 900, 2)), t.clasificacion(Modo.COOPERATIVO));
		// con otro nombre (lo cambió) sigue siendo el mismo jugador
		t = t.registrar(Modo.COOPERATIVO, e(A, "Ana2", 9, 1, 4));
		assertEquals(1, t.clasificacion(Modo.COOPERATIVO).size());
		assertEquals("Ana2", t.clasificacion(Modo.COOPERATIVO).get(0).nombre());
	}

	@Test
	void comoMuchoDiezPorModo() {
		Temporada t = empezada(L16);
		for (int i = 0; i < 25; i++) {
			t = t.registrar(Modo.COOPERATIVO, e(UUID.randomUUID(), "J" + i, i + 1, 10, i));
		}
		List<Temporada.Entrada> l = t.clasificacion(Modo.COOPERATIVO);
		assertEquals(Temporada.MAX_POR_MODO, l.size());
		assertEquals(25, l.get(0).oleadas());
		assertEquals(16, l.get(9).oleadas());
		assertEquals(25, t.record(Modo.COOPERATIVO).orElseThrow().oleadas());
	}

	@Test
	void elRecordSoloMejora() {
		Temporada t = empezada(L16).registrar(Modo.COOPERATIVO, e(A, "Ana", 12, 100, 1));
		t = t.avanzar(L23, LUNES, 8).temporada().registrar(Modo.COOPERATIVO, e(B, "Bea", 9, 50, 2));
		assertEquals("Ana", t.record(Modo.COOPERATIVO).orElseThrow().nombre(), "el récord no se reinicia con la semana");
		assertEquals("Bea", t.clasificacion(Modo.COOPERATIVO).get(0).nombre());
	}

	@Test
	void laPrimeraSemanaSoloSeApunta() {
		Temporada.Cierre c = Temporada.VACIA.avanzar(L16, LUNES, 8);
		assertNull(c.cerrada());
		assertEquals(L16.toEpochDay(), c.temporada().semana());
		assertTrue(c.temporada().historico().isEmpty());
		// la misma semana otra vez: nada
		Temporada.Cierre d = c.temporada().avanzar(L16, LUNES, 8);
		assertNull(d.cerrada());
		assertSame(c.temporada(), d.temporada());
	}

	@Test
	void cierreDeLaSemanaYCampeones() {
		Temporada t = empezada(L16).registrar(Modo.COOPERATIVO, e(A, "Ana", 9, 100, 1))
				.registrar(Modo.CONTRARRELOJ, ta(B, "Bea", 10, 9000, 2, 10));
		Temporada.Cierre c = t.avanzar(L23, LUNES, 8);
		assertNotNull(c.cerrada());
		assertEquals(L16.toEpochDay(), c.cerrada().inicio());
		assertEquals(L23.toEpochDay(), c.cerrada().cierre());
		Temporada n = c.temporada();
		assertEquals(L23.toEpochDay(), n.semana());
		assertTrue(n.actual().isEmpty(), "la semana nueva empieza vacía");
		assertEquals(1, n.historico().size());
		Map<Modo, Temporada.Entrada> camp = n.campeones(L23);
		assertEquals(Set.of(Modo.COOPERATIVO, Modo.CONTRARRELOJ), camp.keySet());
		assertEquals("Ana", camp.get(Modo.COOPERATIVO).nombre());
		assertEquals("Bea", camp.get(Modo.CONTRARRELOJ).nombre());
		assertEquals(Set.of(Modo.CONTRARRELOJ), n.ganadas(B));
		assertTrue(n.ganadas(C).isEmpty());
		// una semana después ya no son «los de la semana anterior»
		assertTrue(n.campeones(L30).isEmpty());
	}

	@Test
	void servidorApagadoDuranteElReinicio() {
		// se apagó el domingo 22 y arranca el martes 24: la semana del 16 se cierra al arrancar y sus campeones valen
		Temporada t = empezada(L16).registrar(Modo.SUPERVIVENCIA, e(A, "Ana", 11, 100, 1));
		Temporada.Cierre c = t.avanzar(L23, LUNES, 8);
		assertEquals(L23.toEpochDay(), c.cerrada().cierre());
		assertEquals("Ana", c.temporada().campeones(L23).get(Modo.SUPERVIVENCIA).nombre());
	}

	@Test
	void servidorApagadoMasDeUnaSemana() {
		// se apagó el 20 y arranca el 2-12 (semana del 30-11): la del 16 se cierra (al 23, no al 30); la semana anterior
		// (la del 23) nadie jugó: sin campeones, pero los de la del 16 conservan su logro
		Temporada t = empezada(L16).registrar(Modo.COOPERATIVO, e(A, "Ana", 9, 100, 1));
		Temporada.Cierre c = t.avanzar(L30, LUNES, 8);
		assertEquals(L16.toEpochDay(), c.cerrada().inicio());
		assertEquals(L23.toEpochDay(), c.cerrada().cierre());
		assertEquals(L30.toEpochDay(), c.temporada().semana());
		assertTrue(c.temporada().campeones(L30).isEmpty());
		assertEquals(Set.of(Modo.COOPERATIVO), c.temporada().ganadas(A));
		assertEquals(1, c.temporada().historico().size(), "las semanas sin datos no se guardan");
	}

	@Test
	void cambioDelDiaDeReinicio() {
		// la guardada empezó el lunes 16; el día pasa a ser el miércoles: el jueves 19 (semana del miércoles 18) cierra
		Temporada t = empezada(L16).registrar(Modo.COOPERATIVO, e(A, "Ana", 3, 1, 1));
		Temporada.Cierre c = t.avanzar(LocalDate.of(2026, 11, 18), DayOfWeek.WEDNESDAY, 8);
		assertEquals(LocalDate.of(2026, 11, 18).toEpochDay(), c.cerrada().cierre());
		assertEquals("Ana", c.temporada().campeones(LocalDate.of(2026, 11, 18)).get(Modo.COOPERATIVO).nombre());
		// un inicio anterior al guardado (p. ej. de miércoles a lunes a mitad de semana) no cierra nada
		Temporada u = Temporada.VACIA.avanzar(LocalDate.of(2026, 11, 18), DayOfWeek.WEDNESDAY, 8).temporada();
		assertNull(u.avanzar(L16, LUNES, 8).cerrada());
	}

	@Test
	void historicoAcotado() {
		Temporada t = empezada(L16);
		LocalDate d = L16;
		for (int i = 0; i < 12; i++) {
			t = t.registrar(Modo.COOPERATIVO, e(A, "Ana", i + 1, 1, i));
			d = d.plusWeeks(1);
			t = t.avanzar(d, LUNES, 5).temporada();
		}
		assertEquals(5, t.historico().size());
		assertEquals(12, t.historico().get(0).campeon(Modo.COOPERATIVO).orElseThrow().oleadas(), "la más reciente primero");
		assertEquals(8, t.historico().get(4).campeon(Modo.COOPERATIVO).orElseThrow().oleadas());
		assertEquals(12, t.cerrada(1).orElseThrow().campeon(Modo.COOPERATIVO).orElseThrow().oleadas());
		assertTrue(t.cerrada(6).isEmpty());
		assertTrue(t.cerrada(0).isEmpty());
		// bajar la opción recorta ya; subirla no inventa semanas
		assertEquals(2, t.recortar(2).historico().size());
		assertEquals(5, t.recortar(40).historico().size());
		assertEquals(1, t.recortar(0).historico().size(), "al menos una");
		assertEquals(12, t.record(Modo.COOPERATIVO).orElseThrow().oleadas());
	}

	@Test
	void reinicioForzado() {
		// a mitad de la semana del 16 (miércoles 18): se cierra ya, con cierre = hoy, y sus campeones valen en seguida
		Temporada t = empezada(L16).registrar(Modo.CONTRARRELOJ, ta(A, "Ana", 10, 8000, 1, 10));
		LocalDate hoy = LocalDate.of(2026, 11, 18);
		Temporada.Cierre c = t.forzar(hoy, L16, 8);
		assertEquals(hoy.toEpochDay(), c.cerrada().cierre());
		Temporada n = c.temporada();
		assertEquals(L16.toEpochDay(), n.semana(), "la semana de calendario no cambia");
		assertTrue(n.actual().isEmpty());
		assertEquals("Ana", n.campeones(L16).get(Modo.CONTRARRELOJ).nombre());
		// y el lunes 23 se cierra otra vez (la parte que quedaba de semana), con sus propios campeones
		n = n.registrar(Modo.CONTRARRELOJ, ta(B, "Bea", 10, 9000, 2, 10));
		Temporada.Cierre d = n.avanzar(L23, LUNES, 8);
		assertEquals(2, d.temporada().historico().size());
		assertEquals("Bea", d.temporada().campeones(L23).get(Modo.CONTRARRELOJ).nombre());
		// sin semana empezada, el forzado parte de la de calendario
		Temporada.Cierre v = Temporada.VACIA.forzar(hoy, L16, 8);
		assertEquals(L16.toEpochDay(), v.cerrada().inicio());
		assertTrue(v.temporada().campeones(L16).isEmpty());
		assertEquals(L16.toEpochDay(), v.temporada().semana());
	}

	@Test
	void migracionDelMarcador() {
		Map<String, Integer> marcador = Map.of("-servidor-", 14, "Ana", 9, "Bea", 14, "Cid", 14, "Nadie", 0);
		Temporada t = Temporada.VACIA.migrar(marcador, "-servidor-", 77);
		assertTrue(t.migrada());
		Temporada.Entrada r = t.record(Modo.COOPERATIVO).orElseThrow();
		assertEquals("Bea", r.nombre(), "empate: por nombre (sin tiempo ni fecha que desempaten)");
		assertEquals(14, r.oleadas());
		assertEquals(-1, r.ticks());
		assertEquals(Temporada.SIN_JUGADOR, r.jugador());
		assertTrue(t.actual().isEmpty() && t.historico().isEmpty(), "solo el récord: la semana empieza limpia");
		// una sola vez
		assertSame(t, t.migrar(Map.of("Zoe", 99), "-servidor-", 1));
		// un récord mejor que el del marcador no se pisa
		Temporada mejor = Temporada.VACIA.registrar(Modo.COOPERATIVO, e(A, "Ana", 20, 5, 1)).migrar(marcador, "-servidor-", 1);
		assertEquals(20, mejor.record(Modo.COOPERATIVO).orElseThrow().oleadas());
		// sin marcador (mundo sin arena o desde cero)
		Temporada vacia = Temporada.VACIA.migrar(Map.of(), "-servidor-", 1);
		assertTrue(vacia.migrada() && vacia.records().isEmpty());
		Temporada solo = Temporada.VACIA.migrar(Map.of("-servidor-", 4), "-servidor-", 1);
		assertTrue(solo.records().isEmpty(), "solo el del servidor: no se sabe de quién era");
	}

	@Test
	void lasMigradasSeDistinguenPorNombre() {
		Temporada.Entrada v1 = e(Temporada.SIN_JUGADOR, "Viejo", 5, -1, 0), v2 = e(Temporada.SIN_JUGADOR, "Otro", 4, -1, 0);
		List<Temporada.Entrada> l = Temporada.con(Temporada.con(List.of(), v1), v2);
		assertEquals(2, l.size());
	}

	@Test
	void seGuardaYSeLeeIgual() {
		Temporada t = empezada(L16).registrar(Modo.COOPERATIVO, e(A, "Ana", 9, 100, 1))
				.registrar(Modo.CONTRARRELOJ, ta(B, "Bea", 10, 9000, 2, 10));
		t = t.avanzar(L23, LUNES, 8).temporada().registrar(Modo.SUPERVIVENCIA, e(C, "Cid", 3, 30, 3))
				.migrar(Map.of("Viejo", 4), "-servidor-", 9);
		JsonElement j = Temporada.CODEC.encodeStart(JsonOps.INSTANCE, t).getOrThrow();
		Temporada u = Temporada.CODEC.parse(JsonOps.INSTANCE, j).getOrThrow();
		assertEquals(t, u);
		// un estado vacío (o de una versión sin estos datos) se lee como VACIA
		assertEquals(Temporada.VACIA, Temporada.CODEC.parse(JsonOps.INSTANCE, new com.google.gson.JsonObject()).getOrThrow());
	}
}
