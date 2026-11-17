package io.github.albertosa23.heraldia.caravanas;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.caminos.Trazado;
import io.github.albertosa23.heraldia.encargos.Datos;
import io.github.albertosa23.heraldia.encargos.Reputacion;
import java.util.HashSet;
import java.util.Set;
import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Cuándo sale una caravana, cómo es, qué paga, la reputación con su aldea de destino y qué entidades sobran. */
class ReglasTest {
	static final long ESPERA = Reglas.ESPERA_TICKS;

	@Test
	void decisionDeAparicion() {
		// activada, sin ninguna en camino, pasada la espera y con el sorteo a favor
		assertTrue(Reglas.sale(true, 0, 1, ESPERA, 0, 10, 0.05));
		assertFalse(Reglas.sale(true, 0, 1, ESPERA, 0, 10, 0.10), "10 %: sale con azar < 0,10");
		assertFalse(Reglas.sale(false, 0, 1, ESPERA, 0, 100, 0), "desactivadas: nunca");
		assertFalse(Reglas.sale(true, 1, 1, ESPERA, 0, 100, 0), "límite de activas");
		assertTrue(Reglas.sale(true, 1, 2, ESPERA, 0, 100, 0), "con 2 de máximo, sale la segunda");
		assertFalse(Reglas.sale(true, 0, 1, ESPERA - 1, 0, 100, 0), "la espera tras la anterior");
		assertFalse(Reglas.sale(true, 0, 1, 1_000_000, 0, 0, 0), "frecuencia 0: solo con el comando");
		assertTrue(Reglas.sale(true, 0, 1, 1_000_000, 0, 100, 0.999), "frecuencia 100: siempre");
		// al arrancar no hay espera (la última terminó «hace» ESPERA ticks)
		assertTrue(Reglas.sale(true, 0, 1, 0, -ESPERA, 100, 0));
	}

	@Test
	void frecuenciaMedia() {
		java.util.Random r = new java.util.Random(1);
		int n = 0;
		for (int i = 0; i < 100_000; i++) {
			n += Reglas.sale(true, 0, 1, ESPERA, 0, 10, r.nextDouble()) ? 1 : 0;
		}
		assertEquals(10_000, n, 400, "10 % de los sorteos");
	}

	@Test
	void asaltoYComposicion() {
		assertTrue(Reglas.asalto(35, 0.34));
		assertFalse(Reglas.asalto(35, 0.35));
		assertFalse(Reglas.asalto(0, 0), "sin asaltos");
		assertTrue(Reglas.asalto(100, 0.999));
		assertEquals(1, Reglas.llamas(0));
		assertEquals(2, Reglas.llamas(0.5));
		assertEquals(3, Reglas.llamas(0.999));
		assertTrue(Reglas.guardia(0.1));
		assertFalse(Reglas.guardia(0.3));
		assertEquals(2, Reglas.bandidos(0));
		assertEquals(2, Reglas.bandidos(1));
		assertEquals(3, Reglas.bandidos(2));
		assertEquals(4, Reglas.bandidos(10), "como mucho 4");
		assertFalse(Reglas.conJefe(2));
		assertTrue(Reglas.conJefe(3));
	}

	@Test
	void recompensa() {
		Reglas.Recompensa sin = Reglas.recompensa(9, false, 0.5);
		assertEquals(4, sin.esmeraldas());
		assertEquals(5, sin.reputacion());
		assertFalse(sin.conObjeto());
		assertNull(sin.objeto());
		assertFalse(sin.logro(), "sin asalto no hay logro");
		Reglas.Recompensa con = Reglas.recompensa(9, true, 0.0);
		assertEquals(8, con.esmeraldas());
		assertEquals(15, con.reputacion());
		assertTrue(con.conObjeto());
		assertEquals("minecraft:name_tag", con.objeto());
		assertEquals(1, con.cantidad());
		assertTrue(con.logro());
		for (double a : new double[]{0, 0.3, 0.6, 0.999}) {
			Reglas.Recompensa r = Reglas.recompensa(5, true, a);
			assertTrue(r.objeto().startsWith("minecraft:") && r.cantidad() >= 1);
		}
		// modesto: nada de netherita, diamantes ni élitros (como el botín de una mediana)
		for (Object[] o : Reglas.OBJETOS) {
			String id = (String) o[0];
			assertFalse(id.contains("netherite") || id.contains("diamond") || id.contains("elytra") || id.contains("totem"), id);
		}
	}

	@Test
	void reputacionConLaAldeaDeDestino() {
		// el trazado da la plaza de la aldea (chunk del inicio * 16 + 8): la reputación es la de ese chunk
		long aldea = Trazado.pack(-37 * 16 + 8, 12 * 16 + 8);
		assertArrayEquals(new int[]{-37, 12}, Reglas.chunk(aldea));
		String clave = Reputacion.clave(-37, 12);
		// lo que suma Encargos.sumarReputacion: con una caravana defendida y dos acompañadas, de desconocido a conocido
		Datos d = Datos.VACIO.sumarReputacion(clave, Reglas.recompensa(9, true, 0).reputacion());
		assertEquals(15, d.reputacion(clave));
		assertEquals(Reputacion.Nivel.DESCONOCIDO, d.nivel(clave));
		d = d.sumarReputacion(clave, Reglas.recompensa(9, false, 0).reputacion());
		assertEquals(Reputacion.Nivel.CONOCIDO, d.nivel(clave));
		assertEquals(0, d.reputacion(Reputacion.clave(-36, 12)), "solo con la aldea de destino");
	}

	@Test
	void entidadesSobrantesAlReiniciar() {
		UUID mia = UUID.randomUUID(), vieja = UUID.randomUUID();
		Set<UUID> activas = new HashSet<>(Set.of(mia));
		assertFalse(Reglas.huerfana(Set.of(Reglas.TAG, Reglas.MERCADER), mia, activas), "de una caravana en camino");
		assertTrue(Reglas.huerfana(Set.of(Reglas.TAG, Reglas.LLAMA), vieja, activas), "de una que ya no está");
		// tras reiniciar no hay ninguna activa: todas sobran
		for (String papel : new String[]{Reglas.MERCADER, Reglas.LLAMA, Reglas.GUARDIA, Reglas.BANDIDO}) {
			assertTrue(Reglas.huerfana(Set.of(Reglas.TAG, papel), mia, Set.of()), papel);
		}
		assertFalse(Reglas.huerfana(Set.of(), vieja, Set.of()), "una entidad cualquiera no se toca");
		assertFalse(Reglas.huerfana(Set.of("heraldia_anclado"), vieja, Set.of()));
	}

	@Test
	void sinBotinDeExplotacion() {
		assertTrue(Caravanas.sinBotin(Set.of(Reglas.TAG, Reglas.MERCADER)));
		assertTrue(Caravanas.sinBotin(Set.of(Reglas.TAG, Reglas.LLAMA)));
		assertTrue(Caravanas.sinBotin(Set.of(Reglas.TAG, Reglas.GUARDIA)));
		assertFalse(Caravanas.sinBotin(Set.of(Reglas.TAG, Reglas.BANDIDO)), "los bandidos, lo suyo");
		assertFalse(Caravanas.sinBotin(Set.of()));
	}
}
