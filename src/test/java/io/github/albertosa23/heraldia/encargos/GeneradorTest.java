package io.github.albertosa23.heraldia.encargos;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.TreeSet;
import net.minecraft.SharedConstants;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** El tablón de cada aldea: determinista por aldea y periodo, con 2-4 encargos de los tipos que haya alrededor. */
class GeneradorTest {
	static final long SEED = 123456789L;
	static final List<Generador.Objetivo> GUARDIANES = List.of(new Generador.Objetivo("castillo", 900, -300, 950),
			new Generador.Objetivo("catedral", -1800, 400, 1850), new Generador.Objetivo("piramide", 3000, 2000, 3600));
	static final List<Generador.Objetivo> LUGARES = List.of(new Generador.Objetivo("heraldia:medianas/posada/llanuras", 300, 200, 360),
			new Generador.Objetivo("heraldia:minas/pequena/montes", -700, 900, 1140));
	static final List<Generador.Objetivo> VECINAS = List.of(new Generador.Objetivo("Torre del Roble", 1500, 0, 1500));
	static final Generador.Candidatos TODO = new Generador.Candidatos("llanuras", GUARDIANES, LUGARES, VECINAS, true);

	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void mismoTablonConLosMismosDatos() {
		for (long p = 0; p < 20; p++) {
			assertEquals(Generador.tablon(SEED, 10, -20, p, TODO), Generador.tablon(SEED, 10, -20, p, TODO));
		}
	}

	@Test
	void cambiaConElPeriodoLaAldeaYLaSemilla() {
		Set<List<Encargo>> distintos = new HashSet<>();
		for (long p = 0; p < 20; p++) {
			distintos.add(strip(Generador.tablon(SEED, 10, -20, p, TODO)));
		}
		assertTrue(distintos.size() > 10, "el tablón casi no rota: " + distintos.size());
		assertNotEquals(strip(Generador.tablon(SEED, 10, -20, 3, TODO)), strip(Generador.tablon(SEED, 11, -20, 3, TODO)));
		assertNotEquals(strip(Generador.tablon(SEED, 10, -20, 3, TODO)), strip(Generador.tablon(SEED + 1, 10, -20, 3, TODO)));
	}

	/** Sin aldea ni periodo (para comparar el contenido). */
	private static List<Encargo> strip(List<Encargo> t) {
		return t.stream().map(e -> new Encargo(0, 0, 0, e.hueco(), e.tipo(), e.objetivo(), e.cantidad(), e.x(), e.z(), e.esmeraldas(),
				e.experiencia())).toList();
	}

	@Test
	void deDosACuatroConElPrimeroDeTraer() {
		int[] tamanos = new int[Generador.MAX + 1];
		for (long p = 0; p < 300; p++) {
			List<Encargo> t = Generador.tablon(SEED, 3, 4, p, TODO);
			assertTrue(t.size() >= Generador.MIN && t.size() <= Generador.MAX, "tamaño " + t.size());
			tamanos[t.size()]++;
			assertEquals(Tipo.TRAER, t.get(0).tipo());
			assertEquals(Tipo.GUARDIAN, t.get(1).tipo(), "con guardianes cerca, el segundo es de guardián");
			for (int i = 0; i < t.size(); i++) {
				Encargo e = t.get(i);
				assertEquals(i, e.hueco());
				assertEquals(3, e.aldeaX());
				assertEquals(4, e.aldeaZ());
				assertEquals(p, e.periodo());
				assertEquals("3.4." + p + "." + i, e.id());
				assertEquals("3,4", e.aldea());
			}
			assertEquals(t.size(), t.stream().map(Encargo::id).distinct().count());
		}
		for (int n = Generador.MIN; n <= Generador.MAX; n++) {
			assertTrue(tamanos[n] > 30, "casi nunca salen " + n + " encargos");
		}
	}

	@Test
	void salenTodosLosTiposQueHayAlrededor() {
		Set<Tipo> vistos = new TreeSet<>();
		for (long p = 0; p < 200; p++) {
			Generador.tablon(SEED, 0, 0, p, TODO).forEach(e -> vistos.add(e.tipo()));
		}
		assertEquals(Set.of(Tipo.values()), vistos);
	}

	@Test
	void soloLoQueHay() {
		Generador.Candidatos solo = Generador.Candidatos.solo("desierto");
		Generador.Candidatos lugares = new Generador.Candidatos("desierto", List.of(), LUGARES, List.of(), false);
		for (long p = 0; p < 200; p++) {
			List<Encargo> t = Generador.tablon(SEED, 7, 7, p, solo);
			assertTrue(t.stream().allMatch(e -> e.tipo() == Tipo.TRAER), "sin nada alrededor, solo traer: " + t);
			List<Encargo> l = Generador.tablon(SEED, 7, 7, p, lugares);
			assertEquals(Tipo.EXPLORAR, l.get(1).tipo(), "sin guardianes, el segundo es explorar");
			assertTrue(l.stream().noneMatch(e -> e.tipo() == Tipo.GUARDIAN || e.tipo() == Tipo.ARENA || e.tipo() == Tipo.VIAJE));
		}
	}

