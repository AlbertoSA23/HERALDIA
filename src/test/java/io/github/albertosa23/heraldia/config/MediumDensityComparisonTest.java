package io.github.albertosa23.heraldia.config;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import org.junit.jupiter.api.AfterAll;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * How the medium structures feel at several frequencies (the simulation of {@link MediumFrequencyTest}: real 26.3 biomes,
 * three seeds, 16 x 16 km each): average separation of everything, mediums passed per kilometre walked, and each type on its
 * own, so that lowering the density does not make one type disappear in practice. It prints the table used to choose the
 * default frequency (docs/CONFIGURATION.md, "Medium structures density") and checks that the old density (100 %) is still the
 * one of before and that every type keeps spawning in every seed at every frequency down to that of the light profile.
 * Long (one simulation per frequency): it runs in testPesado.
 */
class MediumDensityComparisonTest {
	/** The previous density (100 %), intermediate ones, the new default (60), the light profile (50) and lower ones. */
	static final int[] FREQUENCIES = {100, 85, 70, 60, 50, 40, 25};

	@BeforeAll
	static void bootstrap() {
		MediumFrequencyTest.bootstrap();
	}

	@AfterAll
	static void restore() {
		MediumFrequencyTest.restore();
	}

	private static String config(int frequency) {
		return "{\"medianas\": {\"frecuencia_porcentaje\": " + frequency + "}}";
	}

	@Test
	void densityTable() throws IOException {
		List<MediumFrequencyTest.Simulation> sims = new ArrayList<>();
		for (int f : FREQUENCIES) {
			sims.add(MediumFrequencyTest.simulate(config(f)));
		}
		StringBuilder t = new StringBuilder("frecuencia | una cada (bloques) | por km de paseo | km entre dos | tipo más raro (una cada) | mínimo de un tipo en una semilla\n");
		for (MediumFrequencyTest.Simulation s : sims) {
			String rarest = null;
			int min = Integer.MAX_VALUE;
			for (Map.Entry<String, int[]> e : s.perType().entrySet()) {
				if (rarest == null || s.each(e.getKey()) > s.each(rarest)) {
					rarest = e.getKey();
				}
				for (int n : e.getValue()) {
					min = Math.min(min, n);
				}
			}
			t.append(String.format("%d %% | %.0f | %.2f | %.2f | %s (%.0f) | %d%n", s.frequency(), s.each(), s.perKm(), 1 / s.perKm(),
					rarest, s.each(rarest), min));
		}
		t.append("por tipo (una cada, bloques):\n");
		for (String type : sims.getFirst().perType().keySet()) {
			t.append("  ").append(type);
			for (MediumFrequencyTest.Simulation s : sims) {
				int[] n = s.perType().get(type);
				t.append(String.format(" | %d %%: %.0f (%d/%d/%d)", s.frequency(), s.each(type), n[0], n[1], n[2]));
			}
			t.append('\n');
		}
		sims.forEach(s -> System.out.print("frecuencia " + s.frequency() + " %:\n" + s.report()));
		System.out.print(t);
		for (int i = 0; i < FREQUENCIES.length; i++) {
			assertEquals(FREQUENCIES[i], sims.get(i).frequency(), "la frecuencia en uso");
			for (Map.Entry<String, int[]> e : sims.get(i).perType().entrySet()) {
				for (int n : e.getValue()) {
					assertTrue(n >= MediumFrequencyTest.MIN_PER_TYPE * 0.6, e.getKey() + " casi desaparece al " + FREQUENCIES[i] + " %\n" + t);
				}
			}
			if (FREQUENCIES[i] == HeraldiaConfig.defaults().get("medianas.frecuencia_porcentaje").getAsInt()) {
				// the default really thins them out: at least 15 % fewer than the previous density (100 %, FREQUENCIES[0])
				assertTrue(sims.get(i).total() <= 0.85 * sims.getFirst().total(), "el valor por defecto apenas cambia la densidad\n" + t);
			}
			if (i > 0) {
				assertTrue(sims.get(i).total() < sims.get(i - 1).total(), "menos frecuencia, menos medianas\n" + t);
			}
		}
	}
}
