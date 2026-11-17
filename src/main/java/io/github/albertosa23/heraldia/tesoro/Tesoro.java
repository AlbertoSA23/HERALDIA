package io.github.albertosa23.heraldia.tesoro;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.serialization.Codec;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comando.InfoCommand;
import io.github.albertosa23.heraldia.comando.LlaveCommand;
import io.github.albertosa23.heraldia.comando.Textos;
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
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Búsqueda del tesoro encadenada (T40). El fragmento de mapa (tabla heraldia:tesoro/fragmento, en el botín de medianas,
 * minas y únicas con la condición {@link PistaCondition}) se usa con clic derecho:
 * <ol>
 * <li>Sin descifrar: la cadena se elige FUERA del hilo del servidor ({@link Busqueda}: medianas y entradas a mina reales a
 * menos de tesoro.radio_max bloques, sin cargar ni generar chunks; {@link Planificador}, determinista con la semilla del
 * jugador: mundo, UUID y cuántas lleva descifradas, adjunto heraldia:tesoro_contador). Al acabar, en el hilo del servidor,
 * el fragmento se cambia por un mapa vanilla con la marca del primer destino, y la cadena entera queda en el objeto
 * (custom_data {@value Cadena#MARCA}, {@link Cadena}).</li>
 * <li>Con cadena: lejos de la marca, dice a cuántos bloques y hacia dónde queda; en una estructura, el mapa pasa a la
 * siguiente marca; en el tesoro, entierra el cofre (tabla heraldia:tesoro/cofre) en un sitio seguro ({@link Sitio}: solo
 * chunks ya cargados, nunca dentro ni encima de construcciones, con margen) y la cadena queda completada: su semilla se
 * apunta en el mundo (adjunto heraldia:tesoros del mundo principal), así que ni una copia del mapa da otro cofre.</li>
 * </ol>
 * Nada por tick: solo trabaja al usar una pista o con /heraldia treasure. Enganche para otros orígenes (p. ej. los
 * encargos): {@link #fragmento(ServerLevel)} o anidar la tabla heraldia:tesoro/fragmento.
 */
public final class Tesoro {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final ResourceKey<LootTable> FRAGMENTO = ResourceKey.create(Registries.LOOT_TABLE, Heraldia.id("tesoro/fragmento"));
	public static final ResourceKey<LootTable> COFRE = ResourceKey.create(Registries.LOOT_TABLE, Heraldia.id("tesoro/cofre"));
	static final String CLAVE = "heraldia.tesoro.";
	/** Jugadores con un fragmento descifrándose (en otro hilo): uno a la vez por jugador. */
	private static final Set<UUID> BUSCANDO = ConcurrentHashMap.newKeySet();

	private Tesoro() {
	}

	/** Los adjuntos, aparte para que los tests (ComandosTest arma el árbol de comandos) no registren nada. */
	static final class Datos {
		/** Pistas descifradas por el jugador (la n de su semilla); se conserva al morir. */
		static final AttachmentType<Integer> CONTADOR = AttachmentRegistry.create(Heraldia.id("tesoro_contador"),
				b -> b.persistent(Codec.INT).copyOnDeath());
		/** Semillas de las cadenas cuyo cofre ya está enterrado (en el mundo principal). */
		static final AttachmentType<List<Long>> COMPLETADAS = AttachmentRegistry.create(Heraldia.id("tesoros"),
				b -> b.persistent(Codec.LONG.listOf()));

		private Datos() {
		}
	}

	public static void registrar() {
		Registry.register(BuiltInRegistries.LOOT_CONDITION_TYPE, Heraldia.id("tesoro_pista"), PistaCondition.CODEC);
		LOGGER.debug("Heraldia: adjuntos {} y {} registrados", Datos.CONTADOR.identifier(), Datos.COMPLETADAS.identifier());
		UseItemCallback.EVENT.register(Tesoro::usar);
	}

	/** Un fragmento de mapa del tesoro nuevo (sin descifrar), de la tabla heraldia:tesoro/fragmento. */
	public static ItemStack fragmento(ServerLevel level) {
		LootParams params = new LootParams.Builder(level).create(LootContextParamSets.EMPTY);
		List<ItemStack> items = level.getServer().reloadableRegistries().getLootTable(FRAGMENTO).getRandomItems(params);
		return items.isEmpty() ? ItemStack.EMPTY : items.getFirst();
	}

	/** La marca de pista de un objeto ({@value Cadena#MARCA}), o null si no es una pista. */
	static CompoundTag marca(ItemStack stack) {
		CustomData data = stack.get(DataComponents.CUSTOM_DATA);
		return data == null ? null : data.copyTag().getCompound(Cadena.MARCA).orElse(null);
	}

	private static InteractionResult usar(Player p, Level lv, InteractionHand hand) {
		if (!(p instanceof ServerPlayer player) || !(lv instanceof ServerLevel level)) {
			return InteractionResult.PASS;
		}
		ItemStack stack = player.getItemInHand(hand);
		if (!stack.is(Items.PAPER) && !stack.is(Items.FILLED_MAP)) {
			return InteractionResult.PASS;   // salida temprana barata: casi todo lo que se usa no es una pista
		}
		CompoundTag tag = marca(stack);
		if (tag == null) {
			return InteractionResult.PASS;
		}
		Map<String, String> textos = textos(player);
		if (!HeraldiaConfig.get().getBool(PistaCondition.ACTIVADO)) {
			player.sendSystemMessage(t(textos, "desactivado").withStyle(ChatFormatting.GRAY));
		} else if (level.dimension() != Level.OVERWORLD) {
			player.sendSystemMessage(t(textos, "dimension").withStyle(ChatFormatting.GRAY));
		} else {
			Optional<Cadena> c = Cadena.deTag(tag);
			if (c.isEmpty()) {
				descifrar(player, level, textos);
			} else {
				seguir(player, level, hand, c.get(), textos);
			}
		}
		return InteractionResult.SUCCESS;
	}

	// --- descifrar ---

	private static void descifrar(ServerPlayer player, ServerLevel level, Map<String, String> textos) {
		UUID uuid = player.getUUID();
		if (!BUSCANDO.add(uuid)) {
			player.sendSystemMessage(t(textos, "ocupado").withStyle(ChatFormatting.GRAY));
			return;
		}
		player.sendSystemMessage(t(textos, "descifrando").withStyle(ChatFormatting.GRAY, ChatFormatting.ITALIC));
		int n = player.getAttachedOrElse(Datos.CONTADOR, 0);
		long semilla = Planificador.semilla(level.getSeed(), uuid, n);
		BlockPos origen = player.blockPosition();
		int radio = HeraldiaConfig.get().getInt(PistaCondition.RADIO);
		List<InfoCommand.Group> grupos = InfoCommand.groups(level);   // en el hilo del servidor: lee los registros
		long t0 = System.nanoTime();
		CompletableFuture.supplyAsync(() -> {
			Busqueda b = new Busqueda(level, grupos);
			Optional<List<Destino>> d = Planificador.planificar(semilla, origen.getX(), origen.getZ(), radio, b, b);
			LOGGER.info("Heraldia: tesoro: cadena de {} elegida en {} ms ({} casillas miradas, fuera del hilo del servidor): {}",
					player.getGameProfile().name(), (System.nanoTime() - t0) / 1_000_000, b.celdas, d.orElse(List.of()));
			return d;
		}, Util.backgroundExecutor()).thenAcceptAsync(d -> {
			BUSCANDO.remove(uuid);
			if (player.hasDisconnected()) {
				return;
			}
			int slot = slotFragmento(player.getInventory());
			if (slot < 0) {
				return;   // ya no lleva el fragmento (lo soltó mientras tanto)
			}
			if (d.isEmpty()) {
				player.sendSystemMessage(t(textos, "sin_destino", radio).withStyle(ChatFormatting.GRAY));
				return;
			}
			Cadena c = Cadena.nueva(semilla, origen.getX(), origen.getZ(), d.get());
			player.setAttached(Datos.CONTADOR, n + 1);
			player.getInventory().setItem(slot, mapa(level, c, textos));
			player.sendSystemMessage(t(textos, "descifrado", c.marcas()).withStyle(ChatFormatting.GOLD));
			level.playSound(null, player.blockPosition(), SoundEvents.UI_CARTOGRAPHY_TABLE_TAKE_RESULT, SoundSource.PLAYERS, 1, 1);
		}, level.getServer()).exceptionally(e -> {
			BUSCANDO.remove(uuid);
			LOGGER.error("Heraldia: tesoro: no se pudo descifrar el fragmento", e);
			return null;
		});
	}

	/** El hueco del inventario con un fragmento sin descifrar: el de la mano principal si lo es; si no, el primero. */
	static int slotFragmento(Inventory inv) {
		int sel = inv.getSelectedSlot();
		if (esFragmento(inv.getItem(sel))) {
			return sel;
		}
		for (int i = 0; i < inv.getContainerSize(); i++) {
			if (esFragmento(inv.getItem(i))) {
				return i;
			}
		}
		return -1;
	}

	static boolean esFragmento(ItemStack s) {
		CompoundTag m = marca(s);
		return m != null && Cadena.deTag(m).isEmpty();
	}

	// --- seguir la cadena ---

	private static void seguir(ServerPlayer player, ServerLevel level, InteractionHand hand, Cadena c, Map<String, String> textos) {
		int px = player.getBlockX(), pz = player.getBlockZ();
		Set<Long> completadas = completadas(level);
		switch (Avance.evaluar(c, px, pz, completadas)) {
			case HECHA -> player.sendSystemMessage(t(textos, "hecho").withStyle(ChatFormatting.GRAY));
			case LEJOS -> {
				Destino d = c.actual();
				player.sendSystemMessage(t(textos, "lejos", Avance.distanciaAproximada(d, px, pz), direccion(textos, d.x() - px, d.z() - pz))
						.withStyle(ChatFormatting.GRAY));
			}
			case SIGUIENTE -> {
				Cadena sig = c.avanzar();
				player.setItemInHand(hand, mapa(level, sig, textos));
				player.sendSystemMessage(t(textos, "paso", sig.paso() + 1, sig.marcas()).withStyle(ChatFormatting.GOLD));
				level.playSound(null, player.blockPosition(), SoundEvents.UI_CARTOGRAPHY_TABLE_TAKE_RESULT, SoundSource.PLAYERS, 1, 1);
			}
			case COFRE -> enterrar(player, level, hand, c, textos, completadas);
		}
	}

	private static void enterrar(ServerPlayer player, ServerLevel level, InteractionHand hand, Cadena c, Map<String, String> textos,
			Set<Long> completadas) {
		Destino t = c.actual();
		long t0 = System.nanoTime();
		Sitio.Eleccion e = Sitio.elegir(vista(level), t.x(), t.z());
		LOGGER.info("Heraldia: tesoro: sitio del cofre de {} en ({}, {}): {} en {} µs", player.getGameProfile().name(), t.x(), t.z(),
				e, (System.nanoTime() - t0) / 1000);
		if (e.motivo() == Sitio.Motivo.SIN_CARGAR) {
			player.sendSystemMessage(t(textos, "sin_sitio").withStyle(ChatFormatting.GRAY));
			return;
		}
		if (e.cofre().isEmpty()) {   // todo cargado y nada seguro: el tesoro se va un poco más allá
			Busqueda.Simple biomas = new Busqueda.Simple(level);
			Cadena movida = c.conTesoro(Planificador.moverTesoro(c, biomas));
			player.setItemInHand(hand, mapa(level, movida, textos));
			player.sendSystemMessage(t(textos, "movido").withStyle(ChatFormatting.YELLOW));
			return;
		}
		BlockPos pos = e.cofre().get();
		Direction mira = Direction.from2DDataValue(new Random(c.semilla()).nextInt(4));
		level.setBlock(pos, Blocks.CHEST.defaultBlockState().setValue(ChestBlock.FACING, mira), 3);
		if (level.getBlockEntity(pos) instanceof ChestBlockEntity be) {
			be.setLootTable(COFRE, c.semilla());
			be.applyComponents(DataComponentMap.builder().set(DataComponents.CUSTOM_NAME, t(textos, "cofre.titulo")).build(),
					DataComponentPatch.EMPTY);
			be.setChanged();
		}
		completadas.add(c.semilla());
		level.setAttached(Datos.COMPLETADAS, List.copyOf(completadas));
		Cadena hecha = c.conCofre(pos);
		ItemStack mapa = player.getItemInHand(hand).copy();
		decorar(mapa, hecha, textos);
		player.setItemInHand(hand, mapa);
		int dx = pos.getX() - player.getBlockX(), dz = pos.getZ() - player.getBlockZ();
		int dist = (int) Math.round(Math.sqrt((double) dx * dx + (double) dz * dz));
		player.sendSystemMessage((dist <= 2 ? t(textos, "cofre.aqui") : t(textos, "cofre", dist, direccion(textos, dx, dz)))
				.withStyle(ChatFormatting.GOLD));
		level.sendParticles(ParticleTypes.HAPPY_VILLAGER, pos.getX() + 0.5, pos.getY() + 1.5, pos.getZ() + 0.5, 30, 0.6, 0.6, 0.6, 0);
		level.playSound(null, pos, SoundEvents.PLAYER_LEVELUP, SoundSource.PLAYERS, 0.6f, 1.2f);
		LOGGER.info("Heraldia: tesoro: cofre de {} enterrado en {} {} {} (semilla {})", player.getGameProfile().name(), pos.getX(),
				pos.getY(), pos.getZ(), c.semilla());
	}

	/** Semillas de las cadenas ya completadas en este mundo (las del mundo principal). */
	static Set<Long> completadas(ServerLevel level) {
		return new HashSet<>(level.getAttachedOrElse(Datos.COMPLETADAS, List.of()));
	}

	/** El mundo para {@link Sitio}: solo chunks ya cargados (nunca carga ni genera uno). */
	static Sitio.Vista vista(ServerLevel level) {
		return new Sitio.Vista() {
			private LevelChunk chunk(int x, int z) {
				return level.getChunkSource().getChunkNow(x >> 4, z >> 4);
			}

			@Override
			public OptionalInt cima(int x, int z) {
				LevelChunk c = chunk(x, z);
				return c == null ? OptionalInt.empty() : OptionalInt.of(c.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15));
			}

			private BlockState estado(int x, int y, int z) {
				LevelChunk c = chunk(x, z);
				return c == null ? Blocks.AIR.defaultBlockState() : c.getBlockState(new BlockPos(x, y, z));
			}

			@Override
			public String bloque(int x, int y, int z) {
				return BuiltInRegistries.BLOCK.getKey(estado(x, y, z).getBlock()).toString();
			}

			@Override
			public boolean liquido(int x, int y, int z) {
				return !estado(x, y, z).getFluidState().isEmpty();
			}

			@Override
			public boolean enEstructura(int x, int y, int z) {
				return level.structureManager().getStructureWithPieceAt(new BlockPos(x, y, z), h -> true).isValid();
			}
		};
	}

	// --- el mapa ---

	/** Un mapa vanilla nuevo con la marca del destino en curso de la cadena (y la cadena en el objeto). */
	static ItemStack mapa(ServerLevel level, Cadena c, Map<String, String> textos) {
		Destino d = c.actual();
		boolean tesoro = d.tipo() == Destino.Tipo.TESORO;
		ItemStack m = MapItem.create(level, d.x(), d.z(), (byte) (tesoro ? 1 : 2), true, true);
		MapItem.renderBiomePreviewMap(level, m);
		MapItemSavedData.addTargetDecoration(m, new BlockPos(d.x(), 0, d.z()), "+", tesoro ? MapDecorationTypes.RED_X : MapDecorationTypes.TARGET_X);
		decorar(m, c, textos);
		return m;
	}

	/** Nombre, lore (la pista: qué es, bioma y dirección desde la marca anterior) y la cadena en custom_data. */
	static void decorar(ItemStack m, Cadena c, Map<String, String> textos) {
		MutableComponent nombre = c.completada() ? t(textos, "mapa.hecho") : t(textos, "mapa.nombre", c.paso() + 1, c.marcas());
		m.set(DataComponents.ITEM_NAME, nombre);
		m.set(DataComponents.CUSTOM_NAME, nombre.copy().withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GOLD)));
		List<Component> lore = new ArrayList<>();
		if (!c.completada()) {
			Destino d = c.actual();
			int[] desde = c.desde(c.paso());
			lore.add(t(textos, "pista." + d.tipo().id()).withStyle(s -> s.withItalic(false).withColor(ChatFormatting.YELLOW)));
			lore.add(t(textos, "pista.donde", bioma(d.bioma()), direccion(textos, d.x() - desde[0], d.z() - desde[1]))
					.withStyle(s -> s.withItalic(false).withColor(ChatFormatting.YELLOW)));
			if (!d.generada() && d.tipo() != Destino.Tipo.TESORO) {
				lore.add(t(textos, "pista.prevista").withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GRAY)));
			}
			lore.add(t(textos, "mapa.uso").withStyle(s -> s.withItalic(false).withColor(ChatFormatting.DARK_AQUA)));
		}
		m.set(DataComponents.LORE, new ItemLore(lore));
		m.set(DataComponents.RARITY, Rarity.UNCOMMON);
		CustomData.update(DataComponents.CUSTOM_DATA, m, tag -> tag.put(Cadena.MARCA, c.aTag()));
	}

	/** Nombre del bioma: el de su lang (lo traduce el cliente) o el id en bonito. */
	static Component bioma(String id) {
		Identifier i = Identifier.tryParse(id);
		if (i == null) {
			return Component.literal(id);
		}
		String bonito = i.getPath().replace('_', ' ');
		return Component.translatableWithFallback("biome." + i.getNamespace() + "." + i.getPath(), bonito);
	}

	static Component direccion(Map<String, String> textos, int dx, int dz) {
		return Textos.t(textos, "heraldia.info.dir." + InfoCommand.direction(dx, dz));
	}

	static Map<String, String> textos(ServerPlayer player) {
		return Textos.textos(player.clientInformation().language());
	}

	static MutableComponent t(Map<String, String> textos, String k, Object... args) {
		return Textos.t(textos, CLAVE + k, args);
	}

	// --- /heraldia treasure ---

	/** /heraldia treasure give [&lt;players&gt;] | info (operadores, nivel 2; lo registra Comandos). */
	public static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("treasure")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.literal("give")
						.executes(ctx -> dar(ctx, List.of(ctx.getSource().getPlayerOrException())))
						.then(Commands.argument("players", EntityArgument.players())
								.executes(ctx -> dar(ctx, EntityArgument.getPlayers(ctx, "players")))))
				.then(Commands.literal("info").executes(Tesoro::info));
	}

	private static int dar(CommandContext<CommandSourceStack> ctx, Collection<ServerPlayer> players) {
		int n = 0;
		for (ServerPlayer p : players) {
			ItemStack f = fragmento(p.level());
			if (!f.isEmpty()) {
				LlaveCommand.give(p, f);
				n++;
			}
		}
		int total = n;
		ctx.getSource().sendSuccess(() -> Textos.t(CLAVE + "comando.dado", total), true);
		return n;
	}

	private static int info(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		CompoundTag tag = marca(p.getMainHandItem());
		if (tag == null) {
			src.sendFailure(Textos.t(CLAVE + "comando.sin_pista"));
			return 0;
		}
		Optional<Cadena> oc = Cadena.deTag(tag);
		if (oc.isEmpty()) {
			src.sendSuccess(() -> Textos.t(CLAVE + "comando.sin_descifrar"), false);
			return 1;
		}
		Cadena c = oc.get();
		src.sendSuccess(() -> Textos.t(CLAVE + "comando.cadena", Long.toString(c.semilla()), Math.min(c.paso() + 1, c.marcas()), c.marcas()), false);
		for (int i = 0; i < c.destinos().size(); i++) {
			Destino d = c.destinos().get(i);
			Component line = Textos.t(CLAVE + "comando.destino", i + 1, Textos.t(CLAVE + "tipo." + d.tipo().id()),
					InfoCommand.coordinates(new BlockPos(d.x(), 0, d.z())), d.estructura().isEmpty() ? bioma(d.bioma()) : Component.literal(d.estructura()),
					Textos.t(CLAVE + (d.generada() ? "estado.generada" : "estado.prevista")));
			src.sendSuccess(() -> line, false);
		}
		c.cofre().ifPresent(pos -> src.sendSuccess(() -> Textos.t(CLAVE + "comando.cofre", pos.getX(), pos.getY(), pos.getZ()), false));
		LOGGER.info("Heraldia: tesoro: info {}", c.aTag());
		return 1;
	}
}
