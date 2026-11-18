package io.github.albertosa23.heraldia;

import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.loot.WithoutLootrCondition;
import io.github.albertosa23.heraldia.uniques.atlantis.Atlantis;
import net.fabricmc.api.ModInitializer;
import net.fabricmc.loader.api.FabricLoader;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.core.Registry;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.world.scores.Objective;
import net.minecraft.world.scores.ScoreHolder;
import net.minecraft.world.scores.Scoreboard;
import net.minecraft.world.scores.criteria.ObjectiveCriteria;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/** Entry point. The content is data (data/heraldia); this registers what the data cannot express. */
public final class Heraldia implements ModInitializer {
	public static final String MOD_ID = "heraldia";
	/** Tag of the template mobs that must not spawn as babies (the generator's core.ADULT_TAG; ZombieMixin, ZombieEquipmentMixin and DrownedMixin). */
	public static final String ADULT = "heraldia_adulto";
	private static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		// Before any datapack is read: the heraldia:rejilla grid takes its values from here.
		HeraldiaConfig.load(FabricLoader.getInstance().getConfigDir().resolve("heraldia.json"));
		Registry.register(BuiltInRegistries.LOOT_CONDITION_TYPE, id("sin_lootr"), WithoutLootrCondition.CODEC);
		Registry.register(BuiltInRegistries.LOOT_CONDITION_TYPE, id("opcion"), io.github.albertosa23.heraldia.loot.OptionCondition.CODEC);
		Registry.register(BuiltInRegistries.STRUCTURE_PLACEMENT, id("rejilla"), GridPlacement.CODEC);
		GridPlacement.registerBiomeSearch();
		Atlantis.register();
		io.github.albertosa23.heraldia.uniques.citadel.Citadel.register();
		io.github.albertosa23.heraldia.uniques.mine.Mine.register();
		io.github.albertosa23.heraldia.mines.Mines.register();
		io.github.albertosa23.heraldia.coast.Coast.register();
		io.github.albertosa23.heraldia.uniques.lighthouse.Lighthouse.init();
		io.github.albertosa23.heraldia.dimensions.Dimensions.register();
		io.github.albertosa23.heraldia.common.ToGroundProcessor.register();
		io.github.albertosa23.heraldia.common.Anchoring.register();
		io.github.albertosa23.heraldia.bosses.Bosses.register();
		io.github.albertosa23.heraldia.chronicle.ChronicleEnding.register();
		io.github.albertosa23.heraldia.villages.VillageStructure.register();
		io.github.albertosa23.heraldia.roads.Roads.register();
		io.github.albertosa23.heraldia.uniques.galleon.GalleonUnique.register();
		io.github.albertosa23.heraldia.uniques.island.Island.register();
		io.github.albertosa23.heraldia.command.KeyCommand.register();
		io.github.albertosa23.heraldia.command.Guide.register();
		io.github.albertosa23.heraldia.command.HeraldiaCommands.register();
		io.github.albertosa23.heraldia.command.VersionNotice.register();
		io.github.albertosa23.heraldia.command.ProfileNotice.register();
		io.github.albertosa23.heraldia.loot.PerPlayerChest.register();
		io.github.albertosa23.heraldia.loot.RestockedLoot.register();
		io.github.albertosa23.heraldia.difficulty.MobDifficulty.register();
		io.github.albertosa23.heraldia.arena.Arena.register();
		io.github.albertosa23.heraldia.quests.Quests.register();
		io.github.albertosa23.heraldia.dialogue.Dialogue.register();
		io.github.albertosa23.heraldia.caravans.Caravans.register();
		io.github.albertosa23.heraldia.common.Profiler.register();
		io.github.albertosa23.heraldia.common.SearchCaches.register();
		io.github.albertosa23.heraldia.maps.WebMaps.register();
		io.github.albertosa23.heraldia.treasure.Treasure.register();
		io.github.albertosa23.heraldia.huts.Wizards.register();
		io.github.albertosa23.heraldia.ambience.Ambience.register();
		io.github.albertosa23.heraldia.update.Updater.register();
		io.github.albertosa23.heraldia.inhabitants.Inhabitants.register();
		ServerLifecycleEvents.SERVER_STARTED.register(Heraldia::logRegisteredStructures);
		ServerLifecycleEvents.SERVER_STARTED.register(Heraldia::publishGolemSettings);
	}

	public static Identifier id(String path) {
		return Identifier.fromNamespaceAndPath(MOD_ID, path);
	}

	/** Logs how many of the mod's structures and advancements have loaded, to check loading without joining the game
	 *  (without players, /advancement never looks at the advancement). Once, at startup. */
	private static void logRegisteredStructures(MinecraftServer server) {
		long count = server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet().stream()
				.filter(id -> MOD_ID.equals(id.getNamespace()))
				.count();
		LOGGER.info("Heraldia: {} estructuras registradas", count);
		long advancements = server.getAdvancements().getAllAdvancements().stream()
				.filter(a -> MOD_ID.equals(a.id().getNamespace()))
				.count();
		LOGGER.info("Heraldia: {} logros cargados", advancements);
	}

	/** Passes the configuration's cleanup and limits to the golem functions (heraldia_cfg scoreboard) (at startup and on /heraldia reload). */
	public static void publishGolemSettings(MinecraftServer server) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		Scoreboard board = server.getScoreboard();
		Objective obj = board.getObjective("heraldia_cfg");
		if (obj == null) {
			obj = board.addObjective("heraldia_cfg", ObjectiveCriteria.DUMMY, Component.literal("heraldia_cfg"),
					ObjectiveCriteria.RenderType.INTEGER, false, null);
		}
		board.getOrCreatePlayerScore(ScoreHolder.forNameOnly("#limpieza"), obj).set(cfg.getBool("golems.limpieza") ? 1 : 0);
		board.getOrCreatePlayerScore(ScoreHolder.forNameOnly("#limite_estandar"), obj).set(cfg.getInt("golems.limite_estandar"));
		board.getOrCreatePlayerScore(ScoreHolder.forNameOnly("#limite_grande"), obj).set(cfg.getInt("golems.limite_grande"));
		LOGGER.info("Heraldia: aldeas: {} estilos activados, {} % grandes; gólems: limpieza {}, límites {}/{}",
				cfg.villages().enabledStyles(), cfg.getInt("aldeas.porcentaje_grandes"), cfg.getBool("golems.limpieza"),
				cfg.getInt("golems.limite_estandar"), cfg.getInt("golems.limite_grande"));
	}
}
