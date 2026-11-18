package io.github.albertosa23.heraldia.actualizar;

import io.github.albertosa23.heraldia.actualizar.Arreglos.Arreglo;
import io.github.albertosa23.heraldia.actualizar.Arreglos.Efecto;
import java.util.List;
import java.util.Set;

/**
 * Arreglos iniciales de los mobs de plantilla (T46): fallos ya corregidos en el código que pueden seguir en mundos
 * generados con versiones anteriores (ver CHANGELOG y APRENDIZAJES). Sobre una vista mínima del mob ({@link Mob}), así la
 * lógica se prueba sin el juego; {@code Actualizar} la monta sobre el mob de verdad.
 * <ol>
 * <li>{@code marcas}: los guardianes y mobs con nombre de la 0.1.0 no llevaban etiquetas; se reconocen por su nombre
 * traducible {@code heraldia.*} (y persistentes) y reciben las de ahora: {@code heraldia_anclado} (no pasean fuera de su
 * sala —la «deriva»— ni recogen objetos), {@code heraldia_adulto} si son de la familia de los zombis y
 * {@code heraldia_guardian} si su nombre es el de un guardián (fases de jefe, barra y refuerzos).</li>
 * <li>{@code bebes}: un zombi, husk, ahogado, zombi aldeano o piglin zombificado de plantilla que salió bebé pasa a adulto
 * (y si iba en una gallina, se baja y la gallina de jinete se quita).</li>
 * <li>{@code nautilos}: un ahogado de plantilla montado en un nautilo zombi se baja y el nautilo se quita (si no tiene
 * nombre ni otro jinete).</li>
 * <li>{@code recoger}: un mob de plantilla que puede recoger objetos deja de poder ({@code CanPickUpLoot}).</li>
 * <li>{@code armas}: un ahogado de plantilla con un tridente o una caña sin nada especial, o un zombi con una pala, lanza o
 * espada de hierro sin nada especial, pudo perder el arma de su plantilla; no se sabe cuál era, así que solo se cuenta en
 * el informe (aviso), sin cambiarlo.</li>
 * </ol>
 */
public final class ArreglosMobs {
	public static final String ADULTO = "heraldia_adulto", ANCLADO = "heraldia_anclado", GUARDIAN = "heraldia_guardian";
	/** Tipos que pueden salir bebés al colocarse (core.BEBE_ZOMBI del generador). */
	static final Set<String> ZOMBIS = Set.of("zombie", "husk", "drowned", "zombie_villager", "zombified_piglin");
	static final Set<String> ARMAS_AHOGADO = Set.of("trident", "fishing_rod");
	static final Set<String> ARMAS_ZOMBI = Set.of("iron_shovel", "iron_sword", "iron_spear");

	/** Lo que los arreglos necesitan ver y tocar de un mob. */
	public interface Mob {
		/** Tipo sin espacio de nombres («zombie»). */
		String tipo();

		Set<String> etiquetas();

		void etiquetar(String etiqueta);

		/** Clave de su nombre si es traducible, o null. */
		String claveNombre();

		boolean persistente();

		boolean bebe();

		void hacerAdulto();

		/** Tipo de lo que monta, sin espacio de nombres, o null. */
		String montura();

		/** ¿La montura tiene nombre u otro jinete? (entonces no se quita) */
		boolean monturaPropia();

		/** Se baja y quita la montura. */
		void quitarMontura();

		boolean recoge();

		void noRecoger();

		/** Objeto de la mano principal sin espacio de nombres, o null. */
		String arma();

		/** ¿El arma tiene nombre o encantamientos? (entonces es de la plantilla) */
		boolean armaEspecial();
	}

	private ArreglosMobs() {
	}

