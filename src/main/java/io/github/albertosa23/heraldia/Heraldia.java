package io.github.albertosa23.heraldia;

import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.loot.WithoutLootrCondition;
import io.github.albertosa23.heraldia.unicas.atlantida.Atlantida;
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

/** Punto de entrada. El contenido es de datos (data/heraldia); aquí se registra lo que los datos no pueden expresar. */
public final class Heraldia implements ModInitializer {
	public static final String MOD_ID = "heraldia";
	private static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

	@Override
	public void onInitialize() {
		// Antes de que se lea ningún datapack: la rejilla heraldia:rejilla toma sus valores de aquí.
		HeraldiaConfig.load(FabricLoader.getInstance().getConfigDir().resolve("heraldia.json"));
		Registry.register(BuiltInRegistries.LOOT_CONDITION_TYPE, id("sin_lootr"), WithoutLootrCondition.CODEC);
		Registry.register(BuiltInRegistries.STRUCTURE_PLACEMENT, id("rejilla"), GridPlacement.CODEC);
		Atlantida.register();
		io.github.albertosa23.heraldia.unicas.ciudadela.Ciudadela.register();
		io.github.albertosa23.heraldia.unicas.faro.Faro.init();
		io.github.albertosa23.heraldia.comun.HastaElSueloProcessor.register();
		io.github.albertosa23.heraldia.aldeas.AldeaStructure.registrar();
		io.github.albertosa23.heraldia.unicas.galeon.GaleonUnica.registrar();
		io.github.albertosa23.heraldia.comando.LlaveCommand.register();
		io.github.albertosa23.heraldia.comando.InfoCommand.register();
		io.github.albertosa23.heraldia.loot.CofrePorJugador.register();
		ServerLifecycleEvents.SERVER_STARTED.register(Heraldia::logRegisteredStructures);
		ServerLifecycleEvents.SERVER_STARTED.register(Heraldia::publishGolemSettings);
	}

	public static Identifier id(String path) {
		return Identifier.fromNamespaceAndPath(MOD_ID, path);
	}

	/** Deja en el log cuántas estructuras y logros del mod se han cargado, para comprobar la carga sin entrar al juego
	 *  (sin jugadores, /advancement no llega a mirar el logro). Una vez, al arrancar. */
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

	/** Pasa a las funciones de gólems (marcador heraldia_cfg) la limpieza y los límites de la configuración. */
	private static void publishGolemSettings(MinecraftServer server) {
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
