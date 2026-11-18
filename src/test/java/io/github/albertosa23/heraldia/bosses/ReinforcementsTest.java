package io.github.albertosa23.heraldia.bosses;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.io.Reader;
import java.io.StringReader;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import net.minecraft.SharedConstants;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.entity.EquipmentSlot;
import net.minecraft.world.entity.MobCategory;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Choice of reinforcements per unique and per family, and the generated jefes.json against the game's registries. */
class ReinforcementsTest {
	private static final String JSON = """
			{"version": 1, "generica": "generica",
			 "familias": {"momia": [{"mob": "minecraft:husk"}, {"mob": "minecraft:husk"}],
			              "generica": [{"mob": "minecraft:zombie"}, {"mob": "minecraft:skeleton"}]},
			 "mob_familia": {"minecraft:husk": "momia", "minecraft:raro": "no_existe"},
			 "unicas": {"coliseo": [{"mob": "minecraft:husk", "equipo": {"mainhand": "minecraft:iron_sword"}},
			                        {"mob": "minecraft:witch"}, {"mob": "minecraft:husk"}]}}
			""";

	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void perUniqueAndPerFamily() {
		Reinforcements r = Reinforcements.read(new StringReader(JSON));
		List<Reinforcements.Reinforcement> col = r.stop("coliseo", "minecraft:zombie");     // the unique overrides the type
		assertEquals(3, col.size());
		assertEquals("minecraft:husk", col.get(0).mob());
		assertEquals(Map.of("mainhand", "minecraft:iron_sword"), col.get(0).equipment());
		assertEquals(Map.of(), col.get(1).equipment());
		// unknown unique (or guardian without an id from an old world): the family of its type
		assertEquals("minecraft:husk", r.stop("ya_no_existe", "minecraft:husk").get(0).mob());
		assertEquals("minecraft:husk", r.stop(null, "minecraft:husk").get(1).mob());
		// type without a family, or with a family that does not exist: the generic one
		assertEquals(List.of("minecraft:zombie", "minecraft:skeleton"), mobs(r.stop(null, "minecraft:creeper")));
		assertEquals(List.of("minecraft:zombie", "minecraft:skeleton"), mobs(r.stop(null, "minecraft:raro")));
	}

	private static List<String> mobs(List<Reinforcements.Reinforcement> l) {
		return l.stream().map(Reinforcements.Reinforcement::mob).toList();
	}

	/** The one in the .jar (build/generated): each unique with 2-3 reinforcements of mobs and items that exist, in valid slots. */
	@Test
	void generated() throws IOException {
		Path gen = Path.of(System.getProperty("heraldia.generated"));
		Path f = gen.resolve("heraldia/jefes.json");
		Reinforcements r;
		try (Reader in = Files.newBufferedReader(f, StandardCharsets.UTF_8)) {
			r = Reinforcements.read(in);
		}
		List<String> uniques = new ArrayList<>();
		try (Stream<Path> s = Files.list(gen.resolve("data/heraldia/worldgen/structure/unicas"))) {
			s.forEach(p -> uniques.add(p.getFileName().toString().replace(".json", "")));
		}
		assertFalse(uniques.isEmpty());
		Set<String> slots = Set.of("mainhand", "offhand", "head", "chest", "legs", "feet");
		for (String sid : uniques) {
			List<Reinforcements.Reinforcement> l = r.stop(sid, "minecraft:creeper");
			assertTrue(l.size() >= 2 && l.size() <= 3, sid + ": " + l);
			for (Reinforcements.Reinforcement x : l) {
				var type = BuiltInRegistries.ENTITY_TYPE.getOptional(Identifier.parse(x.mob()));
				assertTrue(type.isPresent(), sid + ": " + x.mob());
				assertEquals(MobCategory.MONSTER, type.get().getCategory(), sid + ": " + x.mob() + " no es hostil");
				for (Map.Entry<String, String> e : x.equipment().entrySet()) {
					assertTrue(slots.contains(e.getKey()), sid + ": ranura " + e.getKey());
					EquipmentSlot.byName(e.getKey());
					assertTrue(BuiltInRegistries.ITEM.getOptional(Identifier.parse(e.getValue())).isPresent(), sid + ": " + e.getValue());
				}
			}
		}
		// the Atlantis boss (elder guardian) calls sea scouts
		assertTrue(mobs(r.stop("atlantida", "minecraft:elder_guardian")).contains("minecraft:guardian"));
	}
}
