package io.github.albertosa23.heraldia.tesoro;

import static org.junit.jupiter.api.Assertions.assertEquals;

import java.util.HashSet;
import java.util.Set;
import net.minecraft.core.BlockPos;
import org.junit.jupiter.api.Test;

/** Usar el mapa: lejos, en cada marca y en el tesoro; la cadena se completa una sola vez (también con copias). */
class AvanceTest {
	@Test
	void lejosCercaYLlegada() {
		Cadena c = CadenaTest.cadena();
		Destino m = CadenaTest.MEDIANA;
		assertEquals(Avance.Resultado.LEJOS, Avance.evaluar(c, 0, 0, Set.of()));
		assertEquals(Avance.Resultado.SIGUIENTE, Avance.evaluar(c, m.x() + Avance.LLEGADA_ESTRUCTURA, m.z(), Set.of()));
		assertEquals(Avance.Resultado.LEJOS, Avance.evaluar(c, m.x() + Avance.LLEGADA_ESTRUCTURA + 1, m.z(), Set.of()));
	}

	@Test
	void recorridoEnteroYUnaSolaVez() {
		Set<Long> completadas = new HashSet<>();
		Cadena c = CadenaTest.cadena();
		Cadena copia = c;   // una copia del mapa (mesa de cartografía) con la misma cadena
		int pasos = 0;
		while (true) {
			Destino d = c.actual();
			Avance.Resultado r = Avance.evaluar(c, d.x(), d.z(), completadas);
			if (r == Avance.Resultado.SIGUIENTE) {
				c = c.avanzar();
				pasos++;
			} else {
				assertEquals(Avance.Resultado.COFRE, r);
				break;
			}
		}
		assertEquals(2, pasos);
		completadas.add(c.semilla());
		c = c.conCofre(new BlockPos(c.actual().x(), 63, c.actual().z()));
		assertEquals(Avance.Resultado.HECHA, Avance.evaluar(c, c.actual().x(), c.actual().z(), completadas));
		assertEquals(Avance.Resultado.HECHA, Avance.evaluar(c, c.actual().x(), c.actual().z(), Set.of()), "completada por sí misma");
		Cadena copiaEnTesoro = copia.avanzar().avanzar();
		assertEquals(Avance.Resultado.HECHA, Avance.evaluar(copiaEnTesoro, copiaEnTesoro.actual().x(), copiaEnTesoro.actual().z(), completadas),
				"la copia no da otro cofre");
		assertEquals(Avance.Resultado.HECHA, Avance.evaluar(copia, 0, 0, completadas), "ni lejos dice nada más");
	}

	@Test
	void elTesoroPideLlegarMasCerca() {
		Cadena c = CadenaTest.cadena().avanzar().avanzar();
		Destino t = c.actual();
		assertEquals(Avance.Resultado.COFRE, Avance.evaluar(c, t.x() + Avance.LLEGADA_TESORO, t.z(), Set.of()));
		assertEquals(Avance.Resultado.LEJOS, Avance.evaluar(c, t.x() + Avance.LLEGADA_TESORO + 1, t.z(), Set.of()));
	}

	@Test
	void distanciaAproximada() {
		Destino d = new Destino(Destino.Tipo.TESORO, "", 0, 0, false, "minecraft:plains");
		assertEquals(120, Avance.distanciaAproximada(d, 123, 0));
		assertEquals(130, Avance.distanciaAproximada(d, 0, -126));
		assertEquals(0, Avance.distanciaAproximada(d, 2, 2));
	}
}