	/** ¿Es un mob de una plantilla de Heraldia? Lleva una de sus etiquetas, o es persistente con un nombre heraldia.*. */
	public static boolean dePlantilla(Mob m) {
		Set<String> t = m.etiquetas();
		if (!t.isEmpty() && (t.contains(ADULTO) || t.contains(ANCLADO) || t.contains(GUARDIAN))) {
			return true;
		}
		return m.persistente() && nombreHeraldia(m.claveNombre());
	}

	static boolean nombreHeraldia(String clave) {
		return clave != null && clave.startsWith("heraldia.");
	}

	/** ¿Es el nombre de un guardián? (heraldia.unicas.castillo.guardian, heraldia.ciudadela.guardian...) */
	static boolean nombreDeGuardian(String clave) {
		return nombreHeraldia(clave) && clave.contains("guardian");
	}

	static Efecto marcas(Mob m, boolean prueba) {
		if (!nombreHeraldia(m.claveNombre()) || !m.persistente()) {
			return Efecto.NADA;
		}
		boolean falta = !m.etiquetas().contains(ANCLADO) || ZOMBIS.contains(m.tipo()) && !m.etiquetas().contains(ADULTO)
				|| nombreDeGuardian(m.claveNombre()) && !m.etiquetas().contains(GUARDIAN);
		if (!falta) {
			return Efecto.NADA;
		}
		if (!prueba) {
			m.etiquetar(ANCLADO);
			if (ZOMBIS.contains(m.tipo())) {
				m.etiquetar(ADULTO);
			}
			if (nombreDeGuardian(m.claveNombre())) {
				m.etiquetar(GUARDIAN);
			}
		}
		return Efecto.CAMBIA;
	}

	static Efecto bebes(Mob m, boolean prueba) {
		if (!ZOMBIS.contains(m.tipo()) || !m.bebe()) {
			return Efecto.NADA;
		}
		if (!prueba) {
			m.hacerAdulto();
			if ("chicken".equals(m.montura()) && !m.monturaPropia()) {
				m.quitarMontura();
			}
		}
		return Efecto.CAMBIA;
	}

	static Efecto nautilos(Mob m, boolean prueba) {
		if (!"drowned".equals(m.tipo()) || !"zombie_nautilus".equals(m.montura()) || m.monturaPropia()) {
			return Efecto.NADA;
		}
		if (!prueba) {
			m.quitarMontura();
		}
		return Efecto.CAMBIA;
	}

	static Efecto recoger(Mob m, boolean prueba) {
		if (!m.recoge()) {
			return Efecto.NADA;
		}
		if (!prueba) {
			m.noRecoger();
		}
		return Efecto.CAMBIA;
	}

	static Efecto armas(Mob m, boolean prueba) {
		String a = m.arma();
		if (a == null || m.armaEspecial()) {
			return Efecto.NADA;
		}
		boolean sospechosa = "drowned".equals(m.tipo()) ? ARMAS_AHOGADO.contains(a)
				: ZOMBIS.contains(m.tipo()) && !"zombified_piglin".equals(m.tipo()) && ARMAS_ZOMBI.contains(a);
		return sospechosa ? Efecto.AVISO : Efecto.NADA;
	}

	/** Los arreglos de los mobs de plantilla (solo se ejecutan sobre los que {@link #dePlantilla} reconoce). */
	public static final Arreglos.Registro<Mob> REGISTRO = new Arreglos.Registro<>(List.of(
			new Arreglo<>(1, "marcas", Arreglos.Ambito.ENTIDAD, ArreglosMobs::marcas),
			new Arreglo<>(2, "bebes", Arreglos.Ambito.ENTIDAD, ArreglosMobs::bebes),
			new Arreglo<>(3, "nautilos", Arreglos.Ambito.ENTIDAD, ArreglosMobs::nautilos),
			new Arreglo<>(4, "recoger", Arreglos.Ambito.ENTIDAD, ArreglosMobs::recoger),
			new Arreglo<>(5, "armas", Arreglos.Ambito.ENTIDAD, ArreglosMobs::armas)));
}
