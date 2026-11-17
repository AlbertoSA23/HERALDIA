package io.github.albertosa23.heraldia.loot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.loot.Reposicion.Decision;
import io.github.albertosa23.heraldia.loot.Reposicion.Registro;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.TreeSet;
import java.util.stream.Stream;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.Tag;
import org.junit.jupiter.api.Test;

/** Botín que se repone: cuándo se repone un cofre (días, jugadores cerca, vacío), qué tablas y qué se guarda. */
class ReposicionTest {
	private static final String ALDEA = "heraldia:cofres/herreria", UNICA = "heraldia:unicas/castillo/armeria",
			MEDIANA = "heraldia:medianas/posada/despensa";
	private static final long DIA = Reposicion.DIA;

	private static Optional<Registro> reg(String tabla, long t) {
		return Optional.of(new Registro(tabla, t));
	}

	@Test
	void tablasQueSeReponen() {
		for (String t : List.of(ALDEA, UNICA, MEDIANA)) {
			assertTrue(Reposicion.tablaRepone(t), t);
		}
		for (String t : List.of("heraldia:trofeos/castillo", "heraldia:guardianes/castillo/zombie", "heraldia:llaves/castillo/llave",
				"heraldia:mapas/castillo", "heraldia:encargos/a", "heraldia:unicas/castillo/trofeo", "minecraft:chests/simple_dungeon",
				"heraldia:cofres/", "heraldia:unicas", "", "otro:cofres/x")) {
			assertFalse(Reposicion.tablaRepone(t), t);
		}
		assertFalse(Reposicion.tablaRepone(null));
	}

	@Test
	void conTablaPendienteSeApuntaSoloSiEsDeHeraldia() {
		assertEquals(Decision.APUNTAR, Reposicion.decidir(ALDEA, Optional.empty(), 0, 7, 0, 0));
		// también si ya había registro (se repuso y aún no se ha abierto, o el cofre se rellenó con /loot): se reapunta
		assertEquals(Decision.APUNTAR, Reposicion.decidir(UNICA, reg(UNICA, 5), 100 * DIA, 7, 3, 27));
		assertEquals(Decision.NADA, Reposicion.decidir("minecraft:chests/simple_dungeon", Optional.empty(), 0, 7, 0, 0));
		assertEquals(Decision.NADA, Reposicion.decidir("heraldia:trofeos/castillo", Optional.empty(), 0, 7, 0, 0));
	}

	@Test
	void sinRegistroNiTablaNoHaceNada() {
		assertEquals(Decision.NADA, Reposicion.decidir(null, Optional.empty(), 100 * DIA, 1, 0, 0));
		assertEquals(Decision.NADA, Reposicion.decidir(null, reg("heraldia:trofeos/x", 0), 100 * DIA, 1, 0, 0));
	}

	@Test
	void esperaLosDiasJustos() {
		long t0 = 3 * DIA + 123;
		assertEquals(Decision.ESPERAR, Reposicion.decidir(null, reg(ALDEA, t0), t0, 7, 0, 0));
		assertEquals(Decision.ESPERAR, Reposicion.decidir(null, reg(ALDEA, t0), t0 + 7 * DIA - 1, 7, 0, 0));
		assertEquals(Decision.REPONER, Reposicion.decidir(null, reg(ALDEA, t0), t0 + 7 * DIA, 7, 0, 0));
		assertEquals(Decision.REPONER, Reposicion.decidir(null, reg(ALDEA, t0), t0 + 60 * DIA, 7, 0, 0));
		assertEquals(Decision.REPONER, Reposicion.decidir(null, reg(ALDEA, 0), DIA, 1, 0, 0));
		assertEquals(Decision.ESPERAR, Reposicion.decidir(null, reg(ALDEA, 0), 59 * DIA, 60, 0, 0));
	}

	@Test
	void otroJugadorCercaLoImpide() {
		assertEquals(Decision.ESPERAR, Reposicion.decidir(null, reg(MEDIANA, 0), 10 * DIA, 7, 1, 0));
		assertEquals(Decision.ESPERAR, Reposicion.decidir(null, reg(MEDIANA, 0), 10 * DIA, 7, 4, 0));
		assertEquals(Decision.REPONER, Reposicion.decidir(null, reg(MEDIANA, 0), 10 * DIA, 7, 0, 0));
	}

