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
class SeasonTest {
	private static final UUID A = UUID.nameUUIDFromBytes("a".getBytes()), B = UUID.nameUUIDFromBytes("b".getBytes()),
			C = UUID.nameUUIDFromBytes("c".getBytes());
	private static final LocalDate L16 = LocalDate.of(2026, 11, 16), L23 = LocalDate.of(2026, 11, 23), L30 = LocalDate.of(2026, 11, 30),
			L7 = LocalDate.of(2026, 12, 7);
	private static final DayOfWeek MONDAY = DayOfWeek.MONDAY;

	private static Season.Entry e(UUID u, String n, int waves, long ticks, long date) {
		return new Season.Entry(u, n, waves, ticks, date, 0);
	}

	private static Season.Entry ta(UUID u, String n, int waves, long ticks, long date, int target) {
		return new Season.Entry(u, n, waves, ticks, date, target);
	}

	private static Season started(LocalDate ini) {
		return Season.EMPTY.advance(ini, MONDAY, 8).season();
	}

	@Test
	void orderAndTiebreaks() {
		// más oleadas gana; con las mismas, menos tiempo; con el mismo, antes; y luego por nombre
		Season.Entry a10 = e(A, "Ana", 10, 5000, 3), b12 = e(B, "Bea", 12, 9000, 2), c10 = e(C, "Cid", 10, 4000, 9);
		Season t = started(L16).register(Mode.COOP, a10).register(Mode.COOP, b12).register(Mode.COOP, c10);
		assertEquals(List.of(b12, c10, a10), t.ranking(Mode.COOP));
		Season.Entry x = e(A, "Ana", 7, 100, 5), y = e(B, "Bea", 7, 100, 4);
		assertTrue(Season.best(y, x), "a igual marca, el que la hizo antes");
		assertTrue(Season.best(e(A, "Ana", 7, 100, 4), e(B, "Bea", 7, 100, 4)), "y por nombre");
		assertTrue(Season.best(x, null));
		// tiempo desconocido (migrado): detrás de cualquiera con tiempo y las mismas oleadas
		assertTrue(Season.best(e(A, "Ana", 7, 99999, 9), e(Season.NO_PLAYER, "Viejo", 7, -1, 0)));
		assertTrue(Season.best(e(Season.NO_PLAYER, "Viejo", 8, -1, 0), e(A, "Ana", 7, 1, 9)));
	}

	@Test
	void timeTrialScoresTime() {
		// acabado (10 de 10): decide el tiempo; a medias va detrás de cualquiera acabado
		Season.Entry fast = ta(A, "Ana", 10, 12000, 5, 10), slow = ta(B, "Bea", 10, 15000, 1, 10),
				halves = ta(C, "Cid", 7, 3000, 1, 10);
		Season t = started(L16);
		for (Season.Entry x : List.of(halves, slow, fast)) {
			t = t.register(Mode.TIME_TRIAL, x);
		}
		assertEquals(List.of(fast, slow, halves), t.ranking(Mode.TIME_TRIAL));
		assertTrue(fast.complete() && !halves.complete());
		assertFalse(e(A, "Ana", 10, 1, 1).complete(), "fuera del contrarreloj no hay «completa»");
		assertEquals(fast, t.record(Mode.TIME_TRIAL).orElseThrow());
		// los modos no se mezclan
		assertTrue(t.ranking(Mode.SURVIVAL).isEmpty());
		assertTrue(t.record(Mode.COOP).isEmpty());
	}

	@Test
	void survivalScoresWave() {
		Season t = started(L16).register(Mode.SURVIVAL, e(A, "Ana", 14, 90000, 1))
				.register(Mode.SURVIVAL, e(B, "Bea", 16, 120000, 2));
		assertEquals("Bea", t.ranking(Mode.SURVIVAL).get(0).name());
	}

	@Test
	void oneMarkPerPlayerTheBest() {
		Season t = started(L16).register(Mode.COOP, e(A, "Ana", 5, 100, 1))
				.register(Mode.COOP, e(A, "Ana", 8, 900, 2))
				.register(Mode.COOP, e(A, "Ana", 6, 50, 3));
		assertEquals(List.of(e(A, "Ana", 8, 900, 2)), t.ranking(Mode.COOP));
		// con otro nombre (lo cambió) sigue siendo el mismo jugador
		t = t.register(Mode.COOP, e(A, "Ana2", 9, 1, 4));
		assertEquals(1, t.ranking(Mode.COOP).size());
		assertEquals("Ana2", t.ranking(Mode.COOP).get(0).name());
	}

	@Test
	void atMostTenPerMode() {
		Season t = started(L16);
		for (int i = 0; i < 25; i++) {
			t = t.register(Mode.COOP, e(UUID.randomUUID(), "J" + i, i + 1, 10, i));
		}
		List<Season.Entry> l = t.ranking(Mode.COOP);
		assertEquals(Season.MAX_PER_MODE, l.size());
		assertEquals(25, l.get(0).waves());
		assertEquals(16, l.get(9).waves());
		assertEquals(25, t.record(Mode.COOP).orElseThrow().waves());
	}

