package io.github.albertosa23.heraldia.jefes;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comando.Textos;
import io.github.albertosa23.heraldia.comun.Anclaje;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.List;
import java.util.Map;
import java.util.Set;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.minecraft.core.BlockPos;
import net.minecraft.core.particles.ParticleTypes;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.sounds.SoundEvents;
import net.minecraft.sounds.SoundSource;
import net.minecraft.world.Difficulty;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.effect.MobEffectInstance;
import net.minecraft.world.effect.MobEffects;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.EntitySpawnReason;
import net.minecraft.world.entity.EntityType;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.phys.AABB;
import net.minecraft.world.phys.Vec3;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Jefes: fases, refuerzos y barra de jefe de los guardianes finales (etiqueta {@link Fases#GUARDIAN}), también de los
 * ya generados. Todo sale de eventos de Fabric API (daño, muerte, descarga) con salida temprana por etiquetas; el
 * único trabajo periódico es {@link Barras}, una vez por segundo y solo con combates en marcha (casi siempre ninguno).
 * Sin mixins: el daño lo da {@code ServerLivingEntityEvents.AFTER_DAMAGE}.
 * <ul>
 * <li>Fases: al bajar del 66 % y del 33 % de vida (una vez cada una, etiqueta {@code heraldia_fase.<n>} en el propio
 * guardián): velocidad, resistencia y fuerza breve, partículas, sonido y un aviso traducible en la barra de acción a
 * los jugadores cercanos.</li>
 * <li>Refuerzos: en cada fase, los de su única ({@link Refuerzos}), con {@code heraldia_anclado} y
 * {@code heraldia_adulto} (las mismas protecciones que los mobs de plantilla: ni bebés, ni monturas, ni armas cambiadas,
 * ni recoger objetos), sin su tabla de botín ni su trofeo, sin persistencia (desaparecen como cualquier monstruo si
 * todos se van) y nunca más vivos cerca que el tope (jefes.refuerzos.maximo_vivos, 4 por defecto).</li>
 * </ul>
 */
public final class Jefes {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static Refuerzos refuerzos;

	private Jefes() {
	}

	public static void registrar() {
		refuerzos = Refuerzos.delJar();
		ServerLivingEntityEvents.AFTER_DAMAGE.register((entity, source, base, taken, blocked) -> alDanar(entity, source));
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			if (Fases.esGuardian(entity.entityTags())) {
				Barras.quitar(entity, "muerto");
			}
		});
		ServerEntityEvents.ENTITY_UNLOAD.register((entity, level) -> {
			if (Fases.esGuardian(entity.entityTags())) {
				Barras.quitar(entity, "descargado");
			}
		});
		ServerTickEvents.END_SERVER_TICK.register(Barras::cadaTick);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> Barras.vaciar());
	}

	private static void alDanar(LivingEntity entity, DamageSource source) {
		if (entity instanceof Mob mob) {
			if (Fases.esGuardian(mob.entityTags())) {
				guardianHerido(mob, source);
			}
		} else if (entity instanceof ServerPlayer && source.getEntity() instanceof Mob jefe && Fases.esGuardian(jefe.entityTags())) {
			// el guardián ha golpeado a un jugador: también empieza el combate
			if (HeraldiaConfig.get().getBool("jefes.barra.activado")) {
				Barras.combate(jefe);
			}
		}
	}

	private static void guardianHerido(Mob jefe, DamageSource source) {
		if (jefe.isDeadOrDying() || !(jefe.level() instanceof ServerLevel level)) {
			return;
		}
		if (!hayJugadores(level, jefe, Fases.RADIO_FUERA)) {
			return;      // daño sin nadie cerca (sol, lava, asfixia): ni fases ni barra; la fase llega con el siguiente golpe
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		boolean fases = cfg.getBool("jefes.fases.activado");
		boolean conRefuerzos = cfg.getBool("jefes.refuerzos.activado") && level.getDifficulty() != Difficulty.PEACEFUL;
		List<Integer> pendientes = Fases.pendientes(jefe.entityTags(), jefe.getHealth(), jefe.getMaxHealth(), fases,
				cfg.getBool("jefes.refuerzos.activado"));
		int llamados = 0;
		for (int fase : pendientes) {
			jefe.addTag(Fases.FASE + fase);
			if (conRefuerzos) {
				llamados += llamar(level, jefe, source.getEntity());
			}
		}
		if (!pendientes.isEmpty()) {
			int fase = pendientes.getLast();
			if (fases) {
				enfurecer(level, jefe, fase);
			}
			if (llamados > 0) {
				level.playSound(null, jefe.getX(), jefe.getY(), jefe.getZ(), SoundEvents.EVOKER_PREPARE_SUMMON, SoundSource.HOSTILE, 1.5f, 0.8f);
			}
			String clave = Fases.clave(fase, fases, llamados);
			if (clave != null) {
				Component aviso = Textos.t(clave, jefe.getDisplayName());
				for (ServerPlayer p : level.players()) {
					if (p.distanceToSqr(jefe) <= (double) Fases.RADIO * Fases.RADIO) {
						p.sendOverlayMessage(aviso);
					}
				}
			}
			LOGGER.info("Heraldia: jefes: {} pasa a la fase {} ({} refuerzos)", nombre(jefe), fase, llamados);
		}
		if (cfg.getBool("jefes.barra.activado")) {
			Barras.combate(jefe);
		}
	}

	/** Velocidad y resistencia mientras dura la fase y una fuerza breve; partículas y un rugido. */
	private static void enfurecer(ServerLevel level, Mob jefe, int fase) {
		boolean ultima = fase >= Fases.MAX_FASE;
		jefe.addEffect(new MobEffectInstance(MobEffects.SPEED, ultima ? 600 : 400, ultima ? 1 : 0));
		jefe.addEffect(new MobEffectInstance(MobEffects.RESISTANCE, ultima ? 600 : 400, 0));
		jefe.addEffect(new MobEffectInstance(MobEffects.STRENGTH, ultima ? 160 : 120, ultima ? 1 : 0));
		double y = jefe.getY() + jefe.getBbHeight() / 2;
		level.sendParticles(ParticleTypes.LARGE_SMOKE, jefe.getX(), y, jefe.getZ(), 30, 0.6, 0.8, 0.6, 0.02);
		level.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, jefe.getX(), y, jefe.getZ(), 20, 0.5, 0.8, 0.5, 0.03);
		level.playSound(null, jefe.getX(), jefe.getY(), jefe.getZ(), SoundEvents.RAVAGER_ROAR, SoundSource.HOSTILE, 1.5f, ultima ? 0.7f : 0.9f);
	}

	/** Llama a los refuerzos de una fase, sin pasar del tope de vivos cerca (jefes.refuerzos.maximo_vivos). Devuelve cuántos. */
	private static int llamar(ServerLevel level, Mob jefe, @Nullable Entity atacante) {
		Set<String> tags = jefe.entityTags();
		List<Refuerzos.Refuerzo> lista = refuerzos.para(Fases.unica(tags), BuiltInRegistries.ENTITY_TYPE.getKey(jefe.getType()).toString());
		AABB zona = jefe.getBoundingBox().inflate(Fases.RADIO);
		int vivos = level.getEntitiesOfClass(Mob.class, zona, m -> m.isAlive() && m.entityTags().contains(Fases.REFUERZO)).size();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		int n = lista.isEmpty() ? 0 : Fases.cuantos(lista.size(), vivos, cfg.getInt("jefes.refuerzos.porcentaje"),
				cfg.getInt("jefes.refuerzos.maximo_vivos"));
		LivingEntity objetivo = atacante instanceof Player p && p.canBeSeenAsEnemy() ? p : null;
		int hechos = 0;
		for (int i = 0; i < n; i++) {
			if (aparecer(level, jefe, lista.get(i % lista.size()), i, objetivo)) {   // con más del 100 %, la lista se repite
				hechos++;
			}
		}
		return hechos;
	}

	private static boolean aparecer(ServerLevel level, Mob jefe, Refuerzos.Refuerzo r, int i, @Nullable LivingEntity objetivo) {
		Identifier id = Identifier.tryParse(r.mob());
		EntityType<?> tipo = id == null ? null : BuiltInRegistries.ENTITY_TYPE.getOptional(id).orElse(null);
		if (tipo == null || !(tipo.create(level, EntitySpawnReason.STRUCTURE) instanceof Mob mob)) {
			LOGGER.warn("Heraldia: jefes: refuerzo {} desconocido o no es un mob", r.mob());
			return false;
		}
		// Antes de finalizeSpawn, como un mob de plantilla: ZombieMixin, ZombieEquipoMixin y DrownedMixin miran la
		// etiqueta de adulto con el motivo STRUCTURE (ni bebé, ni montura, ni arma al azar), y Anclaje la de anclado.
		mob.addTag(Fases.REFUERZO);
		mob.addTag(Anclaje.TAG);
		mob.addTag(Heraldia.ADULTO);
		Vec3 sitio = sitio(level, tipo, jefe, i);
		mob.snapTo(sitio.x, sitio.y, sitio.z, level.getRandom().nextFloat() * 360f, 0f);
		mob.finalizeSpawn(level, level.getCurrentDifficultyAt(BlockPos.containing(sitio)), EntitySpawnReason.STRUCTURE, null);
		for (Map.Entry<String, String> e : r.equipo().entrySet()) {
			Identifier item = Identifier.tryParse(e.getValue());
			Item obj = item == null ? null : BuiltInRegistries.ITEM.getOptional(item).orElse(null);
			if (obj == null) {
				LOGGER.warn("Heraldia: jefes: objeto {} desconocido para un refuerzo", e.getValue());
				continue;
			}
			EquipmentSlot ranura = EquipmentSlot.byName(e.getKey());
			mob.setItemSlot(ranura, new ItemStack(obj));
			mob.setDropChance(ranura, 0f);       // no regalan su equipo
		}
		// sin jinetes ni monturas (la araña sortea un esqueleto jinete en finalizeSpawn): no entrarían en el tope
		mob.ejectPassengers();
		mob.stopRiding();
		if (objetivo != null) {
			mob.setTarget(objetivo);             // antes de entrar al mundo: Anclaje no lo deja quieto
		}
		return level.addFreshEntity(mob);
	}

	/** Un sitio libre a 2 bloques del guardián (cada refuerzo en un lado), o el del propio guardián. */
	private static Vec3 sitio(ServerLevel level, EntityType<?> tipo, Mob jefe, int i) {
		int[][] lados = {{2, 0}, {-2, 0}, {0, 2}, {0, -2}, {2, 2}, {-2, -2}, {2, -2}, {-2, 2}};
		for (int k = 0; k < lados.length; k++) {
			int[] d = lados[(i + k) % lados.length];
			Vec3 v = new Vec3(jefe.getX() + d[0], jefe.getY(), jefe.getZ() + d[1]);
			if (level.noCollision(tipo.getSpawnAABB(v.x, v.y, v.z))) {
				return v;
			}
		}
		return jefe.position();
	}

	/** ¿Algún jugador (no espectador) a menos de {@code radio} bloques? */
	static boolean hayJugadores(ServerLevel level, Entity jefe, int radio) {
		for (ServerPlayer p : level.players()) {
			if (!p.isSpectator() && p.distanceToSqr(jefe) <= (double) radio * radio) {
				return true;
			}
		}
		return false;
	}

	/** Nombre para el log: su única (o su tipo) y el principio de su UUID. */
	static String nombre(Entity e) {
		String sid = Fases.unica(e.entityTags());
		return (sid != null ? sid : BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).getPath()) + "/" + e.getUUID().toString().substring(0, 8);
	}
}