	@Test
	void objetivosSinRepetirYConSuSitio() {
		for (long p = 0; p < 300; p++) {
			List<Encargo> t = Generador.tablon(SEED, -5, 9, p, TODO);
			List<String> objetos = t.stream().filter(e -> e.tipo() == Tipo.TRAER).map(Encargo::objetivo).toList();
			assertEquals(objetos.size(), new HashSet<>(objetos).size(), "objeto repetido: " + t);
			List<String> guardianes = t.stream().filter(e -> e.tipo() == Tipo.GUARDIAN).map(Encargo::objetivo).toList();
			assertEquals(guardianes.size(), new HashSet<>(guardianes).size(), "guardián repetido: " + t);
			for (Encargo e : t) {
				switch (e.tipo()) {
					case GUARDIAN -> assertTrue(GUARDIANES.stream().anyMatch(o -> o.id().equals(e.objetivo()) && o.x() == e.x() && o.z() == e.z()));
					case EXPLORAR -> assertTrue(LUGARES.stream().anyMatch(o -> o.id().equals(e.objetivo()) && o.x() == e.x() && o.z() == e.z()));
					case VIAJE -> assertEquals("Torre del Roble", e.objetivo());
					case ARENA -> assertTrue(List.of(3, 5, 8).contains(e.cantidad()));
					case TRAER -> assertTrue(Generador.objetos("llanuras").stream().anyMatch(o -> o.id().equals(e.objetivo())
							&& e.cantidad() >= o.min() && e.cantidad() <= o.max()));
				}
				assertEquals(e.conLugar(), e.tipo() == Tipo.GUARDIAN || e.tipo() == Tipo.EXPLORAR || e.tipo() == Tipo.VIAJE);
			}
		}
	}

	@Test
	void elGuardianLejanoEsElMasLejano() {
		boolean visto = false;
		for (long p = 0; p < 200; p++) {
			List<Encargo> t = Generador.tablon(SEED, 1, 1, p, TODO);
			Encargo primero = t.get(1);
			assertTrue(List.of("castillo", "catedral").contains(primero.objetivo()), "el primero, de los dos más cercanos");
			List<Encargo> otros = t.subList(2, t.size()).stream().filter(e -> e.tipo() == Tipo.GUARDIAN).toList();
			for (Encargo e : otros) {
				visto = true;
				assertEquals("piramide", e.objetivo());
				assertEquals(Generador.EM_GUARDIAN_LEJOS, e.esmeraldas(), "lejos paga más");
			}
		}
		assertTrue(visto);
	}

	@Test
	void recompensasModestas() {
		for (String fam : familias()) {
			Generador.Candidatos c = new Generador.Candidatos(fam, GUARDIANES, LUGARES, VECINAS, true);
			for (long p = 0; p < 100; p++) {
				for (Encargo e : Generador.tablon(SEED, 2, 2, p, c)) {
					assertTrue(e.esmeraldas() >= 1 && e.esmeraldas() <= 12, e.toString());
					assertTrue(e.experiencia() > 0 && e.experiencia() <= 120, e.toString());
					assertTrue(e.reputacion() > 0 && e.reputacion() <= 30, e.toString());
				}
			}
		}
	}

	/** Las familias de aldeas del esquema (themes.FAMILIES): cada una con sus materiales del bioma. */
	static Set<String> familias() {
		JsonObject estilos = HeraldiaConfig.get().schema().getAsJsonObject("aldeas").getAsJsonObject("estilos");
		Set<String> out = new TreeSet<>();
		estilos.entrySet().forEach(e -> out.add(e.getValue().getAsString()));
		return out;
	}

	@Test
	void cadaFamiliaTieneSusMaterialesYTodosExisten() {
		assertEquals(familias(), new TreeSet<>(Generador.BIOMA.keySet()));
		List<Generador.Objeto> todos = new ArrayList<>(Generador.COMIDA);
		todos.addAll(Generador.MENAS);
		Generador.BIOMA.values().forEach(todos::addAll);
		for (Generador.Objeto o : todos) {
			assertTrue(BuiltInRegistries.ITEM.containsKey(Identifier.parse(o.id())), "no existe " + o.id());
			assertTrue(o.min() > 0 && o.min() <= o.max() && o.max() <= 64, o.toString());
			assertFalse(o.id().contains("diamond") || o.id().contains("netherite") || o.id().contains("emerald"), o.id());
		}
		for (String fam : familias()) {
			List<Generador.Objeto> l = Generador.objetos(fam);
			assertTrue(l.containsAll(Generador.BIOMA.get(fam)) && l.containsAll(Generador.COMIDA) && l.containsAll(Generador.MENAS));
		}
	}

	@Test
	void periodoYRestante() {
		assertEquals(0, Generador.periodo(0, 3));
		assertEquals(0, Generador.periodo(3 * Generador.DIA - 1, 3));
		assertEquals(1, Generador.periodo(3 * Generador.DIA, 3));
		assertEquals(10, Generador.periodo(10 * Generador.DIA + 5, 1));
		assertEquals(0, Generador.periodo(5, 0), "días < 1 cuenta como 1");
		assertEquals(3 * Generador.DIA, Generador.restante(0, 3));
		assertEquals(1, Generador.restante(3 * Generador.DIA - 1, 3));
		assertEquals(Generador.DIA - 5, Generador.restante(Generador.DIA + 5, 1));
		for (long t : new long[]{0, 5, 3 * Generador.DIA, 7 * Generador.DIA + 123}) {
			long p = Generador.periodo(t, 3);
			assertTrue(Generador.inicio(p, 3) <= t && t < Generador.inicio(p + 1, 3));
		}
	}
}
