package io.github.albertosa23.heraldia.common;

import java.util.Set;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;

/**
 * Anchored template mobs (tag {@link #TAG}, the generator's core.ANCHORED_TAG: the final guardians and the
 * zombies and skeletons of the templates). Every time the world loads one ({@code ENTITY_LOAD}: when the template
 * is placed, when the generated chunk is promoted and on every chunk load):
 * <ul>
 * <li>it picks up no items: {@code finalizeSpawn} of zombies and skeletons rolls {@code CanPickUpLoot} without looking at the NBT, and
 * with it they would swap their gear or keep the loot the player drops;</li>
 * <li>it does not wander: {@code RandomStrollGoal.canUse} requires {@code getNoActionTime() < 100}, and a persistent mob with no
 * players nearby only wanders those first 100 ticks (up to 10 blocks, sometimes out of its room) after each load,
 * because {@code noActionTime} is not saved. With {@link #STILL} it does not wander; it sees, chases and attacks as always (that
 * does not look at {@code noActionTime}), and when it takes damage the game sets it to 0 and it moves normally again.</li>
 * </ul>
 * No mixin: a Fabric API event with an early exit (tag set, almost always empty); nothing per tick.
 * Drowned also have two goals that move them without looking at {@code noActionTime} (going to water by day, to the shore
 * by night): {@code DrownedWaterMixin} and {@code DrownedBeachMixin} switch them off with {@link #still(Mob)}. The same
 * for magma cubes and slimes, which hop forever instead of strolling ({@code CubeMobJumpMixin}), and for piglins and
 * piglin brutes, whose brain picks walk targets without looking at {@code noActionTime} ({@code PiglinStrollMixin}).
 */
public final class Anchoring {
	/** Tag of the anchored mobs; the same as core.ANCHORED_TAG. */
	public static final String TAG = "heraldia_anclado";
	/** {@code noActionTime} from which {@code RandomStrollGoal} no longer activates (26.3). */
	public static final int STILL = 100;

	private Anchoring() {
	}

	public static void register() {
		ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> onLoad(entity));
	}

	static void onLoad(Entity entity) {
		if (!anchored(entity.entityTags()) || !(entity instanceof Mob mob)) {
			return;
		}
		mob.setCanPickUpLoot(false);
		if (mob.getTarget() == null) {
			mob.setNoActionTime(still(mob.getNoActionTime()));
		}
	}

	/** Anchored mob that has not entered combat yet (no target and no damage since it loaded)? */
	public static boolean still(Mob mob) {
		return anchored(mob.entityTags()) && still(mob.getTarget() != null, mob.getNoActionTime());
	}

	/** No target and no recent damage (damage sets {@code noActionTime} to 0). */
	static boolean still(boolean withTarget, int noActionTime) {
		return !withTarget && noActionTime >= STILL;
	}

	/** Does it carry the anchored tag? */
	static boolean anchored(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(TAG);
	}

	/** {@code noActionTime} at which the mob no longer wanders (does not lower it if it was already higher). */
	static int still(int noActionTime) {
		return Math.max(noActionTime, STILL);
	}
}
