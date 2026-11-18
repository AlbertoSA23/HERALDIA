package io.github.albertosa23.heraldia.difficulty;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.loot.Restock;
import java.util.List;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.loot.v3.LootTableEvents;
import net.minecraft.core.Holder;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.Enemy;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootTable;
import org.jspecify.annotations.Nullable;

/**
 * Configurable difficulty of Heraldia's mobs (options dificultad.*). Own attribute modifiers, with their
 * identifier ({@link #HEALTH}, {@link #DAMAGE}, {@link #PLAYERS}), added to those others set (the bosses, the
 * game, other mods) without touching them:
 * <ul>
 * <li>on every {@code ENTITY_LOAD} (when the template is placed, when the chunk generates and on every load) those of the
 * level in use are set, or removed on normal: so they apply to already generated mobs and are recomputed if the option changes (the
 * configuration is read at startup; /heraldia reload recomputes them on already loaded mobs with {@link #apply}). Setting them
 * twice changes nothing ({@code addOrReplacePermanentModifier}).</li>
 * <li>with dificultad.escalar_por_jugadores, players within 32 blocks are counted when it takes a hit (not per tick).</li>
 * <li>with dificultad.escalar_botin, the loot of Heraldia's chests (tables cofres/, unicas/, medianas/, minas/) comes with the
 * amount of its simple stackable items multiplied ({@link ModDifficulty.Tier#loot}).</li>
 * </ul>
 * Cheap early exit (the mob's tags, almost always empty); no mixins.
 */
public final class MobDifficulty {
	public static final Identifier HEALTH = Heraldia.id("dificultad_vida"), DAMAGE = Heraldia.id("dificultad_dano"),
			PLAYERS = Heraldia.id("dificultad_jugadores");

	private MobDifficulty() {
	}

	public static void register() {
		ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> onLoad(entity));
		ServerLivingEntityEvents.AFTER_DAMAGE.register((entity, source, base, taken, blocked) -> onHurt(entity));
		LootTableEvents.MODIFY_DROPS.register(MobDifficulty::loot);
	}

	static void onLoad(Entity entity) {
		apply(entity);
	}

	/**
	 * Sets on the mob the modifiers of the configuration in use (recomputes them if it changed): when it loads and, after
	 * /heraldia reload, on all the already loaded ones. True if it is a Heraldia mob the difficulty applies to.
	 */
	public static boolean apply(Entity entity) {
		if (!(entity instanceof Mob mob) || !ModDifficulty.applies(mob.entityTags(), mob instanceof Enemy)) {
			return false;
		}
		double before = mob.getMaxHealth();
		adjust(mob.getAttribute(Attributes.MAX_HEALTH), mob.getAttribute(Attributes.ATTACK_DAMAGE), HeraldiaConfig.get());
		adjustHealth(mob, before);
		return true;
	}

	/** The health and damage modifiers of {@code cfg}'s level (and without the per-player extra if disabled). */
	static void adjust(@Nullable AttributeInstance health, @Nullable AttributeInstance damage, HeraldiaConfig cfg) {
		ModDifficulty.Tier tier = ModDifficulty.Tier.of(cfg.getString("dificultad.nivel"));
		put(health, HEALTH, tier.healthMod());
		put(damage, DAMAGE, tier.damageMod());
		if (!cfg.getBool("dificultad.escalar_por_jugadores")) {
			put(health, PLAYERS, 0);
		}
	}

	static void onHurt(LivingEntity entity) {
		if (!(entity instanceof Mob mob) || !ModDifficulty.applies(mob.entityTags(), mob instanceof Enemy) || !mob.isAlive()
				|| !HeraldiaConfig.get().getBool("dificultad.escalar_por_jugadores")) {
			return;
		}
		double r2 = ModDifficulty.PLAYER_RADIUS * ModDifficulty.PLAYER_RADIUS;
		int near = 0;
		for (Player p : mob.level().players()) {
			if (!p.isSpectator() && p.isAlive() && p.distanceToSqr(mob) <= r2) {
				near++;
			}
		}
		double before = mob.getMaxHealth();
		put(mob.getAttribute(Attributes.MAX_HEALTH), PLAYERS, ModDifficulty.extraPlayers(near));
		adjustHealth(mob, before);
	}

	/** Sets (or removes, with amount 0) the permanent modifier {@code id}; idempotent. */
	public static void put(@Nullable AttributeInstance attr, Identifier id, double amount) {
		if (attr == null) {
			return;
		}
		if (amount == 0) {
			attr.removeModifier(id);
			return;
		}
		AttributeModifier actual = attr.getModifier(id);
		if (actual == null || actual.amount() != amount || actual.operation() != AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL) {
			attr.addOrReplacePermanentModifier(new AttributeModifier(id, amount, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL));
		}
	}

	private static void adjustHealth(Mob mob, double before) {
		double after = mob.getMaxHealth();
		if (after != before) {
			mob.setHealth(ModDifficulty.readjustHealth(mob.getHealth(), before, after));
		}
	}

	private static void loot(Holder<LootTable> table, net.minecraft.world.level.storage.loot.LootContext context, List<ItemStack> drops) {
		if (drops.isEmpty() || !isChestLoot(table.unwrapKey().orElse(null))) {
			return;
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		double m = ModDifficulty.Tier.of(cfg.getString("dificultad.nivel")).loot;
		if (m == 1 || !cfg.getBool("dificultad.escalar_botin")) {
			return;
		}
		for (ItemStack stack : drops) {
			if (stack.isStackable() && stack.getComponentsPatch().isEmpty()) {
				stack.setCount(ModDifficulty.amount(stack.getCount(), m, stack.getMaxStackSize(), context.getRandom().nextDouble()));
			}
		}
	}

	/**
	 * Heraldia chest tables (villages, mediums, mine entrances and uniques): the same that get restocked
	 * ({@link Restock#tableRestocks}); not those of the guardians, trophies, keys or trades.
	 */
	static boolean isChestLoot(@Nullable ResourceKey<LootTable> key) {
		return key != null && Restock.tableRestocks(key.identifier().toString());
	}

	/** For the tests: the amount of an attribute's modifier (0 if it has none). */
	static double amount(@Nullable AttributeInstance attr, Identifier id) {
		AttributeModifier m = attr == null ? null : attr.getModifier(id);
		return m == null ? 0 : m.amount();
	}
}
