package io.github.albertosa23.heraldia.maps;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.net.URISyntaxException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;
import java.util.stream.Stream;
import org.junit.jupiter.api.Test;

/**
 * Optional web map dependencies: without BlueMap, Dynmap or squaremap none of their classes is loaded. Their APIs
 * are compileOnly (they are not on the tests' classpath, so any load would fail) and no mod class,
 * except its adapter, names a map class or an adapter (they are searched for in the bytecode).
 */
class WebMapsIsolationTest {
	/** Packages of the APIs (as they appear in the bytecode) and of the adapters. */
	static final List<String> API = List.of("de/bluecolored/", "xyz/jpenilla/", "org/dynmap/");
	static final String ADAPTERS = "io/github/albertosa23/heraldia/maps/";
	static final Set<String> SUBPACKAGES = Set.of("bluemap", "dynmap", "squaremap");

	@Test
	void noMapsDetectsNone() {
		assertEquals(List.of(), WebMaps.detected(id -> false));
		assertEquals(List.of("squaremap"), WebMaps.detected(Set.of("squaremap", "lithium")::contains));
		assertEquals(List.of("bluemap", "dynmap", "squaremap"), WebMaps.detected(id -> true));
	}

	@Test
	void apisAreNotOnTheClasspath() {
		for (String c : List.of("de.bluecolored.bluemap.api.BlueMapAPI", "xyz.jpenilla.squaremap.api.SquaremapProvider",
				"org.dynmap.DynmapCommonAPIListener")) {
			assertThrows(ClassNotFoundException.class, () -> Class.forName(c, false, getClass().getClassLoader()), c);
		}
	}

	@Test
	void commonClassesLoadWithoutApis() throws ClassNotFoundException {
		for (String c : List.of("WebMaps", "Markers", "Ledger", "Site", "MapMarker", "Layer", "Icons", "WebMap")) {
			Class.forName("io.github.albertosa23.heraldia.maps." + c, true, getClass().getClassLoader());
		}
		Class.forName("io.github.albertosa23.heraldia.mixin.PlayerAdvancementsMixin", false, getClass().getClassLoader());
	}

	@Test
	void eachAdapterExistsAndIsAWebMap() throws IOException, URISyntaxException {
		Path root = root();
		assertEquals(SUBPACKAGES, Set.copyOf(WebMaps.ADAPTERS.keySet()));
		WebMaps.ADAPTERS.forEach((mod, clazz) -> {
			assertTrue(clazz.startsWith("io.github.albertosa23.heraldia.maps." + mod + "."), clazz);
			Path f = root.resolve(clazz.replace('.', '/') + ".class");
			assertTrue(Files.isRegularFile(f), f.toString());
			try {
				assertTrue(mentions(Files.readAllBytes(f), "io/github/albertosa23/heraldia/maps/WebMap"), clazz + " implements WebMap");
			} catch (IOException e) {
				throw new IllegalStateException(e);
			}
		});
	}

	@Test
	void noModClassOutsideAdaptersNamesAMap() throws IOException, URISyntaxException {
		Path root = root();
		List<String> bad = new ArrayList<>();
		int seen = 0;
		try (Stream<Path> fs = Files.walk(root)) {
			for (Path f : fs.filter(p -> p.toString().endsWith(".class")).toList()) {
				String rel = root.relativize(f).toString().replace('\\', '/');
				if (SUBPACKAGES.stream().anyMatch(s -> rel.startsWith(ADAPTERS + s + "/"))) {
					continue;
				}
				seen++;
				byte[] b = Files.readAllBytes(f);
				for (String api : API) {
					if (mentions(b, api)) {
						bad.add(rel + " → " + api);
					}
				}
				for (String s : SUBPACKAGES) {
					if (mentions(b, ADAPTERS + s + "/")) {
						bad.add(rel + " → adaptador " + s);
					}
				}
			}
		}
		assertTrue(seen > 100, "clases recorridas: " + seen);
		assertEquals(List.of(), bad);
	}

	@Test
	void adaptersOnlyNameTheirOwnApi() throws IOException, URISyntaxException {
		Path root = root();
		for (String s : SUBPACKAGES) {
			try (Stream<Path> fs = Files.list(root.resolve(ADAPTERS + s))) {
				for (Path f : fs.toList()) {
					byte[] b = Files.readAllBytes(f);
					String own = switch (s) {
						case "bluemap" -> "de/bluecolored/";
						case "squaremap" -> "xyz/jpenilla/";
						default -> "org/dynmap/";
					};
					assertTrue(mentions(b, own), f + " usa su API");
					for (String api : API) {
						if (!api.equals(own)) {
							assertTrue(!mentions(b, api), f + " no debe nombrar " + api);
						}
					}
				}
			}
		}
	}

	private static Path root() throws URISyntaxException {
		return Path.of(WebMaps.class.getProtectionDomain().getCodeSource().getLocation().toURI());
	}

	static boolean mentions(byte[] b, String text) {
		byte[] t = text.getBytes(StandardCharsets.UTF_8);
		outer:
		for (int i = 0; i + t.length <= b.length; i++) {
			for (int j = 0; j < t.length; j++) {
				if (b[i + j] != t[j]) {
					continue outer;
				}
			}
			return true;
		}
		return false;
	}
}
