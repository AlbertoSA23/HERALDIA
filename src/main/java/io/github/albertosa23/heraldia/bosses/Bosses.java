package io.github.albertosa23.heraldia.bosses;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.common.Anchoring;
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
 * Bosses: phases, reinforcements and boss bar of the final guardians (tag {@link Phases#GUARDIAN}), also the
 * already generated ones. Everything comes from Fabric API events (damage, death, unload) with an early exit by tags; the
 * only periodic work is {@link Bars}, once per second and only with fights going on (almost always none).
 * No mixins: the damage comes from {@code ServerLivingEntityEvents.AFTER_DAMAGE}.
 * <ul>
 * <li>Phases: on dropping below 66 % and 33 % health (once each, tag {@code heraldia_fase.<n>} on the guardian
 * itself): speed, resistance and brief strength, particles, sound and a translatable notice in the action bar for
 * nearby players.</li>
 * <li>Reinforcements: in each phase, those of its unique ({@link Reinforcements}), with {@code heraldia_anclado} and
 * {@code heraldia_adulto} (the same protections as template mobs: no babies, no mounts, no swapped weapons,
 * no item pickup), without their loot table or trophy, without persistence (they despawn like any monster if
 * everyone leaves) and never more alive nearby than the cap (jefes.refuerzos.maximo_vivos, 4 by default).</li>
 * </ul>
 */
public final class Bosses {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private static Reinforcements reinforcements;

	private Bosses() {
	}

	public static void register() {
		reinforcements = Reinforcements.fromJar();
		ServerLivingEntityEvents.AFTER_DAMAGE.register((entity, source, base, taken, blocked) -> onDamage(entity, source));
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			if (Phases.isGuardian(entity.entityTags())) {
				Bars.clear(entity, "muerto");
			}
		});
		ServerEntityEvents.ENTITY_UNLOAD.register((entity, level) -> {
			if (Phases.isGuardian(entity.entityTags())) {
				Bars.clear(entity, "descargado");
			}
		});
		ServerTickEvents.END_SERVER_TICK.register(Bars::everyTick);
		ServerLifecycleEvents.SERVER_STOPPING.register(server -> Bars.drain());
	}

	private static void onDamage(LivingEntity entity, DamageSource source) {
		if (entity instanceof Mob mob) {
			if (Phases.isGuardian(mob.entityTags())) {
				guardianHurt(mob, source);
			}
		} else if (entity instanceof ServerPlayer && source.getEntity() instanceof Mob boss && Phases.isGuardian(boss.entityTags())) {
			// the guardian has hit a player: the fight starts too
			if (HeraldiaConfig.get().getBool("jefes.barra.activado")) {
				Bars.combat(boss);
			}
		}
	}

	private static void guardianHurt(Mob boss, DamageSource source) {
		if (boss.isDeadOrDying() || !(boss.level() instanceof ServerLevel level)) {
			return;
		}
		if (!hasPlayers(level, boss, Phases.OUTSIDE_RADIUS)) {
			return;      // damage with nobody nearby (sun, lava, suffocation): no phases or bar; the phase comes with the next hit
		}
		HeraldiaConfig cfg = HeraldiaConfig.get();
		boolean phases = cfg.getBool("jefes.fases.activado");
		boolean withReinforcements = cfg.getBool("jefes.refuerzos.activado") && level.getDifficulty() != Difficulty.PEACEFUL;
		List<Integer> pending = Phases.pending(boss.entityTags(), boss.getHealth(), boss.getMaxHealth(), phases,
				cfg.getBool("jefes.refuerzos.activado"));
		int called = 0;
		for (int phase : pending) {
			boss.addTag(Phases.PHASE + phase);
			if (withReinforcements) {
				called += call(level, boss, source.getEntity());
			}
		}
		if (!pending.isEmpty()) {
			int phase = pending.getLast();
			if (phases) {
				enrage(level, boss, phase);
			}
			if (called > 0) {
				level.playSound(null, boss.getX(), boss.getY(), boss.getZ(), SoundEvents.EVOKER_PREPARE_SUMMON, SoundSource.HOSTILE, 1.5f, 0.8f);
			}
			String key = Phases.key(phase, phases, called);
			if (key != null) {
				Component notice = Texts.t(key, boss.getDisplayName());
				for (ServerPlayer p : level.players()) {
					if (p.distanceToSqr(boss) <= (double) Phases.RADIUS * Phases.RADIUS) {
						p.sendOverlayMessage(notice);
					}
				}
			}
			LOGGER.info("Heraldia: jefes: {} pasa a la fase {} ({} refuerzos)", name(boss), phase, called);
		}
		if (cfg.getBool("jefes.barra.activado")) {
			Bars.combat(boss);
		}
	}

	/** Speed and resistance while the phase lasts and brief strength; particles and a roar. */
	private static void enrage(ServerLevel level, Mob boss, int phase) {
		boolean latest = phase >= Phases.MAX_PHASE;
		boss.addEffect(new MobEffectInstance(MobEffects.SPEED, latest ? 600 : 400, latest ? 1 : 0));
		boss.addEffect(new MobEffectInstance(MobEffects.RESISTANCE, latest ? 600 : 400, 0));
		boss.addEffect(new MobEffectInstance(MobEffects.STRENGTH, latest ? 160 : 120, latest ? 1 : 0));
		double y = boss.getY() + boss.getBbHeight() / 2;
		level.sendParticles(ParticleTypes.LARGE_SMOKE, boss.getX(), y, boss.getZ(), 30, 0.6, 0.8, 0.6, 0.02);
		level.sendParticles(ParticleTypes.SOUL_FIRE_FLAME, boss.getX(), y, boss.getZ(), 20, 0.5, 0.8, 0.5, 0.03);
		level.playSound(null, boss.getX(), boss.getY(), boss.getZ(), SoundEvents.RAVAGER_ROAR, SoundSource.HOSTILE, 1.5f, latest ? 0.7f : 0.9f);
	}

	/** Calls a phase's reinforcements, without going over the cap of alive ones nearby (jefes.refuerzos.maximo_vivos). Returns how many. */
	private static int call(ServerLevel level, Mob boss, @Nullable Entity attacker) {
		Set<String> tags = boss.entityTags();
		List<Reinforcements.Reinforcement> list = reinforcements.stop(Phases.unique(tags), BuiltInRegistries.ENTITY_TYPE.getKey(boss.getType()).toString());
		AABB zone = boss.getBoundingBox().inflate(Phases.RADIUS);
		int alive = level.getEntitiesOfClass(Mob.class, zone, m -> m.isAlive() && m.entityTags().contains(Phases.REINFORCEMENT)).size();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		int n = list.isEmpty() ? 0 : Phases.howMany(list.size(), alive, cfg.getInt("jefes.refuerzos.porcentaje"),
				cfg.getInt("jefes.refuerzos.maximo_vivos"));
		LivingEntity target = attacker instanceof Player p && p.canBeSeenAsEnemy() ? p : null;
		int finished = 0;
		for (int i = 0; i < n; i++) {
			if (spawn(level, boss, list.get(i % list.size()), i, target)) {   // with more than 100 %, the list repeats
				finished++;
			}
		}
		return finished;
	}

	private static boolean spawn(ServerLevel level, Mob boss, Reinforcements.Reinforcement r, int i, @Nullable LivingEntity target) {
		Identifier id = Identifier.tryParse(r.mob());
		EntityType<?> type = id == null ? null : BuiltInRegistries.ENTITY_TYPE.getOptional(id).orElse(null);
		if (type == null || !(type.create(level, EntitySpawnReason.STRUCTURE) instanceof Mob mob)) {
			LOGGER.warn("Heraldia: jefes: refuerzo {} desconocido o no es un mob", r.mob());
			return false;
		}
		// Before finalizeSpawn, like a template mob: ZombieMixin, ZombieEquipmentMixin and DrownedMixin check the
		// adult tag with the STRUCTURE reason (no baby, no mount, no random weapon), and Anchoring the anchored one.
		mob.addTag(Phases.REINFORCEMENT);
		mob.addTag(Anchoring.TAG);
		mob.addTag(Heraldia.ADULT);
		Vec3 site = site(level, type, boss, i);
		mob.snapTo(site.x, site.y, site.z, level.getRandom().nextFloat() * 360f, 0f);
		mob.finalizeSpawn(level, level.getCurrentDifficultyAt(BlockPos.containing(site)), EntitySpawnReason.STRUCTURE, null);
		for (Map.Entry<String, String> e : r.equipment().entrySet()) {
			Identifier item = Identifier.tryParse(e.getValue());
			Item obj = item == null ? null : BuiltInRegistries.ITEM.getOptional(item).orElse(null);
			if (obj == null) {
				LOGGER.warn("Heraldia: jefes: objeto {} desconocido para un refuerzo", e.getValue());
				continue;
			}
			EquipmentSlot slot = EquipmentSlot.byName(e.getKey());
			mob.setItemSlot(slot, new ItemStack(obj));
			mob.setDropChance(slot, 0f);       // they do not give away their gear
		}
		// no riders or mounts (the spider rolls for a skeleton rider in finalizeSpawn): they would not count towards the cap
		mob.ejectPassengers();
		mob.stopRiding();
		if (target != null) {
			mob.setTarget(target);             // before entering the world: Anchoring does not keep it still
		}
		return level.addFreshEntity(mob);
	}

	/** A free spot 2 blocks from the guardian (each reinforcement on one side), or the guardian's own. */
	private static Vec3 site(ServerLevel level, EntityType<?> type, Mob boss, int i) {
		int[][] sides = {{2, 0}, {-2, 0}, {0, 2}, {0, -2}, {2, 2}, {-2, -2}, {2, -2}, {-2, 2}};
		for (int k = 0; k < sides.length; k++) {
			int[] d = sides[(i + k) % sides.length];
			Vec3 v = new Vec3(boss.getX() + d[0], boss.getY(), boss.getZ() + d[1]);
			if (level.noCollision(type.getSpawnAABB(v.x, v.y, v.z))) {
				return v;
			}
		}
		return boss.position();
	}

	/** Any player (not a spectator) within {@code radius} blocks? */
	static boolean hasPlayers(ServerLevel level, Entity boss, int radius) {
		for (ServerPlayer p : level.players()) {
			if (!p.isSpectator() && p.distanceToSqr(boss) <= (double) radius * radius) {
				return true;
			}
		}
		return false;
	}

	/** Name for the log: its unique (or its type) and the beginning of its UUID. */
	static String name(Entity e) {
		String sid = Phases.unique(e.entityTags());
		return (sid != null ? sid : BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).getPath()) + "/" + e.getUUID().toString().substring(0, 8);
	}
}
