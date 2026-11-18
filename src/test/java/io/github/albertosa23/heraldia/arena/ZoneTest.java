package io.github.albertosa23.heraldia.arena;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import org.junit.jupiter.api.Test;

/** Plano (arena.json), caja de protección (AABB) y permisos, y el ruedo. */
class ZoneTest {
	static final String JSON = """
			{"version": 1, "plantilla": "heraldia:arena/arena", "tamano": [57, 14, 57], "suelo": 7, "centro": [28, 1, 28],
			 "radio_ruedo": 14, "ruedo_y": [1, 10], "puntos": [[39, 1, 28], [17, 1, 28]], "campana": [28, 1, 39],
			 "puerta": [[27, 1, 42], [29, 3, 43]], "reaparicion": [28, 8, 54], "jefes": 4}
			""";

	static Blueprint plan() {
		return Blueprint.read(new StringReader(JSON));
	}

	@Test
	void readsPlan() {
		Blueprint p = plan();
		assertEquals("heraldia:arena/arena", p.template());
		assertArrayEquals(new int[] {57, 14, 57}, p.size());
		assertEquals(2, p.points().size());
		assertArrayEquals(new int[] {29, 3, 43}, p.gate()[1]);
		assertEquals(4, p.bosses());
	}

	@Test
	void protectionBox() {
		Zone z = Zone.centered(300, -100, 70, plan());
		assertEquals(272, z.minX());
		assertEquals(328, z.maxX());
		assertEquals(63, z.minY());
		assertEquals(76, z.maxY());
		assertEquals(-128, z.minZ());
		assertEquals(-72, z.maxZ());
		assertEquals(70, z.groundY());
		assertTrue(z.mentions(272, 63, -128));
		assertTrue(z.mentions(328, 76, -72));
		assertTrue(z.mentions(300, 70, -100));
		assertFalse(z.mentions(271, 70, -100));
		assertFalse(z.mentions(329, 70, -100));
		assertFalse(z.mentions(300, 62, -100));
		assertFalse(z.mentions(300, 77, -100));
		assertFalse(z.mentions(300, 70, -129));
		assertFalse(z.mentions(300, 70, -71));
		assertTrue(z.near(270, 70, -100, 2));
		assertFalse(z.near(269, 70, -100, 2));
	}

	@Test
	void bucketsDeniedNearArenaExceptOperators() {
		Zone z = Zone.centered(300, -100, 70, plan());     // caja x 272..328, como en el test de la caja
		assertTrue(z.bucketDenied(300, 70, -100, false), "dentro");
		assertTrue(z.bucketDenied(272 - Zone.BUCKET_RADIUS, 70, -100, false), "un dispensador pegado por fuera, a 6 bloques");
		assertFalse(z.bucketDenied(271 - Zone.BUCKET_RADIUS, 70, -100, false), "más lejos, sí se puede");
		assertFalse(z.bucketDenied(300, 70, -100, true), "un operador puede");
	}

	@Test
	void permissionsOperatorYesNonOperatorNo() {
		Zone z = Zone.centered(0, 0, 64, plan());
		assertTrue(z.isProtected(0, 64, 0, false), "un jugador normal no puede tocarla");
		assertFalse(z.isProtected(0, 64, 0, true), "un operador sí");
		assertFalse(z.isProtected(100, 64, 0, false), "fuera de la caja no se protege nada");
		assertFalse(z.isProtected(0, 100, 0, false), "por encima de la caja tampoco");
	}

	@Test
	void ring() {
		Zone z = Zone.centered(0, 0, 64, plan());
		// el suelo del ruedo está 7 bloques bajo el exterior: los pies, a y = 58
		assertEquals(57, z.minY());
		assertTrue(z.inRing(0.5, 58, 0.5));
		assertTrue(z.inRing(13.0, 58, 0.5));
		assertTrue(z.inRing(14.6, 58, 0.5), "pegado al muro sigue en el ruedo");
		assertFalse(z.inRing(16.5, 58, 0.5), "en las gradas, fuera");
		assertFalse(z.inRing(0.5, 69, 0.5), "sobre el techo de barreras");
		assertFalse(z.inRing(0.5, 56, 0.5), "bajo el suelo");
		assertArrayEquals(new int[] {0, 58, 11}, z.bell());
		assertTrue(z.isBell(0, 58, 11));
		assertFalse(z.isBell(0, 58, 12));
		assertArrayEquals(new int[] {11, 58, 0}, z.point(0));
		assertArrayEquals(new int[] {11, 58, 0}, z.point(2), "los puntos se reparten en rueda");
		assertArrayEquals(new int[] {0, 65, 26}, z.respawn());
		assertFalse(z.inRing(0.5, 65, 26.5), "la reaparición está fuera del ruedo");
	}

	@Test
	void generatedPlan() throws IOException {
		String gen = System.getProperty("heraldia.generated");
		Path f = gen == null ? null : Path.of(gen, "heraldia", "arena.json");
		if (f == null || !Files.isRegularFile(f)) {
			return;      // sin generar (p. ej. ./gradlew test sin generateStructures): lo cubre el JSON de arriba
		}
		Blueprint p;
		try (Reader r = Files.newBufferedReader(f, StandardCharsets.UTF_8)) {
			p = Blueprint.read(r);
		}
		Zone z = Zone.centered(0, 0, 64, p);
		assertTrue(p.points().size() >= 4);
		for (int i = 0; i < p.points().size(); i++) {
			int[] q = z.point(i);
			assertTrue(z.inRing(q[0] + 0.5, q[1], q[2] + 0.5), "punto " + i + " fuera del ruedo");
		}
		int[] c = z.bell();
		assertTrue(z.inRing(c[0] + 0.5, c[1], c[2] + 0.5), "la campana fuera del ruedo");
		int[] r = z.respawn();
		assertFalse(z.inRing(r[0] + 0.5, r[1], r[2] + 0.5));
		assertTrue(z.mentions(r[0], r[1], r[2]));
		assertTrue(z.mentions(z.gateMin()[0], z.gateMin()[1], z.gateMin()[2]));
		assertTrue(z.mentions(z.gateMax()[0], z.gateMax()[1], z.gateMax()[2]));
	}
}
