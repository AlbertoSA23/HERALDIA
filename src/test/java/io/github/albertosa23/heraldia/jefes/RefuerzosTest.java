package io.github.albertosa23.heraldia.jefes;

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

/** Elección de refuerzos por única y por familia, y el jefes.json generado contra los registros del juego. */
class RefuerzosTest {
	private static final String JSON = """
			{"version": 1, "generica": "generica",
			 "familias": {"momia": [{"mob": "minecraft:husk"}, {"mob": "minecraft:husk"}],
			              "generica": [{"mob": "minecraft:zombie"}, {"mob": "minecraft:skeleton"}]},
			 "mob_familia": {"minecraft:husk": "momia", "minecraft:raro": "no_existe"},
			 "unicas": {"coliseo": [{"mob": "minecraft:husk", "equipo": {"mainhand": "minecraft:iron_sword"}},
			                        {"mob": "minecraft:witch"}, {"mob": "minecraft:husk"}]}}
			""";

	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void porUnicaYPorFamilia() {
		Refuerzos r = Refuerzos.leer(new StringReader(JSON));
		List<Refuerzos.Refuerzo> col = r.para("coliseo", "minecraft:zombie");     // la única manda sobre el tipo
		assertEquals(3, col.size());
		assertEquals("minecraft:husk", col.get(0).mob());
		assertEquals(Map.of("mainhand", "minecraft:iron_sword"), col.get(0).equipo());
		assertEquals(Map.of(), col.get(1).equipo());
		// única desconocida (o guardián sin id de un mundo viejo): la familia de su tipo
		assertEquals("minecraft:husk", r.para("ya_no_existe", "minecraft:husk").get(0).mob());
		assertEquals("minecraft:husk", r.para(null, "minecraft:husk").get(1).mob());
		// tipo sin familia, o con una familia que no está: la genérica
		assertEquals(List.of("minecraft:zombie", "minecraft:skeleton"), mobs(r.para(null, "minecraft:creeper")));
		assertEquals(List.of("minecraft:zombie", "minecraft:skeleton"), mobs(r.para(null, "minecraft:raro")));
	}

	private static List<String> mobs(List<Refuerzos.Refuerzo> l) {
		return l.stream().map(Refuerzos.Refuerzo::mob).toList();
	}

	/** El del .jar (build/generated): cada única con 2-3 refuerzos de mobs y objetos que existen, en ranuras válidas. */
	@Test
	void generado() throws IOException {
		Path gen = Path.of(System.getProperty("heraldia.generated"));
		Path f = gen.resolve("heraldia/jefes.json");
		Refuerzos r;
		try (Reader in = Files.newBufferedReader(f, StandardCharsets.UTF_8)) {
			r = Refuerzos.leer(in);
		}
		List<String> unicas = new ArrayList<>();
		try (Stream<Path> s = Files.list(gen.resolve("data/heraldia/worldgen/structure/unicas"))) {
			s.forEach(p -> unicas.add(p.getFileName().toString().replace(".json", "")));
		}
		assertFalse(unicas.isEmpty());
		Set<String> ranuras = Set.of("mainhand", "offhand", "head", "chest", "legs", "feet");
		for (String sid : unicas) {
			List<Refuerzos.Refuerzo> l = r.para(sid, "minecraft:creeper");
			assertTrue(l.size() >= 2 && l.size() <= 3, sid + ": " + l);
			for (Refuerzos.Refuerzo x : l) {
				var tipo = BuiltInRegistries.ENTITY_TYPE.getOptional(Identifier.parse(x.mob()));
				assertTrue(tipo.isPresent(), sid + ": " + x.mob());
				assertEquals(MobCategory.MONSTER, tipo.get().getCategory(), sid + ": " + x.mob() + " no es hostil");
				for (Map.Entry<String, String> e : x.equipo().entrySet()) {
					assertTrue(ranuras.contains(e.getKey()), sid + ": ranura " + e.getKey());
					EquipmentSlot.byName(e.getKey());
					assertTrue(BuiltInRegistries.ITEM.getOptional(Identifier.parse(e.getValue())).isPresent(), sid + ": " + e.getValue());
				}
			}
		}
		// el jefe de la Atlántida (guardián anciano) llama a vigías del mar
		assertTrue(mobs(r.para("atlantida", "minecraft:elder_guardian")).contains("minecraft:guardian"));
	}
}
