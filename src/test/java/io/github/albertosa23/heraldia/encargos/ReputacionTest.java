package io.github.albertosa23.heraldia.encargos;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Niveles de reputación, subidas, bajadas y su efecto en los precios. */
class ReputacionTest {
	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void niveles() {
		assertEquals(Reputacion.Nivel.DESCONOCIDO, Reputacion.nivel(Reputacion.MIN));
		assertEquals(Reputacion.Nivel.DESCONOCIDO, Reputacion.nivel(0));
		assertEquals(Reputacion.Nivel.DESCONOCIDO, Reputacion.nivel(Reputacion.CONOCIDO - 1));
		assertEquals(Reputacion.Nivel.CONOCIDO, Reputacion.nivel(Reputacion.CONOCIDO));
		assertEquals(Reputacion.Nivel.CONOCIDO, Reputacion.nivel(Reputacion.AMIGO - 1));
		assertEquals(Reputacion.Nivel.AMIGO, Reputacion.nivel(Reputacion.AMIGO));
		assertEquals(Reputacion.Nivel.AMIGO, Reputacion.nivel(Reputacion.HEROE - 1));
		assertEquals(Reputacion.Nivel.HEROE, Reputacion.nivel(Reputacion.HEROE));
		assertEquals(Reputacion.Nivel.HEROE, Reputacion.nivel(Reputacion.MAX));
		assertTrue(Reputacion.CONOCIDO < Reputacion.AMIGO && Reputacion.AMIGO < Reputacion.HEROE && Reputacion.HEROE <= Reputacion.MAX);
	}

	@Test
	void subirYBajarSinSalirseDelRango() {
		assertEquals(25, Reputacion.sumar(15, 10));
		assertEquals(Reputacion.MAX, Reputacion.sumar(Reputacion.MAX - 1, 50));
		assertEquals(Reputacion.MIN, Reputacion.sumar(-90, -40));
		assertEquals(Reputacion.MAX, Reputacion.sumar(Reputacion.MAX, Integer.MAX_VALUE));
		assertEquals(Reputacion.MIN, Reputacion.sumar(Reputacion.MIN, Integer.MIN_VALUE));
		// dos encargos (traer y guardián) bastan para ser conocido; un aldeano muerto lo quita
		int r = Reputacion.sumar(Reputacion.sumar(0, Tipo.TRAER.reputacion), Tipo.GUARDIAN.reputacion);
		assertEquals(Reputacion.Nivel.CONOCIDO, Reputacion.nivel(r));
		assertEquals(Reputacion.Nivel.DESCONOCIDO, Reputacion.nivel(Reputacion.sumar(r, Reputacion.ataque(false, true))));
	}

	@Test
	void ataques() {
		assertEquals(Reputacion.GOLPE_ALDEANO, Reputacion.ataque(false, false));
		assertEquals(Reputacion.MUERTE_ALDEANO, Reputacion.ataque(false, true));
		assertEquals(Reputacion.GOLPE_GOLEM, Reputacion.ataque(true, false));
		assertEquals(Reputacion.MUERTE_GOLEM, Reputacion.ataque(true, true));
		assertTrue(Reputacion.MUERTE_ALDEANO < Reputacion.GOLPE_ALDEANO && Reputacion.GOLPE_ALDEANO < 0);
		assertTrue(Reputacion.MUERTE_GOLEM < Reputacion.GOLPE_GOLEM && Reputacion.GOLPE_GOLEM < 0);
	}

	@Test
	void rebajaComoHeroeDeLaAldea() {
		assertEquals(0, Reputacion.rebaja(Reputacion.Nivel.DESCONOCIDO, 10, true, false));
		assertEquals(-1, Reputacion.rebaja(Reputacion.Nivel.CONOCIDO, 10, true, false));
		assertEquals(-1, Reputacion.rebaja(Reputacion.Nivel.CONOCIDO, 1, true, false), "al menos 1, como vanilla");
		assertEquals(-4, Reputacion.rebaja(Reputacion.Nivel.AMIGO, 20, true, false));
		assertEquals(-19, Reputacion.rebaja(Reputacion.Nivel.HEROE, 64, true, false));
		assertEquals(Reputacion.Nivel.HEROE.descuento, 30, "como Héroe de la aldea I (0,3 + 0,0625 × 0)");
		assertEquals(0, Reputacion.rebaja(Reputacion.Nivel.HEROE, 64, false, false), "reputación desactivada");
		assertEquals(0, Reputacion.rebaja(Reputacion.Nivel.HEROE, 64, true, true), "no se suma a Héroe de la aldea");
		assertEquals(0, Reputacion.rebaja(Reputacion.Nivel.AMIGO, 0, true, false));
	}

	/** El precio que cobra un trato: {@code MerchantOffer.getCostA} (sin demanda), nunca por debajo de 1. */
	static int precio(int base, int diff) {
		return Math.max(1, base + diff);
	}

	@Test
	void precioDeUnTrato() {
		assertEquals(9, precio(10, Reputacion.rebaja(Reputacion.Nivel.CONOCIDO, 10, true, false)));
		assertEquals(8, precio(10, Reputacion.rebaja(Reputacion.Nivel.AMIGO, 10, true, false)));
		assertEquals(7, precio(10, Reputacion.rebaja(Reputacion.Nivel.HEROE, 10, true, false)));
		assertEquals(1, precio(1, Reputacion.rebaja(Reputacion.Nivel.HEROE, 1, true, false)), "nunca por debajo de 1");
		assertEquals(10, precio(10, Reputacion.rebaja(Reputacion.Nivel.DESCONOCIDO, 10, true, false)));
	}

	@Test
	void claveDeAldea() {
		assertEquals("12,-40", Reputacion.clave(12, -40));
		assertArrayEquals(new int[]{12, -40}, Reputacion.chunk("12,-40"));
		assertNull(Reputacion.chunk("x"));
		assertNull(Reputacion.chunk(",3"));
		assertNull(Reputacion.chunk("a,b"));
	}
}
