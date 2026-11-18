package io.github.albertosa23.heraldia.caravans;

import io.github.albertosa23.heraldia.quests.Reputation;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import org.jspecify.annotations.Nullable;

/**
 * Wayfarers on the roads (pure logic, without the game): the people that pass along a road near a player, driven by the
 * caravan engine ({@link Caravans}: the same search for a stretch of road, the same {@link Journey}, the same goodbye and
 * cleanup). What kinds there are, which ones fit a zone, what each brings with it, what it sells and what attacking it
 * costs. Random numbers come in as arguments in [0, 1) so the tests can fix them.
 * <p>
 * The zone is the village family of the biome at the starting vertex (the biome tags {@code heraldia:<family>} that decide
 * the villages' style), or null outside all of them.
 */
public final class Wayfarers {
	public static final String ENABLED = "viajeros.activado", FREQUENCY = "viajeros.frecuencia", MAX_ACTIVE = "viajeros.max_activos";
	/** Tag of every wayfarer leader (the one whose death ends the encounter) and, after it, the role tags. */
	public static final String LEADER = "heraldia_caravana.viajero", SHEEP = "heraldia_caravana.oveja", DOG = "heraldia_caravana.perro",
			PARTNER = "heraldia_caravana.pareja";
	/** Village families (the biome tags heraldia:<family>), in the order they are tried. */
	public static final List<String> FAMILIES = List.of("llanuras", "bosque", "oscuro", "taiga", "nieve", "desierto", "sabana", "jungla",
			"pantano", "cerezos", "badlands", "costa");
	/** The pilgrim only walks if a monastery or a cathedral that really spawns is this close to the player (blocks). */
	public static final int SHRINE_RANGE = 3000;
	/** A wayfarer does not set off within this many blocks of another caravan or wayfarer on the road. */
	public static final int SPACING = 160;
	/** After its stretch, with a player this close it keeps walking (towards the village) instead of vanishing in sight. */
	public static final double LINGER_RADIUS = 32;
	/** ... for at most this long. */
	public static final int LINGER_TICKS = 60 * 20;
	/** The messenger walks this many times faster than a wandering trader. */
	public static final double MESSENGER_SPEED = 2.0;
	/** Reputation lost for hurting (once per player and encounter) or killing one of its animals. */
	public static final int ANIMAL_HIT = -2, ANIMAL_DEATH = -10;

	private Wayfarers() {
	}

	/** The kinds of wayfarer: its id (commands, options, texts), whether it only travels by day and its weight in the draw. */
	public enum Kind {
		PILGRIM("pilgrim", "peregrino", true, 2), SHEPHERD("shepherd", "pastor", true, 3), MESSENGER("messenger", "mensajero", true, 2),
		PATROL("patrol", "guardias", false, 3), HUNTER("hunter", "cazador", true, 3);

		/** The literal of the command (English). */
		public final String command;
		/** The id of its option ({@code viajeros.<id>.activado}) and of its texts ({@code heraldia.viajeros.<id>.*}). */
		public final String id;
		/** People who travel by day (the wandering trader drinks invisibility at night): the guards also patrol by night. */
		public final boolean byDay;
		final int weight;

		Kind(String command, String id, boolean byDay, int weight) {
			this.command = command;
			this.id = id;
			this.byDay = byDay;
			this.weight = weight;
		}

		public String option() {
			return "viajeros." + id + ".activado";
		}

		/** The tag of this kind's leader (besides {@link #LEADER}). */
		public String tag() {
			return LEADER + "." + id;
		}

		public static @Nullable Kind byCommand(String s) {
			for (Kind k : values()) {
				if (k.command.equals(s.toLowerCase(Locale.ROOT))) {
					return k;
				}
			}
			return null;
		}
	}

	/** Does this kind fit the zone? The shepherd needs pasture: not in desert, badlands, jungle or swamp. */
	public static boolean fits(Kind k, @Nullable String zone) {
		if (k != Kind.SHEPHERD || zone == null) {
			return true;
		}
		return !Set.of("desierto", "badlands", "jungla", "pantano").contains(zone);
	}

