package io.github.albertosa23.heraldia.update;

import io.github.albertosa23.heraldia.update.Fixes.Fix;
import io.github.albertosa23.heraldia.update.Fixes.Effect;
import java.util.List;
import java.util.Set;

/**
 * Arreglos iniciales de los mobs de plantilla (T46): fallos ya corregidos en el código que pueden seguir en mundos
 * generados con versiones anteriores (ver CHANGELOG y APRENDIZAJES). Sobre una vista mínima del mob ({@link Mob}), así la
 * lógica se prueba sin el juego; {@code Updater} la monta sobre el mob de verdad.
 * <ol>
 * <li>{@code marks}: los guardianes y mobs con nombre de la 0.1.0 no llevaban etiquetas; se reconocen por su nombre
 * traducible {@code heraldia.*} (y persistentes) y reciben las de ahora: {@code heraldia_anclado} (no pasean fuera de su
 * sala —la «deriva»— ni recogen objetos), {@code heraldia_adulto} si son de la familia de los zombis y
 * {@code heraldia_guardian} si su nombre es el de un guardián (fases de jefe, barra y refuerzos).</li>
 * <li>{@code babies}: un zombi, husk, ahogado, zombi aldeano o piglin zombificado de plantilla que salió bebé pasa a adulto
 * (y si iba en una gallina, se baja y la gallina de jinete se quita).</li>
 * <li>{@code nautiluses}: un ahogado de plantilla montado en un nautilo zombi se baja y el nautilo se quita (si no tiene
 * nombre ni otro jinete).</li>
 * <li>{@code collect}: un mob de plantilla que puede recoger objetos deja de poder ({@code CanPickUpLoot}).</li>
 * <li>{@code weapons}: un ahogado de plantilla con un tridente o una caña sin nada especial, o un zombi con una pala, lanza o
 * espada de hierro sin nada especial, pudo perder el arma de su plantilla; no se sabe cuál era, así que solo se cuenta en
 * el informe (aviso), sin cambiarlo.</li>
 * </ol>
 */
public final class MobFixes {
	public static final String ADULT = "heraldia_adulto", ANCHORED = "heraldia_anclado", GUARDIAN = "heraldia_guardian";
	/** Tipos que pueden salir bebés al colocarse (core.BEBE_ZOMBI del generador). */
	static final Set<String> ZOMBIES = Set.of("zombie", "husk", "drowned", "zombie_villager", "zombified_piglin");
	static final Set<String> DROWNED_WEAPONS = Set.of("trident", "fishing_rod");
	static final Set<String> ZOMBIE_WEAPONS = Set.of("iron_shovel", "iron_sword", "iron_spear");

	/** Lo que los arreglos necesitan ver y tocar de un mob. */
	public interface Mob {
		/** Tipo sin espacio de nombres («zombie»). */
		String type();

		Set<String> tags();

		void tagIt(String tag);

		/** Clave de su nombre si es traducible, o null. */
		String nameKey();

		boolean persistent();

		boolean baby();

		void makeAdult();

		/** Tipo de lo que monta, sin espacio de nombres, o null. */
		String mount();

		/** ¿La montura tiene nombre u otro jinete? (entonces no se quita) */
		boolean ownMount();

		/** Se baja y quita la montura. */
		void removeMount();

		boolean picksUp();

		void noPickup();

		/** Objeto de la mano principal sin espacio de nombres, o null. */
		String weapon();

		/** ¿El arma tiene nombre o encantamientos? (entonces es de la plantilla) */
		boolean specialWeapon();
	}

	private MobFixes() {
	}

	/** ¿Es un mob de una plantilla de Heraldia? Lleva una de sus etiquetas, o es persistente con un nombre heraldia.*. */
	public static boolean fromTemplate(Mob m) {
		Set<String> t = m.tags();
		if (!t.isEmpty() && (t.contains(ADULT) || t.contains(ANCHORED) || t.contains(GUARDIAN))) {
			return true;
		}
		return m.persistent() && heraldiaName(m.nameKey());
	}

	static boolean heraldiaName(String key) {
		return key != null && key.startsWith("heraldia.");
	}

	/** ¿Es el nombre de un guardián? (heraldia.unicas.castillo.guardian, heraldia.ciudadela.guardian...) */
	static boolean guardianName(String key) {
		return heraldiaName(key) && key.contains("guardian");
	}

	static Effect marks(Mob m, boolean dryRun) {
		if (!heraldiaName(m.nameKey()) || !m.persistent()) {
			return Effect.NOTHING;
		}
		boolean missing = !m.tags().contains(ANCHORED) || ZOMBIES.contains(m.type()) && !m.tags().contains(ADULT)
				|| guardianName(m.nameKey()) && !m.tags().contains(GUARDIAN);
		if (!missing) {
			return Effect.NOTHING;
		}
		if (!dryRun) {
			m.tagIt(ANCHORED);
			if (ZOMBIES.contains(m.type())) {
				m.tagIt(ADULT);
			}
			if (guardianName(m.nameKey())) {
				m.tagIt(GUARDIAN);
			}
		}
		return Effect.CHANGES;
	}

	static Effect babies(Mob m, boolean dryRun) {
		if (!ZOMBIES.contains(m.type()) || !m.baby()) {
			return Effect.NOTHING;
		}
		if (!dryRun) {
			m.makeAdult();
			if ("chicken".equals(m.mount()) && !m.ownMount()) {
				m.removeMount();
			}
		}
		return Effect.CHANGES;
	}

	static Effect nautiluses(Mob m, boolean dryRun) {
		if (!"drowned".equals(m.type()) || !"zombie_nautilus".equals(m.mount()) || m.ownMount()) {
			return Effect.NOTHING;
		}
		if (!dryRun) {
			m.removeMount();
		}
		return Effect.CHANGES;
	}

	static Effect collect(Mob m, boolean dryRun) {
		if (!m.picksUp()) {
			return Effect.NOTHING;
		}
		if (!dryRun) {
			m.noPickup();
		}
		return Effect.CHANGES;
	}

	static Effect weapons(Mob m, boolean dryRun) {
		String a = m.weapon();
		if (a == null || m.specialWeapon()) {
			return Effect.NOTHING;
		}
		boolean suspicious = "drowned".equals(m.type()) ? DROWNED_WEAPONS.contains(a)
				: ZOMBIES.contains(m.type()) && !"zombified_piglin".equals(m.type()) && ZOMBIE_WEAPONS.contains(a);
		return suspicious ? Effect.NOTICE : Effect.NOTHING;
	}

	/** Los arreglos de los mobs de plantilla (solo se ejecutan sobre los que {@link #fromTemplate} reconoce). */
	public static final Fixes.Ledger<Mob> LEDGER = new Fixes.Ledger<>(List.of(
			new Fix<>(1, "marcas", Fixes.Scope.ENTITY, MobFixes::marks),
			new Fix<>(2, "bebes", Fixes.Scope.ENTITY, MobFixes::babies),
			new Fix<>(3, "nautilos", Fixes.Scope.ENTITY, MobFixes::nautiluses),
			new Fix<>(4, "recoger", Fixes.Scope.ENTITY, MobFixes::collect),
			new Fix<>(5, "armas", Fixes.Scope.ENTITY, MobFixes::weapons)));
}
