package io.github.albertosa23.heraldia.arena;

import java.time.DayOfWeek;
import java.time.Instant;
import java.time.LocalDate;
import java.time.LocalTime;
import java.time.ZoneId;
import java.time.ZonedDateTime;
import java.time.temporal.TemporalAdjusters;
import java.util.List;
import java.util.Locale;

/**
 * Cálculo de la semana de la clasificación de la arena (T41), lógica pura: la semana empieza el día
 * arena.temporada.dia_reinicio a la hora arena.temporada.hora_reinicio (hora del servidor) y se identifica por la fecha
 * de ese día (su «inicio»). Con fechas locales, y no con instantes, el cambio de hora (verano/invierno) y el de año no
 * mueven la semana; una hora que no existe por el cambio de hora (p. ej. las 2:00 de la noche del cambio) se toma como
 * la primera hora válida de después (como {@link LocalDate#atTime} con {@link ZonedDateTime#of}).
 */
public final class Week {
	/** Valores de arena.temporada.dia_reinicio, de lunes a domingo (el orden de {@link DayOfWeek}). */
	public static final List<String> DAYS = List.of("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo");

	private Week() {
	}

	/** El día de arena.temporada.dia_reinicio (lunes si no se reconoce). */
	public static DayOfWeek day(String value) {
		int i = value == null ? -1 : DAYS.indexOf(value.toLowerCase(Locale.ROOT));
		return DayOfWeek.of(i < 0 ? 1 : i + 1);
	}

	/** El momento en que empieza la semana que empieza el día {@code start} (a la hora {@code hour} en {@code zone}). */
	public static ZonedDateTime limit(LocalDate start, int hour, ZoneId zone) {
		return ZonedDateTime.of(start, LocalTime.of(Math.clamp(hour, 0, 23), 0), zone);
	}

	/**
	 * Inicio (fecha del día de reinicio) de la semana en curso en el instante {@code now}: el último día {@code day} a
	 * la hora {@code hour} que no es posterior a {@code now}.
	 */
	public static LocalDate start(Instant now, ZoneId zone, DayOfWeek day, int hour) {
		ZonedDateTime z = now.atZone(zone);
		LocalDate d = z.toLocalDate().with(TemporalAdjusters.previousOrSame(day));
		if (limit(d, hour, zone).toInstant().isAfter(now)) {
			d = d.minusWeeks(1);
		}
		return d;
	}

	/** Inicio de la semana siguiente a la que empieza en {@code start} (con el día de reinicio {@code day}). */
	public static LocalDate next(LocalDate start, DayOfWeek day) {
		return start.plusDays(1).with(TemporalAdjusters.nextOrSame(day));
	}

	/** Momento en que acaba la semana en curso (empieza la siguiente). */
	public static Instant nextReset(Instant now, ZoneId zone, DayOfWeek day, int hour) {
		return limit(next(start(now, zone, day, hour), day), hour, zone).toInstant();
	}
}
