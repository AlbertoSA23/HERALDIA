package io.github.albertosa23.heraldia.huts;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.common.Anchoring;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.bosses.Phases;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.fabric.api.event.player.UseEntityCallback;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.InteractionResult;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntityProcessor;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EntityTypes;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.Attributes;
import net.minecraft.world.entity.monster.Vex;
import net.minecraft.world.entity.monster.illager.Evoker;
import net.minecraft.world.entity.npc.villager.Villager;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Magos de las chozas de mago (T43; la plantilla en tools/gen/medianas/choza_mago.py). Un mago es un aldeano quieto con
 * la etiqueta {@link Decision#TAG}:
 * <ul>
 * <li>al cargarse ({@code ENTITY_LOAD}, salida temprana por etiquetas) recibe su nombre generado y la decisión de su choza
 * ({@link Decision#evil}, con chozas_mago.prob_malvado), que se guarda en sus etiquetas;</li>
 * <li>si es malvado, se revela una sola vez cuando un jugador se acerca a menos de {@link #RADIUS} bloques (una
 * consulta acotada por jugador cada segundo) o intenta comerciar con él ({@code UseEntityCallback}): mensaje traducido,
 * partículas y sonido, el aldeano desaparece y en su sitio aparece el Mago Malvado, un evocador con
 * {@link Phases#GUARDIAN} (fases, refuerzos y barra de jefe de jefes/; la dificultad lo escala como a los guardianes),
 * más vida, tres vexes de entrada (luego invoca los suyos, como cualquier evocador) y su tabla de botín
 * (heraldia:chozas_mago/malvado, o malvado_premium si sale el premio, chozas_mago.prob_botin_premium). Esa tabla
 * sustituye a la del evocador: no suelta el tótem vanilla (tools/gen/chozas_mago.py explica por qué).</li>
 * </ul>
 * El logro de vencerlo es de datos (player_killed_entity con {@link Decision#EVIL}).
 */
public final class Wizards {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String EVIL_PROB = "chozas_mago.prob_malvado", PREMIUM_PROB = "chozas_mago.prob_botin_premium";
	public static final String TABLE = "heraldia:chozas_mago/malvado", PREMIUM_TABLE = "heraldia:chozas_mago/malvado_premium";
	/** Distancia (bloques) a la que un jugador hace que el mago malvado se revele. */
	public static final int RADIUS = 7;
	/** Cada cuántos ticks se mira si hay jugadores junto a un mago. */
	static final int PERIOD = 20;
	/** Radio de búsqueda de /heraldia wizard. */
	static final int COMMAND_RADIUS = 32;
	static final float HEALTH = 48f;
	static final int VEXES = 3;
	private static List<String> names = List.of("Aldric");
	private static int nicknames = 1;
	private static int defeated;

	private Wizards() {
	}

	public static void register() {
		readNames();
		ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> onLoad(entity, level));
		UseEntityCallback.EVENT.register((player, world, hand, entity, hit) -> {
			if (entity instanceof Villager v && Decision.isWizard(v.entityTags()) && world instanceof ServerLevel level
					&& !player.isSpectator()) {
				if (decide(v, level) == Decision.State.EVIL) {
					reveal(v, level, false);
					return InteractionResult.FAIL;      // no hay tratos con un mago malvado
				}
			}
			return InteractionResult.PASS;
		});
		ServerTickEvents.END_SERVER_TICK.register(Wizards::tick);
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			if (!entity.entityTags().isEmpty() && entity.entityTags().contains(Decision.EVIL)) {
				defeat(entity);
			}
		});
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> defeated = 0);
	}

	private static void readNames() {
		String path = "/heraldia/chozas_mago.json";
		try (InputStream in = Wizards.class.getResourceAsStream(path)) {
			if (in == null) {
				LOGGER.warn("Heraldia: falta {} en el .jar: los magos se llaman todos igual", path);
				return;
			}
			JsonObject o = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
			List<String> n = new ArrayList<>();
			o.getAsJsonArray("nombres").forEach(e -> n.add(e.getAsString()));
			names = List.copyOf(n);
			nicknames = o.get("apodos").getAsInt();
		} catch (IOException | RuntimeException e) {
			LOGGER.warn("Heraldia: no se pudo leer {}: {}", path, e.toString());
		}
	}

	private static void onLoad(Entity entity, ServerLevel level) {
		if (entity instanceof Villager v && Decision.isWizard(v.entityTags())) {
			decide(v, level);
		}
	}

	/** Nombre y decisión del mago (una vez; luego se lee de sus etiquetas). */
	static Decision.State decide(Villager v, ServerLevel level) {
		Decision.State e = Decision.state(v.entityTags());
		int cx = v.blockPosition().getX() >> 4, cz = v.blockPosition().getZ() >> 4;
		long seed = level.getSeed();
		if (!v.entityTags().contains(Decision.NAMED)) {
			int[] i = Decision.name(seed, cx, cz, names.size(), nicknames);
			v.setCustomName(Texts.t("heraldia.chozas_mago.nombre", names.get(i[0]), Texts.t("heraldia.chozas_mago.apodo." + i[1])));
			v.setCustomNameVisible(true);
			v.addTag(Decision.NAMED);
		}
		if (e == Decision.State.UNDECIDED) {
			boolean evil = Decision.evil(seed, cx, cz, HeraldiaConfig.get().getInt(EVIL_PROB));
			v.addTag(evil ? Decision.EVIL_UNREVEALED : Decision.BENIGN);
			e = evil ? Decision.State.EVIL : Decision.State.BENIGN;
		}
		return e;
	}

	/** Una vez por segundo: ¿algún jugador junto a un mago malvado sin revelar? Una consulta acotada por jugador. */
	private static void tick(MinecraftServer server) {
		if (server.getTickCount() % PERIOD != 0) {
			return;
		}
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			if (p.isSpectator() || !p.isAlive()) {
				continue;
			}
			ServerLevel level = p.level();
			AABB zone = p.getBoundingBox().inflate(RADIUS);
			for (Villager v : level.getEntitiesOfClass(Villager.class, zone, x -> Decision.isWizard(x.entityTags()))) {
				if (v.isAlive() && v.distanceToSqr(p) <= (double) RADIUS * RADIUS && decide(v, level) == Decision.State.EVIL) {
					reveal(v, level, false);
				}
			}
		}
	}

	/**
	 * Revela al mago: el aldeano se va y aparece el Mago Malvado en su sitio. Una sola vez (la etiqueta
	 * {@link Decision#REVEALED} y el propio aldeano, que desaparece). {@code forced}: /heraldia wizard reveal.
	 */
	static @Nullable Evoker reveal(Villager v, ServerLevel level, boolean forced) {
		if (!v.isAlive() || v.entityTags().contains(Decision.REVEALED)) {
			return null;
		}
		v.addTag(Decision.REVEALED);
		int cx = v.blockPosition().getX() >> 4, cz = v.blockPosition().getZ() >> 4;
		boolean prize = Decision.premium(level.getSeed(), cx, cz, HeraldiaConfig.get().getInt(PREMIUM_PROB));
		CompoundTag data = new CompoundTag();
		data.putString("DeathLootTable", prize ? PREMIUM_TABLE : TABLE);   // sustituye a la del evocador (sin tótem)
		Entity e = EntityType.loadEntityRecursive(EntityTypes.EVOKER, data, level, EntitySpawnReason.EVENT, EntityProcessor.NOP);
		if (!(e instanceof Evoker evil)) {
			LOGGER.warn("Heraldia: chozas_mago: no se pudo crear el Mago Malvado en {}", v.blockPosition());
			return null;
		}
		Component name = v.getDisplayName();
		evil.snapTo(v.getX(), v.getY(), v.getZ(), v.getYRot(), 0f);
		evil.addTag(Decision.EVIL);
		evil.addTag(Phases.GUARDIAN);           // fases, refuerzos y barra de jefe (jefes/); escalado de la dificultad
		evil.addTag(Anchoring.TAG);
		evil.addTag(Heraldia.ADULT);
		if (prize) {
			evil.addTag(Decision.PREMIUM);
		}
		evil.setPersistenceRequired();
		evil.setCustomName(Texts.t("heraldia.chozas_mago.malvado").withStyle(ChatFormatting.DARK_PURPLE));
		evil.setCustomNameVisible(true);
		AttributeInstance health = evil.getAttribute(Attributes.MAX_HEALTH);
		if (health != null) {
			health.setBaseValue(HEALTH);
		}
		evil.setHealth(evil.getMaxHealth());
		ServerPlayer target = nearest(level, v.position());
		v.discard();
		if (!level.addFreshEntity(evil)) {
			LOGGER.warn("Heraldia: chozas_mago: el mundo no aceptó al Mago Malvado en {}", v.blockPosition());
			return null;
		}
		if (target != null) {
			evil.setTarget(target);
		}
		int vexes = summon(level, evil, target);
		double y = evil.getY() + 1.2;
		level.sendParticles(ParticleTypes.WITCH, evil.getX(), y, evil.getZ(), 40, 0.6, 0.9, 0.6, 0.05);
		level.sendParticles(ParticleTypes.LARGE_SMOKE, evil.getX(), y, evil.getZ(), 25, 0.5, 0.8, 0.5, 0.02);
		level.playSound(null, evil.getX(), evil.getY(), evil.getZ(), SoundEvents.EVOKER_PREPARE_SUMMON, SoundSource.HOSTILE, 1.5f, 0.8f);
		level.playSound(null, evil.getX(), evil.getY(), evil.getZ(), SoundEvents.EVOKER_CELEBRATE, SoundSource.HOSTILE, 1.2f, 0.7f);
		Component notice = Texts.t("heraldia.chozas_mago.revela", name).withStyle(ChatFormatting.DARK_PURPLE);
		for (ServerPlayer p : level.players()) {
			if (p.distanceToSqr(evil) <= (double) Phases.RADIUS * Phases.RADIUS) {
				p.sendSystemMessage(notice);
			}
		}
		LOGGER.info("Heraldia: chozas_mago: el mago de {} {} {} se revela ({}; premio: {}; {} vexes)", evil.getBlockX(),
				evil.getBlockY(), evil.getBlockZ(), forced ? "forzado" : "malvado", prize ? "sí" : "no", vexes);
		return evil;
	}

	/** Tres vexes de entrada, como los de su conjuro (con dueño, origen y vida limitada). */
	private static int summon(ServerLevel level, Evoker evil, @Nullable LivingEntity target) {
		int n = 0;
		for (int i = 0; i < VEXES; i++) {
			Vex vex = EntityTypes.VEX.create(level, EntitySpawnReason.MOB_SUMMONED);
			if (vex == null) {
				continue;
			}
			BlockPos pos = evil.blockPosition().offset(-1 + i, 1, i % 2 == 0 ? -1 : 1);
			vex.snapTo(pos, 0f, 0f);
			vex.finalizeSpawn(level, level.getCurrentDifficultyAt(pos), EntitySpawnReason.MOB_SUMMONED, null);
			vex.setOwner(evil);
			vex.setBoundOrigin(pos);
			vex.setLimitedLife(20 * (30 + level.getRandom().nextInt(90)));
			vex.addTag(Decision.VEX);
			if (target != null) {
				vex.setTarget(target);
			}
			if (level.addFreshEntity(vex)) {
				n++;
			}
		}
		return n;
	}

	private static @Nullable ServerPlayer nearest(ServerLevel level, Vec3 pos) {
		return level.players().stream()
				.filter(p -> !p.isSpectator() && !p.isCreative() && p.distanceToSqr(pos) <= (double) Phases.RADIUS * Phases.RADIUS)
				.min(Comparator.comparingDouble(p -> p.distanceToSqr(pos))).orElse(null);
	}

	/** El Mago Malvado ha muerto: sus vexes se deshacen, aviso a los cercanos y el recuento de /heraldia status. */
	private static void defeat(LivingEntity evil) {
		if (!(evil.level() instanceof ServerLevel level)) {
			return;
		}
		defeated++;
		for (Vex vex : level.getEntitiesOfClass(Vex.class, evil.getBoundingBox().inflate(32),
				x -> x.entityTags().contains(Decision.VEX))) {
			vex.discard();
		}
		Component notice = Texts.t("heraldia.chozas_mago.vencido").withStyle(ChatFormatting.GOLD);
		for (ServerPlayer p : level.players()) {
			if (p.distanceToSqr(evil) <= (double) Phases.RADIUS * Phases.RADIUS) {
				p.sendSystemMessage(notice);
			}
		}
		level.sendParticles(ParticleTypes.SOUL, evil.getX(), evil.getY() + 1, evil.getZ(), 30, 0.5, 0.8, 0.5, 0.05);
		LOGGER.info("Heraldia: chozas_mago: Mago Malvado vencido en {} {} {} (premio: {})", evil.getBlockX(), evil.getBlockY(),
				evil.getBlockZ(), evil.entityTags().contains(Decision.PREMIUM) ? "sí" : "no");
	}

	// ---- /heraldia wizard (operadores)

	public static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("wizard").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(Wizards::list)
				.then(Commands.literal("reveal").executes(Wizards::force));
	}

	private static List<Villager> wizards(CommandSourceStack src) {
		Vec3 pos = src.getPosition();
		return src.getLevel().getEntitiesOfClass(Villager.class, new AABB(pos, pos).inflate(COMMAND_RADIUS),
				v -> Decision.isWizard(v.entityTags()) && v.isAlive()).stream()
				.sorted(Comparator.comparingDouble(v -> v.distanceToSqr(pos))).toList();
	}

	private static int list(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		List<Villager> l = wizards(src);
		src.sendSuccess(() -> Texts.t("heraldia.chozas_mago.lista", COMMAND_RADIUS, l.size()), false);
		for (Villager v : l) {
			Decision.State e = decide(v, src.getLevel());
			String key = switch (e) {
				case BENIGN -> "benigno";
				case EVIL -> "malvado";
				case REVEALED -> "revelado";
				case UNDECIDED -> "sin_decidir";
			};
			src.sendSuccess(() -> Texts.t("heraldia.chozas_mago.lista.linea", v.getDisplayName(), v.getBlockX(), v.getBlockY(),
					v.getBlockZ(), Texts.t("heraldia.chozas_mago.estado." + key)), false);
		}
		return l.size();
	}

	/** Revela el mago más cercano aunque sea bondadoso (para probar). */
	private static int force(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		for (Villager v : wizards(src)) {
			decide(v, src.getLevel());
			v.removeTag(Decision.BENIGN);
			v.addTag(Decision.EVIL_UNREVEALED);
			Evoker evil = reveal(v, src.getLevel(), true);
			if (evil != null) {
				src.sendSuccess(() -> Texts.t("heraldia.chozas_mago.reveal.hecho", evil.getBlockX(), evil.getBlockY(), evil.getBlockZ()), true);
				return 1;
			}
		}
		src.sendSuccess(() -> Texts.t("heraldia.chozas_mago.reveal.ninguno", COMMAND_RADIUS), false);
		return 0;
	}

	/** La línea de /heraldia status. */
	public static List<Component> state() {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		return List.of(Texts.t("heraldia.estado.chozas_mago", cfg.getInt(EVIL_PROB), cfg.getInt(PREMIUM_PROB), defeated));
	}
}
