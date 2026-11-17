package io.github.albertosa23.heraldia.mapas;

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
class MapasWebAisladoTest {
	/** Paquetes de las API (como aparecen en el bytecode) y de los adaptadores. */
	static final List<String> API = List.of("de/bluecolored/", "xyz/jpenilla/", "org/dynmap/");
	static final String ADAPTADORES = "io/github/albertosa23/heraldia/mapas/";
	static final Set<String> SUBPAQUETES = Set.of("bluemap", "dynmap", "squaremap");

	@Test
	void sinMapasNoSeDetectaNinguno() {
		assertEquals(List.of(), MapasWeb.detectados(id -> false));
		assertEquals(List.of("squaremap"), MapasWeb.detectados(Set.of("squaremap", "lithium")::contains));
		assertEquals(List.of("bluemap", "dynmap", "squaremap"), MapasWeb.detectados(id -> true));
	}

	@Test
	void lasApiNoEstanEnElClasspath() {
		for (String c : List.of("de.bluecolored.bluemap.api.BlueMapAPI", "xyz.jpenilla.squaremap.api.SquaremapProvider",
				"org.dynmap.DynmapCommonAPIListener")) {
			assertThrows(ClassNotFoundException.class, () -> Class.forName(c, false, getClass().getClassLoader()), c);
		}
	}

	@Test
	void lasClasesComunesSeCarganSinLasApi() throws ClassNotFoundException {
		for (String c : List.of("MapasWeb", "Marcadores", "Registro", "Sitio", "Marcador", "Capa", "Iconos", "MapaWeb")) {
			Class.forName("io.github.albertosa23.heraldia.mapas." + c, true, getClass().getClassLoader());
		}
		Class.forName("io.github.albertosa23.heraldia.mixin.PlayerAdvancementsMixin", false, getClass().getClassLoader());
	}

	@Test
	void cadaAdaptadorExisteYEsUnMapaWeb() throws IOException, URISyntaxException {
		Path raiz = raiz();
		assertEquals(SUBPAQUETES, Set.copyOf(MapasWeb.ADAPTADORES.keySet()));
		MapasWeb.ADAPTADORES.forEach((mod, clase) -> {
			assertTrue(clase.startsWith("io.github.albertosa23.heraldia.mapas." + mod + "."), clase);
			Path f = raiz.resolve(clase.replace('.', '/') + ".class");
			assertTrue(Files.isRegularFile(f), f.toString());
			try {
				assertTrue(contiene(Files.readAllBytes(f), "io/github/albertosa23/heraldia/mapas/MapaWeb"), clase + " implementa MapaWeb");
			} catch (IOException e) {
				throw new IllegalStateException(e);
			}
		});
	}

	@Test
	void ningunaClaseDelModFueraDeLosAdaptadoresNombraUnMapa() throws IOException, URISyntaxException {
		Path raiz = raiz();
		List<String> malas = new ArrayList<>();
		int vistas = 0;
		try (Stream<Path> fs = Files.walk(raiz)) {
			for (Path f : fs.filter(p -> p.toString().endsWith(".class")).toList()) {
				String rel = raiz.relativize(f).toString().replace('\\', '/');
				if (SUBPAQUETES.stream().anyMatch(s -> rel.startsWith(ADAPTADORES + s + "/"))) {
					continue;
				}
				vistas++;
				byte[] b = Files.readAllBytes(f);
				for (String api : API) {
					if (contiene(b, api)) {
						malas.add(rel + " → " + api);
					}
				}
				for (String s : SUBPAQUETES) {
					if (contiene(b, ADAPTADORES + s + "/")) {
						malas.add(rel + " → adaptador " + s);
					}
				}
			}
		}
		assertTrue(vistas > 100, "clases recorridas: " + vistas);
		assertEquals(List.of(), malas);
	}

	@Test
	void losAdaptadoresSoloNombranSuPropiaApi() throws IOException, URISyntaxException {
		Path raiz = raiz();
		for (String s : SUBPAQUETES) {
			try (Stream<Path> fs = Files.list(raiz.resolve(ADAPTADORES + s))) {
				for (Path f : fs.toList()) {
					byte[] b = Files.readAllBytes(f);
					String propia = switch (s) {
						case "bluemap" -> "de/bluecolored/";
						case "squaremap" -> "xyz/jpenilla/";
						default -> "org/dynmap/";
					};
					assertTrue(contiene(b, propia), f + " usa su API");
					for (String api : API) {
						if (!api.equals(propia)) {
							assertTrue(!contiene(b, api), f + " no debe nombrar " + api);
						}
					}
				}
			}
		}
	}

	private static Path raiz() throws URISyntaxException {
		return Path.of(MapasWeb.class.getProtectionDomain().getCodeSource().getLocation().toURI());
	}

	static boolean contiene(byte[] b, String texto) {
		byte[] t = texto.getBytes(StandardCharsets.UTF_8);
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
