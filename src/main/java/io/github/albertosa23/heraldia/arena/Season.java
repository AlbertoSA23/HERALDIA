package io.github.albertosa23.heraldia.arena;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.time.DayOfWeek;
import java.time.LocalDate;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.EnumMap;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.UUID;
import org.jspecify.annotations.Nullable;

/**
 * Clasificación semanal de la arena por modo (T41), inmutable y sin clases del juego (la prueban los tests): lo que se
 * guarda en el mundo principal (adjunto persistente heraldia:arena_temporada, ver {@link Fame}).
 * <ul>
 * <li>{@link #week}: inicio (día de época, {@link LocalDate#toEpochDay()}) de la semana en curso, o {@link #NO_WEEK}
 * antes de la primera; {@link #actual}: su clasificación por modo (id de {@link Mode} → las mejores marcas, una por
 * jugador, ordenadas con {@link #ORDER}, como mucho {@link #MAX_PER_MODE}).</li>
 * <li>{@link #history}: las últimas semanas cerradas, la más reciente primero (arena.temporada.historico).</li>
 * <li>{@link #records}: la mejor marca de siempre de cada modo; {@link #migrated}: ya se copió el récord del marcador
 * vanilla de antes de T41 (el del cooperativo).</li>
 * </ul>
 * Todos los modos se ordenan igual (más oleadas superadas, luego menos tiempo, luego antes): en el contrarreloj, las
 * partidas acabadas tienen todas las oleadas y deciden por el tiempo; en el cooperativo y la supervivencia, la oleada.
 */
