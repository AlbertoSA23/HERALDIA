package io.github.albertosa23.heraldia.comando;

import com.google.gson.JsonObject;
import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.GridPlacement;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.loot.WithoutLootrCondition;
import it.unimi.dsi.fastutil.longs.LongSet;
import io.github.albertosa23.heraldia.comun.Medianas;
import io.github.albertosa23.heraldia.unicas.atlantida.AtlantisAnchor;
import java.util.concurrent.CompletableFuture;
import net.minecraft.core.RegistryAccess;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.IntTag;
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
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
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
 * /heraldia info [cerca [radio] | aqui] (operador, nivel 2). Solo trabaja cuando se ejecuta:
 * <ul>
 * <li>info: la configuración en uso y cuántas estructuras hay registradas.</li>
 * <li>info cerca [radio]: la estructura única y la mediana más cercanas de cada tipo y la aldea Heraldia más cercana. Recorre las
 * casillas de cada rejilla dentro del radio con las reglas de la generación (las de StructureCheck y los mixins más la
 * zona de exclusión de las aldeas vanilla) y lee los chunks ya guardados con el escáner de StructureCheck: todo fuera
 * del hilo del servidor; en él solo se miran los chunks ya cargados. No carga ni genera chunks: una casilla sin generar
 * se da como «prevista». Radio acotado (MAX_RADIUS); el tiempo total y el del hilo del servidor se miden.</li>
 * <li>info aqui: la estructura Heraldia en cuyas piezas está la posición y, si es única, si vive su guardián (las
 * entidades con la etiqueta heraldia_guardian.&lt;id&gt; dentro de su caja, solo si toda la caja está cargada).</li>
 * </ul>
 */
public final class InfoCommand {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final int DEFAULT_RADIUS = 3000, MAX_RADIUS = 10000;
	private static final String GUARDIAN_TAG = "heraldia_guardian"; // _comun/piezas.GUARDIAN_TAG
	private static final String[] DIRECTIONS = {"s", "so", "o", "no", "n", "ne", "e", "se"};

	private InfoCommand() {
	}

