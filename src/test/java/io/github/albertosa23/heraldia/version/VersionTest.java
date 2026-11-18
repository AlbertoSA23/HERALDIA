package io.github.albertosa23.heraldia.version;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;
import org.junit.jupiter.api.Test;

/** Semantic version comparison and Minecraft's "~" rule (pure logic). */
class VersionTest {
	private static Version v(String s) {
		return Version.of(s).orElseThrow(() -> new AssertionError("no es versión: " + s));
	}

	@Test
	void readsVersions() {
		assertEquals(List.of(0, 1, 0), v("0.1.0").numbers());
		assertEquals(List.of(0, 1, 0), v("v0.1.0").numbers());
		assertEquals(List.of(26, 3), v("26.3").numbers());
		assertEquals(List.of("beta", "1"), v("1.2.0-beta.1").pre());
		assertEquals(List.of(0, 2, 0), v("0.2.0+26.3").numbers());
		assertTrue(v("0.2.0+26.3").pre().isEmpty());
		assertEquals("1.2.0-rc.2", v("V1.2.0-RC.2").toString());
	}

	@Test
	void rejectsNonVersions() {
		for (String s : new String[] {null, "", "v", "nightly", "1..2", "1.2.", ".1", "1.2.3.4.5", "1.x", "1.2-", "1.2-beta..1",
				"1.2-be ta", "9999999999.0", "${version}", "-1.0"}) {
			assertTrue(Version.of(s).isEmpty(), String.valueOf(s));
		}
	}

	@Test
	void semverOrder() {
		List<String> order = List.of("0.1.0", "0.1.1", "0.2.0-alpha", "0.2.0-alpha.1", "0.2.0-alpha.beta", "0.2.0-beta",
				"0.2.0-beta.2", "0.2.0-beta.11", "0.2.0-rc.1", "0.2.0", "0.10.0", "1.0.0");
		List<Version> vs = new ArrayList<>(order.stream().map(VersionTest::v).toList());
		Collections.shuffle(vs, new java.util.Random(7));
		Collections.sort(vs);
		assertEquals(order, vs.stream().map(Version::toString).toList());
		assertEquals(0, v("1.0").compareTo(v("1.0.0")));
		assertEquals(0, v("v0.2.0").compareTo(v("0.2.0+build.5")));
		assertTrue(v("0.10.0").compareTo(v("0.9.9")) > 0, "por número, no por texto");
		assertTrue(v("0.2.0").prerelease() == false && v("0.2.0-beta").prerelease());
	}

	@Test
	void sameMinecraftLikeFabricTilde() {
		assertTrue(Version.sameMinecraft("26.3", "26.3"));
		assertTrue(Version.sameMinecraft("26.3", "26.3.1"));
		assertTrue(Version.sameMinecraft("26.3.1", "26.3.2"));
		assertFalse(Version.sameMinecraft("26.3.1", "26.3"), "compilada para una revisión posterior a la del servidor");
		assertFalse(Version.sameMinecraft("26.4", "26.3"));
		assertFalse(Version.sameMinecraft("26.3", "26.4"));
		assertFalse(Version.sameMinecraft("27.3", "26.3"));
		assertFalse(Version.sameMinecraft("raro", "26.3"));
		assertFalse(Version.sameMinecraft("26.3", null));
	}
}
