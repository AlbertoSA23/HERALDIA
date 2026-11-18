package io.github.albertosa23.heraldia.inhabitants;

import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.update.MobFixes;
import java.util.Set;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Inhabitants of the medium structures (tools/gen/mediums/_inhabitants.py): the villagers who live in the inn, the mill,
 * the fisher's hut, the hunters' lodge, the watchtower and the hermitage, and the inn's pigs. They come in the templates
 * (the game spawns them when the structure generates) and live with vanilla AI: this class does nothing every tick.
 * <p>
 * The option {@link #OPTION} (on by default, off in the light profile) is applied once per inhabitant, the first time it
 * loads ({@code ENTITY_LOAD}, early exit when it has no {@link #TAG}): on, it is marked {@link #SEEN} and lives; off,
 * the inhabitants that were still figures in earlier versions ({@link #STILL_BEFORE}) become still again ({@code NoAI})
 * and the new ones are removed. Once seen, an inhabitant is never touched again: changing the option does not change what
 * a world already has.
 */
public final class Inhabitants {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String OPTION = "medianas.habitantes";
	public static final String TAG = MobFixes.INHABITANT;
	public static final String STILL_BEFORE = "heraldia_habitante.quieto_antes", SEEN = "heraldia_habitante.visto";

	/** What to do with an entity when it loads. */
	enum Action { NONE, LIVE, STILL, REMOVE }

	private Inhabitants() {
	}

	public static void register() {
		ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> onLoad(entity));
		ServerLifecycleEvents.SERVER_STARTED.register(server -> LOGGER.info("Heraldia: habitantes de las medianas: {}",
				enabled() ? "activados" : "desactivados"));
	}

	static boolean enabled() {
		HeraldiaConfig c = HeraldiaConfig.get();
		return !c.has(OPTION) || c.getBool(OPTION);
	}

	/** The decision (pure logic, tested in InhabitantsTest). */
	static Action decide(Set<String> tags, boolean enabled) {
		if (tags.isEmpty() || !tags.contains(TAG) || tags.contains(SEEN)) {
			return Action.NONE;
		}
		if (enabled) {
			return Action.LIVE;
		}
		return tags.contains(STILL_BEFORE) ? Action.STILL : Action.REMOVE;
	}

	static void onLoad(Entity e) {
		Set<String> tags = e.entityTags();
		if (tags.isEmpty() || !tags.contains(TAG)) {
			return;                                   // almost every entity: one set lookup
		}
		switch (decide(tags, enabled())) {
			case LIVE -> e.addTag(SEEN);
			case STILL -> {
				if (e instanceof Mob m) {
					m.setNoAi(true);
				}
				e.addTag(SEEN);
			}
			case REMOVE -> e.discard();
			case NONE -> {
			}
		}
	}
}
