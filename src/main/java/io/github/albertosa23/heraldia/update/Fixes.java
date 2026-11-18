package io.github.albertosa23.heraldia.update;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Per-version fix registry (T46), pure logic: each fix has a number (it grows with the versions; the highest is
 * this version's fix level), an id, its scope (entity or chunk) and an idempotent action that looks at the target
 * and, if needed, corrects it (in dry-run mode it only says whether it would change it). They are applied lazily, like
 * common/Anchoring: when each entity or chunk loads, those with a number greater than the mark it carries (none = 0) run and
 * the current level's mark is set on it, so each one runs only once per target; /heraldia update repair forces them
 * on what is loaded (without looking at the mark: that is why they have to be idempotent).
 * <p>To add one in a future version: the number after the last one, its id (text heraldia.arreglos.&lt;id&gt;) and its
 * idempotency test in {@code FixesTest}. The number of a published one is never changed.
 */
public final class Fixes {
	public enum Scope { ENTITY, CHUNK }

	/** What an action did (or would do) on a target. */
	public enum Effect {
		/** It was not needed. */
		NOTHING,
		/** It corrected it (or would, in dry-run mode). */
		CHANGES,
		/** Something is wrong that cannot be corrected on its own (counted in the report). */
		NOTICE
	}

	/** The action of a fix on a target of type T. Idempotent: after a CHANGES, the next one gives NOTHING. */
	@FunctionalInterface
	public interface Action<T> {
		Effect apply(T target, boolean dryRun);
	}

	public record Fix<T>(int number, String id, Scope scope, Action<T> action) {
	}

	/** The fixes of a scope, by number. */
	public static final class Ledger<T> {
		private final List<Fix<T>> fixes;

		public Ledger(List<Fix<T>> fixes) {
			List<Fix<T>> l = new ArrayList<>(fixes);
			l.sort(Comparator.comparingInt(Fix::number));
			for (int i = 1; i < l.size(); i++) {
				if (l.get(i).number() == l.get(i - 1).number()) {
					throw new IllegalArgumentException("dos arreglos con el número " + l.get(i).number());
				}
			}
			this.fixes = List.copyOf(l);
		}

		public List<Fix<T>> fixes() {
			return fixes;
		}

		/** The highest number (0 without fixes): the mark left on an already checked target. */
		public int tier() {
			return fixes.isEmpty() ? 0 : fixes.get(fixes.size() - 1).number();
		}

		/** Is a target with this mark missing any? */
		public boolean pending(int mark) {
			return mark < tier();
		}

		/**
		 * Runs on {@code target} the fixes with a number greater than {@code mark} (all if {@code force}). Returns
		 * the effect of each one that did not give NOTHING, in order.
		 */
		public Map<String, Effect> execute(T target, int mark, boolean dryRun, boolean force) {
			Map<String, Effect> out = new LinkedHashMap<>();
			for (Fix<T> a : fixes) {
				if (force || a.number() > mark) {
					Effect e = a.action().apply(target, dryRun);
					if (e != Effect.NOTHING) {
						out.put(a.id(), e);
					}
				}
			}
			return out;
		}
	}

	/** Counts the effects of many targets: {id: [changes, warnings]}, in the order they appear. */
	public static final class Tally {
		private final Map<String, int[]> byId = new LinkedHashMap<>();
		private int checked;

		public void add(Map<String, Effect> effects) {
			checked++;
			effects.forEach((id, e) -> byId.computeIfAbsent(id, k -> new int[2])[e == Effect.NOTICE ? 1 : 0]++);
		}

		public Map<String, int[]> byId() {
			return byId;
		}

		public int checked() {
			return checked;
		}

		public int changes() {
			return byId.values().stream().mapToInt(v -> v[0]).sum();
		}
	}

	private Fixes() {
	}
}
