package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.google.gson.JsonPrimitive;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Perfiles de juego (opción «perfil», {@link Perfiles}): estándar es exactamente lo de siempre, una opción escrita en el
 * fichero manda sobre el perfil (y el perfil pasa a personalizado si difiere), el perfil nunca toca la generación, la
 * migración de los ficheros de la 0.1.0 no cambia nada, la pantalla guarda lo que difiere del perfil y releer el
 * fichero (el camino de la recarga en caliente) aplica el perfil nuevo.
 */
class PerfilesTest {
	@TempDir
	Path dir;

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private static Perfiles perfiles() {
		return HeraldiaConfig.profiles();
	}

	private static JsonObject json(Path file) throws IOException {
		return JsonParser.parseString(Files.readString(file, StandardCharsets.UTF_8)).getAsJsonObject();
	}

	private Path fichero(String contenido) throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, contenido);
		return f;
	}

	private static boolean tiene(JsonObject root, String clave) {
		String[] p = clave.split("\\.");
		JsonObject n = root;
		for (int i = 0; i < p.length - 1; i++) {
			if (!n.has(p[i])) {
				return false;
			}
			n = n.getAsJsonObject(p[i]);
		}
		return n.has(p[p.length - 1]);
	}

	@Test
	void hayTresPerfilesYFijanOpcionesDeJuego() {
		assertEquals(Set.of("casual", "estandar", "hardcore"), perfiles().nombres());
		List<String> claves = perfiles().claves();
		for (String k : List.of("dificultad.nivel", "dificultad.escalar_por_jugadores", "botin.reponer.activado", "botin.reponer.dias",
				"jefes.refuerzos.activado", "jefes.fases.activado", "arena.experiencia_porcentaje", "arena.oleada.mobs_incremento",
				"arena.oleada.stats_incremento", "jefes.refuerzos.porcentaje", "jefes.refuerzos.maximo_vivos")) {
			assertTrue(claves.contains(k), k);
		}
		ConfigOption perfil = HeraldiaConfig.options().stream().filter(o -> o.key().equals(Perfiles.CLAVE)).findFirst().orElseThrow();
		assertEquals(List.of("casual", "estandar", "hardcore", "personalizado"), perfil.values());
		assertEquals("estandar", perfil.defaultValue().getAsString());
	}

	@Test
	void estandarEsExactamenteElComportamientoDeSiempre() {
		Map<String, JsonPrimitive> defecto = HeraldiaConfig.defaults();
		assertEquals("estandar", defecto.get(Perfiles.CLAVE).getAsString());
		perfiles().valores(Perfiles.ESTANDAR).forEach((k, v) -> assertEquals(defecto.get(k), v, k));
		// sin fichero y con un fichero que solo dice «estandar», los valores de por defecto
		assertEquals(defecto, HeraldiaConfig.readValues(dir.resolve("no.json")));
		// los refuerzos nuevos, por defecto, dan los de antes (100 % y tope 4)
		assertEquals(100, defecto.get("jefes.refuerzos.porcentaje").getAsInt());
		assertEquals(4, defecto.get("jefes.refuerzos.maximo_vivos").getAsInt());
		assertEquals("normal", defecto.get("dificultad.nivel").getAsString());
	}

	@Test
	void estandarEnElFicheroTambien() throws IOException {
		Path f = fichero("{\"version\": 2, \"perfil\": \"estandar\"}");
		HeraldiaConfig.Lectura l = HeraldiaConfig.readWithProfile(f);
		assertEquals(HeraldiaConfig.defaults(), l.values());
		assertEquals("estandar", l.perfil().efectivo());
		assertTrue(l.perfil().fijadas().isEmpty());
	}

	@Test
	void unPerfilFijaSusOpcionesYNadaMas() throws IOException {
		for (String nombre : List.of("casual", "hardcore")) {
			Map<String, JsonPrimitive> v = HeraldiaConfig.readValues(fichero("{\"perfil\": \"" + nombre + "\"}"));
			Map<String, JsonPrimitive> perfil = perfiles().valores(nombre);
			Map<String, JsonPrimitive> defecto = HeraldiaConfig.defaults();
			for (String k : defecto.keySet()) {
				if (perfil.containsKey(k)) {
					assertEquals(perfil.get(k), v.get(k), nombre + ": " + k);
				} else if (!k.equals(Perfiles.CLAVE)) {
					assertEquals(defecto.get(k), v.get(k), nombre + " no debe tocar " + k);
				}
			}
		}
		Map<String, JsonPrimitive> h = HeraldiaConfig.readValues(fichero("{\"perfil\": \"hardcore\"}"));
		assertEquals("heroica", h.get("dificultad.nivel").getAsString());
		assertTrue(h.get("jefes.refuerzos.porcentaje").getAsInt() > 100 && h.get("jefes.refuerzos.maximo_vivos").getAsInt() > 4, "más refuerzos");
		assertTrue(h.get("arena.experiencia_porcentaje").getAsInt() < 15, "menos experiencia");
		Map<String, JsonPrimitive> c = HeraldiaConfig.readValues(fichero("{\"perfil\": \"casual\"}"));
		assertEquals("facil", c.get("dificultad.nivel").getAsString());
		assertTrue(c.get("botin.reponer.activado").getAsBoolean(), "casual: con el botín que se repone");
	}

	@Test
	void elPerfilNuncaTocaLaGeneracion() {
		Set<String> gen = perfiles().generacion();
		for (String k : perfiles().claves()) {
			assertFalse(gen.contains(k), k);
			for (String prefijo : List.of("aldeas.", "unicas.", "medianas.", "minas.", "compatibilidad.")) {
				assertFalse(k.startsWith(prefijo), k);
			}
		}
		assertFalse(perfiles().claves().contains("arena.generar_en_mundos_nuevos"));
		// las opciones de la generación están marcadas en el esquema
		for (ConfigOption o : HeraldiaConfig.options()) {
			if (o.key().startsWith("aldeas.separacion") || o.key().startsWith("unicas.") || o.key().startsWith("medianas.")
					|| o.key().startsWith("minas.") || o.key().equals("arena.generar_en_mundos_nuevos")) {
				assertTrue(gen.contains(o.key()), o.key());
			}
		}
		assertTrue(gen.size() > 100, "opciones de la generación: " + gen.size());
	}

	@Test
	void unaOpcionEnElFicheroMandaSobreElPerfil() throws IOException {
		Path f = fichero("{\"perfil\": \"hardcore\", \"dificultad\": {\"nivel\": \"normal\"}, \"arena\": {\"experiencia_porcentaje\": 5}}");
		HeraldiaConfig c = HeraldiaConfig.load(f);
		assertEquals("normal", c.getString("dificultad.nivel"), "lo del fichero manda");
		assertEquals("hardcore", c.profile().elegido());
		assertEquals("personalizado", c.profile().efectivo(), "una opción distinta del perfil: personalizado");
		assertEquals(Set.of("dificultad.nivel"), c.profile().difieren().keySet(), "solo difiere la que no es la del perfil");
		assertEquals("heroica", c.profile().difieren().get("dificultad.nivel")[1].getAsString());
		assertEquals(Set.of("dificultad.nivel", "arena.experiencia_porcentaje"), c.profile().fijadas().keySet());
		assertEquals(perfiles().valores("hardcore").get("jefes.refuerzos.maximo_vivos"), c.values().get("jefes.refuerzos.maximo_vivos"));
		// al reescribirse, lo fijado a mano sigue en el fichero (y lo demás del perfil no)
		JsonObject root = json(f);
		assertTrue(tiene(root, "dificultad.nivel") && tiene(root, "arena.experiencia_porcentaje"));
		assertFalse(tiene(root, "jefes.refuerzos.maximo_vivos"));
		assertEquals("personalizado", root.getAsJsonObject("_perfil").get("efectivo").getAsString());
		assertTrue(root.getAsJsonObject("_perfil").getAsJsonObject("difieren").has("dificultad.nivel"));
		// y al volver a leerlo, lo mismo
		assertEquals(c.values(), HeraldiaConfig.readValues(f));
	}

	@Test
	void fijadaConElValorDelPerfilNoLoCambia() throws IOException {
		HeraldiaConfig c = HeraldiaConfig.load(fichero("{\"perfil\": \"casual\", \"dificultad\": {\"nivel\": \"facil\"}}"));
		assertEquals("casual", c.profile().efectivo());
		assertTrue(c.profile().difieren().isEmpty());
		assertEquals(Set.of("dificultad.nivel"), c.profile().fijadas().keySet());
	}

	@Test
	void personalizadoNoFijaNada() throws IOException {
		HeraldiaConfig c = HeraldiaConfig.load(fichero("{\"perfil\": \"personalizado\", \"botin\": {\"reponer\": {\"activado\": true}}}"));
		assertEquals("personalizado", c.profile().efectivo());
		assertTrue(c.profile().difieren().isEmpty());
		assertTrue(c.getBool("botin.reponer.activado"));
		Map<String, JsonPrimitive> defecto = HeraldiaConfig.defaults();
		for (String k : perfiles().claves()) {
			if (!k.equals("botin.reponer.activado")) {
				assertEquals(defecto.get(k), c.values().get(k), k);
			}
		}
	}

	@Test
	void valoresNoValidos() throws IOException {
		// un perfil que no existe: el de por defecto; una opción del perfil fuera de rango: la del perfil, sin fijarla
		HeraldiaConfig c = HeraldiaConfig.load(fichero("{\"perfil\": \"imposible\"}"));
		assertEquals("estandar", c.profile().elegido());
		c = HeraldiaConfig.load(fichero("{\"perfil\": \"hardcore\", \"arena\": {\"max_mobs_vivos\": 999}, \"jefes\": {\"refuerzos\": {\"porcentaje\": \"x\"}}}"));
		assertEquals(perfiles().valores("hardcore").get("arena.max_mobs_vivos"), c.values().get("arena.max_mobs_vivos"));
		assertEquals(perfiles().valores("hardcore").get("jefes.refuerzos.porcentaje"), c.values().get("jefes.refuerzos.porcentaje"));
		assertTrue(c.profile().fijadas().isEmpty());
		assertEquals("hardcore", c.profile().efectivo());
	}

	/** Fichero de la 0.1.0 (versión 1): el mod escribía todas las opciones con su valor. */
	private Path ficheroV1(Map<String, JsonPrimitive> valores) throws IOException {
		JsonObject root = new JsonObject();
		root.addProperty("version", 1);
		valores.forEach((k, v) -> {
			if (k.equals(Perfiles.CLAVE) || k.startsWith("jefes.refuerzos.porcentaje") || k.startsWith("jefes.refuerzos.maximo_vivos")) {
				return;                      // no existían
			}
			String[] p = k.split("\\.");
			JsonObject n = root;
			for (int i = 0; i < p.length - 1; i++) {
				if (!n.has(p[i])) {
					n.add(p[i], new JsonObject());
				}
				n = n.getAsJsonObject(p[i]);
			}
			n.add(p[p.length - 1], v);
		});
		return fichero(root.toString());
	}

	@Test
	void migrarUnFicheroDeLa010NoCambiaNada() throws IOException {
		Path f = ficheroV1(HeraldiaConfig.defaults());
		HeraldiaConfig c = HeraldiaConfig.load(f);
		assertEquals(HeraldiaConfig.defaults(), c.values());
		assertEquals("estandar", c.profile().efectivo());
		assertTrue(c.profile().fijadas().isEmpty(), "lo que escribía el mod no cuenta como fijado a mano");
		JsonObject root = json(f);
		assertEquals(2, root.get("version").getAsInt());
		for (String k : perfiles().claves()) {
			assertFalse(tiene(root, k), "tras migrar no se escribe " + k);
		}
		// y ahora cambiar de perfil en el fichero sí hace algo
		root.addProperty("perfil", "hardcore");
		Files.writeString(f, root.toString());
		assertEquals("heroica", HeraldiaConfig.load(f).getString("dificultad.nivel"));
	}

	@Test
	void migrarConservaLoQueSeCambioAMano() throws IOException {
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put("dificultad.nivel", new JsonPrimitive("dificil"));
		v.put("botin.reponer.activado", new JsonPrimitive(true));
		v.put("aldeas.separacion_bloques", new JsonPrimitive(2500));
		HeraldiaConfig c = HeraldiaConfig.load(ficheroV1(v));
		assertEquals("dificil", c.getString("dificultad.nivel"));
		assertTrue(c.getBool("botin.reponer.activado"));
		assertEquals(2500, c.getInt("aldeas.separacion_bloques"));
		assertEquals(Set.of("dificultad.nivel", "botin.reponer.activado"), c.profile().fijadas().keySet());
		assertEquals("personalizado", c.profile().efectivo());
		Map<String, JsonPrimitive> esperado = new LinkedHashMap<>(v);
		assertEquals(esperado, c.values(), "los mismos valores que en la 0.1.0");
	}

	@Test
	void laPantallaGuardaLoQueDifiereDelPerfil() throws IOException {
		Path f = dir.resolve("pantalla.json");
		Map<String, JsonPrimitive> v = new LinkedHashMap<>(HeraldiaConfig.defaults());
		v.put(Perfiles.CLAVE, new JsonPrimitive("hardcore"));
		v.putAll(perfiles().valores("hardcore"));
		v.put("arena.max_mobs_vivos", new JsonPrimitive(40));
		HeraldiaConfig.save(f, v);
		JsonObject root = json(f);
		assertTrue(tiene(root, "arena.max_mobs_vivos"));
		assertFalse(tiene(root, "dificultad.nivel"), "lo que da el perfil no se escribe");
		HeraldiaConfig.Lectura l = HeraldiaConfig.readWithProfile(f);
		assertEquals(v, l.values());
		assertEquals(Set.of("arena.max_mobs_vivos"), l.perfil().fijadas().keySet());
		assertEquals(Set.of("arena.max_mobs_vivos"), perfiles().fijadasPorDiferencia("hardcore", v));
	}

	@Test
	void releerElFicheroAplicaElPerfilNuevo() throws IOException {
		// el camino de la recarga en caliente: HeraldiaConfig.load otra vez con el fichero cambiado
		Path f = fichero("{\"perfil\": \"casual\"}");
		assertEquals("facil", HeraldiaConfig.load(f).getString("dificultad.nivel"));
		assertEquals("facil", HeraldiaConfig.get().getString("dificultad.nivel"));
		JsonObject root = json(f);
		root.addProperty("perfil", "hardcore");
		Files.writeString(f, root.toString());
		HeraldiaConfig.load(f);
		assertEquals("heroica", HeraldiaConfig.get().getString("dificultad.nivel"));
		assertEquals("hardcore", HeraldiaConfig.get().profile().efectivo());
		root = json(f);
		root.addProperty("perfil", "estandar");
		Files.writeString(f, root.toString());
		assertEquals(HeraldiaConfig.defaults(), HeraldiaConfig.load(f).values());
	}

	@Test
	void laAyudaDelFicheroDiceLosValoresDeCadaPerfil() throws IOException {
		Path f = dir.resolve("ayuda.json");
		HeraldiaConfig.load(f);
		JsonObject root = json(f);
		String es = root.getAsJsonObject("_ayuda").getAsJsonObject("es_es").get("dificultad.nivel").getAsString();
		assertTrue(es.contains("casual facil") && es.contains("hardcore heroica"), es);
		assertTrue(root.getAsJsonObject("_ayuda").getAsJsonObject("en_us").has("perfil"));
		assertEquals("estandar", root.get("perfil").getAsString());
		assertNotEquals(null, root.getAsJsonObject("_perfil"));
	}

	@Test
	void aplicarEsLogicaPura() {
		Perfiles p = perfiles();
		Perfiles.Aplicado a = p.aplicar("hardcore", Map.of());
		assertEquals(p.valores("hardcore"), a.valores());
		assertEquals("hardcore", a.efectivo());
		a = p.aplicar("hardcore", Map.of("dificultad.nivel", new JsonPrimitive("heroica")));
		assertEquals("hardcore", a.efectivo());
		a = p.aplicar("hardcore", Map.of("dificultad.nivel", new JsonPrimitive("facil")));
		assertEquals("personalizado", a.efectivo());
		assertEquals("facil", a.valores().get("dificultad.nivel").getAsString());
		assertEquals(p.valores(Perfiles.ESTANDAR), p.valores(Perfiles.PERSONALIZADO), "personalizado parte de los de por defecto");
	}
}
