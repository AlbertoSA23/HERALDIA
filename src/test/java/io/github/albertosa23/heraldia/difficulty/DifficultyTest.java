package io.github.albertosa23.heraldia.difficulty;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.difficulty.ModDifficulty.Tier;
import java.util.Set;
import net.minecraft.SharedConstants;
import net.minecraft.core.registries.Registries;
import net.minecraft.resources.Identifier;
import net.minecraft.resources.ResourceKey;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.entity.ai.attributes.AttributeInstance;
import net.minecraft.world.entity.ai.attributes.AttributeModifier;
import net.minecraft.world.entity.ai.attributes.Attributes;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/** Dificultad configurable: niveles, modificadores idempotentes y acumulables, normal = sin cambios, vida y botín. */
class DifficultyTest {
	@BeforeAll
	static void game() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static AttributeInstance health(double base) {
		AttributeInstance a = new AttributeInstance(Attributes.MAX_HEALTH, x -> { });
		a.setBaseValue(base);
		return a;
	}

	@Test
	void optionLevels() {
		assertEquals(Tier.EASY, Tier.of("facil"));
		assertEquals(Tier.NORMAL, Tier.of("normal"));
		assertEquals(Tier.HARD, Tier.of("dificil"));
		assertEquals(Tier.HEROIC, Tier.of("heroica"));
		assertEquals(Tier.NORMAL, Tier.of("imposible"));
		for (Tier n : Tier.values()) {
			assertEquals(n, Tier.of(n.id()));
		}
		// normal es exactamente lo de siempre
		assertEquals(0, Tier.NORMAL.healthMod());
		assertEquals(0, Tier.NORMAL.damageMod());
		assertEquals(1, Tier.NORMAL.loot);
		// más difícil, más vida, daño y botín (y fácil, menos)
		for (int i = 1; i < Tier.values().length; i++) {
			Tier a = Tier.values()[i - 1], b = Tier.values()[i];
			assertTrue(a.health < b.health && a.damage < b.damage && a.loot < b.loot, a + " < " + b);
		}
		// botín modesto
		for (Tier n : Tier.values()) {
			assertTrue(n.loot >= 0.75 && n.loot <= 1.5, n.toString());
		}
	}

	@Test
	void defaultOptionIsNormal() {
		assertEquals("normal", HeraldiaConfig.defaults().get("dificultad.nivel").getAsString());
		assertFalse(HeraldiaConfig.defaults().get("dificultad.escalar_por_jugadores").getAsBoolean());
		assertFalse(HeraldiaConfig.defaults().get("botin.reponer.activado").getAsBoolean());
		var o = HeraldiaConfig.options().stream().filter(x -> x.key().equals("dificultad.nivel")).findFirst().orElseThrow();
		assertTrue(o.isChoice());
		assertEquals(java.util.List.of("facil", "normal", "dificil", "heroica"), o.values());
		assertTrue(o.accept(new com.google.gson.JsonPrimitive("heroica")).isPresent());
		assertTrue(o.accept(new com.google.gson.JsonPrimitive("Heroica")).isEmpty());
		assertTrue(o.accept(new com.google.gson.JsonPrimitive(2)).isEmpty());
	}

	@Test
	void whoItAppliesTo() {
		assertTrue(ModDifficulty.applies(Set.of("heraldia_anclado"), true));
		assertTrue(ModDifficulty.applies(Set.of("heraldia_guardian", "heraldia_guardian.castillo"), true));
		assertTrue(ModDifficulty.applies(Set.of("heraldia_refuerzo", "heraldia_anclado", "heraldia_adulto"), true), "refuerzo de un jefe");
		assertTrue(ModDifficulty.applies(Set.of("heraldia_refuerzo"), true));
		assertEquals(io.github.albertosa23.heraldia.bosses.Phases.REINFORCEMENT, ModDifficulty.REINFORCEMENT);
		assertEquals(io.github.albertosa23.heraldia.bosses.Phases.GUARDIAN, ModDifficulty.GUARDIAN);
		assertEquals(io.github.albertosa23.heraldia.common.Anchoring.TAG, ModDifficulty.ANCHORED);
		assertFalse(ModDifficulty.applies(Set.of("heraldia_anclado"), false), "un gato o un lobo anclado no");
		assertFalse(ModDifficulty.applies(Set.of(), true));
		assertFalse(ModDifficulty.applies(Set.of("heraldia_adulto", "otra"), true));
	}

