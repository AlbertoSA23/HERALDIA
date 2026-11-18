package io.github.albertosa23.heraldia.command;

import com.google.gson.JsonObject;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.loot.WithoutLootrCondition;
import it.unimi.dsi.fastutil.longs.LongSet;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.coast.Coast;
import io.github.albertosa23.heraldia.mines.Mines;
import io.github.albertosa23.heraldia.uniques.atlantis.AtlantisAnchor;
import java.util.concurrent.CompletableFuture;
import net.minecraft.core.RegistryAccess;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.IntTag;
import net.minecraft.nbt.StringTag;
import net.minecraft.world.level.chunk.status.ChunkStatus;
import net.minecraft.nbt.visitors.CollectFields;
import net.minecraft.nbt.visitors.FieldSelector;
import net.minecraft.world.level.chunk.storage.ChunkScanAccess;
import net.minecraft.util.Util;
import net.minecraft.world.level.biome.Climate;
import net.minecraft.world.level.chunk.ChunkGenerator;
import net.minecraft.world.level.levelgen.RandomState;
import net.minecraft.world.level.levelgen.densityfunction.SamplerContext;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.Registry;
import net.minecraft.core.SectionPos;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.ComponentUtils;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.util.Mth;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.level.ChunkPos;
import net.minecraft.world.level.StructureManager;
import net.minecraft.world.level.chunk.ChunkGeneratorStructureState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import net.minecraft.world.level.levelgen.structure.placement.RandomSpreadStructurePlacement;
import net.minecraft.world.level.levelgen.structure.placement.StructurePlacement;
import net.minecraft.world.phys.AABB;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * /heraldia info [nearby [radius] | here] (operator, level 2). It only works when run:
 * <ul>
 * <li>info: the configuration in use and how many structures are registered.</li>
 * <li>info nearby [radius]: the nearest unique and medium structure of each type and the nearest Heraldia village. It
 * walks the cells of each grid within the radius with the generation rules (those of StructureCheck and the mixins plus the
 * exclusion zone of vanilla villages) and reads the already saved chunks with StructureCheck's scanner: all off
 * the server thread; on it only already loaded chunks are checked. It neither loads nor generates chunks: an ungenerated cell
 * is reported as "expected". Bounded radius (MAX_RADIUS); the total time and the server thread's are measured.</li>
 * <li>info here: the Heraldia structure whose pieces contain the position and, if it is a unique, whether its guardian
 * is alive (entities with the heraldia_guardian.&lt;id&gt; tag inside its box, only if the whole box is loaded).</li>
 * </ul>
 */
public final class InfoCommand {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final int DEFAULT_RADIUS = 3000, MAX_RADIUS = 10000;
	private static final String GUARDIAN_TAG = "heraldia_guardian"; // _comun/piezas.GUARDIAN_TAG
	private static final String[] DIRECTIONS = {"s", "so", "o", "no", "n", "ne", "e", "se"};

	private InfoCommand() {
	}

