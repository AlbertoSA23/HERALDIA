package io.github.albertosa23.heraldia.ambience;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.common.Profiler;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashMap;
import java.util.IdentityHashMap;
import java.util.Iterator;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.UUID;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Holder;
import net.minecraft.core.HolderSet;
import net.minecraft.core.Registry;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.protocol.game.ClientboundSoundPacket;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvent;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.tags.TagKey;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.level.levelgen.structure.StructureStart;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Ambient effects with the game's own sounds and particles (nothing new to download: vanilla clients hear them as they
 * are). Every sound is sent only to the players it is meant for, in the "ambient" sound category (the player's own
 * Ambient/Environment slider turns it down), and each player has a cooldown per effect.
 * <ul>
 * <li><b>Village bell</b> ({@code ambiente.campanas}): at sunrise and at nightfall the bell of a Heraldia village rings
 * three strikes for the players inside it (its box: streets, houses and outskirts).</li>
 * <li><b>Lighthouse siren</b> ({@code ambiente.sirena_faro}): in rain or a thunderstorm, a lighthouse (coastal or the
 * smugglers' one) sounds a deep horn for the players out in the open within {@link AmbienceRules#SIREN_RADIUS} blocks;
 * from the sea it is heard far off. At most once every 3 min per player.</li>
 * <li><b>Mine galleries</b> ({@code ambiente.minas}): underground in a Heraldia mine (the entrances and the Lost Mine), a
 * drop of water falls from the ceiling now and then (the particle plays its own drip when it lands) and, rarely, the
 * cave's echo sounds down the gallery.</li>
 * </ul>
 * Cost: on the server tick only {@code tick % 100} (and whether a peal is still sounding). Every 5 s a loop over the
 * players: per player, one structure lookup in their own chunk every 20-45 s (mines), one more only in the minutes of
 * sunrise and nightfall (villages) and,
 * only while it rains and the player's siren is due, a look at the structure starts of the loaded chunks around them.
 * Nothing is saved; {@code ambiente.*} is read on each check (it reloads with /heraldia reload).
 */
public final class Ambience {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String ENABLED = "ambiente.activado", BELLS = "ambiente.campanas", SIREN = "ambiente.sirena_faro",
			MINES = "ambiente.minas";
	/** With {@code -Dheraldia.ambiente.registro=true}, each effect played is written to the log (for the tests). */
	static final boolean LOG = Boolean.getBoolean("heraldia.ambiente.registro");
	static final TagKey<Structure> VILLAGES = tag("aldeas"), COAST_LIGHTHOUSES = tag("costa/faro"),
			UNIQUE_LIGHTHOUSE = tag("unicas/faro"), MINE_ENTRANCES = tag("minas"), LOST_MINE = tag("unicas/mina_perdida");
	/** Goat horn "Ponder", the deepest one, as the foghorn. */
	private static final int HORN = 0;
	private static final float SIREN_VOLUME = AmbienceRules.SIREN_RADIUS / 16f, SIREN_PITCH = 0.6f;

	/** When each player last heard each effect (server ticks), and when their next mine cue is due. */
	static final class Heard {
		long bell = AmbienceRules.NEVER, siren = AmbienceRules.NEVER, sirenSearch = AmbienceRules.NEVER, echo = AmbienceRules.NEVER;
		long nextMineCue = AmbienceRules.NEVER;
	}

	/** A peal still sounding: its next strike and who hears it. */
	private record Peal(ServerLevel level, BlockPos bell, List<UUID> players, int strike, long at) {
	}

	private static final Map<UUID, Heard> HEARD = new HashMap<>();
	private static final List<Peal> PEALS = new ArrayList<>();
	private static Set<Structure> lighthouses = Set.of(), mines = Set.of();
	private static HolderSet<Structure> villages;
	private static long lastHalfDay = -1;

	private Ambience() {
	}

	private static TagKey<Structure> tag(String path) {
		return TagKey.create(Registries.STRUCTURE, Heraldia.id(path));
	}

	/** One line in Heraldia.onInitialize. */
	public static void register() {
		ServerLifecycleEvents.SERVER_STARTED.register(Ambience::resolve);
		ServerTickEvents.END_SERVER_TICK.register(Ambience::tick);
		ServerPlayConnectionEvents.DISCONNECT.register((handler, server) -> HEARD.remove(handler.getPlayer().getUUID()));
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> {
			HEARD.clear();
			PEALS.clear();
			lighthouses = mines = Set.of();
			villages = null;
			lastHalfDay = -1;
		});
	}

	/** The structures each effect looks for, once per start (worldgen does not change with /reload). */
	private static void resolve(MinecraftServer server) {
		Registry<Structure> reg = server.registryAccess().lookupOrThrow(Registries.STRUCTURE);
		villages = reg.get(VILLAGES).map(h -> (HolderSet<Structure>) h).orElse(HolderSet.empty());
		lighthouses = values(reg, COAST_LIGHTHOUSES, UNIQUE_LIGHTHOUSE);
		mines = values(reg, MINE_ENTRANCES, LOST_MINE);
	}

	@SafeVarargs
	private static Set<Structure> values(Registry<Structure> reg, TagKey<Structure>... tags) {
		Set<Structure> out = Collections.newSetFromMap(new IdentityHashMap<>());
		for (TagKey<Structure> t : tags) {
			reg.get(t).ifPresent(set -> set.forEach(h -> out.add(h.value())));
		}
		return out;
	}

	// --- every tick: only the modulo and the peals still sounding ---

	private static void tick(MinecraftServer server) {
		long t = server.getTickCount();
		if (!PEALS.isEmpty()) {
			strike(server, t);
		}
		if (!AmbienceRules.checkTick(t) || villages == null) {
			return;
		}
		long t0 = Profiler.start();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		if (cfg.getBool(ENABLED) && !server.getPlayerList().getPlayers().isEmpty()) {
			check(server, cfg, t);
		}
		Profiler.end(Profiler.Segment.AMBIENCE, t0);
	}

	private static void check(MinecraftServer server, HeraldiaConfig cfg, long t) {
		boolean bells = cfg.getBool(BELLS), siren = cfg.getBool(SIREN), mineCues = cfg.getBool(MINES);
		ServerLevel overworld = server.overworld();
		long half = bells ? AmbienceRules.bellHalfDay(overworld.getOverworldClockTime(), lastHalfDay) : -1;
		if (half >= 0) {
			lastHalfDay = half;
			ring(overworld, t, AmbienceRules.morning(half));
		}
		boolean storm = siren && AmbienceRules.sirenWeather(overworld.isRaining(), overworld.isThundering());
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			if (!p.isAlive()) {
				continue;
			}
			Heard h = HEARD.computeIfAbsent(p.getUUID(), u -> new Heard());
			ServerLevel level = p.level();
			if (storm && level == overworld && AmbienceRules.ready(t, h.siren, AmbienceRules.SIREN_COOLDOWN)
					&& AmbienceRules.ready(t, h.sirenSearch, AmbienceRules.SIREN_SEARCH_COOLDOWN)) {
				sirenFor(server, level, p, h, t);
			}
			if (mineCues && !mines.isEmpty() && (h.nextMineCue == AmbienceRules.NEVER || t >= h.nextMineCue || t < h.nextMineCue - AmbienceRules.DRIP_MAX)) {
				mineCue(level, p, h, t);
			}
		}
	}

	// --- village bell ---

	/** Sunrise or nightfall: a peal for each village with players inside (each player hears only their village's). */
	private static void ring(ServerLevel level, long t, boolean morning) {
		Map<StructureStart, List<UUID>> byVillage = new IdentityHashMap<>();
		for (ServerPlayer p : level.players()) {
			Heard h = HEARD.computeIfAbsent(p.getUUID(), u -> new Heard());
			if (!p.isAlive() || !AmbienceRules.ready(t, h.bell, AmbienceRules.BELL_COOLDOWN)) {
				continue;
			}
			StructureStart v = village(level, p.blockPosition());
			if (v != null) {
				h.bell = t;
				byVillage.computeIfAbsent(v, k -> new ArrayList<>()).add(p.getUUID());
			}
		}
		byVillage.forEach((v, players) -> {
			BlockPos bell = belfry(v);
			if (LOG) {
				LOGGER.info("Heraldia: ambiente: campana de {} en {} {} {} para {} jugador(es)", morning ? "alba" : "anochecer",
						bell.getX(), bell.getY(), bell.getZ(), players.size());
			}
			PEALS.add(new Peal(level, bell, players, 0, t));
		});
		if (!PEALS.isEmpty()) {
			strike(level.getServer(), t);
		}
	}

	/** The Heraldia village whose box holds this point, or null (only the references of the point's own chunk are read). */
	private static StructureStart village(ServerLevel level, BlockPos pos) {
		StructureStart s = level.structureManager().getStructureAt(pos, villages);
		return s.isValid() ? s : null;
	}

	/** Where the bell rings from: the centre of the village's first piece (its square), a little above the ground. */
	private static BlockPos belfry(StructureStart v) {
		BoundingBox b = v.getPieces().isEmpty() ? v.getBoundingBox() : v.getPieces().getFirst().getBoundingBox();
		BlockPos c = b.getCenter();
		return new BlockPos(c.getX(), b.minY() + 6, c.getZ());
	}

	/** The strikes due at {@code t}. */
	private static void strike(MinecraftServer server, long t) {
		Holder<SoundEvent> bell = BuiltInRegistries.SOUND_EVENT.wrapAsHolder(SoundEvents.BELL_BLOCK);
		List<Peal> next = new ArrayList<>();
		for (Iterator<Peal> it = PEALS.iterator(); it.hasNext(); ) {
			Peal p = it.next();
			if (t < p.at() && p.at() - t <= AmbienceRules.BELL_GAP) {
				continue;
			}
			it.remove();
			for (UUID u : p.players()) {
				ServerPlayer pl = server.getPlayerList().getPlayer(u);
				if (pl != null && pl.level() == p.level()) {
					play(pl, bell, p.bell(), AmbienceRules.BELL_REACH, 2.0f, 1.0f);
				}
			}
			if (p.strike() + 1 < AmbienceRules.BELL_STRIKES) {
				next.add(new Peal(p.level(), p.bell(), p.players(), p.strike() + 1, t + AmbienceRules.BELL_GAP));
			}
		}
		PEALS.addAll(next);
	}

	// --- lighthouse siren ---

	/** The nearest loaded lighthouse within range of the player; if there is one, its horn for everyone in range who is due. */
	private static void sirenFor(MinecraftServer server, ServerLevel level, ServerPlayer p, Heard h, long t) {
		h.sirenSearch = t;
		if (lighthouses.isEmpty() || !outdoors(level, p)) {
			return;
		}
		BlockPos light = lighthouse(level, p);
		if (light == null) {
			return;
		}
		Holder<SoundEvent> horn = SoundEvents.GOAT_HORN_SOUND_VARIANTS.get(HORN);
		double r2 = (double) AmbienceRules.SIREN_RADIUS * AmbienceRules.SIREN_RADIUS;
		int n = 0;
		for (ServerPlayer q : level.players()) {
			Heard hq = HEARD.computeIfAbsent(q.getUUID(), u -> new Heard());
			if (q.isAlive() && AmbienceRules.ready(t, hq.siren, AmbienceRules.SIREN_COOLDOWN) && outdoors(level, q)
					&& AmbienceRules.horizontal2(q.getX(), q.getZ(), light.getX() + 0.5, light.getZ() + 0.5) <= r2) {
				hq.siren = hq.sirenSearch = t;
				play(q, horn, light, AmbienceRules.SIREN_RADIUS, SIREN_VOLUME, SIREN_PITCH);
				n++;
			}
		}
		if (LOG) {
			LOGGER.info("Heraldia: ambiente: sirena del faro de {} {} {} para {} jugador(es)", light.getX(), light.getY(), light.getZ(), n);
		}
	}

	/** Out in the open air, above the sea's depth (not in a cave or under water). */
	private static boolean outdoors(ServerLevel level, ServerPlayer p) {
		return p.getBlockY() >= level.getSeaLevel() - AmbienceRules.SIREN_DEPTH
				&& p.getEyeY() >= level.getHeight(Heightmap.Types.MOTION_BLOCKING, p.getBlockX(), p.getBlockZ());
	}

	/** The top of the nearest lighthouse whose start chunk is loaded within the radius, or null. Never loads a chunk. */
	private static BlockPos lighthouse(ServerLevel level, ServerPlayer p) {
		int r = (AmbienceRules.SIREN_RADIUS >> 4) + 1, cx = p.getBlockX() >> 4, cz = p.getBlockZ() >> 4;
		double best = (double) AmbienceRules.SIREN_RADIUS * AmbienceRules.SIREN_RADIUS;
		BlockPos out = null;
		for (int x = cx - r; x <= cx + r; x++) {
			for (int z = cz - r; z <= cz + r; z++) {
				LevelChunk c = level.getChunkSource().getChunkNow(x, z);
				if (c == null) {
					continue;
				}
				Map<Structure, StructureStart> starts = c.getAllStarts();
				if (starts.isEmpty()) {
					continue;
				}
				for (Map.Entry<Structure, StructureStart> e : starts.entrySet()) {
					if (!lighthouses.contains(e.getKey()) || !e.getValue().isValid()) {
						continue;
					}
					BoundingBox b = e.getValue().getBoundingBox();
					BlockPos top = new BlockPos(b.getCenter().getX(), b.maxY() - 2, b.getCenter().getZ());
					double d = AmbienceRules.horizontal2(p.getX(), p.getZ(), top.getX() + 0.5, top.getZ() + 0.5);
					if (d <= best) {
						best = d;
						out = top;
					}
				}
			}
		}
		return out;
	}

	// --- mine galleries ---

	/** The player's turn for a mine cue: underground in a Heraldia mine, a drip from the ceiling or, now and then, the echo. */
	private static void mineCue(ServerLevel level, ServerPlayer p, Heard h, long t) {
		BlockPos head = BlockPos.containing(p.getX(), p.getEyeY(), p.getZ());
		boolean first = h.nextMineCue == AmbienceRules.NEVER;
		h.nextMineCue = t + (first ? AmbienceRules.PERIOD : AmbienceRules.nextMineCue(p.getRandom().nextDouble()));
		if (p.isSpectator() || level.getHeight(Heightmap.Types.MOTION_BLOCKING, head.getX(), head.getZ()) <= head.getY() + 1) {
			return;                                  // under the open sky: not in a gallery
		}
		StructureStart s = level.structureManager().getStructureWithPieceAt(head, holder -> mines.contains(holder.value()));
		if (!s.isValid()) {
			return;
		}
		if (first) {                                 // just walked in: the first drip comes after the usual wait
			h.nextMineCue = t + AmbienceRules.nextMineCue(p.getRandom().nextDouble());
			return;
		}
		BlockPos ceiling = ceiling(level, p);
		switch (AmbienceRules.mineCue(p.getRandom().nextInt(100), AmbienceRules.ready(t, h.echo, AmbienceRules.ECHO_COOLDOWN), ceiling != null)) {
			case DRIP -> {
				// the drop hangs from the ceiling, falls and plays the drip sound itself when it lands (vanilla client)
				level.sendParticles(p, ParticleTypes.DRIPPING_DRIPSTONE_WATER, false, false, ceiling.getX() + 0.3 + p.getRandom().nextDouble() * 0.4,
						ceiling.getY() + 0.95, ceiling.getZ() + 0.3 + p.getRandom().nextDouble() * 0.4, 1, 0, 0, 0, 0);
				if (LOG) {
					LOGGER.info("Heraldia: ambiente: gota en {} {} {} para {}", ceiling.getX(), ceiling.getY(), ceiling.getZ(), p.getScoreboardName());
				}
			}
			case ECHO -> {
				h.echo = t;
				double a = p.getRandom().nextDouble() * Math.PI * 2;
				BlockPos from = BlockPos.containing(p.getX() + Math.cos(a) * AmbienceRules.ECHO_DISTANCE, p.getEyeY(),
						p.getZ() + Math.sin(a) * AmbienceRules.ECHO_DISTANCE);
				play(p, SoundEvents.AMBIENT_CAVE, from, AmbienceRules.ECHO_DISTANCE, 0.6f, 0.8f + p.getRandom().nextFloat() * 0.2f);
				if (LOG) {
					LOGGER.info("Heraldia: ambiente: eco en {} {} {} para {}", from.getX(), from.getY(), from.getZ(), p.getScoreboardName());
				}
			}
			case NONE -> {
			}
		}
	}

	/**
	 * An air block right under the ceiling, near and above the player's head, or null: a few random columns within 2 blocks
	 * (in a 3-wide gallery many fall in the wall) and, last, the player's own. A handful of block reads.
	 */
	private static BlockPos ceiling(ServerLevel level, ServerPlayer p) {
		int y0 = (int) Math.floor(p.getEyeY());
		BlockPos.MutableBlockPos m = new BlockPos.MutableBlockPos();
		for (int i = 0; i <= AmbienceRules.CEILING_TRIES; i++) {
			boolean own = i == AmbienceRules.CEILING_TRIES;
			int x = p.getBlockX() + (own ? 0 : p.getRandom().nextInt(5) - 2), z = p.getBlockZ() + (own ? 0 : p.getRandom().nextInt(5) - 2);
			m.set(x, y0, z);
			if (!level.getBlockState(m).isAir()) {
				continue;
			}
			for (int dy = 1; dy <= AmbienceRules.CEILING_SEARCH; dy++) {
				m.setY(y0 + dy);
				BlockState st = level.getBlockState(m);
				if (!st.isAir()) {
					if (st.getFluidState().isEmpty() && st.isSolidRender()) {
						return new BlockPos(x, y0 + dy - 1, z);
					}
					break;
				}
			}
		}
		return null;
	}

	// --- sending ---

	/** The sound only to this player, from {@code at} or, if it is farther than {@code reach}, from that far on the way to it. */
	private static void play(ServerPlayer p, Holder<SoundEvent> sound, BlockPos at, double reach, float volume, float pitch) {
		double[] s = AmbienceRules.source(p.getX(), p.getEyeY(), p.getZ(), at.getX() + 0.5, at.getY() + 0.5, at.getZ() + 0.5, reach);
		p.connection.send(new ClientboundSoundPacket(sound, SoundSource.AMBIENT, s[0], s[1], s[2], volume, pitch, p.getRandom().nextLong()));
	}
}
