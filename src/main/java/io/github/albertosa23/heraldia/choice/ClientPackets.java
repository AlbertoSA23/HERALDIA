package io.github.albertosa23.heraldia.choice;

import com.mojang.brigadier.arguments.BoolArgumentType;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import java.util.concurrent.atomic.AtomicReference;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.Component;
import net.minecraft.network.protocol.game.ServerboundContainerButtonClickPacket;
import net.minecraft.network.protocol.game.ServerboundContainerSlotStateChangedPacket;
import net.minecraft.network.protocol.game.ServerboundPickItemFromBlockPacket;
import net.minecraft.network.protocol.game.ServerboundPlaceRecipePacket;
import net.minecraft.network.protocol.game.ServerboundSelectBundleItemPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.item.crafting.display.RecipeDisplayId;

/**
 * /heraldia choice send ...: the other packets a client sends about its open window (and a pick-block), exactly as it
 * sends them, through the player's own connection handler, for the server tests (Carpet's simulated players have no
 * client): a menu button, a recipe book placement, a crafter's slot toggle, a bundle's selected item and a creative
 * pick-block with or without data. Operators only, like /heraldia choice click.
 */
final class ClientPackets {
	private ClientPackets() {
	}

	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("send")
				.then(Commands.literal("button").then(Commands.argument("id", IntegerArgumentType.integer(0, 255))
						.executes(ctx -> sent(ctx, "button", p -> p.connection.handleContainerButtonClick(
								new ServerboundContainerButtonClickPacket(p.containerMenu.containerId, IntegerArgumentType.getInteger(ctx, "id")))))))
				.then(Commands.literal("slot-state").then(Commands.argument("slot", IntegerArgumentType.integer(0, 127))
						.then(Commands.argument("on", BoolArgumentType.bool())
								.executes(ctx -> sent(ctx, "slot-state", p -> p.connection.handleContainerSlotStateChanged(
										new ServerboundContainerSlotStateChangedPacket(IntegerArgumentType.getInteger(ctx, "slot"),
												p.containerMenu.containerId, BoolArgumentType.getBool(ctx, "on"))))))))
				.then(Commands.literal("bundle").then(Commands.argument("slot", IntegerArgumentType.integer(0, 127))
						.then(Commands.argument("index", IntegerArgumentType.integer(-1, 63))
								.executes(ctx -> sent(ctx, "bundle", p -> p.connection.handleBundleItemSelectedPacket(
										new ServerboundSelectBundleItemPacket(IntegerArgumentType.getInteger(ctx, "slot"),
												IntegerArgumentType.getInteger(ctx, "index"))))))))
				.then(Commands.literal("pick").then(Commands.argument("x", IntegerArgumentType.integer())
						.then(Commands.argument("y", IntegerArgumentType.integer()).then(Commands.argument("z", IntegerArgumentType.integer())
								.then(Commands.argument("data", BoolArgumentType.bool())
										.executes(ctx -> sent(ctx, "pick", p -> p.connection.handlePickItemFromBlock(
												new ServerboundPickItemFromBlockPacket(new BlockPos(IntegerArgumentType.getInteger(ctx, "x"),
														IntegerArgumentType.getInteger(ctx, "y"), IntegerArgumentType.getInteger(ctx, "z")),
														BoolArgumentType.getBool(ctx, "data"))))))))))
				.then(Commands.literal("recipe").then(Commands.argument("recipe", StringArgumentType.greedyString())
						.executes(ClientPackets::recipe)));
	}

	private interface Send {
		void to(ServerPlayer p);
	}

	private static int sent(CommandContext<CommandSourceStack> ctx, String what, Send send) throws CommandSyntaxException {
		ServerPlayer p = ctx.getSource().getPlayerOrException();
		int window = p.containerMenu.containerId;
		send.to(p);
		ctx.getSource().sendSuccess(() -> Component.literal("choice send: " + what + " in window " + window), false);
		return 1;
	}

	/** The recipe book's "place this recipe" (the recipe must be in the player's book), with its display id as the client has it. */
	private static int recipe(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		ServerPlayer p = ctx.getSource().getPlayerOrException();
		String id = StringArgumentType.getString(ctx, "recipe");
		AtomicReference<RecipeDisplayId> display = new AtomicReference<>();
		p.level().getServer().getRecipeManager().listDisplaysForRecipe(ResourceKey.create(Registries.RECIPE, Identifier.parse(id)),
				e -> display.compareAndSet(null, e.id()));
		if (display.get() == null) {
			ctx.getSource().sendFailure(Component.literal("choice send: no recipe " + id));
			return 0;
		}
		return sent(ctx, "recipe", q -> q.connection.handlePlaceRecipe(new ServerboundPlaceRecipePacket(q.containerMenu.containerId,
				display.get(), false)));
	}
}
