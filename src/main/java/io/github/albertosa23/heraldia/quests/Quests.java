package io.github.albertosa23.heraldia.quests;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.roads.Roads;
import io.github.albertosa23.heraldia.roads.Names;
import io.github.albertosa23.heraldia.roads.RoadLayout;
import io.github.albertosa23.heraldia.command.InfoCommand;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.bosses.Phases;
import io.github.albertosa23.heraldia.mines.Mines;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.CompletableFuture;
import java.util.concurrent.ConcurrentHashMap;
import java.util.function.Consumer;
import java.util.stream.Collectors;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.UseBlockCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.HolderSet;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.tags.TagKey;
import net.minecraft.util.Util;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.animal.golem.IronGolem;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.trading.MerchantOffer;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.phys.AABB;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Encargos del tablón y reputación por aldea (T38): lo que toca el juego. La lógica pura está en {@link Generator},
 * {@link Objectives}, {@link Reputation} y {@link Data}.
 * <ul>
 * <li>El tablón: el atril del tablón de la plaza (el que tiene detrás al alguacil) enseña en el chat los encargos de su
 * aldea, con botones (texto clicable: vale con el cliente vanilla); y {@code /heraldia quest} desde dentro de una aldea.
 * Una aldea de Heraldia se reconoce por su estructura (la etiqueta heraldia:aldeas): también las ya generadas.</li>
 * <li>Qué hay alrededor (únicas con guardián, medianas y minas, aldeas vecinas) se busca una vez por aldea fuera del hilo
 * del servidor, con la misma búsqueda que /heraldia info nearby (no carga ni genera chunks).</li>
 * <li>Seguimiento sin trabajo por tick que recorra el mundo: la muerte de un guardián (evento), la oleada superada en la
 * arena (aviso de la arena), la llegada a un sitio (cada 2 s, solo los jugadores con un encargo de ir a un sitio) y lo
 * que se trae (al entregar).</li>
 * <li>Reputación: sube al entregar, baja al golpear o matar a un aldeano o gólem de la aldea; el descuento lo pone
 * {@code VillagerPricesMixin} al abrir los tratos.</li>
 * </ul>
 * Todo se lee de la configuración en cada uso: encargos.activado, encargos.rotacion_dias y reputacion.activado se
 * recargan con /heraldia reload.
 */
public final class Quests {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String ENABLED = "encargos.activado", ROTATION = "encargos.rotacion_dias", REPUTATION = "reputacion.activado";
	static final TagKey<Structure> VILLAGES = TagKey.create(Registries.STRUCTURE, Heraldia.id("aldeas"));
	/** El alguacil del tablón (tablon.TAG_ALGUACIL): sus tratos son fijos y no llevan descuento. */
	public static final String BAILIFF = "heraldia_alguacil";
	/** Logros (tools/gen/encargos.py): heraldia:encargos/<id>, criterio «hecho». */
	static final String FIRST_ADVANCEMENT = "encargos/primero", TEN_ADVANCEMENT = "encargos/diez", FRIEND_ADVANCEMENT = "encargos/amigo",
			HERO_ADVANCEMENT = "encargos/heroe";
	static final int TEN = 10;
	private static final Map<String, CompletableFuture<Generator.Candidates>> CANDIDATES = new ConcurrentHashMap<>();
	/** Tablones ya apuntados en el log (aldea y periodo), para no repetirlo en cada clic. */
	private static final Set<String> REGISTERED = ConcurrentHashMap.newKeySet();

	private Quests() {
	}

	/** Los adjuntos, aparte para que los tests no registren nada al cargar la clase. */
	static final class Attachments {
		static final AttachmentType<Data> PLAYER = AttachmentRegistry.create(Heraldia.id("encargos"),
				b -> b.persistent(Data.CODEC).copyOnDeath());
		static final AttachmentType<World> WORLD = AttachmentRegistry.create(Heraldia.id("encargos_mundo"),
				b -> b.persistent(World.CODEC));

		private Attachments() {
		}
	}

	/** Una aldea de Heraldia: el chunk de su inicio, su estilo y su nombre. */
	record Village(int cx, int cz, String style, String name) {
		String key() {
			return Reputation.key(cx, cz);
		}
	}

