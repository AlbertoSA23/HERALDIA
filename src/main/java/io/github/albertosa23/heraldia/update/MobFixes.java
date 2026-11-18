package io.github.albertosa23.heraldia.update;

import io.github.albertosa23.heraldia.update.Fixes.Fix;
import io.github.albertosa23.heraldia.update.Fixes.Effect;
import java.util.List;
import java.util.Set;

/**
 * Initial fixes for template mobs (T46): bugs already fixed in the code that may remain in worlds
 * generated with earlier versions (see CHANGELOG and docs/LESSONS.md). Over a minimal view of the mob ({@link Mob}), so the
 * logic is tested without the game; {@code Updater} builds it over the real mob.
 * <ol>
 * <li>{@code marcas}: the guardians and named mobs of 0.1.0 had no tags; they are recognized by their
 * translatable name {@code heraldia.*} (and persistence) and get today's: {@code heraldia_anclado} (they do not wander out of their
 * room —the "drift"— nor pick up items), {@code heraldia_adulto} if they are of the zombie family and
 * {@code heraldia_guardian} if their name is a guardian's (boss phases, bar and reinforcements).</li>
 * <li>{@code bebes}: a template zombie, husk, drowned, zombie villager or zombified piglin that spawned as a baby becomes an adult
 * (and if it was riding a chicken, it gets off and the jockey chicken is removed).</li>
 * <li>{@code nautilos}: a template drowned riding a zombie nautilus gets off and the nautilus is removed (if it has no
 * name or other rider).</li>
 * <li>{@code recoger}: a template mob that can pick up items can no longer do so ({@code CanPickUpLoot}).</li>
 * <li>{@code armas}: a template drowned with a plain trident or fishing rod, or a zombie with a plain iron shovel, spear or
 * sword, may have lost its template's weapon; which one it was is unknown, so it is only counted in
 * the report (warning), without changing it.</li>
 * </ol>
 */
public final class MobFixes {
	public static final String ADULT = "heraldia_adulto", ANCHORED = "heraldia_anclado", GUARDIAN = "heraldia_guardian";
	/** Types that can spawn as babies when placed (the generator's core.BABY_ZOMBIE). */
	static final Set<String> ZOMBIES = Set.of("zombie", "husk", "drowned", "zombie_villager", "zombified_piglin");
	static final Set<String> DROWNED_WEAPONS = Set.of("trident", "fishing_rod");
	static final Set<String> ZOMBIE_WEAPONS = Set.of("iron_shovel", "iron_sword", "iron_spear");

	/** What the fixes need to see and touch of a mob. */
	public interface Mob {
		/** Type without namespace ("zombie"). */
		String type();

		Set<String> tags();

		void tagIt(String tag);

		/** Key of its name if it is translatable, or null. */
		String nameKey();

		boolean persistent();

		boolean baby();

		void makeAdult();

		/** Type of what it rides, without namespace, or null. */
		String mount();

		/** Does the mount have a name or another rider? (then it is not removed) */
		boolean ownMount();

		/** Gets off and removes the mount. */
		void removeMount();

		boolean picksUp();

		void noPickup();

		/** Main-hand item without namespace, or null. */
		String weapon();

		/** Does the weapon have a name or enchantments? (then it is the template's) */
		boolean specialWeapon();
	}

	private MobFixes() {
	}

	/** Is it a mob from a Heraldia template? It carries one of its tags, or it is persistent with a heraldia.* name. */
	public static boolean fromTemplate(Mob m) {
		Set<String> t = m.tags();
		if (!t.isEmpty() && (t.contains(ADULT) || t.contains(ANCHORED) || t.contains(GUARDIAN))) {
			return true;
		}
		return m.persistent() && heraldiaName(m.nameKey());
	}

	static boolean heraldiaName(String key) {
		return key != null && key.startsWith("heraldia.");
	}

	/** Is it a guardian's name? (heraldia.unicas.castillo.guardian, heraldia.ciudadela.guardian...) */
	static boolean guardianName(String key) {
		return heraldiaName(key) && key.contains("guardian");
	}

	static Effect marks(Mob m, boolean dryRun) {
		if (!heraldiaName(m.nameKey()) || !m.persistent()) {
			return Effect.NOTHING;
		}
		boolean missing = !m.tags().contains(ANCHORED) || ZOMBIES.contains(m.type()) && !m.tags().contains(ADULT)
				|| guardianName(m.nameKey()) && !m.tags().contains(GUARDIAN);
		if (!missing) {
			return Effect.NOTHING;
		}
		if (!dryRun) {
			m.tagIt(ANCHORED);
			if (ZOMBIES.contains(m.type())) {
				m.tagIt(ADULT);
			}
			if (guardianName(m.nameKey())) {
				m.tagIt(GUARDIAN);
			}
		}
		return Effect.CHANGES;
	}

	static Effect babies(Mob m, boolean dryRun) {
		if (!ZOMBIES.contains(m.type()) || !m.baby()) {
			return Effect.NOTHING;
		}
		if (!dryRun) {
			m.makeAdult();
			if ("chicken".equals(m.mount()) && !m.ownMount()) {
				m.removeMount();
			}
		}
		return Effect.CHANGES;
	}

	static Effect nautiluses(Mob m, boolean dryRun) {
		if (!"drowned".equals(m.type()) || !"zombie_nautilus".equals(m.mount()) || m.ownMount()) {
			return Effect.NOTHING;
		}
		if (!dryRun) {
			m.removeMount();
		}
		return Effect.CHANGES;
	}

	static Effect collect(Mob m, boolean dryRun) {
		if (!m.picksUp()) {
			return Effect.NOTHING;
		}
		if (!dryRun) {
			m.noPickup();
		}
		return Effect.CHANGES;
	}

	static Effect weapons(Mob m, boolean dryRun) {
		String a = m.weapon();
		if (a == null || m.specialWeapon()) {
			return Effect.NOTHING;
		}
		boolean suspicious = "drowned".equals(m.type()) ? DROWNED_WEAPONS.contains(a)
				: ZOMBIES.contains(m.type()) && !"zombified_piglin".equals(m.type()) && ZOMBIE_WEAPONS.contains(a);
		return suspicious ? Effect.NOTICE : Effect.NOTHING;
	}

	/** The template mob fixes (they only run on those {@link #fromTemplate} recognizes). */
	public static final Fixes.Ledger<Mob> LEDGER = new Fixes.Ledger<>(List.of(
			new Fix<>(1, "marcas", Fixes.Scope.ENTITY, MobFixes::marks),
			new Fix<>(2, "bebes", Fixes.Scope.ENTITY, MobFixes::babies),
			new Fix<>(3, "nautilos", Fixes.Scope.ENTITY, MobFixes::nautiluses),
			new Fix<>(4, "recoger", Fixes.Scope.ENTITY, MobFixes::collect),
			new Fix<>(5, "armas", Fixes.Scope.ENTITY, MobFixes::weapons)));
}
