package io.github.albertosa23.heraldia.chozas;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comando.Textos;
import io.github.albertosa23.heraldia.comun.Anclaje;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.jefes.Fases;
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
 * ({@link Decision#malvado}, con chozas_mago.prob_malvado), que se guarda en sus etiquetas;</li>
 * <li>si es malvado, se revela una sola vez cuando un jugador se acerca a menos de {@link #RADIO} bloques (una
 * consulta acotada por jugador cada segundo) o intenta comerciar con él ({@code UseEntityCallback}): mensaje traducido,
 * partículas y sonido, el aldeano desaparece y en su sitio aparece el Mago Malvado, un evocador con
 * {@link Fases#GUARDIAN} (fases, refuerzos y barra de jefe de jefes/; la dificultad lo escala como a los guardianes),
 * más vida, tres vexes de entrada (luego invoca los suyos, como cualquier evocador) y su tabla de botín
 * (heraldia:chozas_mago/malvado, o malvado_premium si sale el premio, chozas_mago.prob_botin_premium). Esa tabla
 * sustituye a la del evocador: no suelta el tótem vanilla (tools/gen/chozas_mago.py explica por qué).</li>
 * </ul>
 * El logro de vencerlo es de datos (player_killed_entity con {@link Decision#MALVADO}).
 */
public final class Magos {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	public static final String PROB_MALVADO = "chozas_mago.prob_malvado", PROB_PREMIUM = "chozas_mago.prob_botin_premium";
	public static final String TABLA = "heraldia:chozas_mago/malvado", TABLA_PREMIUM = "heraldia:chozas_mago/malvado_premium";
	/** Distancia (bloques) a la que un jugador hace que el mago malvado se revele. */
	public static final int RADIO = 7;
	/** Cada cuántos ticks se mira si hay jugadores junto a un mago. */
	static final int PERIODO = 20;
	/** Radio de búsqueda de /heraldia wizard. */
	static final int RADIO_COMANDO = 32;
	static final float VIDA = 48f;
	static final int VEXES = 3;
	private static List<String> nombres = List.of("Aldric");
	private static int apodos = 1;
	private static int vencidos;

	private Magos() {
	}

	public static void registrar() {
		leerNombres();
		ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> alCargar(entity, level));
		UseEntityCallback.EVENT.register((player, world, hand, entity, hit) -> {
			if (entity instanceof Villager v && Decision.esMago(v.entityTags()) && world instanceof ServerLevel level
					&& !player.isSpectator()) {
				if (decidir(v, level) == Decision.Estado.MALVADO) {
					revelar(v, level, false);
					return InteractionResult.FAIL;      // no hay tratos con un mago malvado
				}
			}
			return InteractionResult.PASS;
		});
		ServerTickEvents.END_SERVER_TICK.register(Magos::tick);
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			if (!entity.entityTags().isEmpty() && entity.entityTags().contains(Decision.MALVADO)) {
				vencido(entity);
			}
		});
		ServerLifecycleEvents.SERVER_STOPPED.register(server -> vencidos = 0);
	}

	private static void leerNombres() {
		String path = "/heraldia/chozas_mago.json";
		try (InputStream in = Magos.class.getResourceAsStream(path)) {
			if (in == null) {
				LOGGER.warn("Heraldia: falta {} en el .jar: los magos se llaman todos igual", path);
				return;
			}
			JsonObject o = JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject();
			List<String> n = new ArrayList<>();
			o.getAsJsonArray("nombres").forEach(e -> n.add(e.getAsString()));
			nombres = List.copyOf(n);
			apodos = o.get("apodos").getAsInt();
		} catch (IOException | RuntimeException e) {
			LOGGER.warn("Heraldia: no se pudo leer {}: {}", path, e.toString());
		}
	}

	private static void alCargar(Entity entity, ServerLevel level) {
		if (entity instanceof Villager v && Decision.esMago(v.entityTags())) {
			decidir(v, level);
		}
	}

	/** Nombre y decisión del mago (una vez; luego se lee de sus etiquetas). */
	static Decision.Estado decidir(Villager v, ServerLevel level) {
		Decision.Estado e = Decision.estado(v.entityTags());
		int cx = v.blockPosition().getX() >> 4, cz = v.blockPosition().getZ() >> 4;
		long seed = level.getSeed();
		if (!v.entityTags().contains(Decision.NOMBRADO)) {
			int[] i = Decision.nombre(seed, cx, cz, nombres.size(), apodos);
			v.setCustomName(Textos.t("heraldia.chozas_mago.nombre", nombres.get(i[0]), Textos.t("heraldia.chozas_mago.apodo." + i[1])));
			v.setCustomNameVisible(true);
			v.addTag(Decision.NOMBRADO);
		}
		if (e == Decision.Estado.SIN_DECIDIR) {
			boolean malo = Decision.malvado(seed, cx, cz, HeraldiaConfig.get().getInt(PROB_MALVADO));
			v.addTag(malo ? Decision.MALVADO_SIN_REVELAR : Decision.BENIGNO);
			e = malo ? Decision.Estado.MALVADO : Decision.Estado.BENIGNO;
		}
		return e;
	}

	/** Una vez por segundo: ¿algún jugador junto a un mago malvado sin revelar? Una consulta acotada por jugador. */
	private static void tick(MinecraftServer server) {
		if (server.getTickCount() % PERIODO != 0) {
			return;
		}
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			if (p.isSpectator() || !p.isAlive()) {
				continue;
			}
			ServerLevel level = p.level();
			AABB zona = p.getBoundingBox().inflate(RADIO);
			for (Villager v : level.getEntitiesOfClass(Villager.class, zona, x -> Decision.esMago(x.entityTags()))) {
				if (v.isAlive() && v.distanceToSqr(p) <= (double) RADIO * RADIO && decidir(v, level) == Decision.Estado.MALVADO) {
					revelar(v, level, false);
				}
			}
		}
	}

	/**
	 * Revela al mago: el aldeano se va y aparece el Mago Malvado en su sitio. Una sola vez (la etiqueta
	 * {@link Decision#REVELADO} y el propio aldeano, que desaparece). {@code forzado}: /heraldia wizard reveal.
	 */
	static @Nullable Evoker revelar(Villager v, ServerLevel level, boolean forzado) {
		if (!v.isAlive() || v.entityTags().contains(Decision.REVELADO)) {
			return null;
		}
		v.addTag(Decision.REVELADO);
		int cx = v.blockPosition().getX() >> 4, cz = v.blockPosition().getZ() >> 4;
		boolean premio = Decision.premium(level.getSeed(), cx, cz, HeraldiaConfig.get().getInt(PROB_PREMIUM));
		CompoundTag datos = new CompoundTag();
		datos.putString("DeathLootTable", premio ? TABLA_PREMIUM : TABLA);   // sustituye a la del evocador (sin tótem)
		Entity e = EntityType.loadEntityRecursive(EntityTypes.EVOKER, datos, level, EntitySpawnReason.EVENT, EntityProcessor.NOP);
		if (!(e instanceof Evoker malo)) {
			LOGGER.warn("Heraldia: chozas_mago: no se pudo crear el Mago Malvado en {}", v.blockPosition());
			return null;
		}
		Component nombre = v.getDisplayName();
		malo.snapTo(v.getX(), v.getY(), v.getZ(), v.getYRot(), 0f);
		malo.addTag(Decision.MALVADO);
		malo.addTag(Fases.GUARDIAN);           // fases, refuerzos y barra de jefe (jefes/); escalado de la dificultad
		malo.addTag(Anclaje.TAG);
		malo.addTag(Heraldia.ADULTO);
		if (premio) {
			malo.addTag(Decision.PREMIUM);
		}
		malo.setPersistenceRequired();
		malo.setCustomName(Textos.t("heraldia.chozas_mago.malvado").withStyle(ChatFormatting.DARK_PURPLE));
		malo.setCustomNameVisible(true);
		AttributeInstance vida = malo.getAttribute(Attributes.MAX_HEALTH);
		if (vida != null) {
			vida.setBaseValue(VIDA);
		}
		malo.setHealth(malo.getMaxHealth());
		ServerPlayer objetivo = cercano(level, v.position());
		v.discard();
		if (!level.addFreshEntity(malo)) {
			LOGGER.warn("Heraldia: chozas_mago: el mundo no aceptó al Mago Malvado en {}", v.blockPosition());
			return null;
		}
		if (objetivo != null) {
			malo.setTarget(objetivo);
		}
		int vexes = invocar(level, malo, objetivo);
		double y = malo.getY() + 1.2;
		level.sendParticles(ParticleTypes.WITCH, malo.getX(), y, malo.getZ(), 40, 0.6, 0.9, 0.6, 0.05);
		level.sendParticles(ParticleTypes.LARGE_SMOKE, malo.getX(), y, malo.getZ(), 25, 0.5, 0.8, 0.5, 0.02);
		level.playSound(null, malo.getX(), malo.getY(), malo.getZ(), SoundEvents.EVOKER_PREPARE_SUMMON, SoundSource.HOSTILE, 1.5f, 0.8f);
		level.playSound(null, malo.getX(), malo.getY(), malo.getZ(), SoundEvents.EVOKER_CELEBRATE, SoundSource.HOSTILE, 1.2f, 0.7f);
		Component aviso = Textos.t("heraldia.chozas_mago.revela", nombre).withStyle(ChatFormatting.DARK_PURPLE);
		for (ServerPlayer p : level.players()) {
			if (p.distanceToSqr(malo) <= (double) Fases.RADIO * Fases.RADIO) {
				p.sendSystemMessage(aviso);
			}
		}
		LOGGER.info("Heraldia: chozas_mago: el mago de {} {} {} se revela ({}; premio: {}; {} vexes)", malo.getBlockX(),
				malo.getBlockY(), malo.getBlockZ(), forzado ? "forzado" : "malvado", premio ? "sí" : "no", vexes);
		return malo;
	}

	/** Tres vexes de entrada, como los de su conjuro (con dueño, origen y vida limitada). */
	private static int invocar(ServerLevel level, Evoker malo, @Nullable LivingEntity objetivo) {
		int n = 0;
		for (int i = 0; i < VEXES; i++) {
			Vex vex = EntityTypes.VEX.create(level, EntitySpawnReason.MOB_SUMMONED);
			if (vex == null) {
				continue;
			}
			BlockPos pos = malo.blockPosition().offset(-1 + i, 1, i % 2 == 0 ? -1 : 1);
			vex.snapTo(pos, 0f, 0f);
			vex.finalizeSpawn(level, level.getCurrentDifficultyAt(pos), EntitySpawnReason.MOB_SUMMONED, null);
			vex.setOwner(malo);
			vex.setBoundOrigin(pos);
			vex.setLimitedLife(20 * (30 + level.getRandom().nextInt(90)));
			vex.addTag(Decision.VEX);
			if (objetivo != null) {
				vex.setTarget(objetivo);
			}
			if (level.addFreshEntity(vex)) {
				n++;
			}
		}
		return n;
	}

	private static @Nullable ServerPlayer cercano(ServerLevel level, Vec3 pos) {
		return level.players().stream()
				.filter(p -> !p.isSpectator() && !p.isCreative() && p.distanceToSqr(pos) <= (double) Fases.RADIO * Fases.RADIO)
				.min(Comparator.comparingDouble(p -> p.distanceToSqr(pos))).orElse(null);
	}

	/** El Mago Malvado ha muerto: sus vexes se deshacen, aviso a los cercanos y el recuento de /heraldia status. */
	private static void vencido(LivingEntity malo) {
		if (!(malo.level() instanceof ServerLevel level)) {
			return;
		}
		vencidos++;
		for (Vex vex : level.getEntitiesOfClass(Vex.class, malo.getBoundingBox().inflate(32),
				x -> x.entityTags().contains(Decision.VEX))) {
			vex.discard();
		}
		Component aviso = Textos.t("heraldia.chozas_mago.vencido").withStyle(ChatFormatting.GOLD);
		for (ServerPlayer p : level.players()) {
			if (p.distanceToSqr(malo) <= (double) Fases.RADIO * Fases.RADIO) {
				p.sendSystemMessage(aviso);
			}
		}
		level.sendParticles(ParticleTypes.SOUL, malo.getX(), malo.getY() + 1, malo.getZ(), 30, 0.5, 0.8, 0.5, 0.05);
		LOGGER.info("Heraldia: chozas_mago: Mago Malvado vencido en {} {} {} (premio: {})", malo.getBlockX(), malo.getBlockY(),
				malo.getBlockZ(), malo.entityTags().contains(Decision.PREMIUM) ? "sí" : "no");
	}

	// ---- /heraldia wizard (operadores)

	public static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("wizard").requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.executes(Magos::lista)
				.then(Commands.literal("reveal").executes(Magos::forzar));
	}

	private static List<Villager> magos(CommandSourceStack src) {
		Vec3 pos = src.getPosition();
		return src.getLevel().getEntitiesOfClass(Villager.class, new AABB(pos, pos).inflate(RADIO_COMANDO),
				v -> Decision.esMago(v.entityTags()) && v.isAlive()).stream()
				.sorted(Comparator.comparingDouble(v -> v.distanceToSqr(pos))).toList();
	}

	private static int lista(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		List<Villager> l = magos(src);
		src.sendSuccess(() -> Textos.t("heraldia.chozas_mago.lista", RADIO_COMANDO, l.size()), false);
		for (Villager v : l) {
			Decision.Estado e = decidir(v, src.getLevel());
			String clave = switch (e) {
				case BENIGNO -> "benigno";
				case MALVADO -> "malvado";
				case REVELADO -> "revelado";
				case SIN_DECIDIR -> "sin_decidir";
			};
			src.sendSuccess(() -> Textos.t("heraldia.chozas_mago.lista.linea", v.getDisplayName(), v.getBlockX(), v.getBlockY(),
					v.getBlockZ(), Textos.t("heraldia.chozas_mago.estado." + clave)), false);
		}
		return l.size();
	}

	/** Revela el mago más cercano aunque sea bondadoso (para probar). */
	private static int forzar(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		for (Villager v : magos(src)) {
			decidir(v, src.getLevel());
			v.removeTag(Decision.BENIGNO);
			v.addTag(Decision.MALVADO_SIN_REVELAR);
			Evoker malo = revelar(v, src.getLevel(), true);
			if (malo != null) {
				src.sendSuccess(() -> Textos.t("heraldia.chozas_mago.reveal.hecho", malo.getBlockX(), malo.getBlockY(), malo.getBlockZ()), true);
				return 1;
			}
		}
		src.sendSuccess(() -> Textos.t("heraldia.chozas_mago.reveal.ninguno", RADIO_COMANDO), false);
		return 0;
	}

	/** La línea de /heraldia status. */
	public static List<Component> estado() {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		return List.of(Textos.t("heraldia.estado.chozas_mago", cfg.getInt(PROB_MALVADO), cfg.getInt(PROB_PREMIUM), vencidos));
	}
}
