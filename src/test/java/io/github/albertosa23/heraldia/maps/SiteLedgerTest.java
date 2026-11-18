package io.github.albertosa23.heraldia.maps;

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
class SiteLedgerTest {
	static final Map<String, String> STYLES = Map.of("llanura", "llanuras", "puerto", "costa");

	@TempDir
	Path dir;

	@Test
	void classifiesById() {
		Site u = Site.of("unicas/atlantida", STYLES, 1, 2, 3);
		assertEquals(Layer.UNIQUES, u.layer());
		assertEquals("atlantida", u.sub());
		assertEquals(Layer.MEDIUMS, Site.of("medianas/torre_vigia/taiga", STYLES, 0, 0, 0).layer());
		assertEquals("torre_vigia", Site.of("medianas/torre_vigia/taiga", STYLES, 0, 0, 0).sub());
		assertEquals("pequena", Site.of("minas/pequena/llanura", STYLES, 0, 0, 0).sub());
		assertEquals(Layer.MINES, Site.of("minas/pequena/llanura", STYLES, 0, 0, 0).layer());
		assertEquals(Layer.COAST, Site.of("costa/faro/templada/a", STYLES, 0, 0, 0).layer());
		assertEquals("naufragio", Site.of("costa/naufragio/nevada/b", STYLES, 0, 0, 0).sub());
		assertEquals(Layer.UNIQUES, Site.of("unicas/faro", STYLES, 0, 0, 0).layer(), "el faro único sigue en las únicas");
		assertEquals("llanuras", Site.of("llanura", STYLES, 0, 0, 0).sub());
		assertEquals("llanuras", Site.of("llanura_grande", STYLES, 0, 0, 0).sub());
		assertEquals(Layer.VILLAGES, Site.of("puerto_grande", STYLES, 0, 0, 0).layer());
		assertNull(Site.of("desconocida", STYLES, 0, 0, 0));
		assertNull(Site.of("medianas/x", STYLES, 0, 0, 0), "una mediana lleva tipo y estilo");
		assertNull(Site.of("unicas/", STYLES, 0, 0, 0));
		assertNull(Site.of("caminos/algo/mas", STYLES, 0, 0, 0));
	}

	@Test
	void ledgerDoesNotRepeatAndSavesOnlyOnChange() throws IOException {
		Ledger r = new Ledger();
		Site a = Site.of("unicas/faro", STYLES, 10, 64, -20);
		assertTrue(r.add(a));
		assertFalse(r.add(Site.of("unicas/faro", STYLES, 10, 64, -20)), "el mismo inicio, dos veces");
		assertTrue(r.add(Site.of("unicas/faro", STYLES, 5000, 64, -20)));
		assertTrue(r.add(Site.of("llanura", STYLES, 0, 70, 0)));
		assertEquals(3, r.size());
		Path f = dir.resolve(Ledger.FILE);
		r.save(f);
		assertTrue(Files.isRegularFile(f));
		long t = Files.getLastModifiedTime(f).toMillis();
		Files.delete(f);
		r.save(f);
		assertFalse(Files.exists(f), "sin cambios no se vuelve a escribir");
		Ledger other = new Ledger();
		r.add(Site.of("minas/grande/llanura", STYLES, 1, 1, 1));
		r.save(f);
		assertEquals(4, other.read(f));
		assertEquals(r.all(), other.all());
		assertEquals(0, other.read(f), "volver a leerlo no duplica nada");
		assertTrue(t > 0);
	}

	@Test
	void brokenFiles() throws IOException {
		Ledger r = new Ledger();
		assertEquals(0, r.read(dir.resolve("no_existe.json")));
		assertEquals(0, r.addJson("no es json"));
		assertEquals(0, r.addJson("[]"));
		assertEquals(1, r.addJson("""
				{"version": 1, "sitios": [
				  {"estructura": "unicas/faro", "capa": "unicas", "sub": "faro", "x": 1, "y": 2, "z": 3},
				  {"estructura": "x", "capa": "capa_que_no_existe", "sub": "x", "x": 1, "y": 2, "z": 3},
				  {"estructura": "y"},
				  7
				]}"""));
		assertEquals(List.of(new Site("unicas/faro", Layer.UNIQUES, "faro", 1, 2, 3)), r.all());
	}

	@Test
	void iconsOfEachLayer() throws IOException {
		Set<Integer> colors = new HashSet<>();
		for (Layer c : Layer.values()) {
			BufferedImage img = ImageIO.read(new ByteArrayInputStream(Icons.png(c)));
			assertEquals(Icons.SIDE, img.getWidth());
			assertEquals(Icons.SIDE, img.getHeight());
			assertEquals(0, img.getRGB(0, 0) >>> 24, "esquina transparente");
			assertEquals(c.color, img.getRGB(3, Icons.SIDE / 2) | 0xFF000000, "relleno del color de la capa");
			colors.add(c.color);
			assertTrue(Icons.image(c) == Icons.image(c), "se dibuja una vez");
		}
		assertEquals(Layer.values().length, colors.size(), "un color por capa");
	}

	@Test
	void layerIds() {
		assertEquals("mapas_web.capas.unicas", Layer.UNIQUES.option());
		assertEquals("heraldia_arena", Layer.ARENA.mapId());
		assertEquals("heraldia.mapas_web.capa.minas", Layer.MINES.nameKey());
	}
}