	/** /heraldia info [nearby [radius] | here] (registered by {@link HeraldiaCommands}). */
	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("info")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(InfoCommand::summary)
				.then(Commands.literal("nearby")
						.executes(ctx -> near(ctx, DEFAULT_RADIUS))
						.then(Commands.argument("radius", IntegerArgumentType.integer(16, MAX_RADIUS))
								.executes(ctx -> near(ctx, IntegerArgumentType.getInteger(ctx, "radius")))))
				.then(Commands.literal("here").executes(InfoCommand::here));
	}

	// --- info ---

	private static int summary(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack source = ctx.getSource();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		JsonObject schema = cfg.schema();
		List<Component> lines = new ArrayList<>();
		lines.add(Texts.t("heraldia.info.titulo").withStyle(ChatFormatting.GOLD));
		lines.add(Texts.t("heraldia.info.aldeas", cfg.getInt("aldeas.separacion_bloques"), cfg.getInt("aldeas.maximo"),
				cfg.getInt("aldeas.porcentaje_grandes"), cfg.villages().enabledStyles(),
				schema.getAsJsonObject("aldeas").getAsJsonObject("estilos").size(), cfg.getInt("aldeas.distancia_aldeas_vanilla_bloques")));

		Registry<Structure> registry = source.getServer().registryAccess().lookupOrThrow(Registries.STRUCTURE);
		List<Identifier> uniques = new ArrayList<>();
		int heraldia = 0, medium = 0, mines = 0, coast = 0;
		for (Identifier id : registry.keySet()) {
			if (Heraldia.MOD_ID.equals(id.getNamespace())) {
				heraldia++;
				if (UniqueSeparation.isUnique(id)) {
					uniques.add(id);
				} else if (MediumStructures.isMedium(id)) {
					medium++;
				} else if (Mines.isMine(id)) {
					mines++;
				} else if (Coast.isCoast(id)) {
					coast++;
				}
			}
		}
		uniques.sort(null);
		List<Component> uniqueLines = new ArrayList<>();
		int enabled = 0;
		for (Identifier id : uniques) {
			String sid = id.getPath().substring("unicas/".length());
			String key = "unicas." + sid;
			if (!cfg.has(key + ".activada")) {
				enabled++;
				uniqueLines.add(Texts.t("heraldia.info.unica.mundial", uniqueName(sid)));
			} else if (cfg.getBool(key + ".activada")) {
				enabled++;
				uniqueLines.add(Texts.t("heraldia.info.unica", uniqueName(sid), cfg.getInt(key + ".separacion_bloques")));
			} else {
				uniqueLines.add(Texts.t("heraldia.info.unica.desactivada", uniqueName(sid)).withStyle(ChatFormatting.GRAY));
			}
		}
		lines.add(Texts.t("heraldia.info.unicas", enabled, uniques.size()));
		lines.addAll(uniqueLines);
		lines.add(Texts.t("heraldia.info.distancia", onOff(cfg.getBool("unicas.distancia_minima.activada")),
				cfg.getInt("unicas.distancia_minima.bloques")));
		lines.add(Texts.t("heraldia.info.rejilla", onOff(cfg.getBool(GridPlacement.LEGACY_OPTION))));
		lines.add(Texts.t("heraldia.info.cofre", yesNo(cfg.getBool("unicas.atlantida.cofre_unico_por_jugador")),
				Texts.t(WithoutLootrCondition.LOOTR_LOADED ? "heraldia.info.cargado" : "heraldia.info.no_cargado")));
		lines.addAll(mediumLines(source, cfg));
		lines.add(Texts.t("heraldia.info.minas", onOff(cfg.getBool(Mines.ENABLED)), cfg.getInt(Mines.SEPARATION),
				cfg.getDouble(Mines.MULTIPLIER)));
		lines.add(Texts.t("heraldia.info.costa", onOff(cfg.getBool(Coast.LIGHTHOUSES + ".activado")), cfg.getInt(Coast.LIGHTHOUSES + ".separacion_bloques"),
				onOff(cfg.getBool(Coast.SHIPWRECKS + ".activado")), cfg.getInt(Coast.SHIPWRECKS + ".separacion_bloques"), coast));
		lines.add(Texts.t("heraldia.info.registradas", heraldia, heraldia - uniques.size() - medium - mines - coast, uniques.size(), medium, mines));
		lines.forEach(l -> source.sendSuccess(() -> l, false));
		return heraldia;
	}

	/** Medium structures: the common configuration and, per type (a structure_set medianas/&lt;type&gt;), its separation. */
	private static List<Component> mediumLines(CommandSourceStack source, HeraldiaConfig cfg) {
		MediumStructures m = MediumStructures.of(source.getServer().registryAccess());
		List<Component> out = new ArrayList<>(), types = new ArrayList<>();
		int enabled = 0;
		for (int i = 0; i < m.types(); i++) {
			String tid = m.typeId(i).getPath().substring(MediumStructures.PREFIX.length());
			String key = "medianas." + tid;
			if (cfg.getBool(MediumStructures.ENABLED) && cfg.getBool(key + ".activada")) {
				enabled++;
				types.add(Texts.t("heraldia.info.mediana", mediumName(tid), cfg.getInt(key + ".separacion_bloques")));
			} else {
				types.add(Texts.t("heraldia.info.unica.desactivada", mediumName(tid)).withStyle(ChatFormatting.GRAY));
			}
		}
		out.add(Texts.t("heraldia.info.medianas", onOff(cfg.getBool(MediumStructures.ENABLED)), enabled, m.types(),
				cfg.getInt(MediumStructures.FREQUENCY), cfg.getInt(MediumStructures.ZONE), cfg.getInt(MediumStructures.DISTANCE)));
		out.addAll(types);
		return out;
	}

	// --- info nearby ---

	/** generated: the structure is in the saved or loaded chunk; otherwise it is expected (ungenerated chunk). */
	public record Found(Holder<Structure> structure, ChunkPos chunk, BlockPos pos, long distanceSq, boolean generated) {
	}

	public record Group(RandomSpreadStructurePlacement placement, List<Holder<Structure>> structures) {
	}

	/** What the saved chunk says: null = it does not exist on disk; if it exists, the structures whose start it holds. */
	public record Stored(List<Identifier> starts) {
	}

	private static int near(CommandContext<CommandSourceStack> ctx, int radius) {
		CommandSourceStack source = ctx.getSource();
		ServerLevel level = source.getLevel();
		BlockPos origin = BlockPos.containing(source.getPosition());
		List<Group> groups = groups(level);
		long t0 = System.nanoTime();
		// 1) off the server thread, the expensive part: where each type would spawn and what is already in the saved chunks
		CompletableFuture.supplyAsync(() -> search(level, groups, origin, radius), Util.backgroundExecutor())
				// 2) on the server thread, the cheap part: the already loaded (not yet saved) chunks override the disk
				.thenAcceptAsync(found -> {
					long t1 = System.nanoTime();
					List<Found> out = confirm(level, groups, found);
					long t2 = System.nanoTime();
					report(source, origin, radius, out, (t2 - t0) / 1_000_000, (t2 - t1) / 1_000_000);
				}, source.getServer())
				.exceptionally(e -> {
					LOGGER.error("Heraldia: /heraldia info nearby falló", e);
					source.sendFailure(Component.literal(String.valueOf(e.getMessage())));
					return null;
				});
		return 1;
	}

	private static void report(CommandSourceStack source, BlockPos origin, int radius, List<Found> found, long ms, long mainMs) {
		LOGGER.info("Heraldia: /heraldia info nearby {} en {}, {}: {} estructuras en {} ms ({} ms en el hilo del servidor)",
				radius, origin.getX(), origin.getZ(), found.size(), ms, mainMs);
		if (found.isEmpty()) {
			source.sendSuccess(() -> Texts.t("heraldia.info.cerca.nada", radius, origin.getX(), origin.getZ(), ms), false);
			return;
		}
		source.sendSuccess(() -> Texts.t("heraldia.info.cerca.titulo", radius, origin.getX(), origin.getZ(), ms).withStyle(ChatFormatting.GOLD), false);
		for (Found f : found) {
			int dx = f.pos.getX() - origin.getX(), dz = f.pos.getZ() - origin.getZ();
			Component line = Texts.t("heraldia.info.cerca.linea", name(f.structure), id(f), Mth.floor(Math.sqrt(f.distanceSq)),
					Texts.t("heraldia.info.dir." + direction(dx, dz)), coordinates(f.pos),
					Texts.t(f.generated ? "heraldia.info.generada" : "heraldia.info.prevista"));
			source.sendSuccess(() -> line, false);
		}
	}

	/** The mod's structures grouped by placement: one per unique type; the villages share theirs. */
	public static List<Group> groups(ServerLevel level) {
		ChunkGeneratorStructureState state = level.getChunkSource().getGeneratorState();
		Map<RandomSpreadStructurePlacement, List<Holder<Structure>>> byPlacement = new LinkedHashMap<>();
		level.registryAccess().lookupOrThrow(Registries.STRUCTURE).listElements().forEach(h -> {
			if (Heraldia.MOD_ID.equals(h.key().identifier().getNamespace())) {
				for (StructurePlacement p : state.getPlacementsForStructure(h)) {
					if (p instanceof RandomSpreadStructurePlacement rs) {
						byPlacement.computeIfAbsent(rs, k -> new ArrayList<>()).add(h);
					}
				}
			}
		});
		List<Group> out = new ArrayList<>();
		byPlacement.forEach((p, l) -> out.add(new Group(p, List.copyOf(l))));
		return out;
	}

	/**
	 * For each placement, the cells within radius blocks from nearest to farthest; it keeps the first one in which
	 * there is (saved chunk with its start) or would be (ungenerated chunk in which generation would put it) a
	 * structure. "Would be" follows the generation rules: isStructureChunk (allowed cells and vanilla village exclusion
	 * zone, which /locate does not check before loading the chunk), villages disabled or of another
	 * size, Atlantis exclusion, minimum distance between uniques and findValidGenerationPoint with real biome and
	 * terrain. Everything is thread-safe (the generation threads query it); the disk is read with the same scanner as
	 * StructureCheck. It neither loads nor generates chunks.
	 */
	public static List<Found> search(ServerLevel level, List<Group> groups, BlockPos origin, int radius) {
		ChunkGenerator generator = level.getChunkSource().getGenerator();
		RandomState randomState = level.getChunkSource().randomState();
		ChunkGeneratorStructureState state = level.getChunkSource().getGeneratorState();
		ChunkScanAccess scanner = level.getChunkSource().chunkScanner();
		long seed = state.getLevelSeed();
		RegistryAccess access = level.registryAccess();
		Climate.Sampler sampler = randomState.createClimateSampler(SamplerContext.builder().enableCaches().build()); // of this thread
		UniqueSeparation sep = UniqueSeparation.of(access);
		UniqueSeparation.Viability viability = sep.viability(access, generator, generator.getBiomeSource(), sampler, randomState,
				level.getStructureTemplateManager(), seed, level, level.dimension());
		int cx = SectionPos.blockToSectionCoord(origin.getX()), cz = SectionPos.blockToSectionCoord(origin.getZ());
		int reach = radius / 16 + 1;
		long radiusSq = (long) radius * radius;
		List<Found> out = new ArrayList<>();
		for (Group g : groups) {
			RandomSpreadStructurePlacement p = g.placement;
			int s = p.spacing(), ox = UniqueSeparation.offsetX(p), oz = UniqueSeparation.offsetZ(p);
			List<Found> cells = new ArrayList<>();
			for (int gx = Math.floorDiv(cx - reach - ox, s), gxMax = Math.floorDiv(cx + reach - ox, s); gx <= gxMax; gx++) {
				for (int gz = Math.floorDiv(cz - reach - oz, s), gzMax = Math.floorDiv(cz + reach - oz, s); gz <= gzMax; gz++) {
					ChunkPos c = p.getPotentialStructureChunk(seed, gx * s + ox, gz * s + oz);
					BlockPos at = p.getLocatePos(c);
					long dx = at.getX() - origin.getX(), dz = at.getZ() - origin.getZ(), d = dx * dx + dz * dz;
					if (d <= radiusSq && p.isStructureChunk(state, c.x(), c.z())) {
						cells.add(new Found(null, c, at, d, false));
					}
				}
			}
			cells.sort((a, b) -> Long.compare(a.distanceSq, b.distanceSq));
			for (Found cell : cells) {
				Stored stored = stored(scanner, cell.chunk);
				Holder<Structure> h = null;
				if (stored != null) { // generated: what is saved counts (another village of the set, nothing if explored before the mod...)
					for (Holder<Structure> candidate : g.structures) {
						if (stored.starts.contains(candidate.unwrapKey().orElseThrow().identifier())) {
							h = candidate;
							break;
						}
					}
				} else {
					h = firstViable(g, cell.chunk, seed, level, access, generator, randomState, sampler, sep, viability);
				}
				if (h != null) {
					out.add(new Found(h, cell.chunk, cell.pos, cell.distanceSq, stored != null));
					break;
				}
			}
		}
		return out;
	}

	/**
	 * Structure starts of the saved chunk (only those fields, like StructureCheck), or null if it is not on disk or was
	 * saved before its structures were decided (status before structure_starts, e.g. a half-generated chunk when the
	 * server stopped): then it is not known yet and is reported as expected (T40: otherwise the same search gave different
	 * results depending on the status in which the chunks near spawn had been saved).
	 */
	public static Stored stored(ChunkScanAccess scanner, ChunkPos pos) {
		CollectFields fields = new CollectFields(new FieldSelector(IntTag.TYPE, "DataVersion"),
				new FieldSelector(StringTag.TYPE, "Status"), new FieldSelector("structures", CompoundTag.TYPE, "starts"));
		try {
			scanner.scanChunk(pos, fields).join();
		} catch (RuntimeException e) {
			return null;
		}
		if (!(fields.getResult() instanceof CompoundTag tag)) {
			return null;
		}
		if (!withStructures(tag.getStringOr("Status", ""))) {
			return null;
		}
		List<Identifier> starts = new ArrayList<>();
		tag.getCompound("structures").flatMap(t -> t.getCompound("starts")).ifPresent(st -> st.forEach((key, value) -> {
			Identifier id = Identifier.tryParse(key);
			if (id != null && value.asCompound().map(c -> !"INVALID".equals(c.getStringOr("id", ""))).orElse(false)) {
				starts.add(id);
			}
		}));
		return new Stored(starts);
	}

	/** Has a chunk saved with this status already decided its structures? (Without a status: yes, as it was read before.) */
	static boolean withStructures(String status) {
		return status.isEmpty() || ChunkStatus.byName(status).isOrAfter(ChunkStatus.STRUCTURE_STARTS);
	}

	public static Holder<Structure> firstViable(Group g, ChunkPos c, long seed, ServerLevel level, RegistryAccess access,
												 ChunkGenerator generator, RandomState randomState, Climate.Sampler sampler,
												 UniqueSeparation sep, UniqueSeparation.Viability viability) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		for (Holder<Structure> h : g.structures) {
			Identifier id = h.unwrapKey().orElseThrow().identifier();
			if (!cfg.villages().allows(id, seed, c.x(), c.z())) {
				continue; // village disabled or of another size: cheapest first
			}
			int i = sep.indexOf(id);
			boolean ok;
			if (i >= 0) { // uniques: viability (with the Atlantis exclusion) and minimum distance, like the mixins
				ok = viability.valid(i, c.x(), c.z()) && !sep.blocked(i, c.x(), c.z(), seed, viability);
			} else {
				Structure st = h.value();
				ok = !AtlantisAnchor.excludes(id, level.dimension(), seed, c.x(), c.z())
						&& st.findValidGenerationPoint(new Structure.GenerationContext(access, generator, generator.getBiomeSource(), sampler,
						randomState, level.getStructureTemplateManager(), seed, c, level, st.biomes()::contains)).isPresent()
						&& !(MediumStructures.isMedium(id) && MediumStructures.of(access).rejects(id, c.x(), c.z(), seed, access, generator,
						generator.getBiomeSource(), sampler, randomState, level.getStructureTemplateManager(), level, level.dimension()))
						&& !(Mines.isMine(id) && Mines.of(access).rejects(id, c.x(), c.z(), seed, access, generator,
						generator.getBiomeSource(), sampler, randomState, level.getStructureTemplateManager(), level, level.dimension()))
						&& !(Coast.isCoast(id) && Coast.of(access).rejects(id, c.x(), c.z(), seed, access, generator,
						generator.getBiomeSource(), sampler, randomState, level.getStructureTemplateManager(), level, level.dimension()));
			}
			if (ok) {
				return h;
			}
		}
		return null;
	}

	/**
	 * On the server thread: a loaded chunk can be newer than the disk (generated and not saved yet). If
	 * so, its start wins; an expected one whose chunk is already generated without it is removed. It only checks already loaded chunks.
	 */
	private static List<Found> confirm(ServerLevel level, List<Group> groups, List<Found> found) {
		StructureManager manager = level.structureManager();
		List<Found> out = new ArrayList<>();
		for (Found f : found) {
			LevelChunk chunk = level.getChunkSource().getChunkNow(f.chunk.x(), f.chunk.z());
			if (chunk == null) {
				out.add(f);
				continue;
			}
			Group g = groups.stream().filter(x -> x.structures.contains(f.structure)).findFirst().orElse(null);
			for (Holder<Structure> h : g == null ? List.of(f.structure) : g.structures) {
				StructureStart start = manager.getStartForStructure(h.value(), chunk);
				if (start != null && start.isValid()) {
					out.add(new Found(h, f.chunk, f.pos, f.distanceSq, true));
					break;
				}
			}
		}
		out.sort((a, b) -> Long.compare(a.distanceSq, b.distanceSq));
		return out;
	}


	/** 8-point heading (north = -z). */
	public static String direction(int dx, int dz) {
		double angle = Math.toDegrees(Math.atan2(-dx, dz)); // 0 = south, 90 = west, 180 = north, -90 = east
		int i = Math.floorMod((int) Math.round(angle / 45.0), 8);
		return DIRECTIONS[i];
	}

	public static Component coordinates(BlockPos pos) {
		return ComponentUtils.wrapInSquareBrackets(Component.translatable("chat.coordinates", pos.getX(), "~", pos.getZ()))
				.withStyle(s -> s.withColor(ChatFormatting.GREEN)
						.withClickEvent(new ClickEvent.SuggestCommand("/tp @s " + pos.getX() + " ~ " + pos.getZ()))
						.withHoverEvent(new HoverEvent.ShowText(Component.translatable("chat.coordinates.tooltip"))));
	}

	// --- info here ---

	private static int here(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack source = ctx.getSource();
		ServerLevel level = source.getLevel();
		BlockPos pos = BlockPos.containing(source.getPosition());
		LevelChunk chunk = level.getChunkSource().getChunkNow(SectionPos.blockToSectionCoord(pos.getX()), SectionPos.blockToSectionCoord(pos.getZ()));
		if (chunk == null) { // only already loaded chunks: no loading or generating
			source.sendFailure(Texts.t("heraldia.info.aqui.sin_cargar"));
			return 0;
		}
		StructureManager manager = level.structureManager();
		Registry<Structure> registry = level.registryAccess().lookupOrThrow(Registries.STRUCTURE);
		int count = 0;
		for (Map.Entry<Structure, LongSet> e : chunk.getAllReferences().entrySet()) {
			Identifier id = registry.getKey(e.getKey());
			if (id == null || !Heraldia.MOD_ID.equals(id.getNamespace())) {
				continue;
			}
			StructureStart start = manager.getStructureWithPieceAt(pos.getX(), pos.getY(), pos.getZ(), e.getKey());
			if (!start.isValid()) {
				continue;
			}
			count++;
			Holder<Structure> holder = registry.wrapAsHolder(e.getKey());
			source.sendSuccess(() -> Texts.t("heraldia.info.aqui.linea", name(holder), id.toString()), false);
			if (UniqueSeparation.isUnique(id)) {
				Component g = guardian(level, holder, start, GUARDIAN_TAG + "." + id.getPath().substring("unicas/".length()));
				source.sendSuccess(() -> g, false);
			}
		}
		if (count == 0) {
			source.sendSuccess(() -> Texts.t("heraldia.info.aqui.nada"), false);
		}
		return count;
	}

	/**
	 * Alive if an entity with its tag is in the main start's box (with a margin); defeated only if the whole box
	 * has its entities loaded. The main start is the one the placement gives for this cell: the same one in the grid
	 * ones; in Atlantis (nine starts, one per district) the central district, where the guardian is.
	 */
	private static Component guardian(ServerLevel level, Holder<Structure> holder, StructureStart start, String tag) {
		ChunkPos here = start.getChunkPos();
		ChunkPos main = here;
		for (StructurePlacement p : level.getChunkSource().getGeneratorState().getPlacementsForStructure(holder)) {
			if (p instanceof RandomSpreadStructurePlacement rs) {
				main = rs.getPotentialStructureChunk(level.getSeed(), here.x(), here.z());
				break;
			}
		}
		BoundingBox box = start.getBoundingBox();
		if (!main.equals(here)) {
			LevelChunk mainChunk = level.getChunkSource().getChunkNow(main.x(), main.z());
			StructureStart mainStart = mainChunk == null ? null : level.structureManager().getStartForStructure(holder.value(), mainChunk);
			if (mainStart == null || !mainStart.isValid()) {
				return Texts.t("heraldia.info.guardian.desconocido");
			}
			box = mainStart.getBoundingBox();
		}
		AABB area = AABB.of(box).inflate(16);
		List<Entity> found = level.getEntities((Entity) null, area, e -> e.entityTags().contains(tag));
		if (!found.isEmpty()) {
			BlockPos p = found.getFirst().blockPosition();
			return Texts.t("heraldia.info.guardian.vivo", p.getX(), p.getY(), p.getZ());
		}
		for (int x = SectionPos.blockToSectionCoord(box.minX()); x <= SectionPos.blockToSectionCoord(box.maxX()); x++) {
			for (int z = SectionPos.blockToSectionCoord(box.minZ()); z <= SectionPos.blockToSectionCoord(box.maxZ()); z++) {
				if (!level.areEntitiesLoaded(ChunkPos.pack(x, z))) {
					return Texts.t("heraldia.info.guardian.desconocido");
				}
			}
		}
		return Texts.t("heraldia.info.guardian.derrotado");
	}

	// --- names ---

	/**
	 * Id shown: the structure's, except in an expected village, whose style is not decided yet (the biome sets the
	 * family, but the structure_set rolls the style when it generates): then the set's, heraldia:aldeas.
	 */
	private static String id(Found f) {
		Identifier id = f.structure.unwrapKey().map(k -> k.identifier()).orElse(null);
		if (id == null) {
			return "?";
		}
		if (f.generated || UniqueSeparation.isUnique(id)) {
			return id.toString();
		}
		if (MediumStructures.isMedium(id)) { // expected: the type's structure_set rolls the style when it generates
			return Heraldia.MOD_ID + ":" + id.getPath().substring(0, id.getPath().lastIndexOf('/'));
		}
		if (Mines.isMine(id)) { // expected: the size's structure_set rolls the style (and the variant)
			return Heraldia.MOD_ID + ":minas/" + id.getPath().split("/")[1];
		}
		if (Coast.isCoast(id)) { // expected: the coast's climate gives the style when it generates
			return Heraldia.MOD_ID + ":costa/" + Coast.type(id);
		}
		return Heraldia.MOD_ID + ":aldeas";
	}

	/** Translated name: the unique's (heraldia.unicas.&lt;id&gt;.nombre) or "Heraldia village of &lt;family&gt;". */
	static MutableComponent name(Holder<Structure> h) {
		Identifier id = h.unwrapKey().map(k -> k.identifier()).orElse(null);
		if (id == null) {
			return Component.literal("?");
		}
		String path = id.getPath();
		if (UniqueSeparation.isUnique(id)) {
			return uniqueName(path.substring("unicas/".length()));
		}
		if (MediumStructures.isMedium(id)) { // heraldia:medianas/<type>/<style>
			return mediumName(path.split("/")[1]);
		}
		if (Mines.isMine(id)) { // heraldia:minas/<size>/<style>/<variant>
			return Texts.t("heraldia.minas." + path.split("/")[1] + ".nombre");
		}
		if (Coast.isCoast(id)) { // heraldia:costa/<type>/<style>/<variant>
			return Texts.t("heraldia.costa." + Coast.type(id) + ".nombre");
		}
		String style = path.endsWith("_grande") ? path.substring(0, path.length() - "_grande".length()) : path;
		JsonObject styles = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		if (styles.has(style)) {
			return Texts.t("heraldia.info.aldea", Texts.t("heraldia.familia." + styles.get(style).getAsString()));
		}
		return Component.literal(id.toString());
	}

	/** Can the unique spawn in this world? The one-per-world ones (no option) always; the others, if enabled. */
	static boolean uniqueEnabled(HeraldiaConfig cfg, String sid) {
		String key = "unicas." + sid + ".activada";
		return !cfg.has(key) || cfg.getBool(key);
	}

	static MutableComponent uniqueName(String sid) {
		return Texts.t("heraldia.unicas." + sid + ".nombre");
	}

	static MutableComponent mediumName(String tid) {
		return Texts.t("heraldia.medianas." + tid + ".nombre");
	}

	static Component onOff(boolean b) {
		return Texts.t(b ? "heraldia.info.activada" : "heraldia.info.desactivada");
	}

	static Component yesNo(boolean b) {
		return Texts.t(b ? "heraldia.info.si" : "heraldia.info.no");
	}
}
