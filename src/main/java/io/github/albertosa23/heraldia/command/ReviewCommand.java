package io.github.albertosa23.heraldia.command;

import com.google.gson.JsonObject;
import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.arena.Arena;
import io.github.albertosa23.heraldia.roads.Roads;
import io.github.albertosa23.heraldia.command.Revision.Mark;
import io.github.albertosa23.heraldia.command.Revision.Stop;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.dimensions.Ground;
import io.github.albertosa23.heraldia.coast.Coast;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.io.IOException;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import java.util.concurrent.CompletableFuture;
import java.util.function.Predicate;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.commands.arguments.IdentifierArgument;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.protocol.game.ClientboundSetSubtitleTextPacket;
import net.minecraft.network.protocol.game.ClientboundSetTitleTextPacket;
import net.minecraft.network.protocol.game.ClientboundSetTitlesAnimationPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.level.TicketType;
import net.minecraft.util.Util;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.block.BaseFireBlock;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.CampfireBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.chunk.storage.ChunkScanAccess;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.material.Fluid;
import net.minecraft.world.level.material.Fluids;
import net.minecraft.world.level.Level;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.storage.LevelResource;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * /heraldia review (operator, level 2): guided route to validate all the visual content in an afternoon ({@link Revision}).
 * At each stop: a search off the server thread (each type's grid, like /heraldia info nearby: without loading
 * or generating anything), a safe teleport ({@link SafeSpot}), a title, the checklist and buttons to mark it.
 * <p>It searches from the world spawn point. It prefers an already generated structure (even if farther) to an
 * expected one; going to an expected one generates new terrain, so it warns first and "Go and generate" must be
 * clicked (goto &lt;id&gt; generate). Each player's progress is saved in heraldia_revision.json and the summary in
 * heraldia_revision.md (world folder), written off the server thread.
 */
public final class ReviewCommand {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/** Search radius (blocks from the spawn point); Atlantis, one per world, is searched in the whole world. */
	static final int RADIUS = InfoCommand.MAX_RADIUS, ATLANTIS_RADIUS = 1 << 20;
	/** Checklist items of each stop type (keys heraldia.revisar.mirar.&lt;type&gt;.&lt;n&gt;). */
	static final Map<Revision.Type, Integer> POINTS = Map.of(Revision.Type.VILLAGE, 4, Revision.Type.UNIQUE, 4,
			Revision.Type.MEDIUM, 3, Revision.Type.MINE, 3, Revision.Type.COAST, 3, Revision.Type.ARENA, 3, Revision.Type.ROAD, 3);
	/** Uniques with their own checklist item (heraldia.revisar.mirar.unica.&lt;id&gt;). */
	static final Set<String> WITH_OWN_POINT = Set.of("atlantida", "isla_corsario");

	private static Revision.Ledger ledger = new Revision.Ledger();
	private static @Nullable Path folder;
	private static CompletableFuture<Void> writing = CompletableFuture.completedFuture(null);
	private static final Set<UUID> SEARCHING = new HashSet<>();

	private ReviewCommand() {
	}

