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
 * Dificultad configurable de los mobs de Heraldia (opciones dificultad.*). Modificadores de atributo propios, con su
 * identificador ({@link #HEALTH}, {@link #DAMAGE}, {@link #PLAYERS}), que se suman a los que pongan otros (los jefes, el
 * juego, otros mods) sin tocarlos:
 * <ul>
 * <li>en cada {@code ENTITY_LOAD} (al colocarse la plantilla, al generarse el chunk y en cada carga) se ponen los del
 * nivel en uso, o se quitan en normal: así valen para los mobs ya generados y se recalculan si cambia la opción (la
 * configuración se lee al arrancar; /heraldia reload los recalcula en los mobs ya cargados con {@link #apply}). Ponerlos
 * dos veces no cambia nada ({@code addOrReplacePermanentModifier}).</li>
 * <li>con dificultad.escalar_por_jugadores, al recibir un golpe se cuenta a los jugadores a 32 bloques (no por tick).</li>
 * <li>con dificultad.escalar_botin, el botín de los cofres de Heraldia (tablas cofres/, unicas/, medianas/, minas/) sale con la
 * cantidad de sus objetos sencillos apilables multiplicada ({@link ModDifficulty.Tier#loot}).</li>
 * </ul>
 * Salida temprana barata (las etiquetas del mob, casi siempre vacías); sin mixins.
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
	 * Pone en el mob los modificadores de la configuración en uso (los recalcula si cambió): al cargarse y, tras
	 * /heraldia reload, en todos los ya cargados. True si es un mob de Heraldia al que se aplica la dificultad.
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

	/** Los modificadores de vida y daño del nivel de {@code cfg} (y sin el extra por jugadores si está desactivado). */
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

	/** Pone (o quita, con cantidad 0) el modificador permanente {@code id}; idempotente. */
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
	 * Tablas de cofre de Heraldia (aldeas, medianas, entradas a mina y únicas): las mismas que se reponen
	 * ({@link Restock#tableRestocks}); no las de los guardianes, trofeos, llaves ni tratos.
	 */
	static boolean isChestLoot(@Nullable ResourceKey<LootTable> key) {
		return key != null && Restock.tableRestocks(key.identifier().toString());
	}

	/** Para los tests: la cantidad del modificador de un atributo (0 si no lo tiene). */
	static double amount(@Nullable AttributeInstance attr, Identifier id) {
		AttributeModifier m = attr == null ? null : attr.getModifier(id);
		return m == null ? 0 : m.amount();
	}
}
