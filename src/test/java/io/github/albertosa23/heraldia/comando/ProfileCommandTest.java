package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/** /heraldia profile: el perfil efectivo y el elegido, una línea por opción del perfil y las fijadas a mano marcadas. */
class ProfileCommandTest {
	@TempDir
	Path dir;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	private static String clave(Component c) {
		return ((TranslatableContents) c.getContents()).getKey();
	}

	@Test
	void conUnaOpcionFijadaAMano() throws IOException {
		Path f = dir.resolve("heraldia.json");
		Files.writeString(f, "{\"perfil\": \"hardcore\", \"dificultad\": {\"nivel\": \"facil\"}}");
		HeraldiaConfig cfg = HeraldiaConfig.load(f);
		List<Component> lines = ProfileCommand.lines(cfg);
		assertEquals(HeraldiaConfig.profiles().claves().size() + 2, lines.size());
		assertEquals("heraldia.perfil.titulo", clave(lines.get(0)));
		assertTrue(lines.get(0).getString().contains("Personalizado") && lines.get(0).getString().contains("Hardcore"), lines.get(0).getString());
		long fijadas = lines.stream().filter(l -> clave(l).equals("heraldia.perfil.opcion.fijada")).count();
		assertEquals(1, fijadas);
		assertTrue(lines.stream().anyMatch(l -> l.getString().contains("dificultad.nivel = facil") && l.getString().contains("heroica")));
		assertEquals("heraldia.perfil.personalizado", clave(lines.getLast()));
	}

	@Test
	void sinNadaFijado() {
		List<Component> lines = ProfileCommand.lines(HeraldiaConfig.get());
		assertTrue(lines.get(0).getString().contains("Estándar"), lines.get(0).getString());
		assertEquals("heraldia.perfil.ninguna", clave(lines.getLast()));
		assertTrue(lines.stream().noneMatch(l -> clave(l).equals("heraldia.perfil.opcion.fijada")));
	}
}
