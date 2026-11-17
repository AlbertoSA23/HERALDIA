package io.github.albertosa23.heraldia.mapas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.awt.image.BufferedImage;
import java.io.ByteArrayInputStream;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import javax.imageio.ImageIO;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** Clasificación de las estructuras por su id, el registro de las conocidas (con su fichero) y los iconos. */
class SitioRegistroTest {
	static final Map<String, String> ESTILOS = Map.of("llanura", "llanuras", "puerto", "costa");

	@TempDir
	Path dir;

	@Test
	void clasificaPorElId() {
		Sitio u = Sitio.de("unicas/atlantida", ESTILOS, 1, 2, 3);
		assertEquals(Capa.UNICAS, u.capa());
		assertEquals("atlantida", u.sub());
		assertEquals(Capa.MEDIANAS, Sitio.de("medianas/torre_vigia/taiga", ESTILOS, 0, 0, 0).capa());
		assertEquals("torre_vigia", Sitio.de("medianas/torre_vigia/taiga", ESTILOS, 0, 0, 0).sub());
		assertEquals("pequena", Sitio.de("minas/pequena/llanura", ESTILOS, 0, 0, 0).sub());
		assertEquals(Capa.MINAS, Sitio.de("minas/pequena/llanura", ESTILOS, 0, 0, 0).capa());
		assertEquals(Capa.COSTA, Sitio.de("costa/faro/templada/a", ESTILOS, 0, 0, 0).capa());
		assertEquals("naufragio", Sitio.de("costa/naufragio/nevada/b", ESTILOS, 0, 0, 0).sub());
		assertEquals(Capa.UNICAS, Sitio.de("unicas/faro", ESTILOS, 0, 0, 0).capa(), "el faro único sigue en las únicas");
		assertEquals("llanuras", Sitio.de("llanura", ESTILOS, 0, 0, 0).sub());
		assertEquals("llanuras", Sitio.de("llanura_grande", ESTILOS, 0, 0, 0).sub());
		assertEquals(Capa.ALDEAS, Sitio.de("puerto_grande", ESTILOS, 0, 0, 0).capa());
		assertNull(Sitio.de("desconocida", ESTILOS, 0, 0, 0));
		assertNull(Sitio.de("medianas/x", ESTILOS, 0, 0, 0), "una mediana lleva tipo y estilo");
		assertNull(Sitio.de("unicas/", ESTILOS, 0, 0, 0));
		assertNull(Sitio.de("caminos/algo/mas", ESTILOS, 0, 0, 0));
	}

	@Test
	void elRegistroNoRepiteYGuardaSoloSiCambia() throws IOException {
		Registro r = new Registro();
		Sitio a = Sitio.de("unicas/faro", ESTILOS, 10, 64, -20);
		assertTrue(r.anadir(a));
		assertFalse(r.anadir(Sitio.de("unicas/faro", ESTILOS, 10, 64, -20)), "el mismo inicio, dos veces");
		assertTrue(r.anadir(Sitio.de("unicas/faro", ESTILOS, 5000, 64, -20)));
		assertTrue(r.anadir(Sitio.de("llanura", ESTILOS, 0, 70, 0)));
		assertEquals(3, r.tamano());
		Path f = dir.resolve(Registro.FICHERO);
		r.guardar(f);
		assertTrue(Files.isRegularFile(f));
		long t = Files.getLastModifiedTime(f).toMillis();
		Files.delete(f);
		r.guardar(f);
		assertFalse(Files.exists(f), "sin cambios no se vuelve a escribir");
		Registro otro = new Registro();
		r.anadir(Sitio.de("minas/grande/llanura", ESTILOS, 1, 1, 1));
		r.guardar(f);
		assertEquals(4, otro.leer(f));
		assertEquals(r.todos(), otro.todos());
		assertEquals(0, otro.leer(f), "volver a leerlo no duplica nada");
		assertTrue(t > 0);
	}

	@Test
	void ficherosRotos() throws IOException {
		Registro r = new Registro();
		assertEquals(0, r.leer(dir.resolve("no_existe.json")));
		assertEquals(0, r.sumarJson("no es json"));
		assertEquals(0, r.sumarJson("[]"));
		assertEquals(1, r.sumarJson("""
				{"version": 1, "sitios": [
				  {"estructura": "unicas/faro", "capa": "unicas", "sub": "faro", "x": 1, "y": 2, "z": 3},
				  {"estructura": "x", "capa": "capa_que_no_existe", "sub": "x", "x": 1, "y": 2, "z": 3},
				  {"estructura": "y"},
				  7
				]}"""));
		assertEquals(List.of(new Sitio("unicas/faro", Capa.UNICAS, "faro", 1, 2, 3)), r.todos());
	}

	@Test
	void iconosDeCadaCapa() throws IOException {
		Set<Integer> colores = new HashSet<>();
		for (Capa c : Capa.values()) {
			BufferedImage img = ImageIO.read(new ByteArrayInputStream(Iconos.png(c)));
			assertEquals(Iconos.LADO, img.getWidth());
			assertEquals(Iconos.LADO, img.getHeight());
			assertEquals(0, img.getRGB(0, 0) >>> 24, "esquina transparente");
			assertEquals(c.color, img.getRGB(3, Iconos.LADO / 2) | 0xFF000000, "relleno del color de la capa");
			colores.add(c.color);
			assertTrue(Iconos.imagen(c) == Iconos.imagen(c), "se dibuja una vez");
		}
		assertEquals(Capa.values().length, colores.size(), "un color por capa");
	}

	@Test
	void idsDeLasCapas() {
		assertEquals("mapas_web.capas.unicas", Capa.UNICAS.opcion());
		assertEquals("heraldia_arena", Capa.ARENA.idMapa());
		assertEquals("heraldia.mapas_web.capa.minas", Capa.MINAS.claveNombre());
	}
}
