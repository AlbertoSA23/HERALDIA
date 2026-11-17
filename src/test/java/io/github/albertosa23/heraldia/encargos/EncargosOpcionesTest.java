package io.github.albertosa23.heraldia.encargos;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonPrimitive;
import io.github.albertosa23.heraldia.caminos.Trazado;
import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Recarga;
import java.io.IOException;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.Map;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Las opciones de los encargos y la reputación: sus valores por defecto, que se recargan y que se respetan apagadas. */
class EncargosOpcionesTest {
	@TempDir
	Path dir;

	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restaurar() {
		HeraldiaConfig.load(null);
	}

	static ConfigOption opcion(String k) {
		return HeraldiaConfig.options().stream().filter(o -> o.key().equals(k)).findFirst().orElseThrow();
	}

	@Test
	void porDefectoYRecargables() {
		HeraldiaConfig.load(null);
		assertTrue(HeraldiaConfig.get().getBool(Encargos.ACTIVADO));
		assertEquals(3, HeraldiaConfig.get().getInt(Encargos.ROTACION));
		assertTrue(HeraldiaConfig.get().getBool(Encargos.REPUTACION));
		assertTrue(Encargos.activado());
		assertTrue(Encargos.conReputacion());
		for (String k : new String[]{Encargos.ACTIVADO, Encargos.ROTACION, Encargos.REPUTACION}) {
			assertTrue(Recarga.recargable(k), k + " se aplica sin reiniciar");
		}
		assertEquals("encargos", opcion(Encargos.ACTIVADO).section());
		assertEquals("encargos", opcion(Encargos.REPUTACION).section());
		assertTrue(HeraldiaConfig.sections().containsKey("encargos"));
	}

	@Test
	void desactivadas() throws IOException {
		Path file = dir.resolve("heraldia.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put(Encargos.ACTIVADO, new JsonPrimitive(false));
		v.put(Encargos.REPUTACION, new JsonPrimitive(false));
		v.put(Encargos.ROTACION, new JsonPrimitive(7));
		HeraldiaConfig.save(file, v);
		HeraldiaConfig.load(file);
		assertFalse(Encargos.activado());
		assertFalse(Encargos.conReputacion());
		assertEquals(7, HeraldiaConfig.get().getInt(Encargos.ROTACION));
		// sin reputación, ni descuento ni reputación al entregar
		assertEquals(0, Reputacion.rebaja(Reputacion.Nivel.HEROE, 30, Encargos.conReputacion(), false));
		Encargo e = new Encargo(0, 0, 0, 0, Tipo.TRAER, "minecraft:bread", 16, 0, 0, 3, 20);
		assertEquals(0, Datos.VACIO.aceptar(e).entregar(e.id(), Encargos.conReputacion()).reputacion(e.aldea()));
		// y se vuelven a encender con /heraldia reload
		v.put(Encargos.ACTIVADO, new JsonPrimitive(true));
		v.put(Encargos.REPUTACION, new JsonPrimitive(true));
		HeraldiaConfig.save(file, v);
		Recarga.Resultado r = HeraldiaConfig.recargar(file);
		assertTrue(r.aplicadas().contains(Encargos.ACTIVADO) && r.aplicadas().contains(Encargos.REPUTACION), r.aplicadas().toString());
		assertTrue(Encargos.activado());
		assertTrue(Encargos.conReputacion());
	}

	@Test
	void rangoDeLaRotacion() {
		ConfigOption o = opcion(Encargos.ROTACION);
		assertEquals(1, o.min());
		assertEquals(30, o.max());
	}

	@Test
	void vecinasDeUnaAldeaDelTrazado() {
		int cell = 1504;
		Trazado.Aldeas aldeas = (gx, gz) -> Trazado.pack(gx * cell + 300, gz * cell + 200);
		Trazado t = new Trazado(9, cell, 2000, aldeas, Trazado.Hitos.NINGUNO);
		long[] v = t.vecinasDe(2 * cell + 300, -cell + 200);
		assertArrayEquals(t.vecinas(2, -1), v);
		assertTrue(v.length > 0);
		assertEquals(0, t.vecinasDe(2 * cell + 301, -cell + 200).length, "no es una aldea de la rejilla");
	}

	@Test
	void nombreDeLaAldea() {
		String n = Encargos.nombre(42, 10, -3);
		assertEquals(n, Encargos.nombre(42, 10, -3));
		assertEquals(2, n.split(" ", 2).length);
	}
}
