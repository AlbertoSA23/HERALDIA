package io.github.albertosa23.heraldia.encargos;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import org.junit.jupiter.api.Test;

/** Cuándo se cumple cada tipo de objetivo. */
class ObjetivosTest {
	static Encargo de(Tipo t, String objetivo, int cantidad, int x, int z) {
		return new Encargo(1, 2, 0, 0, t, objetivo, cantidad, x, z, 3, 20);
	}

	@Test
	void guardianDeLaUnicaPedidaYCerca() {
		Encargo e = de(Tipo.GUARDIAN, "castillo", 0, 1000, -500);
		assertTrue(Objetivos.guardian(e, "castillo", 1000, -500));
		assertTrue(Objetivos.guardian(e, "castillo", 1000 + Objetivos.RADIO_GUARDIAN, -500));
		assertFalse(Objetivos.guardian(e, "castillo", 1000 + Objetivos.RADIO_GUARDIAN + 1, -500), "otro castillo, lejos");
		assertFalse(Objetivos.guardian(e, "catedral", 1000, -500), "otra única");
		assertFalse(Objetivos.guardian(de(Tipo.EXPLORAR, "castillo", 0, 1000, -500), "castillo", 1000, -500), "no es de guardián");
	}

	@Test
	void llegarAUnLugarOAUnaAldea() {
		Encargo lugar = de(Tipo.EXPLORAR, "heraldia:medianas/posada/llanuras", 0, 100, 100);
		assertTrue(Objetivos.llegada(lugar, 100 + Objetivos.RADIO_LUGAR, 100));
		assertFalse(Objetivos.llegada(lugar, 100 + Objetivos.RADIO_LUGAR, 101));
		Encargo aldea = de(Tipo.VIAJE, "Torre del Roble", 0, -800, 0);
		assertTrue(Objetivos.llegada(aldea, -800 + Objetivos.RADIO_ALDEA, 0));
		assertFalse(Objetivos.llegada(aldea, -800 + Objetivos.RADIO_ALDEA + 1, 0));
		assertFalse(Objetivos.llegada(de(Tipo.GUARDIAN, "castillo", 0, 0, 0), 0, 0), "llegar no vence a nadie");
		assertFalse(Objetivos.llegada(de(Tipo.TRAER, "minecraft:bread", 16, 0, 0), 0, 0));
	}

	@Test
	void oleadaDeLaArena() {
		Encargo e = de(Tipo.ARENA, "", 5, 0, 0);
		assertFalse(Objetivos.oleada(e, 4));
		assertTrue(Objetivos.oleada(e, 5));
		assertTrue(Objetivos.oleada(e, 9));
		assertFalse(Objetivos.oleada(de(Tipo.TRAER, "minecraft:bread", 5, 0, 0), 9));
	}

	@Test
	void entregable() {
		Datos.Activo traer = new Datos.Activo(de(Tipo.TRAER, "minecraft:bread", 16, 0, 0), false);
		assertFalse(Objetivos.entregable(traer, 15));
		assertTrue(Objetivos.entregable(traer, 16));
		assertTrue(Objetivos.entregable(traer, 64));
		Datos.Activo guardian = new Datos.Activo(de(Tipo.GUARDIAN, "castillo", 0, 0, 0), false);
		assertFalse(Objetivos.entregable(guardian, 99));
		assertTrue(Objetivos.entregable(new Datos.Activo(guardian.encargo(), true), 0));
	}

	@Test
	void esperaLlegadaSoloConLugaresSinCumplir() {
		assertFalse(Objetivos.esperaLlegada(List.of()));
		assertFalse(Objetivos.esperaLlegada(List.of(new Datos.Activo(de(Tipo.TRAER, "minecraft:bread", 1, 0, 0), false),
				new Datos.Activo(de(Tipo.GUARDIAN, "castillo", 0, 0, 0), false))));
		assertTrue(Objetivos.esperaLlegada(List.of(new Datos.Activo(de(Tipo.VIAJE, "X", 0, 0, 0), false))));
		assertFalse(Objetivos.esperaLlegada(List.of(new Datos.Activo(de(Tipo.EXPLORAR, "X", 0, 0, 0), true))));
	}

	@Test
	void pistaDeRumboYDistanciaRedondeada() {
		assertEquals("n", Objetivos.rumbo(0, 0, 0, -500));
		assertEquals("s", Objetivos.rumbo(0, 0, 0, 500));
		assertEquals("e", Objetivos.rumbo(0, 0, 500, 0));
		assertEquals("o", Objetivos.rumbo(0, 0, -500, 0));
		assertEquals("ne", Objetivos.rumbo(0, 0, 400, -400));
		assertEquals("so", Objetivos.rumbo(0, 0, -400, 400));
		assertEquals(100, Objetivos.aproximada(0, 0, 10, 0), "al menos 100");
		assertEquals(1200, Objetivos.aproximada(0, 0, 1234, 0));
		assertEquals(1300, Objetivos.aproximada(0, 0, 1251, 0));
		assertEquals(0, Objetivos.aproximada(0, 0, 777, 333) % 100);
	}
}
