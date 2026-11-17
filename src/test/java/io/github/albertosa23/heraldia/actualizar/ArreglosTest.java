package io.github.albertosa23.heraldia.actualizar;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.actualizar.Arreglos.Efecto;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.Test;

/** Registro de arreglos: orden, marca, modo de prueba e idempotencia de cada arreglo inicial de los mobs. */
class ArreglosTest {
	/** Un mob de mentira con lo que los arreglos miran. */
	static final class Falso implements ArreglosMobs.Mob {
		String tipo = "zombie", nombre, montura, arma;
		Set<String> tags = new HashSet<>();
		boolean persistente = true, bebe, recoge, especial, monturaPropia, montaQuitada;

		@Override public String tipo() { return tipo; }
		@Override public Set<String> etiquetas() { return tags; }
		@Override public void etiquetar(String e) { tags.add(e); }
		@Override public String claveNombre() { return nombre; }
		@Override public boolean persistente() { return persistente; }
		@Override public boolean bebe() { return bebe; }
		@Override public void hacerAdulto() { bebe = false; }
		@Override public String montura() { return montura; }
		@Override public boolean monturaPropia() { return monturaPropia; }
		@Override public void quitarMontura() { montura = null; montaQuitada = true; }
		@Override public boolean recoge() { return recoge; }
		@Override public void noRecoger() { recoge = false; }
		@Override public String arma() { return arma; }
		@Override public boolean armaEspecial() { return especial; }
	}

	/** Un guardián de la 0.1.0: nombre traducible, persistente, sin etiquetas, bebé, en una gallina, recogiendo. */
	static Falso guardianAntiguo() {
		Falso f = new Falso();
		f.nombre = "heraldia.unicas.castillo.guardian";
		f.bebe = true;
		f.montura = "chicken";
		f.recoge = true;
		return f;
	}

	@Test
	void reconoceLosMobsDePlantilla() {
		assertTrue(ArreglosMobs.dePlantilla(guardianAntiguo()));
		Falso nuevo = new Falso();
		nuevo.persistente = false;
		nuevo.tags.add("heraldia_anclado");
		assertTrue(ArreglosMobs.dePlantilla(nuevo));
		Falso vanilla = new Falso();
		vanilla.nombre = "entity.minecraft.zombie";      // con nombre, pero no de Heraldia
		assertFalse(ArreglosMobs.dePlantilla(vanilla));
		Falso sinPersistir = guardianAntiguo();
		sinPersistir.persistente = false;
		assertFalse(ArreglosMobs.dePlantilla(sinPersistir));
	}

	@Test
	void todosLosArreglosSonIdempotentes() {
		Falso g = guardianAntiguo();
		Map<String, Efecto> primera = ArreglosMobs.REGISTRO.ejecutar(g, 0, false, true);
		assertEquals(List.of("marcas", "bebes", "recoger"), List.copyOf(primera.keySet()));
		assertTrue(g.tags.containsAll(Set.of("heraldia_anclado", "heraldia_adulto", "heraldia_guardian")));
		assertFalse(g.bebe);
		assertTrue(g.montaQuitada);
		assertFalse(g.recoge);
		// la segunda vez (forzada, como /heraldia update repair) ya no hay nada que cambiar
		assertTrue(ArreglosMobs.REGISTRO.ejecutar(g, 0, false, true).isEmpty());
		assertTrue(ArreglosMobs.REGISTRO.ejecutar(g, 0, false, true).isEmpty());
	}

	@Test
	void elModoDePruebaNoCambiaNada() {
		Falso g = guardianAntiguo();
		Map<String, Efecto> prueba = ArreglosMobs.REGISTRO.ejecutar(g, 0, true, true);
		assertEquals(3, prueba.size());
		assertTrue(g.tags.isEmpty());
		assertTrue(g.bebe);
		assertFalse(g.montaQuitada);
		assertTrue(g.recoge);
		assertEquals(prueba, ArreglosMobs.REGISTRO.ejecutar(g, 0, true, true));
	}

	@Test
	void conLaMarcaDelNivelNoSeVuelvenAEjecutar() {
		Falso g = guardianAntiguo();
		int nivel = ArreglosMobs.REGISTRO.nivel();
		assertEquals(5, nivel);
		assertTrue(ArreglosMobs.REGISTRO.pendiente(0));
		assertFalse(ArreglosMobs.REGISTRO.pendiente(nivel));
		assertTrue(ArreglosMobs.REGISTRO.ejecutar(g, nivel, false, false).isEmpty());
		assertTrue(g.bebe);                                // con la marca no se ha tocado
		// con una marca intermedia solo corren los de número mayor
		Map<String, Efecto> e = ArreglosMobs.REGISTRO.ejecutar(g, 2, false, false);
		assertEquals(Set.of("recoger"), e.keySet());
		assertTrue(g.bebe);
	}

