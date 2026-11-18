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
 * Dependencias opcionales de los mapas web: sin BlueMap, Dynmap ni squaremap no se carga ninguna clase suya. Sus API
 * son compileOnly (no están en el classpath de las pruebas, así que cualquier carga fallaría) y ninguna clase del mod,
 * salvo su adaptador, nombra una clase de un mapa ni un adaptador (se buscan en el bytecode).
 */
class WebMapsIsolationTest {
	/** Paquetes de las API (como aparecen en el bytecode) y de los adaptadores. */
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
		for (String c : List.of("MapasWeb", "Marcadores", "Registro", "Sitio", "Marcador", "Capa", "Iconos", "MapaWeb")) {
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
				assertTrue(mentions(Files.readAllBytes(f), "io/github/albertosa23/heraldia/maps/MapaWeb"), clazz + " implementa MapaWeb");
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
