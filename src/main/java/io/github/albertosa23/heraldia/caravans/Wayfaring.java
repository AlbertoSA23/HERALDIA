package io.github.albertosa23.heraldia.caravans;

import io.github.albertosa23.heraldia.command.Texts;
import java.util.List;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.animal.golem.IronGolem;
import net.minecraft.world.entity.animal.sheep.Sheep;
import net.minecraft.world.entity.animal.wolf.Wolf;
import net.minecraft.world.entity.npc.wanderingtrader.WanderingTrader;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.trading.ItemCost;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.item.trading.MerchantOffers;
import org.jspecify.annotations.Nullable;

/**
 * The wayfarers in the game: who each one is (a wandering trader dressed by its name, what it carries and what it sells, or a
 * village iron golem for the guards) and who goes with it. The engine ({@link Caravans}) tags them, adds them to the world,
 * moves them and removes them. Vanilla entities only: a client without the mod sees them as they are.
 */
final class Wayfaring {
	private Wayfaring() {
	}

	static Item item(String id) {
		return BuiltInRegistries.ITEM.getValue(Identifier.parse(id));
	}

	/**
	 * The leader, not yet added to the world (null if the game does not create it). The people are wandering traders (the same
	 * entity as the caravan's merchant: goal AI, no POIs, no beds, no job sites): with their name, what they carry in their
	 * crossed arms and their own trades or none. The guards are iron golems of the village of origin, not made by a player:
	 * they defend themselves.
	 */
	static @Nullable Mob leader(ServerLevel level, Wayfarers.Kind k, @Nullable String zone, String origin, List<String> colors) {
		if (k == Wayfarers.Kind.PATROL) {
			IronGolem g = EntityTypes.IRON_GOLEM.create(level, EntitySpawnReason.EVENT);
			if (g != null) {
				g.setCustomName(Texts.t("heraldia.viajeros.guardias.nombre", origin));
			}
			return g;
		}
		WanderingTrader m = EntityTypes.WANDERING_TRADER.create(level, EntitySpawnReason.EVENT);
		if (m == null) {
			return null;
		}
		m.setCustomName(Texts.t("heraldia.viajeros." + k.id + ".nombre"));
		m.setDespawnDelay(Journey.MAX_TICKS + Wayfarers.LINGER_TICKS + 2 * Rules.DRAW_TICKS);   // the engine removes it, not its clock
		String held = Wayfarers.held(k, zone);
		if (held != null) {
			m.setItemSlot(EquipmentSlot.MAINHAND, new ItemStack(item(held)));
			m.setDropChance(EquipmentSlot.MAINHAND, 0f);
		}
		MerchantOffers offers = m.getOffers();       // the first call fills in the vanilla ones: they go
		offers.clear();
		for (Wayfarers.Trade t : Wayfarers.trades(k, zone, colors)) {
			offers.add(new MerchantOffer(new ItemCost(item(t.cost()), t.count()), new ItemStack(item(t.result()), t.amount()), t.uses(), 1, 0.05f));
		}
		if (k == Wayfarers.Kind.MESSENGER) {
			var speed = m.getAttribute(Attributes.MOVEMENT_SPEED);
			if (speed != null) {
				speed.setBaseValue(speed.getBaseValue() * Wayfarers.MESSENGER_SPEED);
			}
		}
		return m;
	}

	/** Who goes with it: the flock behind the shepherd, the second guard beside the first, the hunter's dog behind it. */
	static void companions(Caravans.Caravan c, Mob leader, BlockPos departure, double dx, double dz, float yaw, List<String> colors) {
		ServerLevel level = c.level;
		switch (c.kind) {
			case SHEPHERD -> {
				for (int i = 0; i < colors.size(); i++) {
					Sheep s = EntityTypes.SHEEP.create(level, EntitySpawnReason.EVENT);
					if (s != null) {
						s.setColor(DyeColor.byName(colors.get(i), DyeColor.WHITE));
						double back = 2 + 1.5 * (i / 2), side = i % 2 == 0 ? 1.2 : -1.2;
						Caravans.add(c, s, Wayfarers.SHEEP, departure, -dx * back - dz * side, -dz * back + dx * side, yaw);
					}
				}
			}
			case PATROL -> {
				IronGolem g = EntityTypes.IRON_GOLEM.create(level, EntitySpawnReason.EVENT);
				if (g != null) {
					g.setCustomName(leader.getCustomName());
					Caravans.add(c, g, Wayfarers.PARTNER, departure, -dx * 1.5 - dz * 2.5, -dz * 1.5 + dx * 2.5, yaw);
				}
			}
			case HUNTER -> {
				Wolf w = EntityTypes.WOLF.create(level, EntitySpawnReason.EVENT);
				if (w != null) {
					// the variant of the land (vanilla picks it by biome when it spawns), tame and its owner the hunter
					w.snapTo(departure.getX() + 0.5 - dx * 2, departure.getY(), departure.getZ() + 0.5 - dz * 2, yaw, 0f);
					w.finalizeSpawn(level, level.getCurrentDifficultyAt(departure), EntitySpawnReason.EVENT, null);
					w.setTame(true, false);
					w.setOwner(leader);
					Caravans.add(c, w, Wayfarers.DOG, departure, -dx * 2, -dz * 2, yaw);
				}
			}
			default -> {
			}
		}
	}
}
