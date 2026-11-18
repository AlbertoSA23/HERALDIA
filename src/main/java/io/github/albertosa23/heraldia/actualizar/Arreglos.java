package io.github.albertosa23.heraldia.actualizar;

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
 * test de idempotencia en {@code ArreglosTest}. Nunca se cambia el número de uno publicado.
 */
public final class Arreglos {
	public enum Ambito { ENTIDAD, CHUNK }

	/** Lo que hizo (o haría) una acción sobre un objetivo. */
	public enum Efecto {
		/** No hacía falta. */
		NADA,
		/** Lo ha corregido (o lo corregiría, en modo de prueba). */
		CAMBIA,
		/** Hay algo mal que no se puede corregir solo (se cuenta en el informe). */
		AVISO
	}

	/** La acción de un arreglo sobre un objetivo de tipo T. Idempotente: tras un CAMBIA, la siguiente da NADA. */
	@FunctionalInterface
	public interface Accion<T> {
		Efecto aplicar(T objetivo, boolean prueba);
	}

	public record Arreglo<T>(int numero, String id, Ambito ambito, Accion<T> accion) {
	}

	/** Los arreglos de un ámbito, por número. */
	public static final class Registro<T> {
		private final List<Arreglo<T>> arreglos;

		public Registro(List<Arreglo<T>> arreglos) {
			List<Arreglo<T>> l = new ArrayList<>(arreglos);
			l.sort(Comparator.comparingInt(Arreglo::numero));
			for (int i = 1; i < l.size(); i++) {
				if (l.get(i).numero() == l.get(i - 1).numero()) {
					throw new IllegalArgumentException("dos arreglos con el número " + l.get(i).numero());
				}
			}
			this.arreglos = List.copyOf(l);
		}

		public List<Arreglo<T>> arreglos() {
			return arreglos;
		}

		/** El mayor número (0 sin arreglos): la marca que queda en un objetivo ya revisado. */
		public int nivel() {
			return arreglos.isEmpty() ? 0 : arreglos.get(arreglos.size() - 1).numero();
		}

		/** ¿Le falta alguno a un objetivo con esta marca? */
		public boolean pendiente(int marca) {
			return marca < nivel();
		}

		/**
		 * Ejecuta sobre {@code objetivo} los arreglos de número mayor que {@code marca} (todos si {@code forzar}). Devuelve
		 * el efecto de cada uno que no dio NADA, en orden.
		 */
		public Map<String, Efecto> ejecutar(T objetivo, int marca, boolean prueba, boolean forzar) {
			Map<String, Efecto> out = new LinkedHashMap<>();
			for (Arreglo<T> a : arreglos) {
				if (forzar || a.numero() > marca) {
					Efecto e = a.accion().aplicar(objetivo, prueba);
					if (e != Efecto.NADA) {
						out.put(a.id(), e);
					}
				}
			}
			return out;
		}
	}

	/** Cuenta los efectos de muchos objetivos: {id: [cambios, avisos]}, en el orden en que aparecen. */
	public static final class Cuenta {
		private final Map<String, int[]> porId = new LinkedHashMap<>();
		private int revisados;

		public void sumar(Map<String, Efecto> efectos) {
			revisados++;
			efectos.forEach((id, e) -> porId.computeIfAbsent(id, k -> new int[2])[e == Efecto.AVISO ? 1 : 0]++);
		}

		public Map<String, int[]> porId() {
			return porId;
		}

		public int revisados() {
			return revisados;
		}

		public int cambios() {
			return porId.values().stream().mapToInt(v -> v[0]).sum();
		}
	}

	private Arreglos() {
	}
}