	/**
	 * Which wayfarer sets off: one of the {@code enabled} kinds that fits the zone and the hour (by day all of them; by night
	 * only the patrol) and, the pilgrim, only with a shrine to walk to. Weighted by {@link Kind#weight}; null if none fits.
	 */
	public static @Nullable Kind choose(Set<Kind> enabled, @Nullable String zone, boolean day, boolean shrine, double rng) {
		List<Kind> ok = new ArrayList<>();
		int total = 0;
		for (Kind k : Kind.values()) {
			if (enabled.contains(k) && fits(k, zone) && (day || !k.byDay) && (k != Kind.PILGRIM || shrine)) {
				ok.add(k);
				total += k.weight;
			}
		}
		double r = rng * total;
		for (Kind k : ok) {
			r -= k.weight;
			if (r < 0) {
				return k;
			}
		}
		return ok.isEmpty() ? null : ok.get(ok.size() - 1);
	}

	/** Sheep in the shepherd's flock: 3 to 5. */
	public static int flock(double rng) {
		return 3 + Math.min(2, (int) (rng * 3));
	}

	/** Wool colors of a flock by zone (vanilla dye ids), with their weights: mostly white, the rest as the sheep of the land. */
	static Object[][] wool(@Nullable String zone) {
		return switch (zone == null ? "" : zone) {
			case "nieve" -> new Object[][]{{"white", 6}, {"light_gray", 2}};
			case "taiga" -> new Object[][]{{"white", 4}, {"brown", 2}, {"gray", 1}, {"black", 1}};
			case "oscuro" -> new Object[][]{{"white", 3}, {"black", 2}, {"gray", 2}, {"brown", 1}};
			case "cerezos" -> new Object[][]{{"white", 5}, {"pink", 2}};
			case "sabana" -> new Object[][]{{"white", 4}, {"brown", 2}};
			case "costa" -> new Object[][]{{"white", 5}, {"light_gray", 2}};
			default -> new Object[][]{{"white", 6}, {"light_gray", 1}, {"gray", 1}, {"black", 1}, {"brown", 1}};
		};
	}

	/** The color of one sheep of the flock (a vanilla dye id). */
	public static String woolColor(@Nullable String zone, double rng) {
		Object[][] w = wool(zone);
		int total = 0;
		for (Object[] o : w) {
			total += (Integer) o[1];
		}
		double r = rng * total;
		for (Object[] o : w) {
			r -= (Integer) o[1];
			if (r < 0) {
				return (String) o[0];
			}
		}
		return (String) w[w.length - 1][0];
	}

	/** What the hunter brings back by zone: rabbit in open land, boar (pork) in the taiga and the dark forest, fowl in jungle and swamp. */
	public enum Prey {
		RABBIT("minecraft:rabbit", "minecraft:cooked_rabbit", "minecraft:rabbit_hide"),
		BOAR("minecraft:porkchop", "minecraft:cooked_porkchop", "minecraft:leather"),
		FOWL("minecraft:chicken", "minecraft:cooked_chicken", "minecraft:feather");

		/** In its hands, what it sells cooked and the by-product. */
		public final String raw, cooked, byproduct;

		Prey(String raw, String cooked, String byproduct) {
			this.raw = raw;
			this.cooked = cooked;
			this.byproduct = byproduct;
		}
	}

	public static Prey prey(@Nullable String zone) {
		return switch (zone == null ? "" : zone) {
			case "taiga", "oscuro" -> Prey.BOAR;
			case "jungla", "pantano" -> Prey.FOWL;
			default -> Prey.RABBIT;
		};
	}

	/** What the leader carries in its hands (a vanilla item id; the client shows it in its crossed arms). */
	public static @Nullable String held(Kind k, @Nullable String zone) {
		return switch (k) {
			case PILGRIM -> "minecraft:stick";            // the pilgrim's staff
			case SHEPHERD -> "minecraft:wheat";
			case MESSENGER -> "minecraft:paper";          // the letter
			case HUNTER -> prey(zone).raw;
			case PATROL -> null;
		};
	}

