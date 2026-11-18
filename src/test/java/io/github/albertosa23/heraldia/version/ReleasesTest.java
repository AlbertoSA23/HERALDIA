package io.github.albertosa23.heraldia.version;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.version.Releases.Release;
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

/** GitHub Releases and Modrinth responses (fixtures in src/test/resources/version) and the choice of the new version. */
class ReleasesTest {
	private static String fixture(String name) throws IOException {
		try (InputStream in = ReleasesTest.class.getResourceAsStream("/version/" + name)) {
			return new String(in.readAllBytes(), StandardCharsets.UTF_8);
		}
	}

	private static Version v(String s) {
		return Version.of(s).orElseThrow();
	}

	/** The Minecraft of each GitHub tag, as the gradle.properties would give it; records which ones are asked. */
	private static Function<Release, Optional<String>> mc(Map<String, String> byTag, List<String> asked) {
		return p -> {
			asked.add(p.tag());
			return Optional.ofNullable(byTag.get(p.tag()));
		};
	}

	@Test
	void readsGitHub() throws IOException {
		List<Release> ps = Releases.read(fixture("github.json"));
		// without the draft, the one without a .jar (notes only), the tag that is not a version, the link that is not web and what is not an object
		assertEquals(List.of("v0.3.0-beta.1", "v0.2.0", "v0.1.0"), ps.stream().map(Release::tag).toList());
		Release beta = ps.get(0), b = ps.get(1);
		assertTrue(beta.prerelease());
		assertEquals("Heraldia 0.2.0", b.name());
		assertEquals("https://github.com/Stufanplay/HERALDIA/releases/tag/v0.2.0", b.url());
		assertTrue(b.minecraft().isEmpty() && b.loaders().isEmpty(), "GitHub no dice el Minecraft: se mira en su etiqueta");
		assertEquals(v("0.2.0"), b.version());
	}

	@Test
	void readsModrinth() throws IOException {
		List<Release> ps = Releases.read(fixture("modrinth.json"));
		// without the archived one or the one with the odd id
		assertEquals(List.of("0.4.0", "0.3.5", "0.3.1", "0.3.0", "0.1.0"), ps.stream().map(p -> p.version().toString()).toList());
		Release beta = ps.get(2), r = ps.get(3);
		assertTrue(beta.prerelease(), "version_type beta");
		assertEquals("https://modrinth.com/mod/heRald1a/version/Rel222", r.url());
		assertEquals(List.of("26.3", "26.3.1"), r.minecraft());
		assertEquals(List.of("fabric"), r.loaders());
	}

	@Test
	void emptyOrOddResponses() {
		assertEquals(List.of(), Releases.read("[]"));
		assertEquals(List.of(), Releases.read("[{}, 1, null, [], {\"tag_name\": 5}]"));
		for (String odd : new String[] {"", "   ", "{\"message\": \"API rate limit exceeded\"}", "<html>502 Bad Gateway</html>",
				"[{\"tag_name\": ", "null", "\"texto\"", "42"}) {
			assertThrows(IllegalArgumentException.class, () -> Releases.read(odd), odd);
		}
		assertThrows(IllegalArgumentException.class, () -> Releases.read(null));
	}

	@Test
	void picksNewestGitHubForThisMinecraft() throws IOException {
		List<Release> ps = Releases.read(fixture("github.json"));
		List<String> asked = new ArrayList<>();
		Optional<Release> p = Releases.choose(ps, v("0.1.0"), "26.3", false, mc(Map.of("v0.2.0", "26.3"), asked));
		assertEquals("v0.2.0", p.orElseThrow().tag());
		assertEquals(List.of("v0.2.0"), asked, "la beta no se mira sin prepublicaciones; la actual, nunca");
		// with prereleases, the beta (if it is for this Minecraft)
		asked.clear();
		p = Releases.choose(ps, v("0.1.0"), "26.3", true, mc(Map.of("v0.3.0-beta.1", "26.3", "v0.2.0", "26.3"), asked));
		assertEquals("v0.3.0-beta.1", p.orElseThrow().tag());
		// the beta is for another Minecraft: it goes on with the next one
		p = Releases.choose(ps, v("0.1.0"), "26.3", true, mc(Map.of("v0.3.0-beta.1", "26.4", "v0.2.0", "26.3"), new ArrayList<>()));
		assertEquals("v0.2.0", p.orElseThrow().tag());
		// a server on 26.3.1 works with one compiled for 26.3
		p = Releases.choose(ps, v("0.1.0"), "26.3.1", false, mc(Map.of("v0.2.0", "26.3"), new ArrayList<>()));
		assertEquals("v0.2.0", p.orElseThrow().tag());
	}