	static void registerEvents() {
		ServerLifecycleEvents.SERVER_STARTED.register(server -> {
			folder = server.getWorldPath(LevelResource.ROOT);
			ledger = Revision.read(folder.resolve(Revision.FILE));
		});
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> {
			writing.join();                  // whatever is pending to write, before closing
			SEARCHING.clear();
		});
	}

	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("review")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(ctx -> go(ctx, null, false))
				.then(Commands.literal("next").executes(ctx -> move(ctx, +1)))
				.then(Commands.literal("previous").executes(ctx -> move(ctx, -1)))
				.then(Commands.literal("skip").executes(ctx -> skip(ctx, ""))
						.then(Commands.argument("note", StringArgumentType.greedyString())
								.executes(ctx -> skip(ctx, StringArgumentType.getString(ctx, "note")))))
				.then(Commands.literal("goto")
						.then(Commands.argument("id", IdentifierArgument.id())
								.suggests((ctx, b) -> SharedSuggestionProvider.suggest(
										route(ctx.getSource().getServer()).stream().map(Stop::id), b))
								.executes(ctx -> go(ctx, IdentifierArgument.getId(ctx, "id").getPath(), false))
								.then(Commands.literal("generate")
										.executes(ctx -> go(ctx, IdentifierArgument.getId(ctx, "id").getPath(), true)))))
				.then(Commands.literal("mark")
						.then(Commands.literal("checked").executes(ctx -> markStop(ctx, Mark.REVIEWED, ""))
								.then(Commands.argument("note", StringArgumentType.greedyString())
										.executes(ctx -> markStop(ctx, Mark.REVIEWED, StringArgumentType.getString(ctx, "note")))))
						.then(Commands.literal("problem").executes(ctx -> markStop(ctx, Mark.PROBLEM, ""))
								.then(Commands.argument("note", StringArgumentType.greedyString())
										.executes(ctx -> markStop(ctx, Mark.PROBLEM, StringArgumentType.getString(ctx, "note"))))))
				.then(Commands.literal("list").executes(ReviewCommand::list))
				.then(Commands.literal("status").executes(ReviewCommand::state))
				.then(Commands.literal("reset").executes(ReviewCommand::reset));
	}

	// --- the route ---

	/** The stops of this world (from the structure registry and the configuration in use). Cheap: done every time. */
	static List<Stop> route(MinecraftServer server) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<String> ids = new ArrayList<>();
		server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet().stream()
				.filter(id -> Heraldia.MOD_ID.equals(id.getNamespace())).forEach(id -> ids.add(id.getPath()));
		Map<String, String> styles = familyStyle(cfg);
		Predicate<Stop> active = p -> switch (p.type()) {
			case VILLAGE -> styles.entrySet().stream().anyMatch(e -> e.getValue().equals(p.sub())
					&& option(cfg, "aldeas.estilos." + e.getKey()) && option(cfg, "aldeas.familias." + p.sub()));
			case UNIQUE -> InfoCommand.uniqueEnabled(cfg, p.sub());
			case MEDIUM -> option(cfg, "medianas.activadas") && option(cfg, "medianas." + p.sub() + ".activada");
			case MINE -> option(cfg, "minas.entradas.activado");
			case COAST -> Coast.option(p.sub()) == null || option(cfg, Coast.option(p.sub()) + ".activado");
			case ARENA, ROAD -> true;
		};
		return Revision.route(ids, styles, active, cfg.getBool("arena.activado"), cfg.getBool(Roads.ENABLED));
	}

	private static boolean option(HeraldiaConfig cfg, String key) {
		return !cfg.has(key) || cfg.getBool(key);
	}

	static Map<String, String> familyStyle(HeraldiaConfig cfg) {
		Map<String, String> out = new LinkedHashMap<>();
		JsonObject styles = cfg.schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		styles.entrySet().forEach(e -> out.put(e.getKey(), e.getValue().getAsString()));
		return out;
	}

	/** Translatable name of a stop. */
	static MutableComponent name(Stop p) {
		return switch (p.type()) {
			case VILLAGE -> Texts.t("heraldia.info.aldea", Texts.t("heraldia.familia." + p.sub()));
			case UNIQUE -> InfoCommand.uniqueName(p.sub());
			case MEDIUM -> InfoCommand.mediumName(p.sub());
			case MINE -> Texts.t("heraldia.minas." + p.sub() + ".nombre");
			case COAST -> Texts.t("heraldia.costa." + p.sub() + ".nombre");
			case ARENA -> Texts.t("heraldia.revisar.parada.arena");
			case ROAD -> Texts.t("heraldia.revisar.parada.camino");
		};
	}

	/** The same name in Spanish, for the Markdown report. */
	static String spanishName(Stop p) {
		Map<String, String> es = Texts.language(Texts.ES);
		return switch (p.type()) {
			case VILLAGE -> es.getOrDefault("heraldia.info.aldea", "%s").replace("%s", es.getOrDefault("heraldia.familia." + p.sub(), p.sub()));
			case UNIQUE -> es.getOrDefault("heraldia.unicas." + p.sub() + ".nombre", p.sub());
			case MEDIUM -> es.getOrDefault("heraldia.medianas." + p.sub() + ".nombre", p.sub());
			case MINE -> es.getOrDefault("heraldia.minas." + p.sub() + ".nombre", p.sub());
			case COAST -> es.getOrDefault("heraldia.costa." + p.sub() + ".nombre", p.sub());
			case ARENA -> es.getOrDefault("heraldia.revisar.parada.arena", "arena");
			case ROAD -> es.getOrDefault("heraldia.revisar.parada.camino", "camino");
		};
	}

	/** Checklist keys of a stop. */
	static List<String> points(Stop p) {
		String type = p.type().id;
		List<String> out = new ArrayList<>();
		for (int i = 1; i <= POINTS.get(p.type()); i++) {
			out.add("heraldia.revisar.mirar." + type + "." + i);
		}
		if (p.type() == Revision.Type.UNIQUE && WITH_OWN_POINT.contains(p.sub())) {
			out.add("heraldia.revisar.mirar.unica." + p.sub());
		}
		return out;
	}

	/** Is the (Heraldia) structure `id` of this stop? */
	static boolean ofStop(Stop p, Identifier id, Map<String, String> styles) {
		if (!Heraldia.MOD_ID.equals(id.getNamespace())) {
			return false;
		}
		String path = id.getPath();
		return switch (p.type()) {
			case VILLAGE -> {
				String style = path.endsWith("_grande") ? path.substring(0, path.length() - "_grande".length()) : path;
				yield p.sub().equals(styles.get(style));
			}
			case UNIQUE -> path.equals("unicas/" + p.sub());
			case MEDIUM -> path.startsWith("medianas/" + p.sub() + "/");
			case MINE -> path.startsWith("minas/" + p.sub() + "/");
			case COAST -> path.startsWith("costa/" + p.sub() + "/");
			case ARENA, ROAD -> false;
		};
	}

	// --- commands ---

	private static ServerPlayer player(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		return ctx.getSource().getPlayerOrException();
	}

	private static Revision.Progress progress(ServerPlayer p) {
		return ledger.of(p.getUUID(), p.getGameProfile().name());
	}

	private static int move(CommandContext<CommandSourceStack> ctx, int step) throws CommandSyntaxException {
		ServerPlayer p = player(ctx);
		List<Stop> route = route(ctx.getSource().getServer());
		Revision.Progress pr = progress(p);
		pr.actual = step > 0 ? Revision.next(route, pr.actual) : Revision.previous(route, pr.actual);
		save(ctx.getSource().getServer());
		return goTo(ctx.getSource(), p, route, pr.actual, false);
	}

	private static int go(CommandContext<CommandSourceStack> ctx, @Nullable String id, boolean generate) throws CommandSyntaxException {
		ServerPlayer p = player(ctx);
		List<Stop> route = route(ctx.getSource().getServer());
		Revision.Progress pr = progress(p);
		if (id != null) {
			int i = Revision.index(route, id);
			if (i < 0) {
				ctx.getSource().sendFailure(Texts.t("heraldia.revisar.desconocida", id));
				return 0;
			}
			pr.actual = i;
			save(ctx.getSource().getServer());
		}
		return goTo(ctx.getSource(), p, route, pr.actual, generate);
	}

	private static int skip(CommandContext<CommandSourceStack> ctx, String note) throws CommandSyntaxException {
		ServerPlayer p = player(ctx);
		List<Stop> route = route(ctx.getSource().getServer());
		Revision.Progress pr = progress(p);
		if (pr.actual < route.size()) {
			ledger.markStop(p.getUUID(), p.getGameProfile().name(), route.get(pr.actual).id(), Mark.SKIPPED, note, System.currentTimeMillis());
		}
		pr.actual = Revision.next(route, pr.actual);
		save(ctx.getSource().getServer());
		return goTo(ctx.getSource(), p, route, pr.actual, false);
	}

	private static int markStop(CommandContext<CommandSourceStack> ctx, Mark m, String note) throws CommandSyntaxException {
		ServerPlayer p = player(ctx);
		CommandSourceStack src = ctx.getSource();
		List<Stop> route = route(src.getServer());
		Revision.Progress pr = progress(p);
		if (pr.actual >= route.size()) {
			src.sendFailure(Texts.t("heraldia.revisar.sin_parada"));
			return 0;
		}
		Stop stop = route.get(pr.actual);
		ledger.markStop(p.getUUID(), p.getGameProfile().name(), stop.id(), m, note, System.currentTimeMillis());
		save(src.getServer());
		Revision.Note n = pr.note(stop.id());
		src.sendSuccess(() -> Texts.t("heraldia.revisar.marcada", name(stop), stop.id(), state(m),
				n == null || n.note().isEmpty() ? Component.empty() : Texts.t("heraldia.revisar.con_nota", n.note())), false);
		src.sendSuccess(() -> buttons(false), false);
		return 1;
	}

	private static int list(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		List<Stop> route = route(src.getServer());
		ServerPlayer p = src.getPlayer();
		Revision.Progress pr = p == null ? null : ledger.players().get(p.getUUID());
		src.sendSuccess(() -> Texts.t("heraldia.revisar.lista.titulo", route.size()).withStyle(ChatFormatting.GOLD), false);
		for (int i = 0; i < route.size(); i++) {
			Stop x = route.get(i);
			Revision.Note n = pr == null ? null : pr.note(x.id());
			boolean here = pr != null && pr.actual == i;
			MutableComponent l = Texts.t("heraldia.revisar.lista.linea", i + 1, name(x), x.id(),
					n == null ? Texts.t("heraldia.revisar.estado.pendiente") : state(n.mark()));
			l.withStyle(s -> s.withColor(here ? ChatFormatting.AQUA : n == null ? ChatFormatting.WHITE
							: n.mark() == Mark.PROBLEM ? ChatFormatting.RED : ChatFormatting.GRAY)
					.withClickEvent(new ClickEvent.RunCommand("/heraldia review goto " + x.id()))
					.withHoverEvent(new HoverEvent.ShowText(Texts.t("heraldia.revisar.boton.ir.ayuda"))));
			src.sendSuccess(() -> l, false);
		}
		return route.size();
	}

	private static int state(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		List<Stop> route = route(src.getServer());
		ServerPlayer p = src.getPlayer();
		Map<UUID, Revision.Progress> all = p != null ? (ledger.players().containsKey(p.getUUID())
				? Map.of(p.getUUID(), ledger.players().get(p.getUUID())) : Map.of()) : ledger.players();
		if (all.isEmpty()) {
			Revision.Tally c = Revision.tally(route, null);
			src.sendSuccess(() -> Texts.t("heraldia.revisar.resumen", "-", c.reviewedCount(), route.size(), c.problems(), c.skipped(),
					c.pending()).withStyle(ChatFormatting.GOLD), false);
		}
		for (Revision.Progress pr : all.values()) {
			Revision.Tally c = Revision.tally(route, pr);
			src.sendSuccess(() -> Texts.t("heraldia.revisar.resumen", pr.name(), c.reviewedCount(), route.size(), c.problems(),
					c.skipped(), c.pending()).withStyle(ChatFormatting.GOLD), false);
			for (Stop x : route) {
				Revision.Note n = pr.note(x.id());
				if (n != null && n.mark() == Mark.PROBLEM) {
					src.sendSuccess(() -> Texts.t("heraldia.revisar.resumen.problema", name(x), x.id(), n.note())
							.withStyle(ChatFormatting.RED), false);
				}
			}
		}
		Path md = folder == null ? null : folder.resolve(Revision.REPORT).normalize();
		if (md != null) {
			save(src.getServer());
			src.sendSuccess(() -> Texts.t("heraldia.revisar.exportado", md.toString()).withStyle(ChatFormatting.GRAY), false);
		}
		return all.size();
	}

	private static int reset(CommandContext<CommandSourceStack> ctx) throws CommandSyntaxException {
		ServerPlayer p = player(ctx);
		ledger.reset(p.getUUID());
		save(ctx.getSource().getServer());
		ctx.getSource().sendSuccess(() -> Texts.t("heraldia.revisar.reiniciada"), false);
		return 1;
	}

	// --- going to a stop ---

	private record Destination(BlockPos pos, boolean generated) {
	}

	private static int goTo(CommandSourceStack src, ServerPlayer p, List<Stop> route, int i, boolean generate) {
		if (i >= route.size()) {
			src.sendSuccess(() -> Texts.t("heraldia.revisar.fin").withStyle(ChatFormatting.GOLD), false);
			return 0;
		}
		if (!SEARCHING.add(p.getUUID())) {
			src.sendFailure(Texts.t("heraldia.revisar.ocupado"));
			return 0;
		}
		Stop stop = route.get(i);
		MinecraftServer server = src.getServer();
		ServerLevel level = levelFor(server, stop, familyStyle(HeraldiaConfig.get()));
		// in the Nether and the End there is no spawn point: search from 0, 0
		BlockPos origin = level.dimension() == Level.OVERWORLD ? level.getRespawnData().pos() : new BlockPos(0, 64, 0);
		src.sendSuccess(() -> Texts.t("heraldia.revisar.buscando", name(stop)).withStyle(ChatFormatting.GRAY), false);
		long t0 = System.nanoTime();
		CompletableFuture<@Nullable Destination> search;
		if (stop.type() == Revision.Type.ARENA) {
			BlockPos c = Arena.center();
			search = CompletableFuture.completedFuture(c == null ? null : new Destination(c, true));
		} else {
			Map<String, String> styles = familyStyle(HeraldiaConfig.get());
			List<InfoCommand.Group> groups = stop.type() == Revision.Type.ROAD ? List.of() : InfoCommand.groups(level);
			search = CompletableFuture.supplyAsync(() -> stop.type() == Revision.Type.ROAD ? road(level, origin)
					: search(level, groups, h -> ofStop(stop, h.unwrapKey().orElseThrow().identifier(), styles), origin,
					"unica/atlantida".equals(stop.id()) ? ATLANTIS_RADIUS : RADIUS), Util.backgroundExecutor());
		}
		search.thenAcceptAsync(d -> {
			long ms = (System.nanoTime() - t0) / 1_000_000;
			LOGGER.info("Heraldia: /heraldia review {}: {} en {} ms", stop.id(), d == null ? "nada" : d, ms);
			Destination dest = d == null ? null : confirm(level, stop, d, familyStyle(HeraldiaConfig.get()));
			if (dest == null) {
				SEARCHING.remove(p.getUUID());
				header(src, p, route, i, stop);
				src.sendFailure(Texts.t(stop.type() == Revision.Type.ARENA ? "heraldia.revisar.sin_arena"
						: "heraldia.revisar.no_encontrada", name(stop), RADIUS));
				src.sendSuccess(() -> buttons(true), false);
			} else if (!dest.generated() && !generate) {
				SEARCHING.remove(p.getUUID());
				header(src, p, route, i, stop);
				int dist = (int) Math.sqrt(dest.pos().distSqr(new BlockPos(origin.getX(), dest.pos().getY(), origin.getZ())));
				src.sendSuccess(() -> Texts.t("heraldia.revisar.prevista", InfoCommand.coordinates(dest.pos()), dist)
						.withStyle(ChatFormatting.YELLOW), false);
				src.sendSuccess(() -> button("heraldia.revisar.boton.generar", "/heraldia review goto " + stop.id() + " generate",
						true, ChatFormatting.GOLD), false);
				src.sendSuccess(() -> buttons(true), false);
			} else {
				teleport(src, p, level, dest, () -> {
					SEARCHING.remove(p.getUUID());
					header(src, p, route, i, stop);
					src.sendSuccess(() -> buttons(false), false);
				});
			}
		}, server).exceptionally(e -> {
			SEARCHING.remove(p.getUUID());
			LOGGER.error("Heraldia: /heraldia review falló", e);
			src.sendFailure(Component.literal(String.valueOf(e.getMessage())));
			return null;
		});
		return 1;
	}

	/**
	 * Off the server thread: the stop's structure nearest to {@code origin}, walking the cells of
	 * its grid from nearest to farthest. An already generated one (saved chunk with its start) beats any
	 * expected one; of the expected ones, the nearest (the same generation rules as /heraldia info nearby). It neither loads
	 * nor generates chunks: the disk is read with StructureCheck's scanner.
	 */
	static @Nullable Destination search(ServerLevel level, List<InfoCommand.Group> groups, Predicate<Holder<Structure>> filter,
									BlockPos origin, int radius) {
		ChunkScanAccess scanner = level.getChunkSource().chunkScanner();
		List<InfoCommand.Found> cells = new ArrayList<>();
		Map<InfoCommand.Found, InfoCommand.Group> groupOf = new LinkedHashMap<>();
		long seed = level.getChunkSource().getGeneratorState().getLevelSeed();
		int cx = SectionPos.blockToSectionCoord(origin.getX()), cz = SectionPos.blockToSectionCoord(origin.getZ());
		long radiusSq = (long) radius * radius;
		for (InfoCommand.Group g0 : groups) {
			List<Holder<Structure>> own = g0.structures().stream().filter(filter).toList();
			if (own.isEmpty()) {
				continue;
			}
			InfoCommand.Group g = new InfoCommand.Group(g0.placement(), own);
			RandomSpreadStructurePlacement pl = g.placement();
			int s = pl.spacing(), ox = UniqueSeparation.offsetX(pl), oz = UniqueSeparation.offsetZ(pl);
			int reach = (int) Math.min(radius / 16 + 1, 1L << 16);
			for (int gx = Math.floorDiv(cx - reach - ox, s), gxMax = Math.floorDiv(cx + reach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(cz - reach - oz, s), gzMax = Math.floorDiv(cz + reach - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = pl.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					BlockPos at = pl.getLocatePos(c);
					long dx = at.getX() - origin.getX(), dz = at.getZ() - origin.getZ(), d = dx * dx + dz * dz;
					if (d <= radiusSq && pl.isStructureChunk(level.getChunkSource().getGeneratorState(), c.x(), c.z())) {
						InfoCommand.Found f = new InfoCommand.Found(null, c, at, d, false);
						if (!groupOf.containsKey(f)) {
							cells.add(f);
							groupOf.put(f, g);
						}
					}
				}
			}
		}
		cells.sort((a, b) -> Long.compare(a.distanceSq(), b.distanceSq()));
		Destination expected = null;
		Viability viab = null;
		for (InfoCommand.Found cell : cells) {
			InfoCommand.Group g = groupOf.get(cell);
			InfoCommand.Stored stored = InfoCommand.stored(scanner, cell.chunk());
			if (stored != null) {
				for (Holder<Structure> h : g.structures()) {
					if (stored.starts().contains(h.unwrapKey().orElseThrow().identifier())) {
						return new Destination(cell.pos(), true);
					}
				}
			} else if (expected == null) {
				if (viab == null) {
					viab = new Viability(level, seed);   // as in InfoCommand.search: once per search (it is costly to prepare)
				}
				ChunkGenerator gen = level.getChunkSource().getGenerator();
				if (InfoCommand.firstViable(g, cell.chunk(), seed, level, level.registryAccess(), gen,
						level.getChunkSource().randomState(), viab.sampler, viab.sep, viab.v) != null) {
					expected = new Destination(cell.pos(), false);
				}
			}
		}
		return expected;
	}

	/** What the search for expected ones needs to prepare once (this thread's sampler and the uniques' separation). */
	private static final class Viability {
		final Climate.Sampler sampler;
		final UniqueSeparation sep;
		final UniqueSeparation.Viability v;

		Viability(ServerLevel level, long seed) {
			ChunkGenerator gen = level.getChunkSource().getGenerator();
			RandomState rs = level.getChunkSource().randomState();
			sampler = rs.createClimateSampler(SamplerContext.builder().enableCaches().build());
			sep = UniqueSeparation.of(level.registryAccess());
			v = sep.viability(level.registryAccess(), gen, gen.getBiomeSource(), sampler, rs, level.getStructureTemplateManager(),
					seed, level, level.dimension());
		}
	}

	/** Off the server thread: the center of the road segment nearest to the spawn point. */
	private static @Nullable Destination road(ServerLevel level, BlockPos origin) {
		BlockPos p = Roads.nearestSegment(level, origin.getX(), origin.getZ());
		if (p == null) {
			return null;
		}
		ChunkPos c = ChunkPos.containing(p);
		return new Destination(p, InfoCommand.stored(level.getChunkSource().chunkScanner(), c) != null);
	}

	/**
	 * World of the stop: the first (the overworld, then the Nether and the End) whose grids have some structure of
	 * the stop (the mediums and uniques of the Nether and the End are only in theirs). The arena and the roads, in the
	 * overworld.
	 */
	static ServerLevel levelFor(MinecraftServer server, Stop stop, Map<String, String> styles) {
		if (stop.type() == Revision.Type.ARENA || stop.type() == Revision.Type.ROAD) {
			return server.overworld();
		}
		for (ServerLevel l : server.getAllLevels()) {
			for (InfoCommand.Group g : InfoCommand.groups(l)) {
				for (Holder<Structure> h : g.structures()) {
					if (h.unwrapKey().map(k -> ofStop(stop, k.identifier(), styles)).orElse(false)) {
						return l;
					}
				}
			}
		}
		return server.overworld();
	}

	/** On the server thread: a loaded (not yet saved) chunk may already have the structure the disk does not. */
	private static @Nullable Destination confirm(ServerLevel level, Stop stop, Destination d, Map<String, String> styles) {
		if (d.generated()) {
			return d;
		}
		ChunkPos c = ChunkPos.containing(d.pos());
		LevelChunk chunk = level.getChunkSource().getChunkNow(c.x(), c.z());
		if (chunk == null) {
			return d;
		}
		if (stop.type() == Revision.Type.ROAD) {
			return new Destination(d.pos(), true);
		}
		for (Map.Entry<Structure, StructureStart> e : chunk.getAllStarts().entrySet()) {
			Identifier id = level.registryAccess().lookupOrThrow(Registries.STRUCTURE).getKey(e.getKey());
			if (id != null && e.getValue().isValid() && ofStop(stop, id, styles)) {
				return new Destination(d.pos(), true);
			}
		}
		return d;
	}

	/**
	 * Loads (or, if the operator asked for it, generates) the destination chunk with a temporary ticket, without blocking the
	 * server thread, and appears at the nearest safe spot, in the stop's world ({@link #levelFor}).
	 */
	private static void teleport(CommandSourceStack src, ServerPlayer p, ServerLevel level, Destination d, Runnable after) {
		ChunkPos c = ChunkPos.containing(d.pos());
		src.sendSuccess(() -> Texts.t("heraldia.revisar.cargando").withStyle(ChatFormatting.GRAY), false);
		level.getChunkSource().addTicketAndLoadWithRadius(TicketType.PORTAL, c, 1).thenRunAsync(() -> {
			java.util.Optional<SafeSpot.Site> site = SafeSpot.search(world(level), d.pos().getX(), d.pos().getZ(), SafeSpot.RADIUS);
			if (site.isEmpty() || p.hasDisconnected()) {
				src.sendFailure(Texts.t("heraldia.revisar.sin_sitio", InfoCommand.coordinates(d.pos())));
			} else {
				SafeSpot.Site s = site.get();
				p.teleportTo(level, s.x() + 0.5, s.y(), s.z() + 0.5, Set.of(), p.getYRot(), p.getXRot(), true);
				p.resetFallDistance();
				LOGGER.info("Heraldia: /heraldia review: {} a {} {} {}", p.getGameProfile().name(), s.x(), s.y(), s.z());
				src.sendSuccess(() -> Texts.t("heraldia.revisar.teletransportado", s.x(), s.y(), s.z()).withStyle(ChatFormatting.GRAY), false);
			}
			after.run();
		}, level.getServer()).exceptionally(e -> {
			SEARCHING.remove(p.getUUID());
			LOGGER.error("Heraldia: /heraldia review: no se pudo cargar el destino", e);
			src.sendFailure(Component.literal(String.valueOf(e.getMessage())));
			return null;
		});
	}

	/** The world for {@link SafeSpot}: only already loaded chunks (an unloaded one counts as dangerous: it is not chosen). */
	private static SafeSpot.World world(ServerLevel level) {
		return new SafeSpot.World() {
			@Override
			public SafeSpot.Cell en(int x, int y, int z) {
				LevelChunk ch = level.getChunkSource().getChunkNow(SectionPos.blockToSectionCoord(x), SectionPos.blockToSectionCoord(z));
				if (ch == null) {
					return SafeSpot.Cell.DANGER;
				}
				BlockPos pos = new BlockPos(x, y, z);
				return cell(ch.getBlockState(pos), !ch.getBlockState(pos).getCollisionShape(level, pos).isEmpty());
			}

			@Override
			public int height(int x, int z) {
				LevelChunk ch = level.getChunkSource().getChunkNow(SectionPos.blockToSectionCoord(x), SectionPos.blockToSectionCoord(z));
				if (ch != null && level.dimensionType().hasCeiling()) { // the Nether: under the bedrock ceiling
					return SafeSpot.underCeiling(this, x, z, Ground.NETHER_FROM + 8, Ground.NETHER_TO - 2);
				}
				return ch == null ? level.getMinY() : ch.getHeight(Heightmap.Types.MOTION_BLOCKING_NO_LEAVES, x & 15, z & 15) + 1;
			}

			@Override
			public int minY() {
				return level.getMinY();
			}

			@Override
			public int maxY() {
				return level.getMaxY() + 1;
			}
		};
	}

	/** Classifies a block for {@link SafeSpot}. */
	static SafeSpot.Cell cell(BlockState s, boolean collision) {
		// no tags (BlockTags/FluidTags): so it does not depend on the loaded data
		Fluid f = s.getFluidState().getType();
		if (Fluids.LAVA.isSame(f) || s.getBlock() instanceof BaseFireBlock || s.getBlock() instanceof CampfireBlock
				|| s.is(Blocks.MAGMA_BLOCK) || s.is(Blocks.CACTUS) || s.is(Blocks.POWDER_SNOW) || s.is(Blocks.SWEET_BERRY_BUSH)
				|| s.is(Blocks.WITHER_ROSE) || s.is(Blocks.POINTED_DRIPSTONE)) {
			return SafeSpot.Cell.DANGER;
		}
		if (collision) {
			return SafeSpot.Cell.SOLID;
		}
		return Fluids.WATER.isSame(f) ? SafeSpot.Cell.WATER : SafeSpot.Cell.FREE;
	}

	// --- texts ---

	/** On-screen title and, in the chat, the stop's name and the checklist. */
	private static void header(CommandSourceStack src, ServerPlayer p, List<Stop> route, int i, Stop stop) {
		if (!p.hasDisconnected()) {
			p.connection.send(new ClientboundSetTitlesAnimationPacket(10, 60, 20));
			p.connection.send(new ClientboundSetSubtitleTextPacket(Texts.t("heraldia.revisar.subtitulo", i + 1, route.size())));
			p.connection.send(new ClientboundSetTitleTextPacket(name(stop).withStyle(ChatFormatting.GOLD)));
		}
		src.sendSuccess(() -> Texts.t("heraldia.revisar.titulo", i + 1, route.size(), name(stop), stop.id())
				.withStyle(ChatFormatting.GOLD), false);
		src.sendSuccess(() -> Texts.t("heraldia.revisar.mirar").withStyle(ChatFormatting.YELLOW), false);
		for (String k : points(stop)) {
			src.sendSuccess(() -> Texts.t("heraldia.revisar.punto", Texts.t(k)), false);
		}
		Revision.Note n = progress(p).note(stop.id());
		if (n != null) {
			src.sendSuccess(() -> Texts.t("heraldia.revisar.ya_marcada", state(n.mark()),
					n.note().isEmpty() ? Component.empty() : Texts.t("heraldia.revisar.con_nota", n.note())).withStyle(ChatFormatting.GRAY), false);
		}
	}

	static Component state(Mark m) {
		return Texts.t("heraldia.revisar.estado." + m.id);
	}

	/** The stop's buttons: mark (reviewed, with a note or with a problem), skip, previous, next and list. */
	private static Component buttons(boolean noDestination) {
		MutableComponent out = Component.empty();
		if (!noDestination) {
			out.append(button("heraldia.revisar.boton.revisada", "/heraldia review mark checked", true, ChatFormatting.GREEN)).append(" ");
			out.append(button("heraldia.revisar.boton.nota", "/heraldia review mark checked ", false, ChatFormatting.DARK_GREEN)).append(" ");
			out.append(button("heraldia.revisar.boton.problema", "/heraldia review mark problem ", false, ChatFormatting.RED)).append(" ");
		}
		out.append(button("heraldia.revisar.boton.saltar", "/heraldia review skip", true, ChatFormatting.GRAY)).append(" ");
		out.append(button("heraldia.revisar.boton.anterior", "/heraldia review previous", true, ChatFormatting.AQUA)).append(" ");
		out.append(button("heraldia.revisar.boton.siguiente", "/heraldia review next", true, ChatFormatting.AQUA)).append(" ");
		out.append(button("heraldia.revisar.boton.lista", "/heraldia review list", true, ChatFormatting.GRAY));
		return out;
	}

	/** Clickable [text]: runs the command or leaves it typed to complete it (with the ".ayuda" help on hover). */
	private static Component button(String key, String order, boolean execute, ChatFormatting color) {
		return Texts.t(key).withStyle(s -> s.withColor(color)
				.withClickEvent(execute ? new ClickEvent.RunCommand(order) : new ClickEvent.SuggestCommand(order))
				.withHoverEvent(new HoverEvent.ShowText(Texts.t(key + ".ayuda"))));
	}

	// --- saving ---

	/** Writes the progress (JSON) and the summary (Markdown) off the server thread, in order. */
	private static void save(MinecraftServer server) {
		Path dir = folder;
		if (dir == null) {
			return;
		}
		List<Stop> route = route(server);
		Revision.Ledger backup = ledger.backup();
		Map<String, String> names = new LinkedHashMap<>();
		route.forEach(x -> names.put(x.id(), spanishName(x)));
		long now = System.currentTimeMillis();
		writing = writing.thenRunAsync(() -> {
			try {
				Revision.write(dir.resolve(Revision.FILE), Revision.json(backup));
				Revision.write(dir.resolve(Revision.REPORT), Revision.markdown(route, backup, x -> names.get(x.id()), now));
			} catch (IOException e) {
				LOGGER.warn("Heraldia: no se pudo guardar la revisión en {} ({})", dir, e.getMessage());
			}
		}, Util.ioPool());
	}
}