	/**
	 * One trade: {@code count} of {@code cost} (emeralds, or what it buys) for {@code amount} of {@code result}, at most
	 * {@code uses} times (the wayfarer passes once: it does not restock).
	 */
	public record Trade(String cost, int count, String result, int amount, int uses) {
	}

	/**
	 * What it sells. The pilgrim, the messenger and the guards do not trade (the messenger does not stop; the pilgrim carries
	 * nothing to sell; the guards are on duty). The shepherd and the hunter sell what their trade gives, cheap and in small
	 * amounts, like a village's novice: nothing that breaks the progression (no enchantments, netherite or elytra).
	 */
	public static List<Trade> trades(Kind k, @Nullable String zone, List<String> colors) {
		List<Trade> out = new ArrayList<>();
		if (k == Kind.SHEPHERD) {
			List<String> seen = new ArrayList<>();
			for (String c : colors) {
				if (!seen.contains(c) && seen.size() < 2) {
					seen.add(c);
					out.add(new Trade("minecraft:emerald", 1, "minecraft:" + c + "_wool", 2, 4));
				}
			}
			out.add(new Trade("minecraft:emerald", 1, "minecraft:cooked_mutton", 4, 2));
			out.add(new Trade("minecraft:wheat", 18, "minecraft:emerald", 1, 3));
		} else if (k == Kind.HUNTER) {
			Prey p = prey(zone);
			out.add(new Trade("minecraft:emerald", 1, p.cooked, 3, 3));
			out.add(new Trade("minecraft:emerald", 1, p.byproduct, p == Prey.BOAR ? 2 : 4, 2));
			out.add(new Trade("minecraft:emerald", 1, "minecraft:arrow", 8, 2));
			if (p == Prey.RABBIT) {
				out.add(new Trade("minecraft:emerald", 3, "minecraft:rabbit_foot", 1, 1));
			}
		}
		return out;
	}

	/** The role of one of its entities, from its tags: the leader is a person, the patrol's are guards, the rest animals. */
	public enum Role { PERSON, GUARD, ANIMAL }

	public static Role role(Set<String> tags, boolean golem) {
		if (golem) {
			return Role.GUARD;
		}
		return tags.contains(LEADER) ? Role.PERSON : Role.ANIMAL;
	}

	/**
	 * Reputation the attacker loses with the wayfarer's village of origin: as a villager (person) or a golem (guard) of the village,
	 * and less for its animals. A hit counts once per player and encounter; each death counts.
	 */
	public static int penalty(Role r, boolean death) {
		return switch (r) {
			case PERSON -> Reputation.attack(false, death);
			case GUARD -> Reputation.attack(true, death);
			case ANIMAL -> death ? ANIMAL_DEATH : ANIMAL_HIT;
		};
	}

	/** Entities an encounter brings at most (the leader and its companions): for the report and the tests. */
	public static int entities(Kind k, int sheep) {
		return switch (k) {
			case PILGRIM, MESSENGER -> 1;
			case SHEPHERD -> 1 + sheep;
			case PATROL, HUNTER -> 2;
		};
	}

	/**
	 * Does a wayfarer set off on this roll? Like a caravan ({@link Rules#outcome}): enabled, below its own limit, after the
	 * rest since the last one and with probability {@code rate} %.
	 */
	public static boolean outcome(boolean enabled, int active, int maxActive, long tick, long lastEnd, int rate, double rng) {
		return Rules.outcome(enabled, active, maxActive, tick, lastEnd, rate, rng);
	}

	/**
	 * Does the segment take the pilgrim towards its shrine at (sx, sz)? Its arrival is closer to the shrine than its start.
	 */
	public static boolean towards(Segment s, int sx, int sz) {
		int n = s.vertices() - 1;
		return Math.hypot(s.x(n) - sx, s.z(n) - sz) < Math.hypot(s.x(0) - sx, s.z(0) - sz);
	}
}