	@Test
	void noNewVersionOrUnknownMinecraftNoNotice() throws IOException {
		List<Release> ps = Releases.read(fixture("github.json"));
		assertTrue(Releases.choose(ps, v("0.2.0"), "26.3", false, mc(Map.of("v0.2.0", "26.3"), new ArrayList<>())).isEmpty());
		assertTrue(Releases.choose(ps, v("0.3.0"), "26.3", true, mc(Map.of(), new ArrayList<>())).isEmpty());
		// its Minecraft is unknown (no network for the gradle.properties): no notice
		assertTrue(Releases.choose(ps, v("0.1.0"), "26.3", false, mc(Map.of(), new ArrayList<>())).isEmpty());
		// for another Minecraft
		assertTrue(Releases.choose(ps, v("0.1.0"), "26.4", false, mc(Map.of("v0.2.0", "26.3"), new ArrayList<>())).isEmpty());
		assertTrue(Releases.choose(List.of(), v("0.1.0"), "26.3", true, p -> Optional.of("26.3")).isEmpty());
	}

	@Test
	void atMostThreeMinecraftQueries() {
		List<Release> ps = new ArrayList<>();
		for (int i = 2; i <= 9; i++) {
			ps.add(new Release("x", v("0." + i + ".0"), false, "https://x/" + i, "v0." + i + ".0", List.of(), List.of()));
		}
		List<String> asked = new ArrayList<>();
		assertTrue(Releases.choose(ps, v("0.1.0"), "26.3", false, mc(Map.of("v0.2.0", "26.3"), asked)).isEmpty());
		assertEquals(List.of("v0.9.0", "v0.8.0", "v0.7.0"), asked, "de la más nueva a la más vieja, y no más de tres");
	}

	@Test
	void filtersModrinthByMinecraftAndLoader() throws IOException {
		List<Release> ps = Releases.read(fixture("modrinth.json"));
		Function<Release, Optional<String>> never = p -> {
			throw new AssertionError("Modrinth ya dice su Minecraft");
		};
		// 0.4.0 is for 26.4, 0.3.5 for NeoForge, 0.3.1 is a beta: 0.3.0 remains
		assertEquals("0.3.0", Releases.choose(ps, v("0.1.0"), "26.3", false, never).orElseThrow().version().toString());
		assertEquals("0.3.1", Releases.choose(ps, v("0.1.0"), "26.3", true, never).orElseThrow().version().toString());
		assertEquals("0.3.0", Releases.choose(ps, v("0.1.0"), "26.3.1", true, never).orElseThrow().version().toString());
		assertEquals("0.4.0", Releases.choose(ps, v("0.1.0"), "26.4", false, never).orElseThrow().version().toString());
		assertTrue(Releases.choose(ps, v("0.3.0"), "26.3", false, never).isEmpty());
		assertTrue(Releases.choose(ps, v("0.1.0"), "26.2", true, never).isEmpty());
	}

	@Test
	void minecraftFromGradleProperties() {
		String props = "org.gradle.jvmargs=-Xmx1G\n# comentario\nminecraft_version=26.3\nloader_version=0.20.1\n";
		assertEquals(Optional.of("26.3"), Releases.minecraftFromProperties(props));
		assertEquals(Optional.of("26.3.1"), Releases.minecraftFromProperties("minecraft_version = 26.3.1\r\n"));
		String api = "{\"name\":\"gradle.properties\",\"encoding\":\"base64\",\"content\":\""
				+ Base64.getMimeEncoder().encodeToString(props.getBytes(StandardCharsets.UTF_8)) + "\"}";
		assertEquals(Optional.of("26.3"), Releases.minecraftFromProperties(api), "el JSON de la API de contenidos");
		assertEquals(Optional.empty(), Releases.minecraftFromProperties(null));
		assertEquals(Optional.empty(), Releases.minecraftFromProperties(""));
		assertEquals(Optional.empty(), Releases.minecraftFromProperties("minecraft_version_x=26.3"));
		assertEquals(Optional.empty(), Releases.minecraftFromProperties("minecraft_version=raro"));
		assertEquals(Optional.empty(), Releases.minecraftFromProperties("{\"message\":\"Not Found\"}"));
		assertEquals(Optional.empty(), Releases.minecraftFromProperties("{roto"));
	}
}