	@Test
	void modifiersIdempotentAndRecomputed() {
		AttributeInstance a = health(20);
		MobDifficulty.put(a, MobDifficulty.HEALTH, Tier.HEROIC.healthMod());
		assertEquals(40, a.getValue(), 1e-9);
		MobDifficulty.put(a, MobDifficulty.HEALTH, Tier.HEROIC.healthMod());
		MobDifficulty.put(a, MobDifficulty.HEALTH, Tier.HEROIC.healthMod());
		assertEquals(40, a.getValue(), 1e-9, "aplicarlo varias veces (cada carga) no acumula");
		assertEquals(1, a.getModifiers().size());
		// cambia la opción: se recalcula al cargar
		MobDifficulty.put(a, MobDifficulty.HEALTH, Tier.EASY.healthMod());
		assertEquals(15, a.getValue(), 1e-9);
		MobDifficulty.put(a, MobDifficulty.HEALTH, Tier.HARD.healthMod());
		assertEquals(30, a.getValue(), 1e-9);
		// normal: se quita, vuelve a la vida de siempre y sin modificadores
		MobDifficulty.put(a, MobDifficulty.HEALTH, Tier.NORMAL.healthMod());
		assertEquals(20, a.getValue(), 1e-9);
		assertTrue(a.getModifiers().isEmpty());
		// en normal, un mob que nunca tuvo modificador queda igual
		AttributeInstance b = health(33);
		MobDifficulty.put(b, MobDifficulty.HEALTH, 0);
		assertEquals(33, b.getValue(), 1e-9);
		assertTrue(b.getModifiers().isEmpty());
		MobDifficulty.put(null, MobDifficulty.DAMAGE, 0.5); // un mob sin el atributo (sin daño cuerpo a cuerpo): nada
	}

	@Test
	void addToOthersWithoutOverwriting() {
		AttributeInstance a = health(20);
		Identifier boss = Identifier.fromNamespaceAndPath("heraldia", "jefe_fase");
		a.addPermanentModifier(new AttributeModifier(boss, 10, AttributeModifier.Operation.ADD_VALUE));
		MobDifficulty.put(a, MobDifficulty.HEALTH, Tier.HEROIC.healthMod());
		MobDifficulty.put(a, MobDifficulty.PLAYERS, ModDifficulty.extraPlayers(3));
		assertEquals((20 + 10) * (1 + 1.0) * (1 + 0.5), a.getValue(), 1e-9);
		assertEquals(3, a.getModifiers().size());
		MobDifficulty.put(a, MobDifficulty.HEALTH, 0);
		MobDifficulty.put(a, MobDifficulty.PLAYERS, 0);
		assertEquals(30, a.getValue(), 1e-9);
		assertEquals(10, a.getModifier(boss).amount(), "el modificador ajeno sigue");
		assertNull(a.getModifier(MobDifficulty.HEALTH));
		assertEquals(0, MobDifficulty.amount(a, MobDifficulty.HEALTH));
	}

	@Test
	void ownIdentifiers() {
		assertEquals(Heraldia.MOD_ID, MobDifficulty.HEALTH.getNamespace());
		assertEquals(3, Set.of(MobDifficulty.HEALTH, MobDifficulty.DAMAGE, MobDifficulty.PLAYERS).size());
		for (Identifier id : Set.of(MobDifficulty.HEALTH, MobDifficulty.DAMAGE, MobDifficulty.PLAYERS)) {
			assertTrue(id.getPath().startsWith("dificultad_"), id.toString());
		}
	}