	@Test
	void soloVacioOCasiVacio() {
		for (int n = 0; n <= Reposicion.MAX_OCUPADAS; n++) {
			assertEquals(Decision.REPONER, Reposicion.decidir(null, reg(UNICA, 0), 10 * DIA, 7, 0, n), "ocupadas " + n);
		}
		for (int n = Reposicion.MAX_OCUPADAS + 1; n <= 27; n++) {
			assertEquals(Decision.ESPERAR, Reposicion.decidir(null, reg(UNICA, 0), 10 * DIA, 7, 0, n), "ocupadas " + n);
		}
	}

	@Test
	void relojHaciaAtrasReiniciaLaCuenta() {
		assertEquals(Decision.REINICIAR, Reposicion.decidir(null, reg(ALDEA, 50 * DIA), 10 * DIA, 7, 0, 0));
	}

	@Test
	void registroIdaYVueltaSinTocarOtrasClaves() {
		CompoundTag cd = new CompoundTag();
		cd.putString(CofrePorJugador.MARK + "_no", "x"); // otra clave cualquiera se conserva
		assertTrue(Reposicion.registro(cd).isEmpty());
		CompoundTag con = Reposicion.conRegistro(cd, new Registro(UNICA, 987654321L));
		assertEquals(Optional.of(new Registro(UNICA, 987654321L)), Reposicion.registro(con));
		assertEquals("x", con.getStringOr(CofrePorJugador.MARK + "_no", ""));
		assertFalse(cd.contains(Reposicion.CLAVE), "no modifica el original");
		// idempotente: volver a escribirlo deja lo mismo
		assertEquals(con, Reposicion.conRegistro(con, new Registro(UNICA, 987654321L)));
		// registros rotos: sin tabla o sin hora, se ignoran
		CompoundTag roto = new CompoundTag();
		CompoundTag r = new CompoundTag();
		r.putString("tabla", ALDEA);
		roto.put(Reposicion.CLAVE, r);
		assertTrue(Reposicion.registro(roto).isEmpty());
	}

	/**
	 * Toda tabla de botín de Heraldia en un contenedor de las plantillas generadas (cofres, barriles) se repone, salvo
	 * ninguna: si un generador nuevo pone un cofre con otra tabla, este test lo dice (y hay que decidir si se repone).
	 */
	@Test
	void lasTablasDeLasPlantillasSeReponen() throws IOException {
		Path root = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/structure");
		List<Path> files = new ArrayList<>();
		try (Stream<Path> s = Files.walk(root)) {
			s.filter(p -> p.toString().endsWith(".nbt")).forEach(files::add);
		}
		TreeSet<String> vistas = new TreeSet<>(), malas = new TreeSet<>();
		for (Path f : files) {
			CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
			for (Tag b : t.getListOrEmpty("blocks")) {
				CompoundTag nbt = ((CompoundTag) b).getCompoundOrEmpty("nbt");
				String id = nbt.getStringOr("id", ""), tabla = nbt.getStringOr("LootTable", "");
				if (tabla.startsWith("heraldia:") && (id.endsWith("chest") || id.endsWith("barrel"))) {
					vistas.add(tabla);
					if (!Reposicion.tablaRepone(tabla)) {
						malas.add(tabla + " (" + root.relativize(f) + ")");
					}
				}
			}
		}
		assertTrue(vistas.size() > 50, "pocas tablas de cofre en las plantillas: " + vistas.size());
		assertTrue(vistas.stream().anyMatch(v -> v.startsWith("heraldia:cofres/")), "ninguna de aldea");
		assertTrue(vistas.stream().anyMatch(v -> v.startsWith("heraldia:medianas/")), "ninguna de mediana");
		assertTrue(vistas.stream().anyMatch(v -> v.startsWith("heraldia:unicas/")), "ninguna de única");
		assertTrue(vistas.stream().anyMatch(v -> v.startsWith("heraldia:minas/")), "ninguna de entrada a mina");
		assertTrue(malas.isEmpty(), "tablas de cofre que no se repondrían: " + malas);
	}
}
