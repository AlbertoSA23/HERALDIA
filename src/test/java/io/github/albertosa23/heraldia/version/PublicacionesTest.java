package io.github.albertosa23.heraldia.version;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.version.Publicaciones.Publicacion;
import java.io.IOException;
import java.io.InputStream;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.Base64;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Function;
import org.junit.jupiter.api.Test;

/** Respuestas de GitHub Releases y Modrinth (fixtures en src/test/resources/version) y la elección de la versión nueva. */
class PublicacionesTest {
	private static String fixture(String nombre) throws IOException {
		try (InputStream in = PublicacionesTest.class.getResourceAsStream("/version/" + nombre)) {
			return new String(in.readAllBytes(), StandardCharsets.UTF_8);
		}
	}

	private static Version v(String s) {
		return Version.de(s).orElseThrow();
	}

	/** El Minecraft de cada etiqueta de GitHub, como lo daría el gradle.properties; apunta a cuáles se preguntan. */
	private static Function<Publicacion, Optional<String>> mc(Map<String, String> porEtiqueta, List<String> preguntadas) {
		return p -> {
			preguntadas.add(p.etiqueta());
			return Optional.ofNullable(porEtiqueta.get(p.etiqueta()));
		};
	}

	@Test
	void leeGitHub() throws IOException {
		List<Publicacion> ps = Publicaciones.leer(fixture("github.json"));
		// sin el borrador, la que no tiene .jar (solo notas), la etiqueta que no es versión, el enlace que no es web y lo que no es objeto
		assertEquals(List.of("v0.3.0-beta.1", "v0.2.0", "v0.1.0"), ps.stream().map(Publicacion::etiqueta).toList());
		Publicacion beta = ps.get(0), b = ps.get(1);
		assertTrue(beta.prepublicacion());
		assertEquals("Heraldia 0.2.0", b.nombre());
		assertEquals("https://github.com/AlbertoSA23/HERALDIA/releases/tag/v0.2.0", b.url());
		assertTrue(b.minecraft().isEmpty() && b.cargadores().isEmpty(), "GitHub no dice el Minecraft: se mira en su etiqueta");
		assertEquals(v("0.2.0"), b.version());
	}

	@Test
	void leeModrinth() throws IOException {
		List<Publicacion> ps = Publicaciones.leer(fixture("modrinth.json"));
		// sin la archivada ni la del id raro
		assertEquals(List.of("0.4.0", "0.3.5", "0.3.1", "0.3.0", "0.1.0"), ps.stream().map(p -> p.version().toString()).toList());
		Publicacion beta = ps.get(2), r = ps.get(3);
		assertTrue(beta.prepublicacion(), "version_type beta");
		assertEquals("https://modrinth.com/mod/heRald1a/version/Rel222", r.url());
		assertEquals(List.of("26.3", "26.3.1"), r.minecraft());
		assertEquals(List.of("fabric"), r.cargadores());
	}

	@Test
	void respuestasVaciasORaras() {
		assertEquals(List.of(), Publicaciones.leer("[]"));
		assertEquals(List.of(), Publicaciones.leer("[{}, 1, null, [], {\"tag_name\": 5}]"));
		for (String raro : new String[] {"", "   ", "{\"message\": \"API rate limit exceeded\"}", "<html>502 Bad Gateway</html>",
				"[{\"tag_name\": ", "null", "\"texto\"", "42"}) {
			assertThrows(IllegalArgumentException.class, () -> Publicaciones.leer(raro), raro);
		}
		assertThrows(IllegalArgumentException.class, () -> Publicaciones.leer(null));
	}

	@Test
	void eligeLaMasNuevaDeGitHubParaEsteMinecraft() throws IOException {
		List<Publicacion> ps = Publicaciones.leer(fixture("github.json"));
		List<String> preguntadas = new ArrayList<>();
		Optional<Publicacion> p = Publicaciones.elegir(ps, v("0.1.0"), "26.3", false, mc(Map.of("v0.2.0", "26.3"), preguntadas));
		assertEquals("v0.2.0", p.orElseThrow().etiqueta());
		assertEquals(List.of("v0.2.0"), preguntadas, "la beta no se mira sin prepublicaciones; la actual, nunca");
		// con prepublicaciones, la beta (si es de este Minecraft)
		preguntadas.clear();
		p = Publicaciones.elegir(ps, v("0.1.0"), "26.3", true, mc(Map.of("v0.3.0-beta.1", "26.3", "v0.2.0", "26.3"), preguntadas));
		assertEquals("v0.3.0-beta.1", p.orElseThrow().etiqueta());
		// la beta es para otro Minecraft: sigue con la siguiente
		p = Publicaciones.elegir(ps, v("0.1.0"), "26.3", true, mc(Map.of("v0.3.0-beta.1", "26.4", "v0.2.0", "26.3"), new ArrayList<>()));
		assertEquals("v0.2.0", p.orElseThrow().etiqueta());
		// un servidor en 26.3.1 sirve para una compilada en 26.3
		p = Publicaciones.elegir(ps, v("0.1.0"), "26.3.1", false, mc(Map.of("v0.2.0", "26.3"), new ArrayList<>()));
		assertEquals("v0.2.0", p.orElseThrow().etiqueta());
	}

