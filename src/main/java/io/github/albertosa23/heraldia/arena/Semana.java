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
public final class Semana {
	/** Valores de arena.temporada.dia_reinicio, de lunes a domingo (el orden de {@link DayOfWeek}). */
	public static final List<String> DIAS = List.of("lunes", "martes", "miercoles", "jueves", "viernes", "sabado", "domingo");

	private Semana() {
	}

	/** El día de arena.temporada.dia_reinicio (lunes si no se reconoce). */
	public static DayOfWeek dia(String valor) {
		int i = valor == null ? -1 : DIAS.indexOf(valor.toLowerCase(Locale.ROOT));
		return DayOfWeek.of(i < 0 ? 1 : i + 1);
	}

	/** El momento en que empieza la semana que empieza el día {@code inicio} (a la hora {@code hora} en {@code zona}). */
	public static ZonedDateTime limite(LocalDate inicio, int hora, ZoneId zona) {
		return ZonedDateTime.of(inicio, LocalTime.of(Math.clamp(hora, 0, 23), 0), zona);
	}

	/**
	 * Inicio (fecha del día de reinicio) de la semana en curso en el instante {@code ahora}: el último día {@code dia} a
	 * la hora {@code hora} que no es posterior a {@code ahora}.
	 */
	public static LocalDate inicio(Instant ahora, ZoneId zona, DayOfWeek dia, int hora) {
		ZonedDateTime z = ahora.atZone(zona);
		LocalDate d = z.toLocalDate().with(TemporalAdjusters.previousOrSame(dia));
		if (limite(d, hora, zona).toInstant().isAfter(ahora)) {
			d = d.minusWeeks(1);
		}
		return d;
	}

	/** Inicio de la semana siguiente a la que empieza en {@code inicio} (con el día de reinicio {@code dia}). */
	public static LocalDate siguiente(LocalDate inicio, DayOfWeek dia) {
		return inicio.plusDays(1).with(TemporalAdjusters.nextOrSame(dia));
	}

	/** Momento en que acaba la semana en curso (empieza la siguiente). */
	public static Instant proximoReinicio(Instant ahora, ZoneId zona, DayOfWeek dia, int hora) {
		return limite(siguiente(inicio(ahora, zona, dia, hora), dia), hora, zona).toInstant();
	}
}
