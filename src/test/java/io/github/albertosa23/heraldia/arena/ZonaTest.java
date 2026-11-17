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
class ZonaTest {
	static final String JSON = """
			{"version": 1, "plantilla": "heraldia:arena/arena", "tamano": [57, 14, 57], "suelo": 7, "centro": [28, 1, 28],
			 "radio_ruedo": 14, "ruedo_y": [1, 10], "puntos": [[39, 1, 28], [17, 1, 28]], "campana": [28, 1, 39],
			 "puerta": [[27, 1, 42], [29, 3, 43]], "reaparicion": [28, 8, 54], "jefes": 4}
			""";

	static Plano plano() {
		return Plano.leer(new StringReader(JSON));
	}

	@Test
	void leePlano() {
		Plano p = plano();
		assertEquals("heraldia:arena/arena", p.plantilla());
		assertArrayEquals(new int[] {57, 14, 57}, p.tamano());
		assertEquals(2, p.puntos().size());
		assertArrayEquals(new int[] {29, 3, 43}, p.puerta()[1]);
		assertEquals(4, p.jefes());
	}

	@Test
	void cajaDeProteccion() {
		Zona z = Zona.centrada(300, -100, 70, plano());
		assertEquals(272, z.minX());
		assertEquals(328, z.maxX());
		assertEquals(63, z.minY());
		assertEquals(76, z.maxY());
		assertEquals(-128, z.minZ());
		assertEquals(-72, z.maxZ());
		assertEquals(70, z.sueloY());
		assertTrue(z.contiene(272, 63, -128));
		assertTrue(z.contiene(328, 76, -72));
		assertTrue(z.contiene(300, 70, -100));
		assertFalse(z.contiene(271, 70, -100));
		assertFalse(z.contiene(329, 70, -100));
		assertFalse(z.contiene(300, 62, -100));
		assertFalse(z.contiene(300, 77, -100));
		assertFalse(z.contiene(300, 70, -129));
		assertFalse(z.contiene(300, 70, -71));
		assertTrue(z.cerca(270, 70, -100, 2));
		assertFalse(z.cerca(269, 70, -100, 2));
	}

	@Test
	void cubosNegadosJuntoALaArenaSalvoAOperadores() {
		Zona z = Zona.centrada(300, -100, 70, plano());     // caja x 272..328, como en el test de la caja
		assertTrue(z.cuboNegado(300, 70, -100, false), "dentro");
		assertTrue(z.cuboNegado(272 - Zona.RADIO_CUBOS, 70, -100, false), "un dispensador pegado por fuera, a 6 bloques");
		assertFalse(z.cuboNegado(271 - Zona.RADIO_CUBOS, 70, -100, false), "más lejos, sí se puede");
		assertFalse(z.cuboNegado(300, 70, -100, true), "un operador puede");
	}

	@Test
	void permisosOperadorSiNoOperadorNo() {
		Zona z = Zona.centrada(0, 0, 64, plano());
		assertTrue(z.protegido(0, 64, 0, false), "un jugador normal no puede tocarla");
		assertFalse(z.protegido(0, 64, 0, true), "un operador sí");
		assertFalse(z.protegido(100, 64, 0, false), "fuera de la caja no se protege nada");
		assertFalse(z.protegido(0, 100, 0, false), "por encima de la caja tampoco");
	}

	@Test
	void ruedo() {
		Zona z = Zona.centrada(0, 0, 64, plano());
		// el suelo del ruedo está 7 bloques bajo el exterior: los pies, a y = 58
		assertEquals(57, z.minY());
		assertTrue(z.enRuedo(0.5, 58, 0.5));
		assertTrue(z.enRuedo(13.0, 58, 0.5));
		assertTrue(z.enRuedo(14.6, 58, 0.5), "pegado al muro sigue en el ruedo");
		assertFalse(z.enRuedo(16.5, 58, 0.5), "en las gradas, fuera");
		assertFalse(z.enRuedo(0.5, 69, 0.5), "sobre el techo de barreras");
		assertFalse(z.enRuedo(0.5, 56, 0.5), "bajo el suelo");
		assertArrayEquals(new int[] {0, 58, 11}, z.campana());
		assertTrue(z.esCampana(0, 58, 11));
		assertFalse(z.esCampana(0, 58, 12));
		assertArrayEquals(new int[] {11, 58, 0}, z.punto(0));
		assertArrayEquals(new int[] {11, 58, 0}, z.punto(2), "los puntos se reparten en rueda");
		assertArrayEquals(new int[] {0, 65, 26}, z.reaparicion());
		assertFalse(z.enRuedo(0.5, 65, 26.5), "la reaparición está fuera del ruedo");
	}

	@Test
	void planoGenerado() throws IOException {
		String gen = System.getProperty("heraldia.generated");
		Path f = gen == null ? null : Path.of(gen, "heraldia", "arena.json");
		if (f == null || !Files.isRegularFile(f)) {
			return;      // sin generar (p. ej. ./gradlew test sin generateStructures): lo cubre el JSON de arriba
		}
		Plano p;
		try (Reader r = Files.newBufferedReader(f, StandardCharsets.UTF_8)) {
			p = Plano.leer(r);
		}
		Zona z = Zona.centrada(0, 0, 64, p);
		assertTrue(p.puntos().size() >= 4);
		for (int i = 0; i < p.puntos().size(); i++) {
			int[] q = z.punto(i);
			assertTrue(z.enRuedo(q[0] + 0.5, q[1], q[2] + 0.5), "punto " + i + " fuera del ruedo");
		}
		int[] c = z.campana();
		assertTrue(z.enRuedo(c[0] + 0.5, c[1], c[2] + 0.5), "la campana fuera del ruedo");
		int[] r = z.reaparicion();
		assertFalse(z.enRuedo(r[0] + 0.5, r[1], r[2] + 0.5));
		assertTrue(z.contiene(r[0], r[1], r[2]));
		assertTrue(z.contiene(z.puertaMin()[0], z.puertaMin()[1], z.puertaMin()[2]));
		assertTrue(z.contiene(z.puertaMax()[0], z.puertaMax()[1], z.puertaMax()[2]));
	}
}
