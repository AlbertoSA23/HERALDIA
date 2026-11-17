package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import org.junit.jupiter.api.Test;

/** La semana de la clasificación de la arena: día y hora de reinicio, zonas horarias, cambio de año y de hora. */
class SemanaTest {
	private static final ZoneId MADRID = ZoneId.of("Europe/Madrid"), UTC = ZoneId.of("UTC"), AUCKLAND = ZoneId.of("Pacific/Auckland");

	private static Instant en(String fechaHora, ZoneId z) {
		return LocalDateTime.parse(fechaHora).atZone(z).toInstant();
	}

	@Test
	void lunesALasCero() {
		// martes 17-11-2026: la semana empezó el lunes 16
		assertEquals(LocalDate.of(2026, 11, 16), Semana.inicio(en("2026-11-17T15:00", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		// el propio lunes a las 00:00 ya es la semana nueva; un segundo antes, la anterior
		assertEquals(LocalDate.of(2026, 11, 16), Semana.inicio(en("2026-11-16T00:00", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2026, 11, 9), Semana.inicio(en("2026-11-15T23:59:59", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		// el domingo es aún la semana del lunes anterior
		assertEquals(LocalDate.of(2026, 11, 16), Semana.inicio(en("2026-11-22T23:00", MADRID), MADRID, DayOfWeek.MONDAY, 0));
	}

	@Test
	void horaDeReinicio() {
		// reinicio el lunes a las 6:00: el lunes a las 5:59 sigue la semana anterior
		assertEquals(LocalDate.of(2026, 11, 9), Semana.inicio(en("2026-11-16T05:59", MADRID), MADRID, DayOfWeek.MONDAY, 6));
		assertEquals(LocalDate.of(2026, 11, 16), Semana.inicio(en("2026-11-16T06:00", MADRID), MADRID, DayOfWeek.MONDAY, 6));
		assertEquals(en("2026-11-23T06:00", MADRID), Semana.proximoReinicio(en("2026-11-16T06:00", MADRID), MADRID, DayOfWeek.MONDAY, 6));
		// hora fuera de rango: se acota
		assertEquals(Semana.limite(LocalDate.of(2026, 11, 16), 23, MADRID), Semana.limite(LocalDate.of(2026, 11, 16), 99, MADRID));
	}

	@Test
	void otroDia() {
		// reinicio el viernes: el jueves 19-11 es la semana del viernes 13
		assertEquals(LocalDate.of(2026, 11, 13), Semana.inicio(en("2026-11-19T12:00", MADRID), MADRID, DayOfWeek.FRIDAY, 0));
		assertEquals(LocalDate.of(2026, 11, 20), Semana.inicio(en("2026-11-20T00:00", MADRID), MADRID, DayOfWeek.FRIDAY, 0));
		assertEquals(LocalDate.of(2026, 11, 20), Semana.siguiente(LocalDate.of(2026, 11, 13), DayOfWeek.FRIDAY));
		// si cambia el día de reinicio, la siguiente es el primer día nuevo tras el inicio guardado
		assertEquals(LocalDate.of(2026, 11, 18), Semana.siguiente(LocalDate.of(2026, 11, 16), DayOfWeek.WEDNESDAY));
		assertEquals(LocalDate.of(2026, 11, 23), Semana.siguiente(LocalDate.of(2026, 11, 16), DayOfWeek.MONDAY));
	}

	@Test
	void cambioDeAnio() {
		// jueves 31-12-2026: la semana empezó el lunes 28-12-2026; el lunes 4-1-2027 empieza otra
		assertEquals(LocalDate.of(2026, 12, 28), Semana.inicio(en("2026-12-31T23:30", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2026, 12, 28), Semana.inicio(en("2027-01-03T23:59", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2027, 1, 4), Semana.inicio(en("2027-01-04T00:00", MADRID), MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2027, 1, 4), Semana.siguiente(LocalDate.of(2026, 12, 28), DayOfWeek.MONDAY));
		// año bisiesto: del lunes 26-2-2024 al lunes 4-3-2024 (pasando por el 29-2)
		assertEquals(LocalDate.of(2024, 3, 4), Semana.siguiente(LocalDate.of(2024, 2, 26), DayOfWeek.MONDAY));
	}

	@Test
	void zonasHorarias() {
		// el mismo instante (lunes 16-11-2026 a las 00:30 en Madrid = domingo 23:30 en UTC) es otra semana en cada zona
		Instant i = en("2026-11-16T00:30", MADRID);
		assertEquals(LocalDate.of(2026, 11, 16), Semana.inicio(i, MADRID, DayOfWeek.MONDAY, 0));
		assertEquals(LocalDate.of(2026, 11, 9), Semana.inicio(i, UTC, DayOfWeek.MONDAY, 0));
		// en Auckland (UTC+13 en noviembre) ya es lunes a mediodía
		assertEquals(LocalDate.of(2026, 11, 16), Semana.inicio(i, AUCKLAND, DayOfWeek.MONDAY, 0));
		assertNotEquals(Semana.proximoReinicio(i, MADRID, DayOfWeek.MONDAY, 0), Semana.proximoReinicio(i, UTC, DayOfWeek.MONDAY, 0));
	}

	@Test
	void cambioDeHora() {
		// Madrid adelanta la hora el domingo 29-3-2026 a las 2:00 (no existe de 2:00 a 3:00): un reinicio el domingo a
		// las 2:00 cae a las 3:00 de verano, y una semana con el cambio dura 167 horas
		ZonedDateTime l = Semana.limite(LocalDate.of(2026, 3, 29), 2, MADRID);
		assertEquals(3, l.getHour());
		assertEquals(LocalDate.of(2026, 3, 22), Semana.inicio(en("2026-03-29T01:59", MADRID), MADRID, DayOfWeek.SUNDAY, 2));
		assertEquals(LocalDate.of(2026, 3, 29), Semana.inicio(l.toInstant(), MADRID, DayOfWeek.SUNDAY, 2));
		Instant a = Semana.limite(LocalDate.of(2026, 3, 23), 0, MADRID).toInstant(), b = Semana.limite(LocalDate.of(2026, 3, 30), 0, MADRID).toInstant();
		assertEquals(167, java.time.Duration.between(a, b).toHours());
		assertEquals(LocalDate.of(2026, 3, 30), Semana.inicio(b, MADRID, DayOfWeek.MONDAY, 0));
		// y el retraso de octubre (25-10-2026): 169 horas, la semana no se mueve
		Instant c = Semana.limite(LocalDate.of(2026, 10, 19), 0, MADRID).toInstant(), d = Semana.limite(LocalDate.of(2026, 10, 26), 0, MADRID).toInstant();
		assertEquals(169, java.time.Duration.between(c, d).toHours());
		assertEquals(LocalDate.of(2026, 10, 19), Semana.inicio(d.minusSeconds(1), MADRID, DayOfWeek.MONDAY, 0));
	}

	@Test
	void diasDeLaOpcion() {
		assertEquals(DayOfWeek.MONDAY, Semana.dia("lunes"));
		assertEquals(DayOfWeek.WEDNESDAY, Semana.dia("miercoles"));
		assertEquals(DayOfWeek.SUNDAY, Semana.dia("DOMINGO"));
		assertEquals(DayOfWeek.MONDAY, Semana.dia("otro"));
		assertEquals(DayOfWeek.MONDAY, Semana.dia(null));
		assertEquals(7, Semana.DIAS.size());
		for (int i = 0; i < 7; i++) {
			assertEquals(DayOfWeek.of(i + 1), Semana.dia(Semana.DIAS.get(i)));
			assertTrue(Semana.DIAS.get(i).matches("[a-z]+"));
		}
	}

	@Test
	void elProximoReinicioEsElInicioDeLaSiguiente() {
		for (int h = 0; h < 24 * 14; h += 5) {
			Instant i = en("2026-11-10T00:00", MADRID).plusSeconds(h * 3600L);
			Instant p = Semana.proximoReinicio(i, MADRID, DayOfWeek.MONDAY, 0);
			assertTrue(p.isAfter(i));
			assertEquals(Semana.inicio(i, MADRID, DayOfWeek.MONDAY, 0).plusWeeks(1), Semana.inicio(p, MADRID, DayOfWeek.MONDAY, 0));
		}
	}
}
