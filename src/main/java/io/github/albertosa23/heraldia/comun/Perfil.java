package io.github.albertosa23.heraldia.comun;

import java.util.Locale;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Perfil de la generación (opcional): tiempo acumulado de los tramos más caros de Heraldia, volcado al log al parar el
 * servidor. Solo con {@code -Dheraldia.perfil=true}; sin la propiedad, {@link #ACTIVO} es una constante falsa y
 * {@link #inicio()} y {@link #fin} no hacen nada (el JIT quita las llamadas): coste cero en el servidor de verdad.
 * <p>Uso: {@code long t0 = Perfil.inicio(); ...; Perfil.fin(Perfil.Tramo.LADERA, t0);}. Lo lee
 * {@code tools/smoke/coste_generacion.py} de la línea «Heraldia: perfil: {...}» (JSON).
 */
public final class Perfil {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PROPIEDAD = "heraldia.perfil";
	public static final boolean ACTIVO = Boolean.getBoolean(PROPIEDAD);

	/** Tramos medidos (el nombre en minúsculas es la clave del JSON). */
	public enum Tramo {
		/** El mixin de las reglas de colocación entero (tryGenerateStructure: aldeas, únicas, medianas, minas, ajenas). */
		REGLAS,
		/** Lo mismo en /locate y los mapas (StructureCheck.canCreateStructure). */
		REGLAS_LOCATE,
		/** Estructuras de otros mods junto a una aldea o una única ({@link ZonaAjenas}). */
		ZONA_AJENAS,
		/** Distancia mínima entre únicas (UniqueSeparation.blocked). */
		SEPARACION_UNICAS,
		/** Regla de colocación de las medianas ({@link Medianas#rechaza}). */
		MEDIANAS,
		/** Regla de colocación de las entradas a mina (Minas.rechaza). */
		MINAS,
		/** Búsqueda de la ladera de una entrada a mina (Ladera.buscar). */
		LADERA,
		/** La misma búsqueda, adelantada en otros hilos para /locate (minas/LocateParalelo; no cuenta en LADERA). */
		LADERA_ANTICIPADA,
		/** Punto de inicio de una aldea (el jigsaw de vanilla más lo propio). */
		ALDEA,
		/** Búsqueda de la orilla y colocación del puerto de una aldea de costa. */
		ORILLA,
		/** Rasgo de los caminos entre aldeas, por chunk. */
		CAMINOS,
		/** Regla de colocación de los faros y naufragios (costa/Costa: la de las minas con su familia). */
		COSTA,
		/** Búsqueda de la orilla de un faro o un naufragio (costa/Orilla). */
		COSTA_ORILLA
	}

	/** Contadores de un perfil (instancia aparte para poder probarlos sin la propiedad del sistema). */
	public static final class Contadores {
		private final boolean activo;
		private final LongAdder[] n = new LongAdder[Tramo.values().length], ns = new LongAdder[Tramo.values().length];
		private final AtomicLong[] max = new AtomicLong[Tramo.values().length];

		public Contadores(boolean activo) {
			this.activo = activo;
			for (int i = 0; i < n.length; i++) {
				n[i] = new LongAdder();
				ns[i] = new LongAdder();
				max[i] = new AtomicLong();
			}
		}

		public boolean activo() {
			return activo;
		}

		public long inicio() {
			return activo ? System.nanoTime() : 0L;
		}

		public void fin(Tramo t, long t0) {
			if (activo) {
				anotar(t, System.nanoTime() - t0);
			}
		}

		/** Suma una medida ya tomada (en ns). Sin efecto si el perfil no está activo. */
		public void anotar(Tramo t, long dur) {
			if (!activo) {
				return;
			}
			int i = t.ordinal();
			n[i].increment();
			ns[i].add(dur);
			max[i].accumulateAndGet(dur, Math::max);
		}

		public long veces(Tramo t) {
			return n[t.ordinal()].sum();
		}

		public long nanos(Tramo t) {
			return ns[t.ordinal()].sum();
		}

		public long maximo(Tramo t) {
			return max[t.ordinal()].get();
		}

		/**
		 * JSON de una línea con cada tramo medido: {"ladera":{"n":12,"total_ms":3.4,"media_us":283.3,"max_us":900.0},...}.
		 * Solo lee: llamarlo varias veces da lo mismo.
		 */
		public String json() {
			StringBuilder sb = new StringBuilder("{");
			for (Tramo t : Tramo.values()) {
				long k = veces(t);
				if (k == 0) {
					continue;
				}
				if (sb.length() > 1) {
					sb.append(',');
				}
				long total = nanos(t);
				sb.append(String.format(Locale.ROOT, "\"%s\":{\"n\":%d,\"total_ms\":%.3f,\"media_us\":%.1f,\"max_us\":%.1f}",
						t.name().toLowerCase(Locale.ROOT), k, total / 1e6, total / 1e3 / k, maximo(t) / 1e3));
			}
			return sb.append('}').toString();
		}
	}

	private static final Contadores CONTADORES = new Contadores(ACTIVO);

	private Perfil() {
	}

	/** Una línea en Heraldia.onInitialize: sin la propiedad no registra nada. */
	public static void registrar() {
		if (!ACTIVO) {
			return;
		}
		LOGGER.info("Heraldia: perfil de la generación activado (-D{}=true)", PROPIEDAD);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> volcar());
	}

	public static long inicio() {
		return ACTIVO ? System.nanoTime() : 0L;
	}

	public static void fin(Tramo t, long t0) {
		if (ACTIVO) {
			CONTADORES.anotar(t, System.nanoTime() - t0);
		}
	}

	/** Los contadores globales (para /heraldia o las pruebas). */
	public static Contadores contadores() {
		return CONTADORES;
	}

	/** Escribe el perfil acumulado en el log (si está activo). */
	public static void volcar() {
		if (ACTIVO) {
			LOGGER.info("Heraldia: perfil: {}", CONTADORES.json());
		}
	}
}