	public static void register() {
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> build(dispatcher));
	}

	private static void build(CommandDispatcher<CommandSourceStack> dispatcher) {
		dispatcher.register(Commands.literal("heraldia")
				.then(Commands.literal("info")
						.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
						.executes(InfoCommand::summary)
						.then(Commands.literal("cerca")
								.executes(ctx -> near(ctx, DEFAULT_RADIUS))
								.then(Commands.argument("radio", IntegerArgumentType.integer(16, MAX_RADIUS))
										.executes(ctx -> near(ctx, IntegerArgumentType.getInteger(ctx, "radio")))))
						.then(Commands.literal("aqui").executes(InfoCommand::here))));
	}

	// --- info ---

	private static int summary(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack source = ctx.getSource();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		JsonObject schema = cfg.schema();
		List<Component> lines = new ArrayList<>();
		lines.add(Textos.t("heraldia.info.titulo").withStyle(ChatFormatting.GOLD));
		lines.add(Textos.t("heraldia.info.aldeas", cfg.getInt("aldeas.separacion_bloques"), cfg.getInt("aldeas.maximo"),
				cfg.getInt("aldeas.porcentaje_grandes"), cfg.villages().enabledStyles(),
				schema.getAsJsonObject("aldeas").getAsJsonObject("estilos").size(), cfg.getInt("aldeas.distancia_aldeas_vanilla_bloques")));

		Registry<Structure> registry = source.getServer().registryAccess().lookupOrThrow(Registries.STRUCTURE);
		List<Identifier> uniques = new ArrayList<>();
		int heraldia = 0, medium = 0;
		for (Identifier id : registry.keySet()) {
			if (Heraldia.MOD_ID.equals(id.getNamespace())) {
				heraldia++;
				if (UniqueSeparation.isUnique(id)) {
					uniques.add(id);
				} else if (Medianas.esMediana(id)) {
					medium++;
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
				uniqueLines.add(Textos.t("heraldia.info.unica.mundial", uniqueName(sid)));
			} else if (cfg.getBool(key + ".activada")) {
				enabled++;
				uniqueLines.add(Textos.t("heraldia.info.unica", uniqueName(sid), cfg.getInt(key + ".separacion_bloques")));
			} else {
				uniqueLines.add(Textos.t("heraldia.info.unica.desactivada", uniqueName(sid)).withStyle(ChatFormatting.GRAY));
			}
		}
		lines.add(Textos.t("heraldia.info.unicas", enabled, uniques.size()));
		lines.addAll(uniqueLines);
		lines.add(Textos.t("heraldia.info.distancia", onOff(cfg.getBool("unicas.distancia_minima.activada")),
				cfg.getInt("unicas.distancia_minima.bloques")));
		lines.add(Textos.t("heraldia.info.rejilla", onOff(cfg.getBool(GridPlacement.LEGACY_OPTION))));
		lines.add(Textos.t("heraldia.info.cofre", yesNo(cfg.getBool("unicas.atlantida.cofre_unico_por_jugador")),
				Textos.t(WithoutLootrCondition.LOOTR_LOADED ? "heraldia.info.cargado" : "heraldia.info.no_cargado")));
		lines.addAll(mediumLines(source, cfg));
		lines.add(Textos.t("heraldia.info.registradas", heraldia, heraldia - uniques.size() - medium, uniques.size(), medium));
		lines.forEach(l -> source.sendSuccess(() -> l, false));
		return heraldia;
	}

	/** Estructuras medianas: la configuración común y, por tipo (un structure_set medianas/&lt;tipo&gt;), su separación. */
	private static List<Component> mediumLines(CommandSourceStack source, HeraldiaConfig cfg) {
		Medianas m = Medianas.of(source.getServer().registryAccess());
		List<Component> out = new ArrayList<>(), types = new ArrayList<>();
		int enabled = 0;
		for (int i = 0; i < m.tipos(); i++) {
			String tid = m.tipoId(i).getPath().substring(Medianas.PREFIJO.length());
			String key = "medianas." + tid;
			if (cfg.getBool(Medianas.ACTIVADAS) && cfg.getBool(key + ".activada")) {
				enabled++;
				types.add(Textos.t("heraldia.info.mediana", mediumName(tid), cfg.getInt(key + ".separacion_bloques")));
			} else {
				types.add(Textos.t("heraldia.info.unica.desactivada", mediumName(tid)).withStyle(ChatFormatting.GRAY));
			}
		}
		out.add(Textos.t("heraldia.info.medianas", onOff(cfg.getBool(Medianas.ACTIVADAS)), enabled, m.tipos(),
				cfg.getInt(Medianas.FRECUENCIA), cfg.getInt(Medianas.ZONA), cfg.getInt(Medianas.DISTANCIA)));
		out.addAll(types);
		return out;
	}

	// --- info cerca ---

	/** generated: la estructura está en el chunk guardado o cargado; si no, está prevista (chunk sin generar). */
	private record Found(Holder<Structure> structure, ChunkPos chunk, BlockPos pos, long distanceSq, boolean generated) {
	}

	private record Group(RandomSpreadStructurePlacement placement, List<Holder<Structure>> structures) {
	}

	/** Qué dice el chunk guardado: null = no existe en disco; si existe, las estructuras cuyo inicio guarda. */
	private record Stored(List<Identifier> starts) {
	}

	private static int near(CommandContext<CommandSourceStack> ctx, int radius) {
		CommandSourceStack source = ctx.getSource();
		ServerLevel level = source.getLevel();
		BlockPos origin = BlockPos.containing(source.getPosition());
		List<Group> groups = groups(level);
		long t0 = System.nanoTime();
		// 1) fuera del hilo del servidor, lo caro: dónde saldría cada tipo y qué hay ya en los chunks guardados
		CompletableFuture.supplyAsync(() -> search(level, groups, origin, radius), Util.backgroundExecutor())
				// 2) en el hilo del servidor, lo barato: los chunks ya cargados (aún sin guardar) mandan sobre el disco
				.thenAcceptAsync(found -> {
					long t1 = System.nanoTime();
					List<Found> out = confirm(level, groups, found);
					long t2 = System.nanoTime();
					report(source, origin, radius, out, (t2 - t0) / 1_000_000, (t2 - t1) / 1_000_000);
				}, source.getServer())
				.exceptionally(e -> {
					LOGGER.error("Heraldia: /heraldia info cerca falló", e);
					source.sendFailure(Component.literal(String.valueOf(e.getMessage())));
					return null;
				});
		return 1;
	}

	private static void report(CommandSourceStack source, BlockPos origin, int radius, List<Found> found, long ms, long mainMs) {
		LOGGER.info("Heraldia: /heraldia info cerca {} en {}, {}: {} estructuras en {} ms ({} ms en el hilo del servidor)",
				radius, origin.getX(), origin.getZ(), found.size(), ms, mainMs);
		if (found.isEmpty()) {
			source.sendSuccess(() -> Textos.t("heraldia.info.cerca.nada", radius, origin.getX(), origin.getZ(), ms), false);
			return;
		}
		source.sendSuccess(() -> Textos.t("heraldia.info.cerca.titulo", radius, origin.getX(), origin.getZ(), ms).withStyle(ChatFormatting.GOLD), false);
		for (Found f : found) {
			int dx = f.pos.getX() - origin.getX(), dz = f.pos.getZ() - origin.getZ();
			Component line = Textos.t("heraldia.info.cerca.linea", name(f.structure), id(f), Mth.floor(Math.sqrt(f.distanceSq)),
					Textos.t("heraldia.info.dir." + direction(dx, dz)), coordinates(f.pos),
					Textos.t(f.generated ? "heraldia.info.generada" : "heraldia.info.prevista"));
			source.sendSuccess(() -> line, false);
		}
	}

	/** Estructuras del mod agrupadas por colocación: una por tipo de única; las aldeas comparten la suya. */
	private static List<Group> groups(ServerLevel level) {
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
	 * Por cada colocación, las casillas a menos de radius bloques de la más cercana a la más lejana; se queda con la
	 * primera en la que hay (chunk guardado con su inicio) o habría (chunk sin generar en el que la generación la pondría)
	 * una estructura. «Habría» sigue las reglas de la generación: isStructureChunk (casillas permitidas y zona de
	 * exclusión de las aldeas vanilla, que /locate no mira antes de cargar el chunk), aldeas desactivadas o de otro
	 * tamaño, exclusión de la Atlántida, distancia mínima entre únicas y findValidGenerationPoint con bioma y terreno
	 * reales. Todo es seguro entre hilos (lo consultan los hilos de generación); el disco se lee con el mismo escáner que
	 * StructureCheck. No carga ni genera chunks.
	 */
	static List<Found> search(ServerLevel level, List<Group> groups, BlockPos origin, int radius) {
		ChunkGenerator generator = level.getChunkSource().getGenerator();
		RandomState randomState = level.getChunkSource().randomState();
		ChunkGeneratorStructureState state = level.getChunkSource().getGeneratorState();
		ChunkScanAccess scanner = level.getChunkSource().chunkScanner();
		long seed = state.getLevelSeed();
		RegistryAccess access = level.registryAccess();
		Climate.Sampler sampler = randomState.createClimateSampler(SamplerContext.builder().enableCaches().build()); // de este hilo
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
				if (stored != null) { // generado: vale lo guardado (otra aldea del set, nada si se exploró antes del mod...)
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

	/** Inicios de estructura del chunk guardado (solo esos campos, como StructureCheck), o null si no está en disco. */
	private static Stored stored(ChunkScanAccess scanner, ChunkPos pos) {
		CollectFields fields = new CollectFields(new FieldSelector(IntTag.TYPE, "DataVersion"),
				new FieldSelector("structures", CompoundTag.TYPE, "starts"));
		try {
			scanner.scanChunk(pos, fields).join();
		} catch (RuntimeException e) {
			return null;
		}
		if (!(fields.getResult() instanceof CompoundTag tag)) {
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

	private static Holder<Structure> firstViable(Group g, ChunkPos c, long seed, ServerLevel level, RegistryAccess access,
												 ChunkGenerator generator, RandomState randomState, Climate.Sampler sampler,
												 UniqueSeparation sep, UniqueSeparation.Viability viability) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		for (Holder<Structure> h : g.structures) {
			Identifier id = h.unwrapKey().orElseThrow().identifier();
			if (!cfg.villages().allows(id, seed, c.x(), c.z())) {
				continue; // aldea desactivada o de otro tamaño: lo más barato primero
			}
			int i = sep.indexOf(id);
			boolean ok;
			if (i >= 0) { // únicas: viabilidad (con la exclusión de la Atlántida) y distancia mínima, como los mixins
				ok = viability.valid(i, c.x(), c.z()) && !sep.blocked(i, c.x(), c.z(), seed, viability);
			} else {
				Structure st = h.value();
				ok = !AtlantisAnchor.excludes(id, level.dimension(), seed, c.x(), c.z())
						&& st.findValidGenerationPoint(new Structure.GenerationContext(access, generator, generator.getBiomeSource(), sampler,
						randomState, level.getStructureTemplateManager(), seed, c, level, st.biomes()::contains)).isPresent()
						&& !(Medianas.esMediana(id) && Medianas.of(access).rechaza(id, c.x(), c.z(), seed, access, generator,
						generator.getBiomeSource(), sampler, randomState, level.getStructureTemplateManager(), level, level.dimension()));
			}
			if (ok) {
				return h;
			}
		}
		return null;
	}

	/**
	 * En el hilo del servidor: un chunk cargado puede ser más nuevo que el disco (generado y aún sin guardar). Si lo
	 * está, manda su inicio; una prevista cuyo chunk ya está generado sin ella se quita. Solo mira chunks ya cargados.
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


	/** Rumbo de 8 puntos (norte = -z). */
	static String direction(int dx, int dz) {
		double angle = Math.toDegrees(Math.atan2(-dx, dz)); // 0 = sur, 90 = oeste, 180 = norte, -90 = este
		int i = Math.floorMod((int) Math.round(angle / 45.0), 8);
		return DIRECTIONS[i];
	}

	private static Component coordinates(BlockPos pos) {
		return ComponentUtils.wrapInSquareBrackets(Component.translatable("chat.coordinates", pos.getX(), "~", pos.getZ()))
				.withStyle(s -> s.withColor(ChatFormatting.GREEN)
						.withClickEvent(new ClickEvent.SuggestCommand("/tp @s " + pos.getX() + " ~ " + pos.getZ()))
						.withHoverEvent(new HoverEvent.ShowText(Component.translatable("chat.coordinates.tooltip"))));
	}

	// --- info aqui ---

	private static int here(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack source = ctx.getSource();
		ServerLevel level = source.getLevel();
		BlockPos pos = BlockPos.containing(source.getPosition());
		LevelChunk chunk = level.getChunkSource().getChunkNow(SectionPos.blockToSectionCoord(pos.getX()), SectionPos.blockToSectionCoord(pos.getZ()));
		if (chunk == null) { // solo chunks ya cargados: nada de cargar ni generar
			source.sendFailure(Textos.t("heraldia.info.aqui.sin_cargar"));
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
			source.sendSuccess(() -> Textos.t("heraldia.info.aqui.linea", name(holder), id.toString()), false);
			if (UniqueSeparation.isUnique(id)) {
				Component g = guardian(level, holder, start, GUARDIAN_TAG + "." + id.getPath().substring("unicas/".length()));
				source.sendSuccess(() -> g, false);
			}
		}
		if (count == 0) {
			source.sendSuccess(() -> Textos.t("heraldia.info.aqui.nada"), false);
		}
		return count;
	}

	/**
	 * Vivo si hay una entidad con su etiqueta en la caja del inicio principal (con margen); derrotado solo si toda la caja
	 * tiene sus entidades cargadas. El inicio principal es el que da la colocación para esta casilla: el mismo en las de
	 * rejilla; en la Atlántida (nueve inicios, uno por distrito) el distrito central, donde está el guardián.
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
				return Textos.t("heraldia.info.guardian.desconocido");
			}
			box = mainStart.getBoundingBox();
		}
		AABB area = AABB.of(box).inflate(16);
		List<Entity> found = level.getEntities((Entity) null, area, e -> e.entityTags().contains(tag));
		if (!found.isEmpty()) {
			BlockPos p = found.getFirst().blockPosition();
			return Textos.t("heraldia.info.guardian.vivo", p.getX(), p.getY(), p.getZ());
		}
		for (int x = SectionPos.blockToSectionCoord(box.minX()); x <= SectionPos.blockToSectionCoord(box.maxX()); x++) {
			for (int z = SectionPos.blockToSectionCoord(box.minZ()); z <= SectionPos.blockToSectionCoord(box.maxZ()); z++) {
				if (!level.areEntitiesLoaded(ChunkPos.pack(x, z))) {
					return Textos.t("heraldia.info.guardian.desconocido");
				}
			}
		}
		return Textos.t("heraldia.info.guardian.derrotado");
	}

	// --- nombres ---

	/**
	 * Id que se muestra: el de la estructura, salvo en una aldea prevista, cuyo estilo aún no está decidido (la familia la
	 * fija el bioma, pero el estilo lo sortea el structure_set al generarse): entonces el del set, heraldia:aldeas.
	 */
	private static String id(Found f) {
		Identifier id = f.structure.unwrapKey().map(k -> k.identifier()).orElse(null);
		if (id == null) {
			return "?";
		}
		if (f.generated || UniqueSeparation.isUnique(id)) {
			return id.toString();
		}
		if (Medianas.esMediana(id)) { // prevista: el estilo lo sortea el structure_set del tipo al generarse
			return Heraldia.MOD_ID + ":" + id.getPath().substring(0, id.getPath().lastIndexOf('/'));
		}
		return Heraldia.MOD_ID + ":aldeas";
	}

	/** Nombre traducido: el de la única (heraldia.unicas.&lt;id&gt;.nombre) o «Aldea Heraldia de &lt;familia&gt;». */
	private static MutableComponent name(Holder<Structure> h) {
		Identifier id = h.unwrapKey().map(k -> k.identifier()).orElse(null);
		if (id == null) {
			return Component.literal("?");
		}
		String path = id.getPath();
		if (UniqueSeparation.isUnique(id)) {
			return uniqueName(path.substring("unicas/".length()));
		}
		if (Medianas.esMediana(id)) { // heraldia:medianas/<tipo>/<estilo>
			return mediumName(path.split("/")[1]);
		}
		String style = path.endsWith("_grande") ? path.substring(0, path.length() - "_grande".length()) : path;
		JsonObject styles = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		if (styles.has(style)) {
			return Textos.t("heraldia.info.aldea", Textos.t("heraldia.familia." + styles.get(style).getAsString()));
		}
		return Component.literal(id.toString());
	}

	/** ¿Puede salir la única en este mundo? Las de una por mundo (sin opción) siempre; las demás, si están activadas. */
	static boolean uniqueEnabled(HeraldiaConfig cfg, String sid) {
		String key = "unicas." + sid + ".activada";
		return !cfg.has(key) || cfg.getBool(key);
	}

	private static MutableComponent uniqueName(String sid) {
		return Textos.t("heraldia.unicas." + sid + ".nombre");
	}

	private static MutableComponent mediumName(String tid) {
		return Textos.t("heraldia.medianas." + tid + ".nombre");
	}

	private static Component onOff(boolean b) {
		return Textos.t(b ? "heraldia.info.activada" : "heraldia.info.desactivada");
	}

	private static Component yesNo(boolean b) {
		return Textos.t(b ? "heraldia.info.si" : "heraldia.info.no");
	}
}
