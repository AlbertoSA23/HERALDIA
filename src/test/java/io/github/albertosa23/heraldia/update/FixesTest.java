package io.github.albertosa23.heraldia.update;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.update.Fixes.Effect;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Fix registry: order, mark, dry-run mode and idempotency of each initial mob fix. */
class FixesTest {
	/** A fake mob with what the fixes look at. */
	static final class Fake implements MobFixes.Mob {
		String type = "zombie", name, mount, weapon;
		Set<String> tags = new HashSet<>();
		boolean persistent = true, baby, picksUp, special, ownMount, mountRemoved;

		@Override public String type() { return type; }
		@Override public Set<String> tags() { return tags; }
		@Override public void tagIt(String e) { tags.add(e); }
		@Override public String nameKey() { return name; }
		@Override public boolean persistent() { return persistent; }
		@Override public boolean baby() { return baby; }
		@Override public void makeAdult() { baby = false; }
		@Override public String mount() { return mount; }
		@Override public boolean ownMount() { return ownMount; }
		@Override public void removeMount() { mount = null; mountRemoved = true; }
		@Override public boolean picksUp() { return picksUp; }
		@Override public void noPickup() { picksUp = false; }
		@Override public String weapon() { return weapon; }
		@Override public boolean specialWeapon() { return special; }
	}

	/** A 0.1.0 guardian: translatable name, persistent, no tags, baby, on a chicken, picking up items. */
	static Fake oldGuardian() {
		Fake f = new Fake();
		f.name = "heraldia.unicas.castillo.guardian";
		f.baby = true;
		f.mount = "chicken";
		f.picksUp = true;
		return f;
	}

	@Test
	void recognizesTemplateMobs() {
		assertTrue(MobFixes.fromTemplate(oldGuardian()));
		Fake newValue = new Fake();
		newValue.persistent = false;
		newValue.tags.add("heraldia_anclado");
		assertTrue(MobFixes.fromTemplate(newValue));
		Fake vanilla = new Fake();
		vanilla.name = "entity.minecraft.zombie";      // with a name, but not Heraldia's
		assertFalse(MobFixes.fromTemplate(vanilla));
		Fake notPersisted = oldGuardian();
		notPersisted.persistent = false;
		assertFalse(MobFixes.fromTemplate(notPersisted));
	}

	@Test
	void allFixesAreIdempotent() {
		Fake g = oldGuardian();
		Map<String, Effect> first = MobFixes.LEDGER.execute(g, 0, false, true);
		assertEquals(List.of("marcas", "bebes", "recoger"), List.copyOf(first.keySet()));
		assertTrue(g.tags.containsAll(Set.of("heraldia_anclado", "heraldia_adulto", "heraldia_guardian")));
		assertFalse(g.baby);
		assertTrue(g.mountRemoved);
		assertFalse(g.picksUp);
		// the second time (forced, like /heraldia update repair) there is nothing left to change
		assertTrue(MobFixes.LEDGER.execute(g, 0, false, true).isEmpty());
		assertTrue(MobFixes.LEDGER.execute(g, 0, false, true).isEmpty());
	}

	@Test
	void dryRunChangesNothing() {
		Fake g = oldGuardian();
		Map<String, Effect> dryRun = MobFixes.LEDGER.execute(g, 0, true, true);
		assertEquals(3, dryRun.size());
		assertTrue(g.tags.isEmpty());
		assertTrue(g.baby);
		assertFalse(g.mountRemoved);
		assertTrue(g.picksUp);
		assertEquals(dryRun, MobFixes.LEDGER.execute(g, 0, true, true));
	}

	@Test
	void withLevelMarkTheyDoNotRunAgain() {
		Fake g = oldGuardian();
		int tier = MobFixes.LEDGER.tier();
		assertEquals(5, tier);
		assertTrue(MobFixes.LEDGER.pending(0));
		assertFalse(MobFixes.LEDGER.pending(tier));
		assertTrue(MobFixes.LEDGER.execute(g, tier, false, false).isEmpty());
		assertTrue(g.baby);                                // with the mark it has not been touched
		// with an intermediate mark only the higher-numbered ones run
		Map<String, Effect> e = MobFixes.LEDGER.execute(g, 2, false, false);
		assertEquals(Set.of("recoger"), e.keySet());
		assertTrue(g.baby);
	}