	@Test
	void extraPerPlayers() {
		assertEquals(0, ModDifficulty.extraPlayers(0));
		assertEquals(0, ModDifficulty.extraPlayers(1));
		assertEquals(0.25, ModDifficulty.extraPlayers(2));
		assertEquals(0.75, ModDifficulty.extraPlayers(4));
		assertEquals(1.0, ModDifficulty.extraPlayers(5));
		assertEquals(1.0, ModDifficulty.extraPlayers(40));
	}

	@Test
	void healthKeepsRatio() {
		assertEquals(40f, ModDifficulty.readjustHealth(20f, 20, 40));    // entero sigue entero
		assertEquals(15f, ModDifficulty.readjustHealth(20f, 20, 15));
		assertEquals(20f, ModDifficulty.readjustHealth(10f, 20, 40));    // a media vida sigue a media vida
		assertEquals(20f, ModDifficulty.readjustHealth(20f, 20, 20));
		assertEquals(12f, ModDifficulty.readjustHealth(30f, 12, 12), "sin cambio de máxima: no pasa de ella");
		assertTrue(ModDifficulty.readjustHealth(0.0001f, 100, 1) > 0, "vivo sigue vivo");
		assertEquals(0f, ModDifficulty.readjustHealth(0f, 20, 40));
		// ida y vuelta: normal -> heroica -> normal deja la vida igual
		float v = ModDifficulty.readjustHealth(ModDifficulty.readjustHealth(13f, 20, 40), 40, 20);
		assertEquals(13f, v, 1e-5);
	}

	@Test
	void lootAmount() {
		assertEquals(5, ModDifficulty.amount(5, 1, 64, 0.0));
		assertEquals(5, ModDifficulty.amount(5, 1, 64, 0.99));
		assertEquals(6, ModDifficulty.amount(4, 1.5, 64, 0.5));
		assertEquals(5, ModDifficulty.amount(4, 1.25, 64, 0.99));
		assertEquals(5, ModDifficulty.amount(3, 1.5, 64, 0.49));   // 4,5: 5 con azar < 0,5
		assertEquals(4, ModDifficulty.amount(3, 1.5, 64, 0.5));
		assertEquals(1, ModDifficulty.amount(1, 0.75, 64, 0.9), "nunca menos de 1");
		assertEquals(16, ModDifficulty.amount(16, 1.5, 16, 0.0), "no pasa del máximo de la pila");
		assertEquals(0, ModDifficulty.amount(0, 1.5, 64, 0.0));
		// en media, el multiplicador
		double total = 0;
		int n = 10000;
		for (int i = 0; i < n; i++) {
			total += ModDifficulty.amount(3, 1.25, 64, (i + 0.5) / n);
		}
		assertEquals(3.75, total / n, 0.01);
	}

	@Test
	void heraldiaChestTables() {
		assertTrue(MobDifficulty.isChestLoot(key("heraldia:cofres/herreria")));
		assertTrue(MobDifficulty.isChestLoot(key("heraldia:unicas/castillo/armeria")));
		assertTrue(MobDifficulty.isChestLoot(key("heraldia:medianas/posada/despensa")));
		assertTrue(MobDifficulty.isChestLoot(key("heraldia:minas/capataz")), "las entradas a mina (T30) también");
		assertTrue(MobDifficulty.isChestLoot(key("heraldia:costa/camarote")), "y los faros y naufragios (T42)");
		assertFalse(MobDifficulty.isChestLoot(key("heraldia:arena/recompensa_1")), "las recompensas de la arena no");
		assertFalse(MobDifficulty.isChestLoot(key("heraldia:guardianes/castillo/zombie")));
		assertFalse(MobDifficulty.isChestLoot(key("heraldia:trofeos/castillo")));
		assertFalse(MobDifficulty.isChestLoot(key("minecraft:chests/simple_dungeon")));
		assertFalse(MobDifficulty.isChestLoot(null));
	}

	private static ResourceKey<net.minecraft.world.level.storage.loot.LootTable> key(String id) {
		return ResourceKey.create(Registries.LOOT_TABLE, Identifier.parse(id));
	}
}
