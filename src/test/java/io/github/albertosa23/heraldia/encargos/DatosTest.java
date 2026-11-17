package io.github.albertosa23.heraldia.encargos;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonElement;
import com.mojang.serialization.JsonOps;
import java.util.List;
import java.util.Map;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import org.junit.jupiter.api.Test;

/** Los datos del jugador y del mundo: aceptar, cumplir, entregar y su persistencia (los códecs del adjunto). */
class DatosTest {
	static Encargo e(int hueco, Tipo t) {
		return new Encargo(5, -7, 2, hueco, t, t == Tipo.TRAER ? "minecraft:bread" : "castillo", t == Tipo.TRAER ? 16 : 0, 100, 200, 3, 20);
	}

	@Test
	void aceptarYPorQueNo() {
		Datos d = Datos.VACIO;
		assertNull(d.noAceptable(e(0, Tipo.TRAER)));
		d = d.aceptar(e(0, Tipo.TRAER));
		assertTrue(d.tiene(e(0, Tipo.TRAER).id()));
		assertEquals("ya", d.noAceptable(e(0, Tipo.TRAER)));
		for (int i = 1; i < Datos.MAX_ACTIVOS; i++) {
			d = d.aceptar(e(i, Tipo.GUARDIAN));
		}
		assertEquals(Datos.MAX_ACTIVOS, d.activos().size());
		assertEquals("lleno", d.noAceptable(new Encargo(1, 1, 0, 0, Tipo.ARENA, "", 3, 0, 0, 4, 30)));
		Datos entregado = Datos.VACIO.aceptar(e(0, Tipo.TRAER)).entregar(e(0, Tipo.TRAER).id(), true);
		assertEquals("hecho", entregado.noAceptable(e(0, Tipo.TRAER)), "no se cobra dos veces");
	}

	@Test
	void abandonar() {
		Datos d = Datos.VACIO.aceptar(e(0, Tipo.TRAER)).aceptar(e(1, Tipo.GUARDIAN));
		Datos sin = d.abandonar(0);
		assertEquals(1, sin.activos().size());
		assertEquals(Tipo.GUARDIAN, sin.activos().get(0).encargo().tipo());
		assertSame(d, d.abandonar(5));
		assertSame(d, d.abandonar(-1));
		assertNull(sin.noAceptable(e(0, Tipo.TRAER)), "abandonado se puede volver a aceptar");
	}

	@Test
	void cumplirSoloLoQueCumple() {
		Datos d = Datos.VACIO.aceptar(e(0, Tipo.TRAER)).aceptar(e(1, Tipo.GUARDIAN));
		Datos c = d.cumplir(x -> Objetivos.guardian(x, "castillo", 110, 190));
		assertFalse(c.activos().get(0).cumplido());
		assertTrue(c.activos().get(1).cumplido());
		assertSame(c, c.cumplir(x -> Objetivos.guardian(x, "castillo", 110, 190)), "ya cumplido: sin cambios");
		assertSame(d, d.cumplir(x -> false));
	}

	@Test
	void entregarDaReputacionConSuAldea() {
		Encargo g = e(1, Tipo.GUARDIAN);
		Datos d = Datos.VACIO.aceptar(g).cumplir(x -> true).entregar(g.id(), true);
		assertEquals(0, d.activos().size());
		assertEquals(1, d.completados());
		assertEquals(List.of(g.id()), d.hechos());
		assertEquals(Tipo.GUARDIAN.reputacion, d.reputacion("5,-7"));
		assertEquals(0, d.reputacion("0,0"));
		Datos sin = Datos.VACIO.aceptar(g).entregar(g.id(), false);
		assertEquals(0, sin.reputacion("5,-7"), "con la reputación desactivada no sube");
		assertEquals(1, sin.completados());
		assertSame(d, d.entregar("no.existe.0.0", true));
	}

	@Test
	void hechosAcotados() {
		Datos d = Datos.VACIO;
		for (int i = 0; i < Datos.MAX_HECHOS + 20; i++) {
			Encargo x = new Encargo(i, 0, 0, 0, Tipo.TRAER, "minecraft:bread", 1, 0, 0, 1, 1);
			d = d.aceptar(x).entregar(x.id(), true);
		}
		assertEquals(Datos.MAX_HECHOS, d.hechos().size());
		assertEquals(Datos.MAX_HECHOS + 20, d.completados());
		assertFalse(d.hecho("0.0.0.0"), "los más viejos se olvidan");
		assertTrue(d.hecho((Datos.MAX_HECHOS + 19) + ".0.0.0"));
	}

