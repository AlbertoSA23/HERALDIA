package io.github.albertosa23.heraldia.common;

import java.util.Locale;
import java.util.concurrent.atomic.AtomicLong;
import java.util.concurrent.atomic.LongAdder;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Generation profile (optional): accumulated time of Heraldia's most expensive sections, dumped to the log when the
 * server stops. Only with {@code -Dheraldia.perfil=true}; without the property, {@link #ACTIVE} is a false constant and
 * {@link #start()} and {@link #end} do nothing (the JIT removes the calls): zero cost on the real server.
 * <p>Use: {@code long t0 = Profiler.start(); ...; Profiler.end(Profiler.Segment.HILLSIDE, t0);}. It is read by
 * {@code tools/smoke/generation_cost.py} from the line "Heraldia: perfil: {...}" (JSON).
 */
public final class Profiler {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PROPERTY = "heraldia.perfil";
	public static final boolean ACTIVE = Boolean.getBoolean(PROPERTY);

	/** Measured sections (their {@link #id} is the JSON key). */
	public enum Segment {
		/** The whole placement rules mixin (tryGenerateStructure: villages, uniques, mediums, mines, foreign). */
		RULES("reglas"),
		/** The same in /locate and the maps (StructureCheck.canCreateStructure). */
		RULES_LOCATE("reglas_locate"),
		/** Other mods' structures next to a village or a unique ({@link ForeignZone}). */
		FOREIGN_ZONE("zona_ajenas"),
		/** Minimum distance between uniques (UniqueSeparation.blocked). */
		UNIQUE_SEPARATION("separacion_unicas"),
		/** Placement rule of the mediums ({@link MediumStructures#rejects}). */
		MEDIUMS("medianas"),
		/** Placement rule of the mine entrances (Mines.rejects). */
		MINES("minas"),
		/** Hillside search of a mine entrance (Hillside.search). */
		HILLSIDE("ladera"),
		/** The same search, run ahead on other threads for /locate (mines/ParallelLocate; does not count in HILLSIDE). */
		HILLSIDE_EARLY("ladera_anticipada"),
		/** Start point of a village (vanilla's jigsaw plus our own). */
		VILLAGE("aldea"),
		/** Terrain fit of a village when it is created (villages/TerrainFit: which pieces a villager can walk to). */
		VILLAGE_TERRAIN("aldea_terreno"),
		/** Shore search and port placement of a coastal village. */
		SHORE("orilla"),
		/** Feature of the roads between villages, per chunk. */
		ROADS("caminos"),
		/** Placement rule of the lighthouses and shipwrecks (coast/Coast: the mines' one with its family). */
		COAST("costa"),
		/** Shore search of a lighthouse or a shipwreck (coast/Shoreline). */
		COAST_SHORE("costa_orilla"),
		/** The ambient effects' check, every 5 s with players online (ambience/Ambience: bell, siren, mine drips). */
		AMBIENCE("ambiente");

		/** Saved id (JSON key of the report): never renamed. */
		public final String id;

		Segment(String id) {
			this.id = id;
		}
	}

	/** Counters of a profile (separate instance so they can be tested without the system property). */
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

		/** Adds an already taken measurement (in ns). No effect if the profile is not active. */
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
		 * One-line JSON with each measured section: {"ladera":{"n":12,"total_ms":3.4,"media_us":283.3,"max_us":900.0},...}.
		 * Read-only: calling it several times gives the same.
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
						t.id, k, total / 1e6, total / 1e3 / k, maximum(t) / 1e3));
			}
			return sb.append('}').toString();
		}
	}

	private static final Counters COUNTERS = new Counters(ACTIVE);

	private Profiler() {
	}

	/** One line in Heraldia.onInitialize: without the property it registers nothing. */
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

	/** The global counters (for /heraldia or the tests). */
	public static Counters counters() {
		return COUNTERS;
	}

	/** Writes the accumulated profile to the log (if active). */
	public static void dump() {
		if (ACTIVE) {
			LOGGER.info("Heraldia: perfil: {}", COUNTERS.json());
		}
	}
}
