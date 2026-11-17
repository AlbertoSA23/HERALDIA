package io.github.albertosa23.heraldia.tesoro;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Optional;
import java.util.Random;
import java.util.UUID;

/**
 * Elige la cadena de una pista: lógica pura y determinista (misma semilla, mismo origen y mismas candidatas, misma cadena;
 * PlanificadorTest). Orden de la cadena: una estructura mediana a menos de {@code radio} bloques del origen; desde ella,
 * una entrada a mina (si no hay ninguna, otra mediana); y desde la última, el tesoro, a 48-128 bloques en una dirección al
 * azar. Si no hay mediana, la primera es una mina. Sin ninguna estructura, no hay cadena.
 * <p>Las candidatas las da un {@link Buscador} (en el juego, la búsqueda fuera del hilo del servidor de {@link Busqueda},
 * que no carga ni genera chunks). De cada tipo se prefieren las ya generadas; entre las {@value #ELEGIBLES} primeras (las
 * generadas y luego las previstas, por distancia) se sortea una. Ningún destino se repite (ni a menos de
 * {@value #DISTANCIA_MIN} bloques de otro).
 */
public final class Planificador {
	/** Distancia mínima entre dos marcas seguidas (y entre dos destinos cualesquiera de la cadena). */
	public static final int DISTANCIA_MIN = 96;
	public static final int ELEGIBLES = 3;
	public static final int TESORO_MIN = 48, TESORO_MAX = 128;

	private Planificador() {
	}

	/** Una estructura en la que podría caer una marca. */
	public record Candidata(Destino.Tipo tipo, String estructura, int x, int z, boolean generada) {
	}

	/** Las candidatas de un tipo a menos de {@code radio} bloques de (x, z), en cualquier orden. */
	@FunctionalInterface
	public interface Buscador {
		List<Candidata> buscar(Destino.Tipo tipo, int x, int z, int radio);
	}

	/** El id del bioma en (x, z). */
	@FunctionalInterface
	public interface Biomas {
		String en(int x, int z);
	}

	/** Semilla de la n-ésima pista que descifra un jugador en un mundo: distinta por mundo, jugador y número. */
	public static long semilla(long mundo, UUID jugador, int n) {
		long h = mundo * 0x9E3779B97F4A7C15L ^ jugador.getMostSignificantBits();
		h = mezclar(h) ^ jugador.getLeastSignificantBits();
		h = mezclar(h) + n * 0xBF58476D1CE4E5B9L;
		return mezclar(h);
	}

	static long mezclar(long z) {
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}

	public static Optional<List<Destino>> planificar(long semilla, int ox, int oz, int radio, Buscador buscador, Biomas biomas) {
		Random rnd = new Random(semilla);
		List<Destino> out = new ArrayList<>();
		Destino primera = elegir(buscador, Destino.Tipo.MEDIANA, ox, oz, radio, out, rnd, biomas)
				.or(() -> elegir(buscador, Destino.Tipo.MINA, ox, oz, radio, out, rnd, biomas)).orElse(null);
		if (primera == null) {
			return Optional.empty();
		}
		out.add(primera);
		Destino segunda = elegir(buscador, Destino.Tipo.MINA, primera.x(), primera.z(), radio, out, rnd, biomas)
				.or(() -> elegir(buscador, Destino.Tipo.MEDIANA, primera.x(), primera.z(), radio, out, rnd, biomas)).orElse(null);
		if (segunda != null) {
			out.add(segunda);
		}
		Destino ultima = out.getLast();
		out.add(tesoro(rnd, ultima.x(), ultima.z(), TESORO_MIN, TESORO_MAX, biomas));
		return Optional.of(List.copyOf(out));
	}

	/** El tesoro a [min, max] bloques de (x, z) en una dirección al azar. */
	static Destino tesoro(Random rnd, int x, int z, int min, int max, Biomas biomas) {
		double a = rnd.nextDouble() * 2 * Math.PI;
		int d = min + rnd.nextInt(max - min + 1);
		int tx = x + (int) Math.round(Math.cos(a) * d), tz = z + (int) Math.round(Math.sin(a) * d);
		return new Destino(Destino.Tipo.TESORO, "", tx, tz, false, biomas.en(tx, tz));
	}

	/** El tesoro movido (su sitio no era seguro): otra vez desde donde estaba, con la semilla y el número de intento. */
	public static Destino moverTesoro(Cadena c, Biomas biomas) {
		Random rnd = new Random(c.semilla() ^ mezclar(c.movido() + 1L));
		Destino t = c.destinos().getLast();
		return tesoro(rnd, t.x(), t.z(), 32, 64, biomas);
	}

	static Optional<Destino> elegir(Buscador buscador, Destino.Tipo tipo, int x, int z, int radio, List<Destino> usados, Random rnd,
			Biomas biomas) {
		long min = (long) DISTANCIA_MIN * DISTANCIA_MIN, max = (long) radio * radio;
		List<Candidata> validas = new ArrayList<>();
		for (Candidata c : buscador.buscar(tipo, x, z, radio)) {
			long d = dist(c.x() - x, c.z() - z);
			if (c.tipo() == tipo && d >= min && d <= max && usados.stream().noneMatch(u -> dist(u.x() - c.x(), u.z() - c.z()) < min)) {
				validas.add(c);
			}
		}
		if (validas.isEmpty()) {
			return Optional.empty();
		}
		validas.sort(Comparator.comparing((Candidata c) -> !c.generada()).thenComparingLong(c -> dist(c.x() - x, c.z() - z))
				.thenComparingInt(Candidata::x).thenComparingInt(Candidata::z).thenComparing(Candidata::estructura));
		Candidata c = validas.get(rnd.nextInt(Math.min(ELEGIBLES, validas.size())));
		return Optional.of(new Destino(tipo, c.estructura(), c.x(), c.z(), c.generada(), biomas.en(c.x(), c.z())));
	}

	static long dist(long dx, long dz) {
		return dx * dx + dz * dz;
	}
}