	@Test
	void sinVersionNuevaOSinSaberSuMinecraftNoSeAvisa() throws IOException {
		List<Publicacion> ps = Publicaciones.leer(fixture("github.json"));
		assertTrue(Publicaciones.elegir(ps, v("0.2.0"), "26.3", false, mc(Map.of("v0.2.0", "26.3"), new ArrayList<>())).isEmpty());
		assertTrue(Publicaciones.elegir(ps, v("0.3.0"), "26.3", true, mc(Map.of(), new ArrayList<>())).isEmpty());
		// no se sabe su Minecraft (sin red para el gradle.properties): no se avisa
		assertTrue(Publicaciones.elegir(ps, v("0.1.0"), "26.3", false, mc(Map.of(), new ArrayList<>())).isEmpty());
		// para otro Minecraft
		assertTrue(Publicaciones.elegir(ps, v("0.1.0"), "26.4", false, mc(Map.of("v0.2.0", "26.3"), new ArrayList<>())).isEmpty());
		assertTrue(Publicaciones.elegir(List.of(), v("0.1.0"), "26.3", true, p -> Optional.of("26.3")).isEmpty());
	}

	@Test
	void comoMuchoTresConsultasDelMinecraft() {
		List<Publicacion> ps = new ArrayList<>();
		for (int i = 2; i <= 9; i++) {
			ps.add(new Publicacion("x", v("0." + i + ".0"), false, "https://x/" + i, "v0." + i + ".0", List.of(), List.of()));
		}
		List<String> preguntadas = new ArrayList<>();
		assertTrue(Publicaciones.elegir(ps, v("0.1.0"), "26.3", false, mc(Map.of("v0.2.0", "26.3"), preguntadas)).isEmpty());
		assertEquals(List.of("v0.9.0", "v0.8.0", "v0.7.0"), preguntadas, "de la más nueva a la más vieja, y no más de tres");
	}

	@Test
	void filtraModrinthPorMinecraftYCargador() throws IOException {
		List<Publicacion> ps = Publicaciones.leer(fixture("modrinth.json"));
		Function<Publicacion, Optional<String>> nunca = p -> {
			throw new AssertionError("Modrinth ya dice su Minecraft");
		};
		// 0.4.0 es de 26.4, 0.3.5 de NeoForge, 0.3.1 beta: queda 0.3.0
		assertEquals("0.3.0", Publicaciones.elegir(ps, v("0.1.0"), "26.3", false, nunca).orElseThrow().version().toString());
		assertEquals("0.3.1", Publicaciones.elegir(ps, v("0.1.0"), "26.3", true, nunca).orElseThrow().version().toString());
		assertEquals("0.3.0", Publicaciones.elegir(ps, v("0.1.0"), "26.3.1", true, nunca).orElseThrow().version().toString());
		assertEquals("0.4.0", Publicaciones.elegir(ps, v("0.1.0"), "26.4", false, nunca).orElseThrow().version().toString());
		assertTrue(Publicaciones.elegir(ps, v("0.3.0"), "26.3", false, nunca).isEmpty());
		assertTrue(Publicaciones.elegir(ps, v("0.1.0"), "26.2", true, nunca).isEmpty());
	}

	@Test
	void minecraftDelGradleProperties() {
		String props = "org.gradle.jvmargs=-Xmx1G\n# comentario\nminecraft_version=26.3\nloader_version=0.20.1\n";
		assertEquals(Optional.of("26.3"), Publicaciones.minecraftDePropiedades(props));
		assertEquals(Optional.of("26.3.1"), Publicaciones.minecraftDePropiedades("minecraft_version = 26.3.1\r\n"));
		String api = "{\"name\":\"gradle.properties\",\"encoding\":\"base64\",\"content\":\""
				+ Base64.getMimeEncoder().encodeToString(props.getBytes(StandardCharsets.UTF_8)) + "\"}";
		assertEquals(Optional.of("26.3"), Publicaciones.minecraftDePropiedades(api), "el JSON de la API de contenidos");
		assertEquals(Optional.empty(), Publicaciones.minecraftDePropiedades(null));
		assertEquals(Optional.empty(), Publicaciones.minecraftDePropiedades(""));
		assertEquals(Optional.empty(), Publicaciones.minecraftDePropiedades("minecraft_version_x=26.3"));
		assertEquals(Optional.empty(), Publicaciones.minecraftDePropiedades("minecraft_version=raro"));
		assertEquals(Optional.empty(), Publicaciones.minecraftDePropiedades("{\"message\":\"Not Found\"}"));
		assertEquals(Optional.empty(), Publicaciones.minecraftDePropiedades("{roto"));
	}
}
