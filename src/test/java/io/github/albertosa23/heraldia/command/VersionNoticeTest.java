package io.github.albertosa23.heraldia.command;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.sun.net.httpserver.HttpServer;
import io.github.albertosa23.heraldia.version.Releases.Release;
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
class VersionNoticeTest {
	private HttpServer http;
	private final Map<String, String> responses = new ConcurrentHashMap<>();
	private final Map<String, Integer> statuses = new ConcurrentHashMap<>();
	private final Map<String, String> agents = new ConcurrentHashMap<>();

	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@BeforeEach
	void start() throws IOException {
		http = HttpServer.create(new InetSocketAddress("127.0.0.1", 0), 0);
		http.createContext("/", ex -> {
			String route = ex.getRequestURI().toString();
			agents.put(route, String.valueOf(ex.getRequestHeaders().getFirst("User-Agent")));
			String body = responses.getOrDefault(route, "{\"message\":\"Not Found\"}");
			byte[] b = body.getBytes(StandardCharsets.UTF_8);
			ex.sendResponseHeaders(statuses.getOrDefault(route, responses.containsKey(route) ? 200 : 404), b.length);
			try (OutputStream o = ex.getResponseBody()) {
				o.write(b);
			}
		});
		http.start();
	}

	@AfterEach
	void stop() {
		http.stop(0);
	}

	private String base() {
		return "http://127.0.0.1:" + http.getAddress().getPort() + "/repos/AlbertoSA23/HERALDIA";
	}

	private static String fixture(String name) throws IOException {
		try (InputStream in = VersionNoticeTest.class.getResourceAsStream("/version/" + name)) {
			return new String(in.readAllBytes(), StandardCharsets.UTF_8);
		}
	}

	@Test
	void gradlePropertiesUrlOfATag() {
		assertEquals("https://api.github.com/repos/AlbertoSA23/HERALDIA/contents/gradle.properties?ref=v0.2.0",
				VersionNotice.properties(VersionNotice.URL, "v0.2.0"));
		assertEquals("http://h/repos/a/b/contents/gradle.properties?ref=v1.0.0-beta%2B1", VersionNotice.properties("http://h/repos/a/b/releases", "v1.0.0-beta+1"));
		assertNull(VersionNotice.properties("https://api.modrinth.com/v2/project/x/version", "0.2.0"));
		assertNull(VersionNotice.properties(VersionNotice.URL, ""));
	}

	@Test
	void queriesGitHubWithItsMinecraft() throws Exception {
		responses.put("/repos/AlbertoSA23/HERALDIA/releases", fixture("github.json"));
		responses.put("/repos/AlbertoSA23/HERALDIA/contents/gradle.properties?ref=v0.2.0", "mod_version=0.2.0\nminecraft_version=26.3\n");
		Optional<Release> p = VersionNotice.query(base() + "/releases", Version.of("0.1.0").orElseThrow(), "26.3", false);
		assertEquals("v0.2.0", p.orElseThrow().tag());
		assertEquals(VersionNotice.USER_AGENT, agents.get("/repos/AlbertoSA23/HERALDIA/releases"), "User-Agent genérico");
		assertTrue(VersionNotice.query(base() + "/releases", Version.of("0.1.0").orElseThrow(), "26.4", false).isEmpty());
		assertTrue(VersionNotice.query(base() + "/releases", Version.of("0.2.0").orElseThrow(), "26.3", false).isEmpty());
	}

	@Test
	void queriesModrinth() throws Exception {
		responses.put("/v2/project/heraldia/version", fixture("modrinth.json"));
		String url = "http://127.0.0.1:" + http.getAddress().getPort() + "/v2/project/heraldia/version";
		assertEquals("0.3.0", VersionNotice.query(url, Version.of("0.1.0").orElseThrow(), "26.3", false).orElseThrow().version().toString());
	}

	@Test
	void noGradlePropertiesNoNotice() throws Exception {
		responses.put("/repos/AlbertoSA23/HERALDIA/releases", fixture("github.json"));
		assertTrue(VersionNotice.query(base() + "/releases", Version.of("0.1.0").orElseThrow(), "26.3", true).isEmpty());
	}

	@Test
	void networkErrorsAndOddResponses() throws Exception {
		Version v = Version.of("0.1.0").orElseThrow();
		statuses.put("/repos/AlbertoSA23/HERALDIA/releases", 403);
		responses.put("/repos/AlbertoSA23/HERALDIA/releases", "{\"message\":\"API rate limit exceeded\"}");
		IOException e = assertThrows(IOException.class, () -> VersionNotice.query(base() + "/releases", v, "26.3", false));
		assertTrue(e.getMessage().contains("403"));
		statuses.remove("/repos/AlbertoSA23/HERALDIA/releases");
		responses.put("/repos/AlbertoSA23/HERALDIA/releases", "<html>no</html>");
		assertThrows(IllegalArgumentException.class, () -> VersionNotice.query(base() + "/releases", v, "26.3", false));
		responses.put("/repos/AlbertoSA23/HERALDIA/releases", "x".repeat(VersionNotice.MAX_BYTES + 10));
		assertThrows(IOException.class, () -> VersionNotice.query(base() + "/releases", v, "26.3", false));
		// nadie escucha en el puerto: falla enseguida, sin colgarse
		int free;
		try (ServerSocket s = new ServerSocket(0)) {
			free = s.getLocalPort();
		}
		long t0 = System.nanoTime();
		assertThrows(IOException.class, () -> VersionNotice.query("http://127.0.0.1:" + free + "/repos/a/b/releases", v, "26.3", false));
		assertTrue((System.nanoTime() - t0) / 1_000_000 < VersionNotice.CONNECTION.toMillis() + 2000);
	}

	@Test
	void messageHasLinkAndBackup() {
		Release p = new Release("Heraldia 0.2.0", Version.of("0.2.0").orElseThrow(), false,
				"https://github.com/AlbertoSA23/HERALDIA/releases/tag/v0.2.0", "v0.2.0", List.of(), List.of());
		for (String language : Texts.languages()) {
			List<Component> m = VersionNotice.message(p, "0.1.0", "26.3", Texts.language(language));
			assertEquals(2, m.size());
			TranslatableContents fresh = assertInstanceOf(TranslatableContents.class, m.get(0).getContents());
			assertEquals("heraldia.version.nueva", fresh.getKey());
			assertTrue(fresh.getFallback() != null && fresh.getFallback().contains("%s"), language);
			Component link = m.get(0).getSiblings().get(1);
			ClickEvent.OpenUrl open = assertInstanceOf(ClickEvent.OpenUrl.class, link.getStyle().getClickEvent());
			assertEquals(p.url(), open.uri().toString());
			TranslatableContents backup = assertInstanceOf(TranslatableContents.class, m.get(1).getContents());
			assertEquals("heraldia.version.copia", backup.getKey());
			assertTrue(backup.getFallback().contains("config"), language);
		}
	}
}
