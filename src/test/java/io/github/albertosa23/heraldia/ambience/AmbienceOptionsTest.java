package io.github.albertosa23.heraldia.ambience;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.config.ConfigOption;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.Reload;
import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.AfterEach;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** The ambience options as the generator writes them: on by default, reloadable, in their own section. */
class AmbienceOptionsTest {
	private static final List<String> KEYS = List.of(Ambience.ENABLED, Ambience.BELLS, Ambience.SIREN, Ambience.MINES);

	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@AfterEach
	void restore() {
		HeraldiaConfig.load(null);
	}

	@Test
	void onByDefaultReloadableAndInTheirSection() {
		HeraldiaConfig.load(null);
		assertTrue(HeraldiaConfig.sections().containsKey("ambiente"));
		for (String k : KEYS) {
			ConfigOption o = HeraldiaConfig.options().stream().filter(x -> x.key().equals(k)).findFirst().orElseThrow();
			assertTrue(HeraldiaConfig.get().getBool(k), k);
			assertTrue(Reload.reloadable(k), k + " applies with /heraldia reload");
			assertEquals("ambiente", o.section(), k);
			assertTrue(o.isBoolean(), k);
		}
	}
}
