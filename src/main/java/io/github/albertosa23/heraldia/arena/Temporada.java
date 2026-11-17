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
 * guarda en el mundo principal (adjunto persistente heraldia:arena_temporada, ver {@link Fama}).
 * <ul>
 * <li>{@link #semana}: inicio (día de época, {@link LocalDate#toEpochDay()}) de la semana en curso, o {@link #SIN_SEMANA}
 * antes de la primera; {@link #actual}: su clasificación por modo (id de {@link Modo} → las mejores marcas, una por
 * jugador, ordenadas con {@link #ORDEN}, como mucho {@link #MAX_POR_MODO}).</li>
 * <li>{@link #historico}: las últimas semanas cerradas, la más reciente primero (arena.temporada.historico).</li>
 * <li>{@link #records}: la mejor marca de siempre de cada modo; {@link #migrada}: ya se copió el récord del marcador
 * vanilla de antes de T41 (el del cooperativo).</li>
 * </ul>
 * Todos los modos se ordenan igual (más oleadas superadas, luego menos tiempo, luego antes): en el contrarreloj, las
 * partidas acabadas tienen todas las oleadas y deciden por el tiempo; en el cooperativo y la supervivencia, la oleada.
 */
public record Temporada(long semana, Map<String, List<Entrada>> actual, List<Cerrada> historico, Map<String, Entrada> records,
		boolean migrada) {
	public static final long SIN_SEMANA = Long.MIN_VALUE;
	/** Marcas que se guardan por modo y semana (la clasificación enseña las 10 primeras). */
	public static final int MAX_POR_MODO = 10;
	/** Tope de semanas en el histórico, sea cual sea la opción. */
	public static final int MAX_HISTORICO = 52;
	/** Jugador de las marcas migradas del marcador vanilla (solo se sabía su nombre). */
	public static final UUID SIN_JUGADOR = new UUID(0L, 0L);
	public static final Temporada VACIA = new Temporada(SIN_SEMANA, Map.of(), List.of(), Map.of(), false);

	/**
	 * Una marca: quién, cuántas oleadas superó, en cuántos ticks de partida (desde que empezó la primera oleada hasta que
	 * superó la última; -1 si no se sabe, en las migradas), cuándo (milisegundos de época) y, en el contrarreloj, cuántas
	 * oleadas había que superar (0 en los demás modos).
	 */
	public record Entrada(UUID jugador, String nombre, int oleadas, long ticks, long fecha, int objetivo) {
		static final Codec<UUID> UUID_CODEC = Codec.STRING.xmap(UUID::fromString, UUID::toString);
		public static final Codec<Entrada> CODEC = RecordCodecBuilder.create(i -> i.group(
				UUID_CODEC.fieldOf("jugador").forGetter(Entrada::jugador),
				Codec.STRING.fieldOf("nombre").forGetter(Entrada::nombre),
				Codec.INT.fieldOf("oleadas").forGetter(Entrada::oleadas),
				Codec.LONG.optionalFieldOf("ticks", -1L).forGetter(Entrada::ticks),
				Codec.LONG.optionalFieldOf("fecha", 0L).forGetter(Entrada::fecha),
				Codec.INT.optionalFieldOf("objetivo", 0).forGetter(Entrada::objetivo)).apply(i, Entrada::new));

		/** ¿Acabó el contrarreloj (superó todas las oleadas)? */
		public boolean completa() {
			return objetivo > 0 && oleadas >= objetivo;
		}

		/** Clave para quedarse con una marca por jugador (las migradas, por nombre). */
		String quien() {
			return SIN_JUGADOR.equals(jugador) ? "nombre:" + nombre : jugador.toString();
		}
	}

	/** Una semana cerrada: su inicio, el día en que se cerró (el inicio de la siguiente, u hoy si se forzó) y su clasificación. */
	public record Cerrada(long inicio, long cierre, Map<String, List<Entrada>> clasificacion) {
		static final Codec<Map<String, List<Entrada>>> CLASIFICACION = Codec.unboundedMap(Codec.STRING, Entrada.CODEC.listOf());
		public static final Codec<Cerrada> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.LONG.fieldOf("inicio").forGetter(Cerrada::inicio),
				Codec.LONG.fieldOf("cierre").forGetter(Cerrada::cierre),
				CLASIFICACION.optionalFieldOf("clasificacion", Map.of()).forGetter(Cerrada::clasificacion)).apply(i, Cerrada::new));

		public Cerrada {
			clasificacion = copia(clasificacion);
		}

		/** El primero de un modo, si lo hay. */
		public Optional<Entrada> campeon(Modo m) {
			List<Entrada> l = clasificacion.get(m.id());
			return l == null || l.isEmpty() ? Optional.empty() : Optional.of(l.get(0));
		}
	}

	public static final Codec<Temporada> CODEC = RecordCodecBuilder.create(i -> i.group(
			Codec.LONG.optionalFieldOf("semana", SIN_SEMANA).forGetter(Temporada::semana),
			Cerrada.CLASIFICACION.optionalFieldOf("actual", Map.of()).forGetter(Temporada::actual),
			Cerrada.CODEC.listOf().optionalFieldOf("historico", List.of()).forGetter(Temporada::historico),
			Codec.unboundedMap(Codec.STRING, Entrada.CODEC).optionalFieldOf("records", Map.of()).forGetter(Temporada::records),
			Codec.BOOL.optionalFieldOf("migrada", false).forGetter(Temporada::migrada)).apply(i, Temporada::new));

	/** Mejor primero: más oleadas, luego menos ticks (los desconocidos, al final), luego antes y por nombre. */
	public static final Comparator<Entrada> ORDEN = Comparator.comparingInt(Entrada::oleadas).reversed()
			.thenComparingLong(e -> e.ticks() < 0 ? Long.MAX_VALUE : e.ticks())
			.thenComparingLong(Entrada::fecha)
			.thenComparing(Entrada::nombre);

	public Temporada {
		actual = copia(actual);
		historico = List.copyOf(historico);
		records = Map.copyOf(records);
	}

	private static Map<String, List<Entrada>> copia(Map<String, List<Entrada>> m) {
		Map<String, List<Entrada>> out = new LinkedHashMap<>();
		m.forEach((k, v) -> out.put(k, List.copyOf(v)));
		return java.util.Collections.unmodifiableMap(out);
	}

	/** ¿Es {@code a} mejor marca que {@code b} (o no hay {@code b})? */
	public static boolean mejor(Entrada a, @Nullable Entrada b) {
		return b == null || ORDEN.compare(a, b) < 0;
	}

	/** La lista con {@code e} añadida: una marca por jugador (la mejor), ordenada y recortada a {@link #MAX_POR_MODO}. */
	static List<Entrada> con(List<Entrada> lista, Entrada e) {
		Map<String, Entrada> mejores = new LinkedHashMap<>();
		for (Entrada x : lista) {
			mejores.merge(x.quien(), x, (a, b) -> mejor(b, a) ? b : a);
		}
		mejores.merge(e.quien(), e, (a, b) -> mejor(b, a) ? b : a);
		List<Entrada> out = new ArrayList<>(mejores.values());
		out.sort(ORDEN);
		return List.copyOf(out.subList(0, Math.min(out.size(), MAX_POR_MODO)));
	}

	/** Añade una marca de una partida terminada (a la semana en curso y, si lo es, al récord del modo). */
	public Temporada registrar(Modo m, Entrada e) {
		Map<String, List<Entrada>> a = new LinkedHashMap<>(actual);
		a.put(m.id(), con(a.getOrDefault(m.id(), List.of()), e));
		Map<String, Entrada> r = new LinkedHashMap<>(records);
		if (mejor(e, r.get(m.id()))) {
			r.put(m.id(), e);
		}
		return new Temporada(semana, a, historico, r, migrada);
	}

	/** La clasificación de un modo en la semana en curso. */
	public List<Entrada> clasificacion(Modo m) {
		return actual.getOrDefault(m.id(), List.of());
	}

	public Optional<Entrada> record(Modo m) {
		return Optional.ofNullable(records.get(m.id()));
	}

	/** Resultado de {@link #avanzar} y {@link #forzar}: el estado nuevo y la semana que se cerró (si se cerró alguna). */
	public record Cierre(Temporada temporada, @Nullable Cerrada cerrada) {
	}

	/**
	 * Al arrancar y cada poco: si la semana en curso ya no es la guardada (ha pasado el día de reinicio, también con el
	 * servidor apagado), la guardada se cierra (pasa al histórico, como mucho {@code max} semanas) y empieza otra vacía.
	 * Si el servidor estuvo apagado más de una semana, la cerrada no es la de la semana anterior: su {@code cierre} es el
	 * inicio de la que la siguió, y no tiene campeones de la semana anterior ({@link #campeones}). Antes de la primera
	 * semana solo apunta su inicio. Un {@code inicioActual} anterior al guardado (cambio del día de reinicio) no cierra
	 * nada hasta que lo pase.
	 */
	public Cierre avanzar(LocalDate inicioActual, DayOfWeek dia, int max) {
		long hoy = inicioActual.toEpochDay();
		if (semana == SIN_SEMANA) {
			return new Cierre(new Temporada(hoy, actual, historico, records, migrada), null);
		}
		if (hoy <= semana) {
			return new Cierre(this, null);
		}
		long cierre = Math.min(hoy, Semana.siguiente(LocalDate.ofEpochDay(semana), dia).toEpochDay());
		return cerrar(cierre, hoy, max);
	}

	/**
	 * /heraldia arena season reset: cierra ya la semana en curso (su {@code cierre} es hoy) y empieza otra vacía con el
	 * mismo inicio de calendario: el reinicio automático sigue cayendo el día de siempre.
	 */
	public Cierre forzar(LocalDate hoy, LocalDate inicioActual, int max) {
		long ini = semana == SIN_SEMANA ? inicioActual.toEpochDay() : semana;
		return new Temporada(ini, actual, historico, records, migrada).cerrar(hoy.toEpochDay(), inicioActual.toEpochDay(), max);
	}

	private Cierre cerrar(long cierre, long nueva, int max) {
		Cerrada c = new Cerrada(semana, cierre, actual);
		List<Cerrada> h = new ArrayList<>(historico.size() + 1);
		h.add(c);
		h.addAll(historico);
		Temporada t = new Temporada(nueva, Map.of(), h, records, migrada).recortar(max);
		return new Cierre(t, c);
	}

	/** El histórico recortado a {@code max} semanas (entre 1 y {@link #MAX_HISTORICO}). */
	public Temporada recortar(int max) {
		int n = Math.clamp(max, 1, MAX_HISTORICO);
		return historico.size() <= n ? this : new Temporada(semana, actual, historico.subList(0, n), records, migrada);
	}

	/**
	 * Campeones de la semana anterior a la que empieza en {@code inicioActual}, por modo: el primero de cada modo de la
	 * última semana cerrada, si se cerró al empezar esta (o después, si se forzó); vacío si no hay o si la última cerrada
	 * es más antigua (el servidor estuvo apagado toda la semana anterior: nadie jugó).
	 */
	public Map<Modo, Entrada> campeones(LocalDate inicioActual) {
		Map<Modo, Entrada> out = new EnumMap<>(Modo.class);
		if (historico.isEmpty() || historico.get(0).cierre() < inicioActual.toEpochDay()) {
			return out;
		}
		Cerrada c = historico.get(0);
		for (Modo m : Modo.values()) {
			c.campeon(m).ifPresent(e -> out.put(m, e));
		}
		return out;
	}

	/** La semana cerrada de hace {@code hace} semanas (1 = la anterior), si se guarda. */
	public Optional<Cerrada> cerrada(int hace) {
		return hace >= 1 && hace <= historico.size() ? Optional.of(historico.get(hace - 1)) : Optional.empty();
	}

	/** Modos en los que este jugador ganó alguna de las semanas guardadas (para sus logros, aunque no estuviera al cerrarse). */
	public Set<Modo> ganadas(UUID jugador) {
		Set<Modo> out = new HashSet<>();
		for (Cerrada c : historico) {
			for (Modo m : Modo.values()) {
				c.campeon(m).filter(e -> e.jugador().equals(jugador)).ifPresent(e -> out.add(m));
			}
		}
		return out;
	}

	/**
	 * Migración (una vez) del marcador vanilla de antes de T41 (objetivo heraldia_arena: oleadas superadas por jugador y
	 * la del servidor, {@code servidor}): el mejor jugador pasa a ser el récord del cooperativo, si es mejor que el que
	 * hubiera, sin tiempo (no se sabía). El marcador no se toca: sigue siendo el del cooperativo.
	 */
	public Temporada migrar(Map<String, Integer> puntos, String servidor, long fecha) {
		if (migrada) {
			return this;
		}
		Entrada mejor = null;
		for (Map.Entry<String, Integer> p : new java.util.TreeMap<>(puntos).entrySet()) {
			if (p.getKey().equals(servidor) || p.getValue() == null || p.getValue() <= 0) {
				continue;
			}
			Entrada e = new Entrada(SIN_JUGADOR, p.getKey(), p.getValue(), -1, fecha, 0);
			if (mejor(e, mejor)) {
				mejor = e;
			}
		}
		Map<String, Entrada> r = new LinkedHashMap<>(records);
		String c = Modo.COOPERATIVO.id();
		if (mejor != null && mejor(mejor, r.get(c))) {
			r.put(c, mejor);
		}
		return new Temporada(semana, actual, historico, r, true);
	}
}
