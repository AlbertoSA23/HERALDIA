package io.github.albertosa23.heraldia.comun;

import java.util.Set;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;

/**
 * Mobs de plantilla anclados (etiqueta {@link #TAG}, core.ANCLADO_TAG del generador: los guardianes finales y los
 * zombis y esqueletos de las plantillas). Cada vez que el mundo carga uno ({@code ENTITY_LOAD}: al colocarse la
 * plantilla, al promocionarse el chunk generado y en cada carga del chunk):
 * <ul>
 * <li>no recoge objetos: {@code finalizeSpawn} de zombis y esqueletos sortea {@code CanPickUpLoot} sin mirar el NBT, y
 * con él cambiarían su equipo o se quedarían el botín que suelta el jugador;</li>
 * <li>no pasea: {@code RandomStrollGoal.canUse} exige {@code getNoActionTime() < 100}, y un mob persistente sin
 * jugadores cerca solo pasea esos primeros 100 ticks (hasta 10 bloques, a veces fuera de su sala) tras cada carga,
 * porque {@code noActionTime} no se guarda. Con {@link #QUIETO} no pasea; ve, persigue y ataca como siempre (eso no
 * mira {@code noActionTime}), y al recibir daño el juego lo pone a 0 y vuelve a moverse con normalidad.</li>
 * </ul>
 * Sin mixin: un evento de Fabric API con salida temprana (conjunto de etiquetas, casi siempre vacío); nada por tick.
 */
public final class Anclaje {
	/** Etiqueta (Tags) de los mobs anclados; la misma que core.ANCLADO_TAG. */
	public static final String TAG = "heraldia_anclado";
	/** {@code noActionTime} a partir del cual {@code RandomStrollGoal} ya no se activa (26.3). */
	public static final int QUIETO = 100;

	private Anclaje() {
	}

	public static void registrar() {
		ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> alCargar(entity));
	}

	static void alCargar(Entity entity) {
		if (!anclado(entity.entityTags()) || !(entity instanceof Mob mob)) {
			return;
		}
		mob.setCanPickUpLoot(false);
		if (mob.getTarget() == null) {
			mob.setNoActionTime(quieto(mob.getNoActionTime()));
		}
	}

	/** ¿Lleva la etiqueta de anclado? */
	static boolean anclado(Set<String> tags) {
		return !tags.isEmpty() && tags.contains(TAG);
	}

	/** {@code noActionTime} con el que el mob ya no pasea (no lo baja si ya era mayor). */
	static int quieto(int noActionTime) {
		return Math.max(noActionTime, QUIETO);
	}
}