	/** Una línea en Heraldia.onInitialize. */
	public static void register() {
		Attachments.PLAYER.identifier();
		Attachments.WORLD.identifier();
		UseBlockCallback.EVENT.register((player, level, hand, hit) -> {
			if (player instanceof ServerPlayer p && level instanceof ServerLevel sl && hand == net.minecraft.world.InteractionHand.MAIN_HAND
					&& level.getBlockState(hit.getBlockPos()).is(Blocks.LECTERN)) {
				lectern(p, sl, hit.getBlockPos());
			}
			return InteractionResult.PASS;     // el libro del atril se abre como siempre
		});
		ServerLivingEntityEvents.AFTER_DAMAGE.register((entity, source, base, taken, blocked) -> {
			if (taken > 0 && !entity.isDeadOrDying()) {
				attack(entity, source, false);
			}
		});
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			if (Phases.isGuardian(entity.entityTags())) {
				guardianKilled(entity, source);
			} else {
				attack(entity, source, true);
			}
		});
		ServerTickEvents.END_SERVER_TICK.register(server -> {
			if (server.getTickCount() % Objectives.EVERY_TICKS == 0) {
				arrivals(server);
			}
		});
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
			CANDIDATES.clear();
			REGISTERED.clear();
		});
	}

	static boolean enabled() {
		return HeraldiaConfig.get().getBool(ENABLED);
	}

	static boolean withReputation() {
		return HeraldiaConfig.get().getBool(REPUTATION);
	}

	static Map<String, String> language(@Nullable ServerPlayer p) {
		return p == null ? Texts.language("es_es") : Texts.language(p);
	}

	// --- datos ---

	public static Data data(Player p) {
		Data d = p.getAttached(Attachments.PLAYER);
		return d == null ? Data.EMPTY : d;
	}

	static void save(Player p, Data d) {
		p.setAttached(Attachments.PLAYER, d);
	}

	public static World world(MinecraftServer server) {
		World m = server.overworld().getAttached(Attachments.WORLD);
		return m == null ? World.EMPTY : m;
	}

	static void saveWorld(MinecraftServer server, World m) {
		server.overworld().setAttached(Attachments.WORLD, m);
	}

	// --- aldeas ---

	/** La aldea de Heraldia en cuya caja está la posición (solo chunks cargados; en otra dimensión, ninguna). */
	static @Nullable Village villageAt(ServerLevel level, BlockPos pos) {
		if (level.dimension() != Level.OVERWORLD || !level.isLoaded(pos)) {
			return null;
		}
		Optional<HolderSet.Named<Structure>> set = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).get(VILLAGES);
		if (set.isEmpty()) {
			return null;
		}
		StructureStart start = level.structureManager().getStructureAt(pos, set.get());
		if (start == null || !start.isValid()) {
			return null;
		}
		Identifier id = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).getKey(start.getStructure());
		String style = id == null ? "" : id.getPath();
		if (style.endsWith("_grande")) {
			style = style.substring(0, style.length() - "_grande".length());
		}
		int cx = start.getChunkPos().x(), cz = start.getChunkPos().z();
		return new Village(cx, cz, style, name(level.getSeed(), cx, cz));
	}

	/** Nombre de la aldea con el inicio en ese chunk: el de los carteles de los caminos ({@link Names}). */
	static String name(long seed, int cx, int cz) {
		String[] n = Names.of(seed, cx * 16 + 8, cz * 16 + 8);
		return n[0] + " " + n[1];
	}

	static String family(String style) {
		JsonObject styles = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		JsonElement f = styles.get(style);
		return f == null ? "" : f.getAsString();
	}

	// --- candidatos (fuera del hilo del servidor) ---

	/** Qué hay alrededor de la aldea (sin la arena, que se mira en cada tablón): una vez por aldea y arranque. */
	private static CompletableFuture<Generator.Candidates> candidates(ServerLevel level, Village a) {
		return CANDIDATES.computeIfAbsent(a.key(), k -> {
			List<InfoCommand.Group> groups = InfoCommand.groups(level);
			Set<String> withGuardian = level.getServer().getAdvancements().getAllAdvancements().stream()
					.map(h -> h.id())
					.filter(id -> id.getNamespace().equals(Heraldia.MOD_ID) && id.getPath().startsWith("unicas/") && id.getPath().endsWith("/guardian"))
					.map(id -> id.getPath().substring("unicas/".length(), id.getPath().length() - "/guardian".length()))
					.collect(Collectors.toSet());
			String family = family(a.style());
			long t0 = System.nanoTime();
			return CompletableFuture.supplyAsync(() -> search(level, a, groups, withGuardian, family), Util.backgroundExecutor())
					.whenComplete((c, e) -> {
						if (e != null) {
							LOGGER.error("Heraldia: encargos: no se pudo buscar alrededor de {}", a.name(), e);
							CANDIDATES.remove(k);
						} else {
							LOGGER.info("Heraldia: encargos: alrededor de {} ({}, {}): {} guardianes, {} lugares, {} vecinas en {} ms",
									a.name(), a.cx(), a.cz(), c.guardians().size(), c.places().size(), c.neighbors().size(),
									(System.nanoTime() - t0) / 1_000_000);
						}
					});
		});
	}

	static Generator.Candidates search(ServerLevel level, Village a, List<InfoCommand.Group> groups, Set<String> withGuardian, String family) {
		BlockPos center = new BlockPos(a.cx() * 16 + 8, 64, a.cz() * 16 + 8);
		List<InfoCommand.Group> uniques = new ArrayList<>(), others = new ArrayList<>();
		for (InfoCommand.Group g : groups) {
			Identifier id = g.structures().getFirst().unwrapKey().orElseThrow().identifier();
			if (UniqueSeparation.isUnique(id)) {
				uniques.add(g);
			} else if (MediumStructures.isMedium(id) || Mines.isMine(id)) {
				others.add(g);
			}
		}
		List<Generator.Objective> guardians = new ArrayList<>(), places = new ArrayList<>();
		for (InfoCommand.Found f : InfoCommand.search(level, uniques, center, Generator.GUARDIAN_RADIUS)) {
			String sid = f.structure().unwrapKey().orElseThrow().identifier().getPath().substring("unicas/".length());
			if (withGuardian.contains(sid)) {
				guardians.add(target(sid, f, center));
			}
		}
		for (InfoCommand.Found f : InfoCommand.search(level, others, center, Generator.PLACE_RADIUS)) {
			places.add(target(f.structure().unwrapKey().orElseThrow().identifier().toString(), f, center));
		}
		List<Generator.Objective> neighbors = new ArrayList<>();
		for (long v : Roads.neighbors(level, a.cx(), a.cz())) {
			int x = RoadLayout.px(v), z = RoadLayout.pz(v);
			neighbors.add(new Generator.Objective(name(level.getSeed(), Math.floorDiv(x, 16), Math.floorDiv(z, 16)), x, z,
					(int) Math.hypot(x - center.getX(), z - center.getZ())));
		}
		java.util.Comparator<Generator.Objective> near = java.util.Comparator.comparingInt(Generator.Objective::distance);
		guardians.sort(near);
		places.sort(near);
		neighbors.sort(near);
		return new Generator.Candidates(family, guardians, places, neighbors, false);
	}

	private static Generator.Objective target(String id, InfoCommand.Found f, BlockPos center) {
		return new Generator.Objective(id, f.pos().getX(), f.pos().getZ(), (int) Math.sqrt(f.distanceSq()));
	}

	/** El tablón de la aldea en este periodo, cuando esté listo (en el hilo del servidor). */
	static void withBoard(ServerLevel level, Village a, Consumer<Component> out, Map<String, String> l, Consumer<List<Quest>> f) {
		CompletableFuture<Generator.Candidates> fut = candidates(level, a);
		if (!fut.isDone()) {
			out.accept(Texts.t(l, "heraldia.encargos.preparando", a.name()).withStyle(ChatFormatting.GRAY));
		}
		MinecraftServer server = level.getServer();
		fut.thenAcceptAsync(c -> {
			World m = world(server);
			int days = HeraldiaConfig.get().getInt(ROTATION);
			long period = Generator.period(level.getGameTime(), days);
			long start = Generator.start(period, days);
			// los caídos antes de este periodo ya no salen; los que caen durante él siguen hasta que rote (ver Mundo.caidoAntes)
			List<Generator.Objective> alive = c.guardians().stream().filter(o -> !m.fellBefore(o.id(), o.x(), o.z(), start)).toList();
			boolean arena = HeraldiaConfig.get().getBool("arena.activado") && Arena.center() != null;
			Generator.Candidates now = new Generator.Candidates(c.family(), alive, c.places(), c.neighbors(), arena);
			List<Quest> t = Generator.board(level.getSeed(), a.cx(), a.cz(), period, now);
			if (REGISTERED.add(a.key() + "@" + period + "@" + t.hashCode())) {
				LOGGER.info("Heraldia: encargos: tablón de {} ({}, {}), periodo {}: {}", a.name(), a.cx(), a.cz(), period,
						t.stream().map(e -> e.gap() + 1 + "=" + e.type().id() + ":" + e.target() + ":" + e.amount() + "@" + e.x() + "," + e.z())
								.collect(Collectors.joining(" ")));
			}
			f.accept(t);
		}, server).exceptionally(e -> {
			LOGGER.error("Heraldia: encargos: tablón de {}", a.name(), e);
			return null;
		});
	}

	/** ¿Es de vencer a un guardián que ya ha caído? */
	static boolean hasFallen(World m, Quest e) {
		return e.type() == Type.GUARDIAN && m.hasFallen(e.target(), e.x(), e.z());
	}

	// --- el atril del tablón ---

	/** Clic en un atril: si es el del tablón (con el alguacil detrás, dentro de una aldea), enseña el tablón en el chat. */
	static void lectern(ServerPlayer p, ServerLevel level, BlockPos pos) {
		if (!enabled()) {
			return;
		}
		List<Villager> bailiff = level.getEntitiesOfClass(Villager.class, new AABB(pos).inflate(2), v -> v.entityTags().contains(BAILIFF));
		if (bailiff.isEmpty()) {
			return;
		}
		Village a = villageAt(level, pos);
		if (a != null) {
			LOGGER.info("Heraldia: encargos: {} mira el tablón de {}", p.getGameProfile().name(), a.name());
			Map<String, String> l = language(p);
			withBoard(level, a, p::sendSystemMessage, l, t -> board(p, a, t, p::sendSystemMessage, l));
		}
	}

	// --- textos ---

	static Component button(Map<String, String> l, String key, String order, ChatFormatting color) {
		return Texts.t(l, key).withStyle(s -> s.withColor(color).withClickEvent(new ClickEvent.RunCommand(order))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(order))));
	}

	static Component tier(Map<String, String> l, Reputation.Tier n) {
		return Texts.t(l, "heraldia.encargos.nivel." + n.id());
	}

	/** Qué pide el encargo, con la pista del sitio vista desde (x, z): «Trae 16 × Pan», «Vence al guardián de...». */
	static MutableComponent description(Map<String, String> l, Quest e, int x, int z) {
		MutableComponent clue = e.withPlace()
				? Texts.t(l, "heraldia.encargos.pista", Texts.t(l, "heraldia.info.dir." + Objectives.bearing(x, z, e.x(), e.z())),
				Objectives.approximate(x, z, e.x(), e.z()))
				: Component.empty();
		return switch (e.type()) {
			case BRING -> Texts.t(l, "heraldia.encargos.desc.traer", e.amount(), item(e.target()));
			case GUARDIAN -> Texts.t(l, "heraldia.encargos.desc.guardian", Texts.t(l, "heraldia.unicas." + e.target() + ".nombre"), clue);
			case EXPLORE -> Texts.t(l, "heraldia.encargos.desc.explorar", place(l, e.target()), clue);
			case JOURNEY -> Texts.t(l, "heraldia.encargos.desc.viaje", e.target(), clue);
			case ARENA -> Texts.t(l, "heraldia.encargos.desc.arena", e.amount());
		};
	}

	static Component item(String id) {
		Identifier i = Identifier.tryParse(id);
		Item it = i == null ? Items.AIR : BuiltInRegistries.ITEM.getValue(i);
		return Component.translatable(it.getDescriptionId());
	}

	/** Nombre del tipo de estructura que explorar: «posada de camino», «entrada a mina pequeña»... */
	static Component place(Map<String, String> l, String structureId) {
		Identifier id = Identifier.tryParse(structureId);
		if (id != null && MediumStructures.isMedium(id)) {
			return Texts.t(l, "heraldia.medianas." + id.getPath().split("/")[1] + ".nombre");
		}
		if (id != null && Mines.isMine(id)) {
			return Texts.t(l, "heraldia.minas." + id.getPath().split("/")[1] + ".nombre");
		}
		return Component.literal(structureId);
	}

	static Component reward(Map<String, String> l, Quest e, boolean rep) {
		return rep ? Texts.t(l, "heraldia.encargos.paga", e.emeralds(), e.experience(), e.reputation())
				: Texts.t(l, "heraldia.encargos.paga.sin_reputacion", e.emeralds(), e.experience());
	}

	/** El tablón de la aldea en el chat. */
	static void board(ServerPlayer p, Village a, List<Quest> t, Consumer<Component> out, Map<String, String> l) {
		Data d = data(p);
		boolean rep = withReputation();
		out.accept(Texts.t(l, "heraldia.encargos.tablon.titulo", a.name()).withStyle(ChatFormatting.GOLD));
		if (rep) {
			Reputation.Tier n = d.tier(a.key());
			out.accept(Texts.t(l, "heraldia.encargos.tablon.reputacion", tier(l, n), d.reputation(a.key()))
					.withStyle(n == Reputation.Tier.HERO ? ChatFormatting.LIGHT_PURPLE : ChatFormatting.YELLOW));
		}
		int x = p.getBlockX(), z = p.getBlockZ();
		World m = world(p.level().getServer());
		for (Quest e : t) {
			MutableComponent line = Texts.t(l, "heraldia.encargos.linea", e.gap() + 1, description(l, e, x, z), reward(l, e, rep));
			line.append(" ");
			if (d.done(e.id())) {
				line.append(Texts.t(l, "heraldia.encargos.estado.entregado").withStyle(ChatFormatting.GRAY));
			} else if (d.has(e.id())) {
				line.append(Texts.t(l, "heraldia.encargos.estado.aceptado").withStyle(ChatFormatting.GREEN));
			} else if (hasFallen(m, e)) {
				line.append(Texts.t(l, "heraldia.encargos.estado.vencido").withStyle(ChatFormatting.GRAY));
			} else {
				line.append(button(l, "heraldia.encargos.boton.aceptar", "/heraldia quest accept " + (e.gap() + 1), ChatFormatting.AQUA));
			}
			out.accept(line);
		}
		long days = Math.max(1, (Generator.remaining(p.level().getGameTime(), HeraldiaConfig.get().getInt(ROTATION)) + Generator.DAY - 1) / Generator.DAY);
		out.accept(Texts.t(l, "heraldia.encargos.tablon.rota", days).withStyle(ChatFormatting.GRAY));
		out.accept(Component.empty().append(button(l, "heraldia.encargos.boton.mios", "/heraldia quest list", ChatFormatting.AQUA))
				.append(" ").append(button(l, "heraldia.encargos.boton.entregar", "/heraldia quest turnin", ChatFormatting.GREEN)));
	}

	// --- comandos: /heraldia quest [list | accept <number> | abandon <number> | turnin] ---

	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("quest")
				.executes(ctx -> main(ctx))
				.then(Commands.literal("list").executes(Quests::list))
				.then(Commands.literal("accept").then(Commands.argument("number", IntegerArgumentType.integer(1, Generator.MAX))
						.executes(ctx -> accept(ctx, IntegerArgumentType.getInteger(ctx, "number")))))
				.then(Commands.literal("abandon").then(Commands.argument("number", IntegerArgumentType.integer(1, Data.MAX_ACTIVE))
						.executes(ctx -> abandon(ctx, IntegerArgumentType.getInteger(ctx, "number")))))
				.then(Commands.literal("turnin").executes(Quests::deliver));
	}

	private record Use(ServerPlayer p, ServerLevel level, Map<String, String> l, Consumer<Component> out) {
	}

	/** El jugador que ejecuta la orden (la respuesta va a la fuente: también sale en la consola con «execute as»). */
	private static @Nullable Use use(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		CommandSourceStack src = ctx.getSource();
		ServerPlayer p = src.getPlayerOrException();
		Map<String, String> l = language(p);
		if (!enabled()) {
			src.sendFailure(Texts.t(l, "heraldia.encargos.desactivados"));
			return null;
		}
		return new Use(p, p.level(), l, c -> src.sendSuccess(() -> c, false));
	}

	private static @Nullable Village here(Use u) {
		Village a = villageAt(u.level(), u.p().blockPosition());
		if (a == null) {
			u.out().accept(Texts.t(u.l(), "heraldia.encargos.fuera").withStyle(ChatFormatting.RED));
		}
		return a;
	}

	private static int main(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		Use u = use(ctx);
		if (u == null) {
			return 0;
		}
		Village a = villageAt(u.level(), u.p().blockPosition());
		if (a == null) {
			return list(ctx);
		}
		withBoard(u.level(), a, u.out(), u.l(), t -> board(u.p(), a, t, u.out(), u.l()));
		return 1;
	}

	private static int list(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		Use u = use(ctx);
		if (u == null) {
			return 0;
		}
		Data d = data(u.p());
		Map<String, String> l = u.l();
		u.out().accept(Texts.t(l, "heraldia.encargos.mios.titulo", d.active().size(), Data.MAX_ACTIVE, d.completed())
				.withStyle(ChatFormatting.GOLD));
		int x = u.p().getBlockX(), z = u.p().getBlockZ();
		long seed = u.level().getSeed();
		World m = world(u.level().getServer());
		for (int i = 0; i < d.active().size(); i++) {
			Data.Active a = d.active().get(i);
			Quest e = a.quest();
			String state = a.met() ? "cumplido" : hasFallen(m, e) ? "caido" : "en_curso";
			MutableComponent line = Texts.t(l, "heraldia.encargos.mio", i + 1, description(l, e, x, z),
					name(seed, e.villageX(), e.villageZ()), Texts.t(l, "heraldia.encargos.estado." + state));
			line.append(" ").append(button(l, "heraldia.encargos.boton.abandonar", "/heraldia quest abandon " + (i + 1), ChatFormatting.RED));
			u.out().accept(line);
		}
		if (d.active().isEmpty()) {
			u.out().accept(Texts.t(l, "heraldia.encargos.mios.ninguno").withStyle(ChatFormatting.GRAY));
		}
		if (withReputation()) {
			for (Map.Entry<String, Integer> r : d.reputation().entrySet()) {
				int[] c = Reputation.chunk(r.getKey());
				if (c != null && r.getValue() != 0) {
					u.out().accept(Texts.t(l, "heraldia.encargos.mios.reputacion", name(seed, c[0], c[1]),
							tier(l, Reputation.tier(r.getValue())), r.getValue()));
				}
			}
		}
		return d.active().size();
	}

	private static int accept(CommandContext<CommandSourceStack> ctx, int n) throws CommandSyntaxException {
		Use u = use(ctx);
		Village a = u == null ? null : here(u);
		if (a == null) {
			return 0;
		}
		withBoard(u.level(), a, u.out(), u.l(), t -> {
			if (n > t.size()) {
				u.out().accept(Texts.t(u.l(), "heraldia.encargos.no_existe", n, t.size()).withStyle(ChatFormatting.RED));
				return;
			}
			Quest e = t.get(n - 1);
			Data d = data(u.p());
			String reason = hasFallen(world(u.level().getServer()), e) ? "caido" : d.notAcceptable(e);
			if (reason != null) {
				u.out().accept(Texts.t(u.l(), "heraldia.encargos.no_aceptable." + reason, Data.MAX_ACTIVE).withStyle(ChatFormatting.RED));
				return;
			}
			save(u.p(), d.accept(e));
			u.out().accept(Texts.t(u.l(), "heraldia.encargos.aceptado", description(u.l(), e, u.p().getBlockX(), u.p().getBlockZ()))
					.withStyle(ChatFormatting.GREEN));
			LOGGER.info("Heraldia: encargos: {} acepta {} ({} {} {} en {}, {})", u.p().getGameProfile().name(), e.id(), e.type().id(),
					e.target(), e.amount(), e.x(), e.z());
		});
		return 1;
	}

	private static int abandon(CommandContext<CommandSourceStack> ctx, int n) throws CommandSyntaxException {
		Use u = use(ctx);
		if (u == null) {
			return 0;
		}
		Data d = data(u.p());
		if (n > d.active().size()) {
			u.out().accept(Texts.t(u.l(), "heraldia.encargos.no_existe", n, d.active().size()).withStyle(ChatFormatting.RED));
			return 0;
		}
		Quest e = d.active().get(n - 1).quest();
		save(u.p(), d.abandon(n - 1));
		u.out().accept(Texts.t(u.l(), "heraldia.encargos.abandonado", description(u.l(), e, u.p().getBlockX(), u.p().getBlockZ())));
		return 1;
	}

	private static int deliver(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		Use u = use(ctx);
		Village a = u == null ? null : here(u);
		if (a == null) {
			return 0;
		}
		ServerPlayer p = u.p();
		Data d = data(p);
		boolean rep = withReputation();
		int delivered = 0;
		for (Data.Active act : List.copyOf(d.active())) {
			Quest e = act.quest();
			if (!e.village().equals(a.key())) {
				continue;
			}
			Item item = e.type() == Type.BRING ? itemOf(e.target()) : null;
			int has = item == null ? 0 : count(p.getInventory(), item);
			if (!Objectives.deliverable(act, has)) {
				if (e.type() == Type.BRING) {
					u.out().accept(Texts.t(u.l(), "heraldia.encargos.faltan", has, e.amount(), item(e.target())).withStyle(ChatFormatting.YELLOW));
				}
				continue;
			}
			if (item != null) {
				clear(p.getInventory(), item, e.amount());
			}
			Reputation.Tier before = d.tier(a.key());
			d = d.deliver(e.id(), rep);
			pay(p, e);
			delivered++;
			u.out().accept(Texts.t(u.l(), "heraldia.encargos.entregado", description(u.l(), e, p.getBlockX(), p.getBlockZ()),
					reward(u.l(), e, rep)).withStyle(ChatFormatting.GREEN));
			Reputation.Tier after = d.tier(a.key());
			if (rep && after != before) {
				u.out().accept(Texts.t(u.l(), "heraldia.encargos.sube", a.name(), tier(u.l(), after)).withStyle(ChatFormatting.LIGHT_PURPLE));
			}
			LOGGER.info("Heraldia: encargos: {} entrega {} en {}: {} esmeraldas, {} de experiencia; reputación {} ({})",
					p.getGameProfile().name(), e.id(), a.name(), e.emeralds(), e.experience(), d.reputation(a.key()), after.id());
		}
		if (delivered == 0) {
			u.out().accept(Texts.t(u.l(), "heraldia.encargos.nada").withStyle(ChatFormatting.GRAY));
			return 0;
		}
		save(p, d);
		MinecraftServer server = p.level().getServer();
		World m = world(server);
		for (int i = 0; i < delivered; i++) {
			m = m.isCompleted();
		}
		saveWorld(server, m);
		advancements(p, d);
		return delivered;
	}

	static @Nullable Item itemOf(String id) {
		Identifier i = Identifier.tryParse(id);
		return i == null ? null : BuiltInRegistries.ITEM.getOptional(i).orElse(null);
	}

	/** Cuántos de ese objeto lleva en el inventario (sin mirar el cursor ni la mesa de crafteo). */
	static int count(Inventory inv, Item item) {
		int n = 0;
		for (int i = 0; i < inv.getContainerSize(); i++) {
			ItemStack s = inv.getItem(i);
			if (s.is(item)) {
				n += s.getCount();
			}
		}
		return n;
	}

	static void clear(Inventory inv, Item item, int howMany) {
		for (int i = 0; i < inv.getContainerSize() && howMany > 0; i++) {
			ItemStack s = inv.getItem(i);
			if (s.is(item)) {
				int q = Math.min(howMany, s.getCount());
				s.shrink(q);
				howMany -= q;
			}
		}
		inv.setChanged();
	}

	static void pay(ServerPlayer p, Quest e) {
		p.getInventory().placeItemBackInInventory(new ItemStack(Items.EMERALD, e.emeralds()), net.minecraft.util.Prediction.SERVER_ONLY);   // al suelo si no cabe
		p.giveExperiencePoints(e.experience());
		io.github.albertosa23.heraldia.treasure.Treasure.reward(p);   // a veces, un fragmento de mapa del tesoro (T40)
	}

	static void advancements(ServerPlayer p, Data d) {
		if (d.completed() >= 1) {
			advancement(p, FIRST_ADVANCEMENT);
		}
		if (d.completed() >= TEN) {
			advancement(p, TEN_ADVANCEMENT);
		}
		if (d.villagesWith(Reputation.Tier.FRIEND) > 0) {
			advancement(p, FRIEND_ADVANCEMENT);
		}
		if (d.villagesWith(Reputation.Tier.HERO) > 0) {
			advancement(p, HERO_ADVANCEMENT);
		}
	}

	static void advancement(ServerPlayer p, String route) {
		AdvancementHolder h = p.level().getServer().getAdvancements().get(Heraldia.id(route));
		if (h != null) {
			p.getAdvancements().award(h, "hecho");
		}
	}

	// --- seguimiento ---

	/** Un guardián ha muerto: se apunta y cumple los encargos de quien lo mata y de los que están cerca. */
	static void guardianKilled(LivingEntity e, DamageSource source) {
		if (!(e.level() instanceof ServerLevel level)) {
			return;
		}
		String sid = Phases.unique(e.entityTags());
		if (sid == null) {
			return;
		}
		int x = e.getBlockX(), z = e.getBlockZ();
		MinecraftServer server = level.getServer();
		saveWorld(server, world(server).falls(sid, x, z, level.getGameTime()));
		if (!enabled()) {
			return;
		}
		List<ServerPlayer> whom = new ArrayList<>(level.getEntitiesOfClass(ServerPlayer.class,
				new AABB(e.blockPosition()).inflate(Objectives.PARTICIPATE_RADIUS)));
		if (source.getEntity() instanceof ServerPlayer k && !whom.contains(k)) {
			whom.add(k);
		}
		for (ServerPlayer p : whom) {
			complete(p, en -> Objectives.guardian(en, sid, x, z));
		}
	}

	/** Cada 2 s: los jugadores con un encargo de ir a un sitio, ¿han llegado? */
	static void arrivals(MinecraftServer server) {
		if (!enabled()) {
			return;
		}
		for (ServerPlayer p : server.overworld().players()) {
			Data d = p.getAttached(Attachments.PLAYER);
			if (d != null && Objectives.awaitsArrival(d.active())) {
				int x = p.getBlockX(), z = p.getBlockZ();
				complete(p, e -> Objectives.arrival(e, x, z));
			}
		}
	}

	/** Aviso de la arena: el jugador ha superado la oleada {@code n}. */
	public static void waveCleared(ServerPlayer p, int n) {
		if (enabled()) {
			complete(p, e -> Objectives.wave(e, n));
		}
	}

	static void complete(ServerPlayer p, java.util.function.Predicate<Quest> cond) {
		Data d = p.getAttached(Attachments.PLAYER);
		if (d == null) {
			return;
		}
		Data newValue = d.complete(cond);
		if (newValue == d) {
			return;
		}
		save(p, newValue);
		Map<String, String> l = language(p);
		long seed = p.level().getSeed();
		for (int i = 0; i < newValue.active().size(); i++) {
			if (newValue.active().get(i).met() && !d.active().get(i).met()) {
				Quest e = newValue.active().get(i).quest();
				p.sendSystemMessage(Texts.t(l, "heraldia.encargos.cumplido", description(l, e, p.getBlockX(), p.getBlockZ()),
						name(seed, e.villageX(), e.villageZ())).withStyle(ChatFormatting.GREEN));
				LOGGER.info("Heraldia: encargos: {} cumple {} ({})", p.getGameProfile().name(), e.id(), e.type().id());
			}
		}
	}

	// --- reputación ---

	/** Un jugador golpea o mata a un aldeano o a un gólem de hierro dentro de una aldea de Heraldia: baja su reputación. */
	static void attack(LivingEntity e, DamageSource source, boolean death) {
		boolean golem = e instanceof IronGolem;
		if (!(golem || e instanceof Villager) || !(source.getEntity() instanceof ServerPlayer p) || !(e.level() instanceof ServerLevel level)
				|| !withReputation()) {
			return;
		}
		Village a = villageAt(level, e.blockPosition());
		if (a != null) {
			add(p, a, Reputation.attack(golem, death), (death ? "mata" : "golpea") + " a un " + (golem ? "gólem" : "aldeano"));
		}
	}

	// --- API para otros sistemas (p. ej. las caravanas) ---

	/**
	 * Suma (o resta) reputación del jugador con la aldea de Heraldia cuyo inicio está en el chunk (chunkX, chunkZ), sin
	 * salirse de [{@link Reputation#MIN}, {@link Reputation#MAX}]: avisa al jugador si cambia de nivel, concede los
	 * logros de amigo y héroe y lo apunta en el log con {@code reason}. Sin efecto (devuelve la reputación que tenía) con
	 * reputacion.activado a false. En el hilo del servidor. Devuelve la reputación nueva.
	 */
	public static int addReputation(ServerPlayer p, int chunkX, int chunkZ, int points, String reason) {
		Village a = new Village(chunkX, chunkZ, "", name(p.level().getSeed(), chunkX, chunkZ));
		if (!withReputation()) {
			return data(p).reputation(a.key());
		}
		return add(p, a, points, reason);
	}

	/** Como {@link #addReputation(ServerPlayer, int, int, int, String)} con la aldea en cuya caja está {@code pos};
	 *  devuelve null si ahí no hay ninguna aldea de Heraldia (o el chunk no está cargado). */
	public static @Nullable Integer addReputation(ServerPlayer p, ServerLevel level, BlockPos pos, int points, String reason) {
		Village a = villageAt(level, pos);
		return a == null ? null : addReputation(p, a.cx(), a.cz(), points, reason);
	}

	/** Reputación del jugador con la aldea del chunk (chunkX, chunkZ) (0 si nunca ha tratado con ella). */
	public static int reputation(Player p, int chunkX, int chunkZ) {
		return data(p).reputation(Reputation.key(chunkX, chunkZ));
	}

	/** El chunk del inicio de la aldea de Heraldia en cuya caja está {@code pos}, o null (para usar con lo de arriba). */
	public static net.minecraft.world.level.@Nullable ChunkPos village(ServerLevel level, BlockPos pos) {
		Village a = villageAt(level, pos);
		return a == null ? null : new net.minecraft.world.level.ChunkPos(a.cx(), a.cz());
	}

	static int add(ServerPlayer p, Village a, int points, String reason) {
		Data d = data(p);
		Reputation.Tier before = d.tier(a.key());
		Data newValue = d.addReputation(a.key(), points);
		save(p, newValue);
		Reputation.Tier after = newValue.tier(a.key());
		if (after != before) {
			Map<String, String> l = language(p);
			p.sendSystemMessage(after.compareTo(before) > 0
					? Texts.t(l, "heraldia.encargos.sube", a.name(), tier(l, after)).withStyle(ChatFormatting.LIGHT_PURPLE)
					: Texts.t(l, "heraldia.encargos.baja", a.name(), tier(l, after)).withStyle(ChatFormatting.RED));
			advancements(p, newValue);
		}
		LOGGER.info("Heraldia: encargos: {} {} de {}: reputación {}", p.getGameProfile().name(), reason, a.name(),
				newValue.reputation(a.key()));
		return newValue.reputation(a.key());
	}

	/**
	 * Lo llama VillagerPreciosMixin al final de {@code Villager.updateSpecialPrices} (al abrir los tratos): rebaja cada
	 * oferta según la reputación del jugador con la aldea del aldeano y le saluda. Sin efecto fuera de una aldea, con la
	 * reputación desactivada, con el alguacil o si el jugador ya tiene Héroe de la aldea.
	 */
	public static void prices(Villager v, Player player) {
		if (!(player instanceof ServerPlayer p) || !(v.level() instanceof ServerLevel level) || !withReputation()
				|| v.entityTags().contains(BAILIFF)) {
			return;
		}
		Data d = p.getAttached(Attachments.PLAYER);
		if (d == null || d.reputation().isEmpty()) {
			return;
		}
		Village a = villageAt(level, v.blockPosition());
		if (a == null) {
			return;
		}
		Reputation.Tier n = d.tier(a.key());
		boolean hero = p.hasEffect(MobEffects.HERO_OF_THE_VILLAGE);
		int total = 0;
		for (MerchantOffer o : v.getOffers()) {
			int r = Reputation.discountFor(n, o.getBaseCostA().getCount(), true, hero);
			o.addToSpecialPriceDiff(r);
			total += r;
		}
		if (n != Reputation.Tier.UNKNOWN) {
			p.sendOverlayMessage(Texts.t(language(p), "heraldia.encargos.saludo." + n.id(), a.name()).withStyle(ChatFormatting.GREEN));
			level.sendParticles(ParticleTypes.HAPPY_VILLAGER, v.getX(), v.getY() + 1.8, v.getZ(), 4, 0.3, 0.3, 0.3, 0);
			LOGGER.debug("Heraldia: encargos: {} en {}: {} ({} en total)", p.getGameProfile().name(), a.name(), n.id(), total);
		}
	}

	/** Para /heraldia status: entregados entre todos y por el jugador, y sus aldeas amigas y de las que es héroe. */
	public static List<Component> state(MinecraftServer server, @Nullable ServerPlayer p) {
		List<Component> out = new ArrayList<>();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (!cfg.getBool(ENABLED)) {
			out.add(Texts.t("heraldia.estado.encargos.no"));
			return out;
		}
		out.add(Texts.t("heraldia.estado.encargos", world(server).completed()));
		if (p != null) {
			Data d = data(p);
			out.add(cfg.getBool(REPUTATION)
					? Texts.t("heraldia.estado.encargos.tuyos", d.completed(), d.villagesWith(Reputation.Tier.FRIEND), d.villagesWith(Reputation.Tier.HERO))
					: Texts.t("heraldia.estado.encargos.tuyos.sin_reputacion", d.completed()));
		}
		return out;
	}
}
