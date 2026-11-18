package io.github.albertosa23.heraldia.huts;

import java.util.Set;

/**
 * Pure logic of the wizard huts (T43, no game classes, for the tests). Everything comes from the world seed and
 * the wizard's chunk (it is a still entity, without AI, that the template puts in the center of its hut: the chunk does not change),
 * so the same hut always gives the same and nothing needs to be saved separately. What has been decided is also saved
 * in the wizard's own tags, so a configuration change does not change an already seen hut.
 */
public final class Decision {
	/** Tag of the template wizard (mediums/wizard_hut.TAG_WIZARD). */
	public static final String TAG = "heraldia_mago";
	/** Decision already made (on the wizard): benign or evil. */
	public static final String BENIGN = TAG + ".benigno", EVIL_UNREVEALED = TAG + ".malvado";
	/** The wizard already has its generated name. */
	public static final String NAMED = TAG + ".nombrado";
	/** The wizard has already been revealed (set just before removing it: it is never revealed twice). */
	public static final String REVEALED = TAG + ".revelado";
	/** Tag of the evoker it turns into (mediums/wizard_hut.TAG_EVIL; the advancement checks it). */
	public static final String EVIL = "heraldia_mago_malvado";
	/** Its loot carries the prize (on the evoker). */
	public static final String PREMIUM = EVIL + ".premium";
	/** The vexes it summons when revealed. */
	public static final String VEX = "heraldia_mago_vex";
	private static final long EVIL_SALT = 0x6D61676F5F6D616CL, PREMIUM_SALT = 0x7072656D69756D21L, NAME_SALT = 0x6E6F6D6272653F21L;

	/** State of a wizard according to its tags. */
	public enum State {
		UNDECIDED, BENIGN, EVIL, REVEALED
	}

	private Decision() {
	}

	/** Is it a hut wizard? (early exit: almost no entity has tags). */
	public static boolean isWizard(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(TAG);
	}

	public static State state(Set<String> tags) {
		if (tags.contains(REVEALED)) {
			return State.REVEALED;
		}
		if (tags.contains(EVIL_UNREVEALED)) {
			return State.EVIL;
		}
		return tags.contains(BENIGN) ? State.BENIGN : State.UNDECIDED;
	}

	/** Number from 0 to 99 of a hut (seed, wizard's chunk and salt). */
	static int roll(long seed, int chunkX, int chunkZ, long salt) {
		long h = merge(seed ^ salt);
		h = merge(h ^ ((long) chunkX * 0x9E3779B97F4A7C15L));
		h = merge(h ^ ((long) chunkZ * 0xC2B2AE3D27D4EB4FL));
		return (int) Long.remainderUnsigned(h, 100);
	}

	/** SplitMix64: a cheap, well-spread mix. */
	static long merge(long z) {
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}

	/** Is this hut's wizard evil? {@code prob} in % (0: never; 100: always). */
	public static boolean evil(long seed, int chunkX, int chunkZ, int prob) {
		return roll(seed, chunkX, chunkZ, EVIL_SALT) < Math.clamp(prob, 0, 100);
	}

	/** Does the loot of this hut's Evil Wizard carry the prize? {@code prob} in %. */
	public static boolean premium(long seed, int chunkX, int chunkZ, int prob) {
		return roll(seed, chunkX, chunkZ, PREMIUM_SALT) < Math.clamp(prob, 0, 100);
	}

	/** Indices (name, nickname) of this hut's wizard, out of the possible {@code names} and {@code nicknames}. */
	public static int[] name(long seed, int chunkX, int chunkZ, int names, int nicknames) {
		long h = merge(merge(seed ^ NAME_SALT) ^ ((long) chunkX << 32 | (chunkZ & 0xFFFFFFFFL)));
		return new int[] {(int) Long.remainderUnsigned(h, Math.max(1, names)),
				(int) Long.remainderUnsigned(h >>> 17, Math.max(1, nicknames))};
	}
}
