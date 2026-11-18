package io.github.albertosa23.heraldia.common;

import java.util.Locale;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Perfil de la generación (opcional): tiempo acumulado de los tramos más caros de Heraldia, volcado al log al parar el
 * servidor. Solo con {@code -Dheraldia.profile=true}; sin la propiedad, {@link #ACTIVE} es una constante falsa y
 * {@link #start()} y {@link #end} no hacen nada (el JIT quita las llamadas): coste cero en el servidor de verdad.
 * <p>Uso: {@code long t0 = Profiler.start(); ...; Profiler.end(Profiler.Segment.HILLSIDE, t0);}. Lo lee
 * {@code tools/smoke/coste_generacion.py} de la línea «Heraldia: perfil: {...}» (JSON).
 */
public final class Profiler {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PROPERTY = "heraldia.perfil";
	public static final boolean ACTIVE = Boolean.getBoolean(PROPERTY);

	/** Tramos medidos (el nombre en minúsculas es la clave del JSON). */
	public enum Segment {
		/** El mixin de las reglas de colocación entero (tryGenerateStructure: aldeas, únicas, medianas, minas, ajenas). */
		RULES,
		/** Lo mismo en /locate y los mapas (StructureCheck.canCreateStructure). */
		RULES_LOCATE,
		/** Estructuras de otros mods junto a una aldea o una única ({@link ForeignZone}). */
		FOREIGN_ZONE,
		/** Distancia mínima entre únicas (UniqueSeparation.blocked). */
		UNIQUE_SEPARATION,
		/** Regla de colocación de las medianas ({@link MediumStructures#rejects}). */
		MEDIUMS,
		/** Regla de colocación de las entradas a mina (Minas.rechaza). */
		MINES,
		/** Búsqueda de la ladera de una entrada a mina (Ladera.buscar). */
		HILLSIDE,
		/** La misma búsqueda, adelantada en otros hilos para /locate (minas/LocateParalelo; no cuenta en LADERA). */
		HILLSIDE_EARLY,
		/** Punto de inicio de una aldea (el jigsaw de vanilla más lo propio). */
		VILLAGE,
		/** Búsqueda de la orilla y colocación del puerto de una aldea de costa. */
		SHORE,
		/** Rasgo de los caminos entre aldeas, por chunk. */
		ROADS,
		/** Regla de colocación de los faros y naufragios (costa/Costa: la de las minas con su familia). */
		COAST,
		/** Búsqueda de la orilla de un faro o un naufragio (costa/Orilla). */
		COAST_SHORE
	}

	/** Contadores de un perfil (instancia aparte para poder probarlos sin la propiedad del sistema). */
	public static final class Counters {
		private final boolean active;
		private final LongAdder[] n = new LongAdder[Segment.values().length], ns = new LongAdder[Segment.values().length];
		private final AtomicLong[] max = new AtomicLong[Segment.values().length];

		public Counters(boolean active) {
			this.active = active;
			for (int i = 0; i < n.length; i++) {
				n[i] = new LongAdder();
				ns[i] = new LongAdder();
				max[i] = new AtomicLong();
			}
		}

		public boolean active() {
			return active;
		}

		public long start() {
			return active ? System.nanoTime() : 0L;
		}

		public void end(Segment t, long t0) {
			if (active) {
				recordSample(t, System.nanoTime() - t0);
			}
		}

		/** Suma una medida ya tomada (en ns). Sin efecto si el perfil no está activo. */
		public void recordSample(Segment t, long dur) {
			if (!active) {
				return;
			}
			int i = t.ordinal();
			n[i].increment();
			ns[i].add(dur);
			max[i].accumulateAndGet(dur, Math::max);
		}

		public long times(Segment t) {
			return n[t.ordinal()].sum();
		}

		public long nanos(Segment t) {
			return ns[t.ordinal()].sum();
		}

		public long maximum(Segment t) {
			return max[t.ordinal()].get();
		}

		/**
		 * JSON de una línea con cada tramo medido: {"ladera":{"n":12,"total_ms":3.4,"media_us":283.3,"max_us":900.0},...}.
		 * Solo lee: llamarlo varias veces da lo mismo.
		 */
		public String json() {
			StringBuilder sb = new StringBuilder("{");
			for (Segment t : Segment.values()) {
				long k = times(t);
				if (k == 0) {
					continue;
				}
				if (sb.length() > 1) {
					sb.append(',');
				}
				long total = nanos(t);
				sb.append(String.format(Locale.ROOT, "\"%s\":{\"n\":%d,\"total_ms\":%.3f,\"media_us\":%.1f,\"max_us\":%.1f}",
						t.name().toLowerCase(Locale.ROOT), k, total / 1e6, total / 1e3 / k, maximum(t) / 1e3));
			}
			return sb.append('}').toString();
		}
	}

	private static final Counters COUNTERS = new Counters(ACTIVE);

	private Profiler() {
	}

	/** Una línea en Heraldia.onInitialize: sin la propiedad no registra nada. */
	public static void register() {
		if (!ACTIVE) {
			return;
		}
		LOGGER.info("Heraldia: perfil de la generación activado (-D{}=true)", PROPERTY);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> dump());
	}

	public static long start() {
		return ACTIVE ? System.nanoTime() : 0L;
	}

	public static void end(Segment t, long t0) {
		if (ACTIVE) {
			COUNTERS.recordSample(t, System.nanoTime() - t0);
		}
	}

	/** Los contadores globales (para /heraldia o las pruebas). */
	public static Counters counters() {
		return COUNTERS;
	}

	/** Escribe el perfil acumulado en el log (si está activo). */
	public static void dump() {
		if (ACTIVE) {
			LOGGER.info("Heraldia: perfil: {}", COUNTERS.json());
		}
	}
}
