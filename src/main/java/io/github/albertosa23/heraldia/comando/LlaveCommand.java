package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
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
 * /heraldia llave &lt;jugadores&gt; &lt;todas|estructura|estructura.llave&gt; (operador, nivel 2): da las llaves de los cofres
 * cerrados de las estructuras únicas. Cada llave es la tabla de botín heraldia:llaves/&lt;estructura&gt;/&lt;llave&gt; que
 * escribe el generador (la misma que suelta el juego), así que el objeto es exactamente el que pide la cerradura.
 * El índice /heraldia/llaves.json se lee una vez al iniciar; el comando solo trabaja cuando se ejecuta.
 */
public final class LlaveCommand {
	private static final String TODAS = "todas";
	/** "atlantida.poseidon" -> heraldia:llaves/atlantida/poseidon, en el orden del generador. */
	private static final Map<String, ResourceKey<LootTable>> KEYS = new LinkedHashMap<>();
	private static final Set<String> OPTIONS = new LinkedHashSet<>();

	private LlaveCommand() {
	}

	public static void register() {
		JsonObject keys = readIndex().getAsJsonObject("llaves");
		OPTIONS.add(TODAS);
		for (String id : keys.keySet()) {
			KEYS.put(id, ResourceKey.create(Registries.LOOT_TABLE, Identifier.parse(
					keys.getAsJsonObject(id).get("tabla").getAsString())));
			OPTIONS.add(id.substring(0, id.indexOf('.')));
		}
		OPTIONS.addAll(KEYS.keySet());
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> build(dispatcher));
	}

	private static void build(CommandDispatcher<CommandSourceStack> dispatcher) {
		dispatcher.register(Commands.literal("heraldia")
				.then(Commands.literal("llave")
						.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
						.then(Commands.argument("jugadores", EntityArgument.players())
								.then(Commands.argument("llave", StringArgumentType.word())
										.suggests((ctx, b) -> SharedSuggestionProvider.suggest(OPTIONS, b))
										.executes(LlaveCommand::give)))));
	}

	private static int give(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack source = ctx.getSource();
		String which = StringArgumentType.getString(ctx, "llave");
		List<ResourceKey<LootTable>> tables = new ArrayList<>();
		KEYS.forEach((id, table) -> {
			if (which.equals(TODAS) || which.equals(id) || id.startsWith(which + ".")) {
				tables.add(table);
			}
		});
		if (tables.isEmpty()) {
			source.sendFailure(Component.translatableWithFallback("heraldia.llave.desconocida",
					"No hay ninguna llave «%s». Opciones: %s", which, String.join(", ", OPTIONS)));
			return 0;
		}
		Collection<ServerPlayer> players = EntityArgument.getPlayers(ctx, "jugadores");
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

	/** Como /give: al inventario y, si no cabe, al suelo a nombre del jugador. */
	private static void give(ServerPlayer player, ItemStack stack) {
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
		try (InputStream in = LlaveCommand.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			return JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}
}
