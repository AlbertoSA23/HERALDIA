package io.github.albertosa23.heraldia.treasure;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.serialization.Codec;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.InfoCommand;
import io.github.albertosa23.heraldia.command.KeyCommand;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.ArrayList;
import java.util.Collection;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.OptionalInt;
import java.util.Random;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.event.player.UseItemCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.arguments.EntityArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.Registry;
import net.minecraft.core.component.DataComponentMap;
import net.minecraft.core.component.DataComponentPatch;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.util.Util;
import net.minecraft.world.InteractionHand;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.MapItem;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.item.component.ItemLore;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.ChestBlock;
import net.minecraft.world.level.block.entity.ChestBlockEntity;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.saveddata.maps.MapDecorationTypes;
import net.minecraft.world.level.saveddata.maps.MapItemSavedData;
import net.minecraft.world.level.storage.loot.LootParams;
import net.minecraft.world.level.storage.loot.LootTable;
import net.minecraft.world.level.storage.loot.parameters.LootContextParamSets;
import net.minecraft.world.level.storage.loot.parameters.LootContextParams;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Búsqueda del tesoro encadenada (T40). El fragmento de mapa (tabla heraldia:tesoro/fragmento, en el botín de medianas,
 * minas y únicas con la condición {@link ClueCondition}) se usa con clic derecho:
 * <ol>
 * <li>Sin descifrar: la cadena se elige FUERA del hilo del servidor ({@link Search}: medianas y entradas a mina reales a
 * menos de tesoro.radio_max bloques, sin cargar ni generar chunks; {@link Planner}, determinista con la semilla del
 * jugador: mundo, UUID y cuántas lleva descifradas, adjunto heraldia:tesoro_contador). Al acabar, en el hilo del servidor,
 * el fragmento se cambia por un mapa vanilla con la marca del primer destino, y la cadena entera queda en el objeto
 * (custom_data {@value Chain#MARK}, {@link Chain}).</li>
 * <li>Con cadena: lejos de la marca, dice a cuántos bloques y hacia dónde queda; en una estructura, el mapa pasa a la
 * siguiente marca; en el tesoro, entierra el cofre (tabla heraldia:tesoro/cofre) en un sitio seguro ({@link Site}: solo
 * chunks ya cargados, nunca dentro ni encima de construcciones, con margen) y la cadena queda completada: su semilla se
 * apunta en el mundo (adjunto heraldia:tesoros del mundo principal), así que ni una copia del mapa da otro cofre.</li>
 * </ol>
 * Nada por tick: solo trabaja al usar una pista o con /heraldia treasure. Los encargos del tablón (T38) llaman a
 * {@link #reward(ServerPlayer)} al pagar; para otros orígenes, {@link #fragment(ServerLevel)} o anidar la tabla
 * heraldia:tesoro/fragmento.
 */
public final class Treasure {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final ResourceKey<LootTable> FRAGMENT = ResourceKey.create(Registries.LOOT_TABLE, Heraldia.id("tesoro/fragmento"));
	public static final ResourceKey<LootTable> CHEST = ResourceKey.create(Registries.LOOT_TABLE, Heraldia.id("tesoro/cofre"));
	/** La paga de un encargo del tablón (T38): a veces, un fragmento (tesoro.FACTOR["encargos"] del generador). */
	public static final ResourceKey<LootTable> QUEST = ResourceKey.create(Registries.LOOT_TABLE, Heraldia.id("tesoro/encargo"));
	static final String CLAVE = "heraldia.tesoro.";
	/** Jugadores con un fragmento descifrándose (en otro hilo): uno a la vez por jugador. */
	private static final Set<UUID> SEARCHING = ConcurrentHashMap.newKeySet();

	private Treasure() {
	}

	/** Los adjuntos, aparte para que los tests (ComandosTest arma el árbol de comandos) no registren nada. */
	static final class Data {
		/** Pistas descifradas por el jugador (la n de su semilla); se conserva al morir. */
		static final AttachmentType<Integer> COUNTER = AttachmentRegistry.create(Heraldia.id("tesoro_contador"),
				b -> b.persistent(Codec.INT).copyOnDeath());
		/** Semillas de las cadenas cuyo cofre ya está enterrado (en el mundo principal). */
		static final AttachmentType<List<Long>> COMPLETED = AttachmentRegistry.create(Heraldia.id("tesoros"),
				b -> b.persistent(Codec.LONG.listOf()));

		private Data() {
		}
	}

	public static void register() {
		Registry.register(BuiltInRegistries.LOOT_CONDITION_TYPE, Heraldia.id("tesoro_pista"), ClueCondition.CODEC);
		LOGGER.debug("Heraldia: adjuntos {} y {} registrados", Data.COUNTER.identifier(), Data.COMPLETED.identifier());
		UseItemCallback.EVENT.register(Treasure::use);
	}

	/** Un fragmento de mapa del tesoro nuevo (sin descifrar), de la tabla heraldia:tesoro/fragmento. */
	public static ItemStack fragment(ServerLevel level) {
		LootParams params = new LootParams.Builder(level).create(LootContextParamSets.EMPTY);
		List<ItemStack> items = level.getServer().reloadableRegistries().getLootTable(FRAGMENT).getRandomItems(params);
		return items.isEmpty() ? ItemStack.EMPTY : items.getFirst();
	}

	/**
	 * Enganche de los encargos del tablón (T38, Encargos.pagar): con la probabilidad de la tabla heraldia:tesoro/encargo
	 * (tesoro.probabilidad, si tesoro.activado), le da un fragmento al jugador. Barato: una tirada de botín.
	 */
	public static void reward(ServerPlayer p) {
		ServerLevel level = p.level();
		LootParams params = new LootParams.Builder(level).withParameter(LootContextParams.ORIGIN, p.position())
				.withOptionalParameter(LootContextParams.THIS_ENTITY, p).create(LootContextParamSets.CHEST);
		for (ItemStack s : level.getServer().reloadableRegistries().getLootTable(QUEST).getRandomItems(params)) {
			KeyCommand.give(p, s);
		}
	}

	/** La marca de pista de un objeto ({@value Chain#MARK}), o null si no es una pista. */
	static CompoundTag mark(ItemStack stack) {
		CustomData data = stack.get(DataComponents.CUSTOM_DATA);
		return data == null ? null : data.copyTag().getCompound(Chain.MARK).orElse(null);
	}

	private static InteractionResult use(Player p, Level lv, InteractionHand hand) {
		if (!(p instanceof ServerPlayer player) || !(lv instanceof ServerLevel level)) {
			return InteractionResult.PASS;
		}
		ItemStack stack = player.getItemInHand(hand);
		if (!stack.is(Items.PAPER) && !stack.is(Items.FILLED_MAP)) {
			return InteractionResult.PASS;   // salida temprana barata: casi todo lo que se usa no es una pista
		}
		CompoundTag tag = mark(stack);
		if (tag == null) {
			return InteractionResult.PASS;
		}
		Map<String, String> texts = texts(player);
		if (!HeraldiaConfig.get().getBool(ClueCondition.ENABLED)) {
			player.sendSystemMessage(t(texts, "desactivado").withStyle(ChatFormatting.GRAY));
		} else if (level.dimension() != Level.OVERWORLD) {
			player.sendSystemMessage(t(texts, "dimension").withStyle(ChatFormatting.GRAY));
		} else {
			Optional<Chain> c = Chain.fromTag(tag);
			if (c.isEmpty()) {
				decipher(player, level, texts);
			} else {
				follow(player, level, hand, c.get(), texts);
			}
		}
		return InteractionResult.SUCCESS;
	}

	// --- descifrar ---

	private static void decipher(ServerPlayer player, ServerLevel level, Map<String, String> texts) {
		UUID uuid = player.getUUID();
		if (!SEARCHING.add(uuid)) {
			player.sendSystemMessage(t(texts, "ocupado").withStyle(ChatFormatting.GRAY));
			return;
		}
		player.sendSystemMessage(t(texts, "descifrando").withStyle(ChatFormatting.GRAY, ChatFormatting.ITALIC));
		int n = player.getAttachedOrElse(Data.COUNTER, 0);
		long seed = Planner.seed(level.getSeed(), uuid, n);
		BlockPos origin = player.blockPosition();
		int radius = HeraldiaConfig.get().getInt(ClueCondition.RADIUS);
		List<InfoCommand.Group> groups = InfoCommand.groups(level);   // en el hilo del servidor: lee los registros
		long t0 = System.nanoTime();
		CompletableFuture.supplyAsync(() -> {
			Search b = new Search(level, groups);
			Optional<List<Destination>> d = Planner.plan(seed, origin.getX(), origin.getZ(), radius, b, b);
			LOGGER.info("Heraldia: tesoro: cadena de {} elegida en {} ms ({} casillas miradas, fuera del hilo del servidor): {}",
					player.getGameProfile().name(), (System.nanoTime() - t0) / 1_000_000, b.cellsVisited, d.orElse(List.of()));
			return d;
		}, Util.backgroundExecutor()).thenAcceptAsync(d -> {
			SEARCHING.remove(uuid);
			if (player.hasDisconnected()) {
				return;
			}
			int slot = fragmentSlot(player.getInventory());
			if (slot < 0) {
				return;   // ya no lleva el fragmento (lo soltó mientras tanto)
			}
			if (d.isEmpty()) {
				player.sendSystemMessage(t(texts, "sin_destino", radius).withStyle(ChatFormatting.GRAY));
				return;
			}
			Chain c = Chain.fresh(seed, origin.getX(), origin.getZ(), d.get());
			player.setAttached(Data.COUNTER, n + 1);
			player.getInventory().setItem(slot, map(level, c, texts));
			player.sendSystemMessage(t(texts, "descifrado", c.marks()).withStyle(ChatFormatting.GOLD));
			level.playSound(null, player.blockPosition(), SoundEvents.UI_CARTOGRAPHY_TABLE_TAKE_RESULT, SoundSource.PLAYERS, 1, 1);
		}, level.getServer()).exceptionally(e -> {
			SEARCHING.remove(uuid);
			LOGGER.error("Heraldia: tesoro: no se pudo descifrar el fragmento", e);
			return null;
		});
	}

	/** El hueco del inventario con un fragmento sin descifrar: el de la mano principal si lo es; si no, el primero. */
	static int fragmentSlot(Inventory inv) {
		int sel = inv.getSelectedSlot();
		if (isFragment(inv.getItem(sel))) {
			return sel;
		}
		for (int i = 0; i < inv.getContainerSize(); i++) {
			if (isFragment(inv.getItem(i))) {
				return i;
			}
		}
		return -1;
	}

	static boolean isFragment(ItemStack s) {
		CompoundTag m = mark(s);
		return m != null && Chain.fromTag(m).isEmpty();
	}

	// --- seguir la cadena ---

	private static void follow(ServerPlayer player, ServerLevel level, InteractionHand hand, Chain c, Map<String, String> texts) {
		int px = player.getBlockX(), pz = player.getBlockZ();
		Set<Long> completed = completed(level);
		switch (Advance.evaluateAt(c, px, pz, completed)) {
			case DONE -> player.sendSystemMessage(t(texts, "hecho").withStyle(ChatFormatting.GRAY));
			case FAR -> {
				Destination d = c.actual();
				player.sendSystemMessage(t(texts, "lejos", Advance.approximateDistance(d, px, pz), direction(texts, d.x() - px, d.z() - pz))
						.withStyle(ChatFormatting.GRAY));
			}
			case NEXT -> {
				Chain nxt = c.advance();
				player.setItemInHand(hand, map(level, nxt, texts));
				player.sendSystemMessage(t(texts, "paso", nxt.step() + 1, nxt.marks()).withStyle(ChatFormatting.GOLD));
				level.playSound(null, player.blockPosition(), SoundEvents.UI_CARTOGRAPHY_TABLE_TAKE_RESULT, SoundSource.PLAYERS, 1, 1);
			}
			case CHEST -> bury(player, level, hand, c, texts, completed);
		}
	}

	private static void bury(ServerPlayer player, ServerLevel level, InteractionHand hand, Chain c, Map<String, String> texts,
			Set<Long> completed) {
		Destination t = c.actual();
		long t0 = System.nanoTime();
		Site.Choice e = Site.choose(view(level), t.x(), t.z());
		LOGGER.info("Heraldia: tesoro: sitio del cofre de {} en ({}, {}): {} en {} µs", player.getGameProfile().name(), t.x(), t.z(),
				e, (System.nanoTime() - t0) / 1000);
		if (e.reason() == Site.Reason.UNLOADED) {
			player.sendSystemMessage(t(texts, "sin_sitio").withStyle(ChatFormatting.GRAY));
			return;
		}
		if (e.chest().isEmpty()) {   // todo cargado y nada seguro: el tesoro se va un poco más allá
			Search.Simple biomes = new Search.Simple(level);
			Chain moved = c.withTreasure(Planner.moveTreasure(c, biomes));
			player.setItemInHand(hand, map(level, moved, texts));
			player.sendSystemMessage(t(texts, "movido").withStyle(ChatFormatting.YELLOW));
			return;
		}
		BlockPos pos = e.chest().get();
		Direction looksAt = Direction.from2DDataValue(new Random(c.seed()).nextInt(4));
		level.setBlock(pos, Blocks.CHEST.defaultBlockState().setValue(ChestBlock.FACING, looksAt), 3);
		if (level.getBlockEntity(pos) instanceof ChestBlockEntity be) {
			be.setLootTable(CHEST, c.seed());
			be.applyComponents(DataComponentMap.builder().set(DataComponents.CUSTOM_NAME, t(texts, "cofre.titulo")).build(),
					DataComponentPatch.EMPTY);
			be.setChanged();
		}
		completed.add(c.seed());
		level.setAttached(Data.COMPLETED, List.copyOf(completed));
		Chain done = c.withChest(pos);
		ItemStack map = player.getItemInHand(hand).copy();
		decorate(map, done, texts);
		player.setItemInHand(hand, map);
		int dx = pos.getX() - player.getBlockX(), dz = pos.getZ() - player.getBlockZ();
		int dist = (int) Math.round(Math.sqrt((double) dx * dx + (double) dz * dz));
		player.sendSystemMessage((dist <= 2 ? t(texts, "cofre.aqui") : t(texts, "cofre", dist, direction(texts, dx, dz)))
				.withStyle(ChatFormatting.GOLD));
		level.sendParticles(ParticleTypes.HAPPY_VILLAGER, pos.getX() + 0.5, pos.getY() + 1.5, pos.getZ() + 0.5, 30, 0.6, 0.6, 0.6, 0);
		level.playSound(null, pos, SoundEvents.PLAYER_LEVELUP, SoundSource.PLAYERS, 0.6f, 1.2f);
		LOGGER.info("Heraldia: tesoro: cofre de {} enterrado en {} {} {} (semilla {})", player.getGameProfile().name(), pos.getX(),
				pos.getY(), pos.getZ(), c.seed());
	}

	/** Semillas de las cadenas ya completadas en este mundo (las del mundo principal). */
	static Set<Long> completed(ServerLevel level) {
		return new HashSet<>(level.getAttachedOrElse(Data.COMPLETED, List.of()));
	}

	/** El mundo para {@link Site}: solo chunks ya cargados (nunca carga ni genera uno). */
	static Site.View view(ServerLevel level) {
		return new Site.View() {
			private LevelChunk chunk(int x, int z) {
				return level.getChunkSource().getChunkNow(x >> 4, z >> 4);
			}

			@Override
			public OptionalInt top(int x, int z) {
				LevelChunk c = chunk(x, z);
				return c == null ? OptionalInt.empty() : OptionalInt.of(c.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15));
			}

			private BlockState state(int x, int y, int z) {
				LevelChunk c = chunk(x, z);
				return c == null ? Blocks.AIR.defaultBlockState() : c.getBlockState(new BlockPos(x, y, z));
			}

			@Override
			public String block(int x, int y, int z) {
				return BuiltInRegistries.BLOCK.getKey(state(x, y, z).getBlock()).toString();
			}

			@Override
			public boolean liquid(int x, int y, int z) {
				return !state(x, y, z).getFluidState().isEmpty();
			}

			@Override
			public boolean inStructure(int x, int y, int z) {
				return level.structureManager().getStructureWithPieceAt(new BlockPos(x, y, z), h -> true).isValid();
			}
		};
	}

	// --- el mapa ---

	/** Un mapa vanilla nuevo con la marca del destino en curso de la cadena (y la cadena en el objeto). */
	static ItemStack map(ServerLevel level, Chain c, Map<String, String> texts) {
		Destination d = c.actual();
		boolean treasure = d.type() == Destination.Type.TREASURE;
		ItemStack m = MapItem.create(level, d.x(), d.z(), (byte) (treasure ? 1 : 2), true, true);
		MapItem.renderBiomePreviewMap(level, m);
		MapItemSavedData.addTargetDecoration(m, new BlockPos(d.x(), 0, d.z()), "+", treasure ? MapDecorationTypes.RED_X : MapDecorationTypes.TARGET_X);
		decorate(m, c, texts);
		return m;
	}

	/** Nombre, lore (la pista: qué es, bioma y dirección desde la marca anterior) y la cadena en custom_data. */
	static void decorate(ItemStack m, Chain c, Map<String, String> texts) {
		MutableComponent name = c.completed() ? t(texts, "mapa.hecho") : t(texts, "mapa.nombre", c.step() + 1, c.marks());
		m.set(DataComponents.ITEM_NAME, name);
		m.set(DataComponents.CUSTOM_NAME, name.copy().withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GOLD)));
		List<Component> lore = new ArrayList<>();
		if (!c.completed()) {
			Destination d = c.actual();
			int[] from = c.from(c.step());
			lore.add(t(texts, "pista." + d.type().id()).withStyle(s -> s.withItalic(false).withColor(ChatFormatting.YELLOW)));
			lore.add(t(texts, "pista.donde", biome(d.biome()), direction(texts, d.x() - from[0], d.z() - from[1]))
					.withStyle(s -> s.withItalic(false).withColor(ChatFormatting.YELLOW)));
			if (!d.generated() && d.type() != Destination.Type.TREASURE) {
				lore.add(t(texts, "pista.prevista").withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GRAY)));
			}
			lore.add(t(texts, "mapa.uso").withStyle(s -> s.withItalic(false).withColor(ChatFormatting.DARK_AQUA)));
		}
		m.set(DataComponents.LORE, new ItemLore(lore));
		m.set(DataComponents.RARITY, Rarity.UNCOMMON);
		CustomData.update(DataComponents.CUSTOM_DATA, m, tag -> tag.put(Chain.MARK, c.toTag()));
	}

	/** Nombre del bioma: el de su lang (lo traduce el cliente) o el id en bonito. */
	static Component biome(String id) {
		Identifier i = Identifier.tryParse(id);
		if (i == null) {
			return Component.literal(id);
		}
		String pretty = i.getPath().replace('_', ' ');
		return Component.translatableWithFallback("biome." + i.getNamespace() + "." + i.getPath(), pretty);
	}

	static Component direction(Map<String, String> texts, int dx, int dz) {
		return Texts.t(texts, "heraldia.info.dir." + InfoCommand.direction(dx, dz));
	}

	static Map<String, String> texts(ServerPlayer player) {
		return Texts.language(player);
	}

	static MutableComponent t(Map<String, String> texts, String k, Object... args) {
		return Texts.t(texts, CLAVE + k, args);
	}

	// --- /heraldia treasure ---

	/** /heraldia treasure give [&lt;players&gt;] | info (operadores, nivel 2; lo registra Comandos). */
	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("treasure")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.literal("give")
						.executes(ctx -> give(ctx, List.of(ctx.getSource().getPlayerOrException())))
						.then(Commands.argument("players", EntityArgument.players())
								.executes(ctx -> give(ctx, EntityArgument.getPlayers(ctx, "players")))))
				.then(Commands.literal("info").executes(Treasure::info));
	}

	private static int give(CommandContext<CommandSourceStack> ctx, Collection<ServerPlayer> players) {
		int n = 0;
		for (ServerPlayer p : players) {
			ItemStack f = fragment(p.level());
			if (!f.isEmpty()) {
				KeyCommand.give(p, f);
				n++;
			}
		}
		int total = n;
		ctx.getSource().sendSuccess(() -> Texts.t(CLAVE + "comando.dado", total), true);
		return n;
	}

	private static int info(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		CompoundTag tag = mark(p.getMainHandItem());
		if (tag == null) {
			src.sendFailure(Texts.t(CLAVE + "comando.sin_pista"));
			return 0;
		}
		Optional<Chain> oc = Chain.fromTag(tag);
		if (oc.isEmpty()) {
			src.sendSuccess(() -> Texts.t(CLAVE + "comando.sin_descifrar"), false);
			return 1;
		}
		Chain c = oc.get();
		src.sendSuccess(() -> Texts.t(CLAVE + "comando.cadena", Long.toString(c.seed()), Math.min(c.step() + 1, c.marks()), c.marks()), false);
		for (int i = 0; i < c.destinations().size(); i++) {
			Destination d = c.destinations().get(i);
			Component line = Texts.t(CLAVE + "comando.destino", i + 1, Texts.t(CLAVE + "tipo." + d.type().id()),
					InfoCommand.coordinates(new BlockPos(d.x(), 0, d.z())), d.structure().isEmpty() ? biome(d.biome()) : Component.literal(d.structure()),
					Texts.t(CLAVE + (d.generated() ? "estado.generada" : "estado.prevista")));
			src.sendSuccess(() -> line, false);
		}
		c.chest().ifPresent(pos -> src.sendSuccess(() -> Texts.t(CLAVE + "comando.cofre", pos.getX(), pos.getY(), pos.getZ()), false));
		LOGGER.info("Heraldia: tesoro: info {}", c.toTag());
		return 1;
	}
}
