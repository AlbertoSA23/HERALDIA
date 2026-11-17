package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.sun.net.httpserver.HttpServer;
import io.github.albertosa23.heraldia.version.Publicaciones.Publicacion;
import io.github.albertosa23.heraldia.version.Version;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;
import java.net.InetSocketAddress;
import java.net.ServerSocket;
import java.nio.charset.StandardCharsets;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.concurrent.ConcurrentHashMap;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;

/** La consulta de verdad por HTTP contra un servidor local (como la API de GitHub) y el mensaje del aviso. */
class AvisoVersionTest {
	private HttpServer http;
	private final Map<String, String> respuestas = new ConcurrentHashMap<>();
	private final Map<String, Integer> estados = new ConcurrentHashMap<>();
	private final Map<String, String> agentes = new ConcurrentHashMap<>();

	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@BeforeEach
	void arrancar() throws IOException {
		http = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
		http.createContext("/", ex -> {
			String ruta = ex.getRequestURI().toString();
			agentes.put(ruta, String.valueOf(ex.getRequestHeaders().getFirst("User-Agent")));
			String cuerpo = respuestas.getOrDefault(ruta, "{\"message\":\"Not Found\"}");
			byte[] b = cuerpo.getBytes(StandardCharsets.UTF_8);
			ex.sendResponseHeaders(estados.getOrDefault(ruta, respuestas.containsKey(ruta) ? 200 : 404), b.length);
			try (OutputStream o = ex.getResponseBody()) {
				o.write(b);
			}
		});
		http.start();
	}

	@AfterEach
	void parar() {
		http.stop(0);
	}

	private String base() {
		return "http://127.0.0.1:" + http.getAddress().getPort() + "/repos/AlbertoSA23/HERALDIA";
	}

	private static String fixture(String nombre) throws IOException {
		try (InputStream in = AvisoVersionTest.class.getResourceAsStream("/version/" + nombre)) {
			return new String(in.readAllBytes(), StandardCharsets.UTF_8);
		}
	}

	@Test
	void direccionDelGradlePropertiesDeUnaEtiqueta() {
		assertEquals("https://api.github.com/repos/AlbertoSA23/HERALDIA/contents/gradle.properties?ref=v0.2.0",
				AvisoVersion.propiedades(AvisoVersion.URL, "v0.2.0"));
		assertEquals("http://h/repos/a/b/contents/gradle.properties?ref=v1.0.0-beta%2B1", AvisoVersion.propiedades("http://h/repos/a/b/releases", "v1.0.0-beta+1"));
		assertNull(AvisoVersion.propiedades("https://api.modrinth.com/v2/project/x/version", "0.2.0"));
		assertNull(AvisoVersion.propiedades(AvisoVersion.URL, ""));
	}

	@Test
	void consultaGitHubConSuMinecraft() throws Exception {
		respuestas.put("/repos/AlbertoSA23/HERALDIA/releases", fixture("github.json"));
		respuestas.put("/repos/AlbertoSA23/HERALDIA/contents/gradle.properties?ref=v0.2.0", "mod_version=0.2.0\nminecraft_version=26.3\n");
		Optional<Publicacion> p = AvisoVersion.consultar(base() + "/releases", Version.de("0.1.0").orElseThrow(), "26.3", false);
		assertEquals("v0.2.0", p.orElseThrow().etiqueta());
		assertEquals(AvisoVersion.USER_AGENT, agentes.get("/repos/AlbertoSA23/HERALDIA/releases"), "User-Agent genérico");
		assertTrue(AvisoVersion.consultar(base() + "/releases", Version.de("0.1.0").orElseThrow(), "26.4", false).isEmpty());
		assertTrue(AvisoVersion.consultar(base() + "/releases", Version.de("0.2.0").orElseThrow(), "26.3", false).isEmpty());
	}

	@Test
	void consultaModrinth() throws Exception {
		respuestas.put("/v2/project/heraldia/version", fixture("modrinth.json"));
		String url = "http://127.0.0.1:" + http.getAddress().getPort() + "/v2/project/heraldia/version";
		assertEquals("0.3.0", AvisoVersion.consultar(url, Version.de("0.1.0").orElseThrow(), "26.3", false).orElseThrow().version().toString());
	}

	@Test
	void sinGradlePropertiesNoSeAvisa() throws Exception {
		respuestas.put("/repos/AlbertoSA23/HERALDIA/releases", fixture("github.json"));
		assertTrue(AvisoVersion.consultar(base() + "/releases", Version.de("0.1.0").orElseThrow(), "26.3", true).isEmpty());
	}

	@Test
	void erroresDeRedYRespuestasRaras() throws Exception {
		Version v = Version.de("0.1.0").orElseThrow();
		estados.put("/repos/AlbertoSA23/HERALDIA/releases", 403);
		respuestas.put("/repos/AlbertoSA23/HERALDIA/releases", "{\"message\":\"API rate limit exceeded\"}");
		IOException e = assertThrows(IOException.class, () -> AvisoVersion.consultar(base() + "/releases", v, "26.3", false));
		assertTrue(e.getMessage().contains("403"));
		estados.remove("/repos/AlbertoSA23/HERALDIA/releases");
		respuestas.put("/repos/AlbertoSA23/HERALDIA/releases", "<html>no</html>");
		assertThrows(IllegalArgumentException.class, () -> AvisoVersion.consultar(base() + "/releases", v, "26.3", false));
		respuestas.put("/repos/AlbertoSA23/HERALDIA/releases", "x".repeat(AvisoVersion.MAX_BYTES + 10));
		assertThrows(IOException.class, () -> AvisoVersion.consultar(base() + "/releases", v, "26.3", false));
		// nadie escucha en el puerto: falla enseguida, sin colgarse
		int libre;
		try (ServerSocket s = new ServerSocket(0)) {
			libre = s.getLocalPort();
		}
		long t0 = System.nanoTime();
		assertThrows(IOException.class, () -> AvisoVersion.consultar("http://127.0.0.1:" + libre + "/repos/a/b/releases", v, "26.3", false));
		assertTrue((System.nanoTime() - t0) / 1_000_000 < AvisoVersion.CONEXION.toMillis() + 2000);
	}

	@Test
	void elMensajeLlevaElEnlaceYLaCopiaDeSeguridad() {
		Publicacion p = new Publicacion("Heraldia 0.2.0", Version.de("0.2.0").orElseThrow(), false,
				"https://github.com/AlbertoSA23/HERALDIA/releases/tag/v0.2.0", "v0.2.0", List.of(), List.of());
		for (String idioma : Textos.idiomas()) {
			List<Component> m = AvisoVersion.mensaje(p, "0.1.0", "26.3", Textos.idioma(idioma));
			assertEquals(2, m.size());
			TranslatableContents nueva = assertInstanceOf(TranslatableContents.class, m.get(0).getContents());
			assertEquals("heraldia.version.nueva", nueva.getKey());
			assertTrue(nueva.getFallback() != null && nueva.getFallback().contains("%s"), idioma);
			Component enlace = m.get(0).getSiblings().get(1);
			ClickEvent.OpenUrl abrir = assertInstanceOf(ClickEvent.OpenUrl.class, enlace.getStyle().getClickEvent());
			assertEquals(p.url(), abrir.uri().toString());
			TranslatableContents copia = assertInstanceOf(TranslatableContents.class, m.get(1).getContents());
			assertEquals("heraldia.version.copia", copia.getKey());
			assertTrue(copia.getFallback().contains("config"), idioma);
		}
	}
}