public record Season(long week, Map<String, List<Entry>> actual, List<Closed> history, Map<String, Entry> records,
		boolean migrated) {
	public static final long NO_WEEK = Long.MIN_VALUE;
	/** Marcas que se guardan por modo y semana (la clasificación enseña las 10 primeras). */
	public static final int MAX_PER_MODE = 10;
	/** Tope de semanas en el histórico, sea cual sea la opción. */
	public static final int MAX_HISTORY = 52;
	/** Jugador de las marcas migradas del marcador vanilla (solo se sabía su nombre). */
	public static final UUID NO_PLAYER = new UUID(0L, 0L);
	public static final Season EMPTY = new Season(NO_WEEK, Map.of(), List.of(), Map.of(), false);

	/**
	 * Una marca: quién, cuántas oleadas superó, en cuántos ticks de partida (desde que empezó la primera oleada hasta que
	 * superó la última; -1 si no se sabe, en las migradas), cuándo (milisegundos de época) y, en el contrarreloj, cuántas
	 * oleadas había que superar (0 en los demás modos).
	 */
	public record Entry(UUID player, String name, int waves, long ticks, long date, int target) {
		static final Codec<UUID> UUID_CODEC = Codec.STRING.xmap(UUID::fromString, UUID::toString);
		public static final Codec<Entry> CODEC = RecordCodecBuilder.create(i -> i.group(
				UUID_CODEC.fieldOf("jugador").forGetter(Entry::player),
				Codec.STRING.fieldOf("nombre").forGetter(Entry::name),
				Codec.INT.fieldOf("oleadas").forGetter(Entry::waves),
				Codec.LONG.optionalFieldOf("ticks", -1L).forGetter(Entry::ticks),
				Codec.LONG.optionalFieldOf("fecha", 0L).forGetter(Entry::date),
				Codec.INT.optionalFieldOf("objetivo", 0).forGetter(Entry::target)).apply(i, Entry::new));

		/** ¿Acabó el contrarreloj (superó todas las oleadas)? */
		public boolean complete() {
			return target > 0 && waves >= target;
		}

		/** Clave para quedarse con una marca por jugador (las migradas, por nombre). */
		String who() {
			return NO_PLAYER.equals(player) ? "nombre:" + name : player.toString();
		}
	}

	/** Una semana cerrada: su inicio, el día en que se cerró (el inicio de la siguiente, u hoy si se forzó) y su clasificación. */
	public record Closed(long start, long closing, Map<String, List<Entry>> ranking) {
		static final Codec<Map<String, List<Entry>>> RANKING = Codec.unboundedMap(Codec.STRING, Entry.CODEC.listOf());
		public static final Codec<Closed> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.LONG.fieldOf("inicio").forGetter(Closed::start),
				Codec.LONG.fieldOf("cierre").forGetter(Closed::closing),
				RANKING.optionalFieldOf("clasificacion", Map.of()).forGetter(Closed::ranking)).apply(i, Closed::new));

		public Closed {
			ranking = backup(ranking);
		}

		/** El primero de un modo, si lo hay. */
		public Optional<Entry> champion(Mode m) {
			List<Entry> l = ranking.get(m.id());
			return l == null || l.isEmpty() ? Optional.empty() : Optional.of(l.get(0));
		}
	}

	public static final Codec<Season> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.LONG.optionalFieldOf("semana", NO_WEEK).forGetter(Season::week),
			Closed.RANKING.optionalFieldOf("actual", Map.of()).forGetter(Season::actual),
			Closed.CODEC.listOf().optionalFieldOf("historico", List.of()).forGetter(Season::history),
			Codec.unboundedMap(Codec.STRING, Entry.CODEC).optionalFieldOf("records", Map.of()).forGetter(Season::records),
			Codec.BOOL.optionalFieldOf("migrada", false).forGetter(Season::migrated)).apply(i, Season::new));

	/** Mejor primero: más oleadas, luego menos ticks (los desconocidos, al final), luego antes y por nombre. */
	public static final Comparator<Entry> ORDER = Comparator.comparingInt(Entry::waves).reversed()
			.thenComparingLong(e -> e.ticks() < 0 ? Long.MAX_VALUE : e.ticks())
			.thenComparingLong(Entry::date)
			.thenComparing(Entry::name);

	public Season {
		actual = backup(actual);
		history = List.copyOf(history);
		records = Map.copyOf(records);
	}

	private static Map<String, List<Entry>> backup(Map<String, List<Entry>> m) {
		Map<String, List<Entry>> out = new LinkedHashMap<>();
		m.forEach((k, v) -> out.put(k, List.copyOf(v)));
		return java.util.Collections.unmodifiableMap(out);
	}

	/** ¿Es {@code a} mejor marca que {@code b} (o no hay {@code b})? */
	public static boolean best(Entry a, @Nullable Entry b) {
		return b == null || ORDER.compare(a, b) < 0;
	}

	/** La lista con {@code e} añadida: una marca por jugador (la mejor), ordenada y recortada a {@link #MAX_PER_MODE}. */
	static List<Entry> with(List<Entry> list, Entry e) {
		Map<String, Entry> best = new LinkedHashMap<>();
		for (Entry x : list) {
			best.merge(x.who(), x, (a, b) -> best(b, a) ? b : a);
		}
		best.merge(e.who(), e, (a, b) -> best(b, a) ? b : a);
		List<Entry> out = new ArrayList<>(best.values());
		out.sort(ORDER);
		return List.copyOf(out.subList(0, Math.min(out.size(), MAX_PER_MODE)));
	}

	/** Añade una marca de una partida terminada (a la semana en curso y, si lo es, al récord del modo). */
	public Season register(Mode m, Entry e) {
		Map<String, List<Entry>> a = new LinkedHashMap<>(actual);
		a.put(m.id(), with(a.getOrDefault(m.id(), List.of()), e));
		Map<String, Entry> r = new LinkedHashMap<>(records);
		if (best(e, r.get(m.id()))) {
			r.put(m.id(), e);
		}
		return new Season(week, a, history, r, migrated);
	}

	/** La clasificación de un modo en la semana en curso. */
	public List<Entry> ranking(Mode m) {
		return actual.getOrDefault(m.id(), List.of());
	}

	public Optional<Entry> record(Mode m) {
		return Optional.ofNullable(records.get(m.id()));
	}

	/** Resultado de {@link #advance} y {@link #force}: el estado nuevo y la semana que se cerró (si se cerró alguna). */
	public record Closing(Season season, @Nullable Closed closed) {
	}

	/**
	 * Al arrancar y cada poco: si la semana en curso ya no es la guardada (ha pasado el día de reinicio, también con el
	 * servidor apagado), la guardada se cierra (pasa al histórico, como mucho {@code max} semanas) y empieza otra vacía.
	 * Si el servidor estuvo apagado más de una semana, la cerrada no es la de la semana anterior: su {@code closing} es el
	 * inicio de la que la siguió, y no tiene campeones de la semana anterior ({@link #champions}). Antes de la primera
	 * semana solo apunta su inicio. Un {@code currentStart} anterior al guardado (cambio del día de reinicio) no cierra
	 * nada hasta que lo pase.
	 */
	public Closing advance(LocalDate currentStart, DayOfWeek day, int max) {
		long today = currentStart.toEpochDay();
		if (week == NO_WEEK) {
			return new Closing(new Season(today, actual, history, records, migrated), null);
		}
		if (today <= week) {
			return new Closing(this, null);
		}
		long closing = Math.min(today, Week.next(LocalDate.ofEpochDay(week), day).toEpochDay());
		return close(closing, today, max);
	}

	/**
	 * /heraldia arena season reset: cierra ya la semana en curso (su {@code closing} es hoy) y empieza otra vacía con el
	 * mismo inicio de calendario: el reinicio automático sigue cayendo el día de siempre.
	 */
	public Closing force(LocalDate today, LocalDate currentStart, int max) {
		long ini = week == NO_WEEK ? currentStart.toEpochDay() : week;
		return new Season(ini, actual, history, records, migrated).close(today.toEpochDay(), currentStart.toEpochDay(), max);
	}

	private Closing close(long closing, long fresh, int max) {
		Closed c = new Closed(week, closing, actual);
		List<Closed> h = new ArrayList<>(history.size() + 1);
		h.add(c);
		h.addAll(history);
		Season t = new Season(fresh, Map.of(), h, records, migrated).trim(max);
		return new Closing(t, c);
	}

	/** El histórico recortado a {@code max} semanas (entre 1 y {@link #MAX_HISTORY}). */
	public Season trim(int max) {
		int n = Math.clamp(max, 1, MAX_HISTORY);
		return history.size() <= n ? this : new Season(week, actual, history.subList(0, n), records, migrated);
	}

	/**
	 * Campeones de la semana anterior a la que empieza en {@code currentStart}, por modo: el primero de cada modo de la
	 * última semana cerrada, si se cerró al empezar esta (o después, si se forzó); vacío si no hay o si la última cerrada
	 * es más antigua (el servidor estuvo apagado toda la semana anterior: nadie jugó).
	 */
	public Map<Mode, Entry> champions(LocalDate currentStart) {
		Map<Mode, Entry> out = new EnumMap<>(Mode.class);
		if (history.isEmpty() || history.get(0).closing() < currentStart.toEpochDay()) {
			return out;
		}
		Closed c = history.get(0);
		for (Mode m : Mode.values()) {
			c.champion(m).ifPresent(e -> out.put(m, e));
		}
		return out;
	}

	/** La semana cerrada de hace {@code ago} semanas (1 = la anterior), si se guarda. */
	public Optional<Closed> closed(int ago) {
		return ago >= 1 && ago <= history.size() ? Optional.of(history.get(ago - 1)) : Optional.empty();
	}

	/** Modos en los que este jugador ganó alguna de las semanas guardadas (para sus logros, aunque no estuviera al cerrarse). */
	public Set<Mode> won(UUID player) {
		Set<Mode> out = new HashSet<>();
		for (Closed c : history) {
			for (Mode m : Mode.values()) {
				c.champion(m).filter(e -> e.player().equals(player)).ifPresent(e -> out.add(m));
			}
		}
		return out;
	}

	/**
	 * Migración (una vez) del marcador vanilla de antes de T41 (objetivo heraldia_arena: oleadas superadas por jugador y
	 * la del servidor, {@code server}): el mejor jugador pasa a ser el récord del cooperativo, si es mejor que el que
	 * hubiera, sin tiempo (no se sabía). El marcador no se toca: sigue siendo el del cooperativo.
	 */
	public Season migrate(Map<String, Integer> points, String server, long date) {
		if (migrated) {
			return this;
		}
		Entry best = null;
		for (Map.Entry<String, Integer> p : new java.util.TreeMap<>(points).entrySet()) {
			if (p.getKey().equals(server) || p.getValue() == null || p.getValue() <= 0) {
				continue;
			}
			Entry e = new Entry(NO_PLAYER, p.getKey(), p.getValue(), -1, date, 0);
			if (best(e, best)) {
				best = e;
			}
		}
		Map<String, Entry> r = new LinkedHashMap<>(records);
		String c = Mode.COOP.id();
		if (best != null && best(best, r.get(c))) {
			r.put(c, best);
		}
		return new Season(week, actual, history, r, true);
	}
}