	@Test
	void nautilusesAndWeapons() {
		Fake a = new Fake();
		a.type = "drowned";
		a.tags.add("heraldia_adulto");
		a.mount = "zombie_nautilus";
		a.weapon = "trident";
		Map<String, Effect> e = MobFixes.LEDGER.execute(a, 0, false, true);
		assertEquals(Effect.CHANGES, e.get("nautilos"));
		assertEquals(Effect.NOTICE, e.get("armas"));
		assertTrue(a.mountRemoved);
		assertEquals("trident", a.weapon);                  // the weapon is not changed: only a warning
		assertEquals(Map.of("armas", Effect.NOTICE), MobFixes.LEDGER.execute(a, 0, false, true));
		// a named or enchanted trident is the template's
		a.special = true;
		assertTrue(MobFixes.LEDGER.execute(a, 0, false, true).isEmpty());
		// a named nautilus (a player's) is not removed
		Fake b = new Fake();
		b.type = "drowned";
		b.tags.add("heraldia_adulto");
		b.mount = "zombie_nautilus";
		b.ownMount = true;
		assertTrue(MobFixes.LEDGER.execute(b, 0, false, true).isEmpty());
	}

	@Test
	void namedSkeletonIsOnlyAnchored() {
		Fake s = new Fake();
		s.type = "skeleton";
		s.name = "heraldia.catedral.guardian";
		s.baby = false;
		MobFixes.LEDGER.execute(s, 0, false, true);
		assertEquals(Set.of("heraldia_anclado", "heraldia_guardian"), s.tags);
	}

	@Test
	void registrySortedWithoutRepeatedNumbers() {
		Fixes.Ledger<Object> r = new Fixes.Ledger<>(List.of(
				new Fixes.Fix<>(3, "c", Fixes.Scope.CHUNK, (o, p) -> Effect.NOTHING),
				new Fixes.Fix<>(1, "a", Fixes.Scope.CHUNK, (o, p) -> Effect.CHANGES)));
		assertEquals("a", r.fixes().get(0).id());
		assertEquals(3, r.tier());
		assertEquals(0, new Fixes.Ledger<>(List.of()).tier());
		assertThrows(IllegalArgumentException.class, () -> new Fixes.Ledger<>(List.of(
				new Fixes.Fix<Object>(1, "a", Fixes.Scope.CHUNK, (o, p) -> Effect.NOTHING),
				new Fixes.Fix<Object>(1, "b", Fixes.Scope.CHUNK, (o, p) -> Effect.NOTHING))));
	}

	@Test
	void countPerFix() {
		Fixes.Tally c = new Fixes.Tally();
		c.add(Map.of("bebes", Effect.CHANGES));
		c.add(Map.of("armas", Effect.NOTICE));
		c.add(Map.of());
		assertEquals(3, c.checked());
		assertEquals(1, c.changes());
		assertEquals(1, c.byId().get("armas")[1]);
	}

	@Test
	void worldVersion() {
		// new world: generated with this version; old one without data: "anterior"
		assertEquals(new WorldVersion("0.2.0", "0.2.0", 5), WorldVersion.onStart(java.util.Optional.empty(), "0.2.0", 10, 1200, 5));
		assertEquals(new WorldVersion(WorldVersion.PREVIOUS, "0.2.0", 0), WorldVersion.onStart(java.util.Optional.empty(), "0.2.0", 90_000, 1200, 5));
		WorldVersion before = new WorldVersion("0.1.0", "0.1.5", 2);
		assertEquals(new WorldVersion("0.1.0", "0.2.0", 2), WorldVersion.onStart(java.util.Optional.of(before), "0.2.0", 9, 1200, 5));
		assertTrue(WorldVersion.backsOff(java.util.Optional.of(before), "0.1.2"));
		assertFalse(WorldVersion.backsOff(java.util.Optional.of(before), "0.2.0"));
	}
}
