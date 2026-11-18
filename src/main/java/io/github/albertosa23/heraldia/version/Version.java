package io.github.albertosa23.heraldia.version;

import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.Optional;

/**
 * Semantic version (pure logic): numbers separated by dots ("0.1.0", "26.3"; a leading "v" is ignored), an
 * optional prerelease after "-" ("1.2.0-beta.1") and build metadata after "+" that does not count ("0.2.0+26.3").
 * It compares as in semver: numbers (missing ones are 0), and on a tie the prerelease goes before the final
 * version; between prereleases, identifier by identifier (numeric ones, by value and before text ones).
 */
public record Version(List<Integer> numbers, List<String> pre) implements Comparable<Version> {
	public Version {
		numbers = List.copyOf(numbers);
		pre = List.copyOf(pre);
	}

	/** The version of a text, or empty if it is not one (no numbers, empty parts, more than 4 numbers or huge numbers). */
	public static Optional<Version> of(String text) {
		if (text == null) {
			return Optional.empty();
		}
		String s = text.strip();
		if (s.startsWith("v") || s.startsWith("V")) {
			s = s.substring(1);
		}
		int plus = s.indexOf('+');
		if (plus >= 0) {
			s = s.substring(0, plus);
		}
		String preText = null;
		int dash = s.indexOf('-');
		if (dash >= 0) {
			preText = s.substring(dash + 1);
			s = s.substring(0, dash);
		}
		String[] parts = s.split("\\.", -1);
		if (s.isEmpty() || parts.length > 4) {
			return Optional.empty();
		}
		List<Integer> nums = new ArrayList<>();
		for (String p : parts) {
			if (p.isEmpty() || p.length() > 9 || !p.chars().allMatch(c -> c >= '0' && c <= '9')) {
				return Optional.empty();
			}
			nums.add(Integer.parseInt(p));
		}
		List<String> pre = new ArrayList<>();
		if (preText != null) {
			for (String p : preText.split("\\.", -1)) {
				if (p.isEmpty() || !p.chars().allMatch(c -> Character.isLetterOrDigit(c) || c == '-')) {
					return Optional.empty();
				}
				pre.add(p.toLowerCase(Locale.ROOT));
			}
		}
		return Optional.of(new Version(nums, pre));
	}

	public boolean prerelease() {
		return !pre.isEmpty();
	}

	/** Number `i` (0 if it does not have it). */
	public int number(int i) {
		return i < numbers.size() ? numbers.get(i) : 0;
	}

	@Override
	public int compareTo(Version o) {
		int n = Math.max(numbers.size(), o.numbers.size());
		for (int i = 0; i < n; i++) {
			int c = Integer.compare(number(i), o.number(i));
			if (c != 0) {
				return c;
			}
		}
		if (pre.isEmpty() || o.pre.isEmpty()) {
			return Boolean.compare(pre.isEmpty(), o.pre.isEmpty());
		}
		for (int i = 0; i < Math.min(pre.size(), o.pre.size()); i++) {
			int c = compareIdentifier(pre.get(i), o.pre.get(i));
			if (c != 0) {
				return c;
			}
		}
		return Integer.compare(pre.size(), o.pre.size());
	}

	private static int compareIdentifier(String a, String b) {
		boolean na = a.chars().allMatch(Character::isDigit), nb = b.chars().allMatch(Character::isDigit);
		if (na && nb) {
			return a.length() != b.length() ? Integer.compare(a.length(), b.length()) : a.compareTo(b);
		}
		return na ? -1 : nb ? 1 : a.compareTo(b);
	}

	/**
	 * Does a version of the mod compiled for Minecraft `compiled` work on a `server` server? Like the "~" with which the
	 * mod declares its Minecraft in fabric.mod.json ("~26.3": from 26.3 to 26.4, not included): same major and
	 * minor version, and the server equal or later. False if either is not a version.
	 */
	public static boolean sameMinecraft(String compiled, String server) {
		Optional<Version> c = of(compiled), s = of(server);
		if (c.isEmpty() || s.isEmpty()) {
			return false;
		}
		return c.get().number(0) == s.get().number(0) && c.get().number(1) == s.get().number(1) && s.get().compareTo(c.get()) >= 0;
	}

	@Override
	public String toString() {
		StringBuilder sb = new StringBuilder();
		for (int i = 0; i < numbers.size(); i++) {
			sb.append(i > 0 ? "." : "").append(numbers.get(i));
		}
		return pre.isEmpty() ? sb.toString() : sb.append('-').append(String.join(".", pre)).toString();
	}
}
