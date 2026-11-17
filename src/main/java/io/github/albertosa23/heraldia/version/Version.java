package io.github.albertosa23.heraldia.version;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

/**
 * Versión semántica (lógica pura): números separados por puntos («0.1.0», «26.3»; una «v» delante se ignora), una
 * pre-publicación opcional tras «-» («1.2.0-beta.1») y metadatos de compilación tras «+» que no cuentan («0.2.0+26.3»).
 * Se compara como en semver: números (los que faltan valen 0), y a igualdad la pre-publicación va antes que la versión
 * final; entre pre-publicaciones, identificador a identificador (los numéricos, por valor y antes que los de texto).
 */
public record Version(List<Integer> numeros, List<String> pre) implements Comparable<Version> {
	public Version {
		numeros = List.copyOf(numeros);
		pre = List.copyOf(pre);
	}

	/** La versión de un texto, o vacío si no lo es (sin números, partes vacías, más de 4 números o números enormes). */
	public static Optional<Version> de(String texto) {
		if (texto == null) {
			return Optional.empty();
		}
		String s = texto.strip();
		if (s.startsWith("v") || s.startsWith("V")) {
			s = s.substring(1);
		}
		int mas = s.indexOf('+');
		if (mas >= 0) {
			s = s.substring(0, mas);
		}
		String preTexto = null;
		int guion = s.indexOf('-');
		if (guion >= 0) {
			preTexto = s.substring(guion + 1);
			s = s.substring(0, guion);
		}
		String[] partes = s.split("\\.", -1);
		if (s.isEmpty() || partes.length > 4) {
			return Optional.empty();
		}
		List<Integer> nums = new ArrayList<>();
		for (String p : partes) {
			if (p.isEmpty() || p.length() > 9 || !p.chars().allMatch(c -> c >= '0' && c <= '9')) {
				return Optional.empty();
			}
			nums.add(Integer.parseInt(p));
		}
		List<String> pre = new ArrayList<>();
		if (preTexto != null) {
			for (String p : preTexto.split("\\.", -1)) {
				if (p.isEmpty() || !p.chars().allMatch(c -> Character.isLetterOrDigit(c) || c == '-')) {
					return Optional.empty();
				}
				pre.add(p.toLowerCase(Locale.ROOT));
			}
		}
		return Optional.of(new Version(nums, pre));
	}

	public boolean prepublicacion() {
		return !pre.isEmpty();
	}

	/** El número `i` (0 si no lo tiene). */
	public int numero(int i) {
		return i < numeros.size() ? numeros.get(i) : 0;
	}

	@Override
	public int compareTo(Version o) {
		int n = Math.max(numeros.size(), o.numeros.size());
		for (int i = 0; i < n; i++) {
			int c = Integer.compare(numero(i), o.numero(i));
			if (c != 0) {
				return c;
			}
		}
		if (pre.isEmpty() || o.pre.isEmpty()) {
			return Boolean.compare(pre.isEmpty(), o.pre.isEmpty());
		}
		for (int i = 0; i < Math.min(pre.size(), o.pre.size()); i++) {
			int c = compararIdentificador(pre.get(i), o.pre.get(i));
			if (c != 0) {
				return c;
			}
		}
		return Integer.compare(pre.size(), o.pre.size());
	}

	private static int compararIdentificador(String a, String b) {
		boolean na = a.chars().allMatch(Character::isDigit), nb = b.chars().allMatch(Character::isDigit);
		if (na && nb) {
			return a.length() != b.length() ? Integer.compare(a.length(), b.length()) : a.compareTo(b);
		}
		return na ? -1 : nb ? 1 : a.compareTo(b);
	}

	/**
	 * ¿Sirve una versión del mod compilada para Minecraft `compilada` en un servidor `servidor`? Como el «~» con el que el
	 * mod declara su Minecraft en fabric.mod.json («~26.3»: de la 26.3 a la 26.4, sin incluirla): misma versión mayor y
	 * menor, y el servidor igual o posterior. Falso si alguna no es una versión.
	 */
	public static boolean mismoMinecraft(String compilada, String servidor) {
		Optional<Version> c = de(compilada), s = de(servidor);
		if (c.isEmpty() || s.isEmpty()) {
			return false;
		}
		return c.get().numero(0) == s.get().numero(0) && c.get().numero(1) == s.get().numero(1) && s.get().compareTo(c.get()) >= 0;
	}

	@Override
	public String toString() {
		StringBuilder sb = new StringBuilder();
		for (int i = 0; i < numeros.size(); i++) {
			sb.append(i > 0 ? "." : "").append(numeros.get(i));
		}
		return pre.isEmpty() ? sb.toString() : sb.append('-').append(String.join(".", pre)).toString();
	}
}
