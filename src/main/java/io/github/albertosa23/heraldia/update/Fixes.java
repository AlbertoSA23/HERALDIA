package io.github.albertosa23.heraldia.update;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Registro de arreglos por versión (T46), lógica pura: cada arreglo tiene un número (crece con las versiones; el mayor es
 * el nivel de arreglos de esta versión), un id, su ámbito (entidad o chunk) y una acción idempotente que mira el objetivo
 * y, si hace falta, lo corrige (en modo de prueba solo dice si lo cambiaría). Se aplican de forma perezosa, como
 * comun/Anclaje: al cargar cada entidad o chunk se ejecutan los de número mayor que la marca que lleva (ninguna = 0) y se
 * le pone la marca del nivel actual, así que cada uno corre una sola vez por objetivo; /heraldia update repair los fuerza
 * en lo cargado (sin mirar la marca: por eso tienen que ser idempotentes).
 * <p>Para añadir uno en una versión futura: el número siguiente al último, su id (texto heraldia.arreglos.&lt;id&gt;) y su
 * test de idempotencia en {@code FixesTest}. Nunca se cambia el número de uno publicado.
 */
public final class Fixes {
	public enum Scope { ENTITY, CHUNK }

	/** Lo que hizo (o haría) una acción sobre un objetivo. */
	public enum Effect {
		/** No hacía falta. */
		NOTHING,
		/** Lo ha corregido (o lo corregiría, en modo de prueba). */
		CHANGES,
		/** Hay algo mal que no se puede corregir solo (se cuenta en el informe). */
		NOTICE
	}

	/** La acción de un arreglo sobre un objetivo de tipo T. Idempotente: tras un CAMBIA, la siguiente da NADA. */
	@FunctionalInterface
	public interface Action<T> {
		Effect apply(T target, boolean dryRun);
	}

	public record Fix<T>(int number, String id, Scope scope, Action<T> action) {
	}

	/** Los arreglos de un ámbito, por número. */
	public static final class Ledger<T> {
		private final List<Fix<T>> fixes;

		public Ledger(List<Fix<T>> fixes) {
			List<Fix<T>> l = new ArrayList<>(fixes);
			l.sort(Comparator.comparingInt(Fix::number));
			for (int i = 1; i < l.size(); i++) {
				if (l.get(i).number() == l.get(i - 1).number()) {
					throw new IllegalArgumentException("dos arreglos con el número " + l.get(i).number());
				}
			}
			this.fixes = List.copyOf(l);
		}

		public List<Fix<T>> fixes() {
			return fixes;
		}

		/** El mayor número (0 sin arreglos): la marca que queda en un objetivo ya revisado. */
		public int tier() {
			return fixes.isEmpty() ? 0 : fixes.get(fixes.size() - 1).number();
		}

		/** ¿Le falta alguno a un objetivo con esta marca? */
		public boolean pending(int mark) {
			return mark < tier();
		}

		/**
		 * Ejecuta sobre {@code target} los arreglos de número mayor que {@code mark} (todos si {@code force}). Devuelve
		 * el efecto de cada uno que no dio NADA, en orden.
		 */
		public Map<String, Effect> execute(T target, int mark, boolean dryRun, boolean force) {
			Map<String, Effect> out = new LinkedHashMap<>();
			for (Fix<T> a : fixes) {
				if (force || a.number() > mark) {
					Effect e = a.action().apply(target, dryRun);
					if (e != Effect.NOTHING) {
						out.put(a.id(), e);
					}
				}
			}
			return out;
		}
	}

	/** Cuenta los efectos de muchos objetivos: {id: [cambios, avisos]}, en el orden en que aparecen. */
	public static final class Tally {
		private final Map<String, int[]> byId = new LinkedHashMap<>();
		private int checked;

		public void add(Map<String, Effect> effects) {
			checked++;
			effects.forEach((id, e) -> byId.computeIfAbsent(id, k -> new int[2])[e == Effect.NOTICE ? 1 : 0]++);
		}

		public Map<String, int[]> byId() {
			return byId;
		}

		public int checked() {
			return checked;
		}

		public int changes() {
			return byId.values().stream().mapToInt(v -> v[0]).sum();
		}
	}

	private Fixes() {
	}
}
