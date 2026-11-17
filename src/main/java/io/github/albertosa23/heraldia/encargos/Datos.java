package io.github.albertosa23.heraldia.encargos;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Lo que se guarda de cada jugador (adjunto persistente de Fabric en su .dat, sin enviarlo al cliente): los encargos
 * aceptados, la reputación con cada aldea, cuántos ha entregado y los ids de los últimos entregados (para no cobrar dos
 * veces el mismo). Inmutable: cada cambio da otro valor (y {@code setAttached}).
 */
public record Datos(List<Activo> activos, Map<String, Integer> reputacion, int completados, List<String> hechos) {
	/** Encargos aceptados a la vez, como mucho. */
	public static final int MAX_ACTIVOS = 5;
	/** Ids de entregados que se recuerdan (los más recientes): de sobra para varios periodos de todas las aldeas visitadas. */
	public static final int MAX_HECHOS = 200;
	public static final Datos VACIO = new Datos(List.of(), Map.of(), 0, List.of());

	/** Un encargo aceptado y si ya se cumplió lo que pide (los de traer se comprueban al entregar). */
	public record Activo(Encargo encargo, boolean cumplido) {
		public static final Codec<Activo> CODEC = RecordCodecBuilder.create(i -> i.group(
				Encargo.CODEC.fieldOf("encargo").forGetter(Activo::encargo),
				Codec.BOOL.optionalFieldOf("cumplido", false).forGetter(Activo::cumplido)).apply(i, Activo::new));
	}

	public static final Codec<Datos> CODEC = RecordCodecBuilder.create(i -> i.group(
			Activo.CODEC.listOf().optionalFieldOf("activos", List.of()).forGetter(Datos::activos),
			Codec.unboundedMap(Codec.STRING, Codec.INT).optionalFieldOf("reputacion", Map.of()).forGetter(Datos::reputacion),
			Codec.INT.optionalFieldOf("completados", 0).forGetter(Datos::completados),
			Codec.STRING.listOf().optionalFieldOf("hechos", List.of()).forGetter(Datos::hechos)).apply(i, Datos::new));

	public Datos {
		activos = List.copyOf(activos);
		reputacion = Map.copyOf(reputacion);
		hechos = List.copyOf(hechos);
	}

	public int reputacion(String aldea) {
		return reputacion.getOrDefault(aldea, 0);
	}

	public Reputacion.Nivel nivel(String aldea) {
		return Reputacion.nivel(reputacion(aldea));
	}

	/** ¿Lo tiene aceptado (por id)? */
	public boolean tiene(String id) {
		return activos.stream().anyMatch(a -> a.encargo().id().equals(id));
	}

	public boolean hecho(String id) {
		return hechos.contains(id);
	}

	/** Por qué no se puede aceptar (clave del motivo) o null si se puede. */
	public String noAceptable(Encargo e) {
		if (hecho(e.id())) {
			return "hecho";
		}
		if (tiene(e.id())) {
			return "ya";
		}
		if (activos.size() >= MAX_ACTIVOS) {
			return "lleno";
		}
		return null;
	}

	public Datos aceptar(Encargo e) {
		List<Activo> l = new ArrayList<>(activos);
		l.add(new Activo(e, false));
		return new Datos(l, reputacion, completados, hechos);
	}

	/** Quita el aceptado número {@code i} (0..); sin cambios si no existe. */
	public Datos abandonar(int i) {
		if (i < 0 || i >= activos.size()) {
			return this;
		}
		List<Activo> l = new ArrayList<>(activos);
		l.remove(i);
		return new Datos(l, reputacion, completados, hechos);
	}

	/** Marca como cumplidos los aceptados que cumplen la condición. */
	public Datos cumplir(java.util.function.Predicate<Encargo> cond) {
		boolean cambia = false;
		List<Activo> l = new ArrayList<>(activos.size());
		for (Activo a : activos) {
			if (!a.cumplido() && cond.test(a.encargo())) {
				l.add(new Activo(a.encargo(), true));
				cambia = true;
			} else {
				l.add(a);
			}
		}
		return cambia ? new Datos(l, reputacion, completados, hechos) : this;
	}

	/**
	 * Entrega el aceptado con ese id: lo quita, lo apunta como hecho, suma uno a los completados y, si
	 * {@code conReputacion}, su reputación a su aldea.
	 */
	public Datos entregar(String id, boolean conReputacion) {
		Activo a = activos.stream().filter(x -> x.encargo().id().equals(id)).findFirst().orElse(null);
		if (a == null) {
			return this;
		}
		List<Activo> l = new ArrayList<>(activos);
		l.remove(a);
		List<String> h = new ArrayList<>(hechos);
		h.add(id);
		while (h.size() > MAX_HECHOS) {
			h.remove(0);
		}
		Datos d = new Datos(l, reputacion, completados + 1, h);
		return conReputacion ? d.sumarReputacion(a.encargo().aldea(), a.encargo().reputacion()) : d;
	}

	public Datos sumarReputacion(String aldea, int cambio) {
		Map<String, Integer> m = new LinkedHashMap<>(reputacion);
		m.put(aldea, Reputacion.sumar(reputacion(aldea), cambio));
		return new Datos(activos, m, completados, hechos);
	}

	/** Cuántas aldeas tienen al menos ese nivel con el jugador. */
	public long aldeasCon(Reputacion.Nivel nivel) {
		return reputacion.values().stream().filter(v -> Reputacion.nivel(v).compareTo(nivel) >= 0).count();
	}

	/** Mejor nivel con alguna aldea. */
	public Reputacion.Nivel mejorNivel() {
		return Reputacion.nivel(reputacion.values().stream().mapToInt(Integer::intValue).max().orElse(0));
	}
}