	@Test
	void nivelesPorAldea() {
		Datos d = Datos.VACIO.sumarReputacion("1,1", Reputacion.AMIGO).sumarReputacion("2,2", Reputacion.HEROE)
				.sumarReputacion("3,3", -50);
		assertEquals(Reputacion.Nivel.AMIGO, d.nivel("1,1"));
		assertEquals(Reputacion.Nivel.HEROE, d.nivel("2,2"));
		assertEquals(Reputacion.Nivel.DESCONOCIDO, d.nivel("3,3"));
		assertEquals(2, d.aldeasCon(Reputacion.Nivel.AMIGO));
		assertEquals(1, d.aldeasCon(Reputacion.Nivel.HEROE));
		assertEquals(Reputacion.Nivel.HEROE, d.mejorNivel());
		assertEquals(Reputacion.Nivel.DESCONOCIDO, Datos.VACIO.mejorNivel());
	}

	@Test
	void persistenciaEnNbtYJson() {
		Datos d = Datos.VACIO.aceptar(e(0, Tipo.TRAER)).aceptar(e(1, Tipo.GUARDIAN)).cumplir(x -> x.tipo() == Tipo.GUARDIAN)
				.sumarReputacion("5,-7", 42).sumarReputacion("-3,9", -12);
		d = d.aceptar(e(2, Tipo.VIAJE)).entregar(e(2, Tipo.VIAJE).id(), true);
		Tag nbt = Datos.CODEC.encodeStart(NbtOps.INSTANCE, d).getOrThrow();
		assertEquals(d, Datos.CODEC.parse(NbtOps.INSTANCE, nbt).getOrThrow());
		JsonElement json = Datos.CODEC.encodeStart(JsonOps.INSTANCE, d).getOrThrow();
		assertEquals(d, Datos.CODEC.parse(JsonOps.INSTANCE, json).getOrThrow());
		// un adjunto vacío (o de una versión anterior sin campos) se lee con los valores por defecto
		assertEquals(Datos.VACIO, Datos.CODEC.parse(JsonOps.INSTANCE, new com.google.gson.JsonObject()).getOrThrow());
		assertEquals(Map.of("5,-7", 42 + Tipo.VIAJE.reputacion, "-3,9", -12), d.reputacion());
	}

	@Test
	void mundo() {
		Mundo m = Mundo.VACIO.completado().completado().cae("castillo", 1000, 1000, 5000);
		assertEquals(2, m.completados());
		assertTrue(m.caido("castillo", 1100, 1000));
		assertFalse(m.caido("castillo", 1000 + Objetivos.RADIO_GUARDIAN + 1, 1000));
		assertFalse(m.caido("catedral", 1000, 1000));
		assertSame(m, m.cae("castillo", 1010, 990, 9000), "el mismo guardián no se apunta dos veces");
		// el tablón de un periodo solo descarta los caídos antes de que empezara (no cambia a mitad de periodo)
		assertTrue(m.caidoAntes("castillo", 1000, 1000, 5001));
		assertFalse(m.caidoAntes("castillo", 1000, 1000, 5000));
		assertEquals(5000, m.caidos().get(0).tick());
		Tag nbt = Mundo.CODEC.encodeStart(NbtOps.INSTANCE, m).getOrThrow();
		assertEquals(m, Mundo.CODEC.parse(NbtOps.INSTANCE, nbt).getOrThrow());
		Mundo lleno = Mundo.VACIO;
		for (int i = 0; i <= Mundo.MAX_CAIDOS; i++) {
			lleno = lleno.cae("castillo", i * 1000, 0, i);
		}
		assertEquals(Mundo.MAX_CAIDOS, lleno.caidos().size());
	}

	@Test
	void tipos() {
		for (Tipo t : Tipo.values()) {
			assertEquals(t, Tipo.de(t.id()));
			assertEquals(t.id(), t.id().toLowerCase(java.util.Locale.ROOT));
		}
		assertEquals("traer", Tipo.TRAER.id());
	}
}
