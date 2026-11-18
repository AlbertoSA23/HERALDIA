package io.github.albertosa23.heraldia.command;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;

import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Collection;
import java.util.LinkedHashMap;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * /heraldia key &lt;players&gt; &lt;all|structure|structure.key&gt; (operator, level 2): gives the keys of the locked
 * chests of the unique structures. Each key is the loot table heraldia:llaves/&lt;structure&gt;/&lt;key&gt; that the
 * generator writes (the same one the game drops), so the item is exactly the one the lock asks for.
 * The /heraldia/llaves.json index is read once at startup; the command only works when run.
 */
public final class KeyCommand {
	private static final String ALL = "all", ALL_LEGACY = "todas";
	/** "atlantida.poseidon" -> heraldia:llaves/atlantida/poseidon, in the generator's order. */
	private static final Map<String, ResourceKey<LootTable>> KEYS = new LinkedHashMap<>();
	private static final Set<String> OPTIONS = new LinkedHashSet<>();

	private KeyCommand() {
	}

	public static void register() {
		JsonObject keys = readIndex().getAsJsonObject("llaves");
		OPTIONS.add(ALL);
		for (String id : keys.keySet()) {
			KEYS.put(id, ResourceKey.create(Registries.LOOT_TABLE, Identifier.parse(
					keys.getAsJsonObject(id).get("tabla").getAsString())));
			OPTIONS.add(id.substring(0, id.indexOf('.')));
		}
		OPTIONS.addAll(KEYS.keySet());
	}

	/** /heraldia key &lt;players&gt; &lt;all|structure|structure.key&gt; (registered by {@link HeraldiaCommands}). */
	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("key")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.argument("players", EntityArgument.players())
						.then(Commands.argument("key", StringArgumentType.word())
								.suggests((ctx, b) -> SharedSuggestionProvider.suggest(OPTIONS, b))
								.executes(KeyCommand::give)));
	}

	/** The typed value, with the old name "todas" as "all" (without suggesting it: see {@link Alias}). */
	static String option(String written) {
		return ALL_LEGACY.equals(written) ? ALL : written;
	}

	private static int give(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack source = ctx.getSource();
		String written = StringArgumentType.getString(ctx, "key");
		String which = option(written);
		if (!which.equals(written)) {
			HeraldiaCommands.warn(source, written, which);
		}
		List<ResourceKey<LootTable>> tables = new ArrayList<>();
		KEYS.forEach((id, table) -> {
			if (which.equals(ALL) || which.equals(id) || id.startsWith(which + ".")) {
				tables.add(table);
			}
		});
		if (tables.isEmpty()) {
			source.sendFailure(Component.translatableWithFallback("heraldia.llave.desconocida",
					"No hay ninguna llave «%s». Opciones: %s", which, String.join(", ", OPTIONS)));
			return 0;
		}
		Collection<ServerPlayer> players = EntityArgument.getPlayers(ctx, "players");
		int given = 0;
		for (ServerPlayer player : players) {
			LootParams params = new LootParams.Builder(player.level()).create(LootContextParamSets.EMPTY);
			for (ResourceKey<LootTable> key : tables) {
				for (ItemStack stack : source.getServer().reloadableRegistries().getLootTable(key).getRandomItems(params)) {
					give(player, stack);
					given++;
				}
			}
		}
		int total = given;
		source.sendSuccess(() -> Component.translatableWithFallback("heraldia.llave.dada",
				"Entregadas %s llaves (%s) a %s jugadores", total, which, players.size()), true);
		return total;
	}

	/** Like /give: into the inventory and, if it does not fit, on the ground in the player's name. */
	public static void give(ServerPlayer player, ItemStack stack) {
		if (player.getInventory().add(stack) && stack.isEmpty()) {
			return;
		}
		ItemEntity drop = player.createItemStackToDrop(stack, false, false);
		if (drop != null) {
			drop.setNoPickUpDelay();
			drop.setTarget(player.getUUID());
			player.level().addFreshEntity(drop);
		}
	}

	private static JsonObject readIndex() {
		String path = "/heraldia/llaves.json";
		try (InputStream in = KeyCommand.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			return JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}
}