	@Test
	void recordOnlyImproves() {
		Season t = started(L16).register(Mode.COOP, e(A, "Ana", 12, 100, 1));
		t = t.advance(L23, MONDAY, 8).season().register(Mode.COOP, e(B, "Bea", 9, 50, 2));
		assertEquals("Ana", t.record(Mode.COOP).orElseThrow().name(), "el récord no se reinicia con la semana");
		assertEquals("Bea", t.ranking(Mode.COOP).get(0).name());
	}

	@Test
	void firstWeekIsOnlyRecorded() {
		Season.Closing c = Season.EMPTY.advance(L16, MONDAY, 8);
		assertNull(c.closed());
		assertEquals(L16.toEpochDay(), c.season().week());
		assertTrue(c.season().history().isEmpty());
		// la misma semana otra vez: nada
		Season.Closing d = c.season().advance(L16, MONDAY, 8);
		assertNull(d.closed());
		assertSame(c.season(), d.season());
	}

	@Test
	void weekCloseAndChampions() {
		Season t = started(L16).register(Mode.COOP, e(A, "Ana", 9, 100, 1))
				.register(Mode.TIME_TRIAL, ta(B, "Bea", 10, 9000, 2, 10));
		Season.Closing c = t.advance(L23, MONDAY, 8);
		assertNotNull(c.closed());
		assertEquals(L16.toEpochDay(), c.closed().start());
		assertEquals(L23.toEpochDay(), c.closed().closing());
		Season n = c.season();
		assertEquals(L23.toEpochDay(), n.week());
		assertTrue(n.actual().isEmpty(), "la semana nueva empieza vacía");
		assertEquals(1, n.history().size());
		Map<Mode, Season.Entry> camp = n.champions(L23);
		assertEquals(Set.of(Mode.COOP, Mode.TIME_TRIAL), camp.keySet());
		assertEquals("Ana", camp.get(Mode.COOP).name());
		assertEquals("Bea", camp.get(Mode.TIME_TRIAL).name());
		assertEquals(Set.of(Mode.TIME_TRIAL), n.won(B));
		assertTrue(n.won(C).isEmpty());
		// una semana después ya no son «los de la semana anterior»
		assertTrue(n.champions(L30).isEmpty());
	}

	@Test
	void serverOffDuringReset() {
		// se apagó el domingo 22 y arranca el martes 24: la semana del 16 se cierra al arrancar y sus campeones valen
		Season t = started(L16).register(Mode.SURVIVAL, e(A, "Ana", 11, 100, 1));
		Season.Closing c = t.advance(L23, MONDAY, 8);
		assertEquals(L23.toEpochDay(), c.closed().closing());
		assertEquals("Ana", c.season().champions(L23).get(Mode.SURVIVAL).name());
	}

	@Test
	void serverOffMoreThanAWeek() {
		// se apagó el 20 y arranca el 2-12 (semana del 30-11): la del 16 se cierra (al 23, no al 30); la semana anterior
		// (la del 23) nadie jugó: sin campeones, pero los de la del 16 conservan su logro
		Season t = started(L16).register(Mode.COOP, e(A, "Ana", 9, 100, 1));
		Season.Closing c = t.advance(L30, MONDAY, 8);
		assertEquals(L16.toEpochDay(), c.closed().start());
		assertEquals(L23.toEpochDay(), c.closed().closing());
		assertEquals(L30.toEpochDay(), c.season().week());
		assertTrue(c.season().champions(L30).isEmpty());
		assertEquals(Set.of(Mode.COOP), c.season().won(A));
		assertEquals(1, c.season().history().size(), "las semanas sin datos no se guardan");
	}

	@Test
	void resetDayChange() {
		// la guardada empezó el lunes 16; el día pasa a ser el miércoles: el jueves 19 (semana del miércoles 18) cierra
		Season t = started(L16).register(Mode.COOP, e(A, "Ana", 3, 1, 1));
		Season.Closing c = t.advance(LocalDate.of(2026, 11, 18), DayOfWeek.WEDNESDAY, 8);
		assertEquals(LocalDate.of(2026, 11, 18).toEpochDay(), c.closed().closing());
		assertEquals("Ana", c.season().champions(LocalDate.of(2026, 11, 18)).get(Mode.COOP).name());
		// un inicio anterior al guardado (p. ej. de miércoles a lunes a mitad de semana) no cierra nada
		Season u = Season.EMPTY.advance(LocalDate.of(2026, 11, 18), DayOfWeek.WEDNESDAY, 8).season();
		assertNull(u.advance(L16, MONDAY, 8).closed());
	}

