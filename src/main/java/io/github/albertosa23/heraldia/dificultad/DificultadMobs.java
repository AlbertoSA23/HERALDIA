package io.github.albertosa23.heraldia.dificultad;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
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
 * identificador ({@link #VIDA}, {@link #DANO}, {@link #JUGADORES}), que se suman a los que pongan otros (los jefes, el
 * juego, otros mods) sin tocarlos:
 * <ul>
 * <li>en cada {@code ENTITY_LOAD} (al colocarse la plantilla, al generarse el chunk y en cada carga) se ponen los del
 * nivel en uso, o se quitan en normal: así valen para los mobs ya generados y se recalculan si cambia la opción (la
 * configuración se lee al arrancar; /heraldia recargar los recalcula en los mobs ya cargados con {@link #aplicar}). Ponerlos
 * dos veces no cambia nada ({@code addOrReplacePermanentModifier}).</li>
 * <li>con dificultad.escalar_por_jugadores, al recibir un golpe se cuenta a los jugadores a 32 bloques (no por tick).</li>
 * <li>con dificultad.escalar_botin, el botín de los cofres de Heraldia (tablas cofres/, unicas/, medianas/) sale con la
 * cantidad de sus objetos sencillos apilables multiplicada ({@link Dificultad.Nivel#botin}).</li>
 * </ul>
 * Salida temprana barata (las etiquetas del mob, casi siempre vacías); sin mixins.
 */
public final class DificultadMobs {
	public static final Identifier VIDA = Heraldia.id("dificultad_vida"), DANO = Heraldia.id("dificultad_dano"),
			JUGADORES = Heraldia.id("dificultad_jugadores");
	private static final List<String> BOTIN = List.of("cofres/", "unicas/", "medianas/");

	private DificultadMobs() {
	}

	public static void registrar() {
		ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> alCargar(entity));
		ServerLivingEntityEvents.AFTER_DAMAGE.register((entity, source, base, taken, blocked) -> alRecibirDano(entity));
		LootTableEvents.MODIFY_DROPS.register(DificultadMobs::botin);
	}

	static void alCargar(Entity entity) {
		aplicar(entity);
	}

	/**
	 * Pone en el mob los modificadores de la configuración en uso (los recalcula si cambió): al cargarse y, tras
	 * /heraldia recargar, en todos los ya cargados. True si es un mob de Heraldia al que se aplica la dificultad.
	 */
	public static boolean aplicar(Entity entity) {
		if (!(entity instanceof Mob mob) || !Dificultad.aplica(mob.entityTags(), mob instanceof Enemy)) {
			return false;
		}
		double antes = mob.getMaxHealth();
		ajustar(mob.getAttribute(Attributes.MAX_HEALTH), mob.getAttribute(Attributes.ATTACK_DAMAGE), HeraldiaConfig.get());
		ajustarVida(mob, antes);
		return true;
	}

	/** Los modificadores de vida y daño del nivel de {@code cfg} (y sin el extra por jugadores si está desactivado). */
	static void ajustar(@Nullable AttributeInstance vida, @Nullable AttributeInstance dano, HeraldiaConfig cfg) {
		Dificultad.Nivel nivel = Dificultad.Nivel.de(cfg.getString("dificultad.nivel"));
		poner(vida, VIDA, nivel.modVida());
		poner(dano, DANO, nivel.modDano());
		if (!cfg.getBool("dificultad.escalar_por_jugadores")) {
			poner(vida, JUGADORES, 0);
		}
	}

	static void alRecibirDano(LivingEntity entity) {
		if (!(entity instanceof Mob mob) || !Dificultad.aplica(mob.entityTags(), mob instanceof Enemy) || !mob.isAlive()
				|| !HeraldiaConfig.get().getBool("dificultad.escalar_por_jugadores")) {
			return;
		}
		double r2 = Dificultad.RADIO_JUGADORES * Dificultad.RADIO_JUGADORES;
		int cerca = 0;
		for (Player p : mob.level().players()) {
			if (!p.isSpectator() && p.isAlive() && p.distanceToSqr(mob) <= r2) {
				cerca++;
			}
		}
		double antes = mob.getMaxHealth();
		poner(mob.getAttribute(Attributes.MAX_HEALTH), JUGADORES, Dificultad.extraJugadores(cerca));
		ajustarVida(mob, antes);
	}

	/** Pone (o quita, con cantidad 0) el modificador permanente {@code id}; idempotente. */
	public static void poner(@Nullable AttributeInstance attr, Identifier id, double cantidad) {
		if (attr == null) {
			return;
		}
		if (cantidad == 0) {
			attr.removeModifier(id);
			return;
		}
		AttributeModifier actual = attr.getModifier(id);
		if (actual == null || actual.amount() != cantidad || actual.operation() != AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL) {
			attr.addOrReplacePermanentModifier(new AttributeModifier(id, cantidad, AttributeModifier.Operation.ADD_MULTIPLIED_TOTAL));
		}
	}

	private static void ajustarVida(Mob mob, double antes) {
		double despues = mob.getMaxHealth();
		if (despues != antes) {
			mob.setHealth(Dificultad.reajustarVida(mob.getHealth(), antes, despues));
		}
	}

	private static void botin(Holder<LootTable> table, net.minecraft.world.level.storage.loot.LootContext context, List<ItemStack> drops) {
		if (drops.isEmpty() || !esBotinDeCofre(table.unwrapKey().orElse(null))) {
			return;
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		double m = Dificultad.Nivel.de(cfg.getString("dificultad.nivel")).botin;
		if (m == 1 || !cfg.getBool("dificultad.escalar_botin")) {
			return;
		}
		for (ItemStack stack : drops) {
			if (stack.isStackable() && stack.getComponentsPatch().isEmpty()) {
				stack.setCount(Dificultad.cantidad(stack.getCount(), m, stack.getMaxStackSize(), context.getRandom().nextDouble()));
			}
		}
	}

	/** Tablas de cofre de Heraldia (aldeas, medianas y únicas); no las de los guardianes, trofeos, llaves ni tratos. */
	static boolean esBotinDeCofre(@Nullable ResourceKey<LootTable> key) {
		if (key == null || !Heraldia.MOD_ID.equals(key.identifier().getNamespace())) {
			return false;
		}
		String path = key.identifier().getPath();
		return BOTIN.stream().anyMatch(path::startsWith);
	}

	/** Para los tests: la cantidad del modificador de un atributo (0 si no lo tiene). */
	static double cantidad(@Nullable AttributeInstance attr, Identifier id) {
		AttributeModifier m = attr == null ? null : attr.getModifier(id);
		return m == null ? 0 : m.amount();
	}
}