	@Test
	void nautilosYArmas() {
		Falso a = new Falso();
		a.tipo = "drowned";
		a.tags.add("heraldia_adulto");
		a.montura = "zombie_nautilus";
		a.arma = "trident";
		Map<String, Efecto> e = ArreglosMobs.REGISTRO.ejecutar(a, 0, false, true);
		assertEquals(Efecto.CAMBIA, e.get("nautilos"));
		assertEquals(Efecto.AVISO, e.get("armas"));
		assertTrue(a.montaQuitada);
		assertEquals("trident", a.arma);                  // el arma no se cambia: solo se avisa
		assertEquals(Map.of("armas", Efecto.AVISO), ArreglosMobs.REGISTRO.ejecutar(a, 0, false, true));
		// un tridente con nombre o encantado es de la plantilla
		a.especial = true;
		assertTrue(ArreglosMobs.REGISTRO.ejecutar(a, 0, false, true).isEmpty());
		// un nautilo con nombre (de un jugador) no se quita
		Falso b = new Falso();
		b.tipo = "drowned";
		b.tags.add("heraldia_adulto");
		b.montura = "zombie_nautilus";
		b.monturaPropia = true;
		assertTrue(ArreglosMobs.REGISTRO.ejecutar(b, 0, false, true).isEmpty());
	}

	@Test
	void unEsqueletoConNombreSoloSeAncla() {
		Falso s = new Falso();
		s.tipo = "skeleton";
		s.nombre = "heraldia.catedral.guardian";
		s.bebe = false;
		ArreglosMobs.REGISTRO.ejecutar(s, 0, false, true);
		assertEquals(Set.of("heraldia_anclado", "heraldia_guardian"), s.tags);
	}

	@Test
	void registroOrdenadoYSinNumerosRepetidos() {
		Arreglos.Registro<Object> r = new Arreglos.Registro<>(List.of(
				new Arreglos.Arreglo<>(3, "c", Arreglos.Ambito.CHUNK, (o, p) -> Efecto.NADA),
				new Arreglos.Arreglo<>(1, "a", Arreglos.Ambito.CHUNK, (o, p) -> Efecto.CAMBIA)));
		assertEquals("a", r.arreglos().get(0).id());
		assertEquals(3, r.nivel());
		assertEquals(0, new Arreglos.Registro<>(List.of()).nivel());
		assertThrows(IllegalArgumentException.class, () -> new Arreglos.Registro<>(List.of(
				new Arreglos.Arreglo<Object>(1, "a", Arreglos.Ambito.CHUNK, (o, p) -> Efecto.NADA),
				new Arreglos.Arreglo<Object>(1, "b", Arreglos.Ambito.CHUNK, (o, p) -> Efecto.NADA))));
	}

	@Test
	void cuentaPorArreglo() {
		Arreglos.Cuenta c = new Arreglos.Cuenta();
		c.sumar(Map.of("bebes", Efecto.CAMBIA));
		c.sumar(Map.of("armas", Efecto.AVISO));
		c.sumar(Map.of());
		assertEquals(3, c.revisados());
		assertEquals(1, c.cambios());
		assertEquals(1, c.porId().get("armas")[1]);
	}

	@Test
	void versionDelMundo() {
		// mundo nuevo: generado con esta versión; viejo sin datos: «anterior»
		assertEquals(new VersionMundo("0.2.0", "0.2.0", 5), VersionMundo.alArrancar(java.util.Optional.empty(), "0.2.0", 10, 1200, 5));
		assertEquals(new VersionMundo(VersionMundo.ANTERIOR, "0.2.0", 0), VersionMundo.alArrancar(java.util.Optional.empty(), "0.2.0", 90_000, 1200, 5));
		VersionMundo antes = new VersionMundo("0.1.0", "0.1.5", 2);
		assertEquals(new VersionMundo("0.1.0", "0.2.0", 2), VersionMundo.alArrancar(java.util.Optional.of(antes), "0.2.0", 9, 1200, 5));
		assertTrue(VersionMundo.retrocede(java.util.Optional.of(antes), "0.1.2"));
		assertFalse(VersionMundo.retrocede(java.util.Optional.of(antes), "0.2.0"));
	}
}