	@Test
	void boundedHistory() {
		Season t = started(L16);
		LocalDate d = L16;
		for (int i = 0; i < 12; i++) {
			t = t.register(Mode.COOP, e(A, "Ana", i + 1, 1, i));
			d = d.plusWeeks(1);
			t = t.advance(d, MONDAY, 5).season();
		}
		assertEquals(5, t.history().size());
		assertEquals(12, t.history().get(0).champion(Mode.COOP).orElseThrow().waves(), "la más reciente primero");
		assertEquals(8, t.history().get(4).champion(Mode.COOP).orElseThrow().waves());
		assertEquals(12, t.closed(1).orElseThrow().champion(Mode.COOP).orElseThrow().waves());
		assertTrue(t.closed(6).isEmpty());
		assertTrue(t.closed(0).isEmpty());
		// bajar la opción recorta ya; subirla no inventa semanas
		assertEquals(2, t.trim(2).history().size());
		assertEquals(5, t.trim(40).history().size());
		assertEquals(1, t.trim(0).history().size(), "al menos una");
		assertEquals(12, t.record(Mode.COOP).orElseThrow().waves());
	}

	@Test
	void forcedReset() {
		// a mitad de la semana del 16 (miércoles 18): se cierra ya, con cierre = hoy, y sus campeones valen en seguida
		Season t = started(L16).register(Mode.TIME_TRIAL, ta(A, "Ana", 10, 8000, 1, 10));
		LocalDate today = LocalDate.of(2026, 11, 18);
		Season.Closing c = t.force(today, L16, 8);
		assertEquals(today.toEpochDay(), c.closed().closing());
		Season n = c.season();
		assertEquals(L16.toEpochDay(), n.week(), "la semana de calendario no cambia");
		assertTrue(n.actual().isEmpty());
		assertEquals("Ana", n.champions(L16).get(Mode.TIME_TRIAL).name());
		// y el lunes 23 se cierra otra vez (la parte que quedaba de semana), con sus propios campeones
		n = n.register(Mode.TIME_TRIAL, ta(B, "Bea", 10, 9000, 2, 10));
		Season.Closing d = n.advance(L23, MONDAY, 8);
		assertEquals(2, d.season().history().size());
		assertEquals("Bea", d.season().champions(L23).get(Mode.TIME_TRIAL).name());
		// sin semana empezada, el forzado parte de la de calendario
		Season.Closing v = Season.EMPTY.force(today, L16, 8);
		assertEquals(L16.toEpochDay(), v.closed().start());
		assertTrue(v.season().champions(L16).isEmpty());
		assertEquals(L16.toEpochDay(), v.season().week());
	}

	@Test
	void scoreboardMigration() {
		Map<String, Integer> scoreboard = Map.of("-servidor-", 14, "Ana", 9, "Bea", 14, "Cid", 14, "Nadie", 0);
		Season t = Season.EMPTY.migrate(scoreboard, "-servidor-", 77);
		assertTrue(t.migrated());
		Season.Entry r = t.record(Mode.COOP).orElseThrow();
		assertEquals("Bea", r.name(), "empate: por nombre (sin tiempo ni fecha que desempaten)");
		assertEquals(14, r.waves());
		assertEquals(-1, r.ticks());
		assertEquals(Season.NO_PLAYER, r.player());
		assertTrue(t.actual().isEmpty() && t.history().isEmpty(), "solo el récord: la semana empieza limpia");
		// una sola vez
		assertSame(t, t.migrate(Map.of("Zoe", 99), "-servidor-", 1));
		// un récord mejor que el del marcador no se pisa
		Season best = Season.EMPTY.register(Mode.COOP, e(A, "Ana", 20, 5, 1)).migrate(scoreboard, "-servidor-", 1);
		assertEquals(20, best.record(Mode.COOP).orElseThrow().waves());
		// sin marcador (mundo sin arena o desde cero)
		Season empty = Season.EMPTY.migrate(Map.of(), "-servidor-", 1);
		assertTrue(empty.migrated() && empty.records().isEmpty());
		Season alone = Season.EMPTY.migrate(Map.of("-servidor-", 4), "-servidor-", 1);
		assertTrue(alone.records().isEmpty(), "solo el del servidor: no se sabe de quién era");
	}

	@Test
	void migratedOnesAreToldByName() {
		Season.Entry v1 = e(Season.NO_PLAYER, "Viejo", 5, -1, 0), v2 = e(Season.NO_PLAYER, "Otro", 4, -1, 0);
		List<Season.Entry> l = Season.with(Season.with(List.of(), v1), v2);
		assertEquals(2, l.size());
	}

	@Test
	void savesAndReadsTheSame() {
		Season t = started(L16).register(Mode.COOP, e(A, "Ana", 9, 100, 1))
				.register(Mode.TIME_TRIAL, ta(B, "Bea", 10, 9000, 2, 10));
		t = t.advance(L23, MONDAY, 8).season().register(Mode.SURVIVAL, e(C, "Cid", 3, 30, 3))
				.migrate(Map.of("Viejo", 4), "-servidor-", 9);
		JsonElement j = Season.CODEC.encodeStart(JsonOps.INSTANCE, t).getOrThrow();
		Season u = Season.CODEC.parse(JsonOps.INSTANCE, j).getOrThrow();
		assertEquals(t, u);
		// un estado vacío (o de una versión sin estos datos) se lee como VACIA
		assertEquals(Season.EMPTY, Season.CODEC.parse(JsonOps.INSTANCE, new com.google.gson.JsonObject()).getOrThrow());
	}
}
