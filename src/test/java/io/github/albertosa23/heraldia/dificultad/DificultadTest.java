package io.github.albertosa23.heraldia.dificultad;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.dificultad.Dificultad.Nivel;
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
class DificultadTest {
	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static AttributeInstance vida(double base) {
		AttributeInstance a = new AttributeInstance(Attributes.MAX_HEALTH, x -> { });
		a.setBaseValue(base);
		return a;
	}

	@Test
	void nivelesDeLaOpcion() {
		assertEquals(Nivel.FACIL, Nivel.de("facil"));
		assertEquals(Nivel.NORMAL, Nivel.de("normal"));
		assertEquals(Nivel.DIFICIL, Nivel.de("dificil"));
		assertEquals(Nivel.HEROICA, Nivel.de("heroica"));
		assertEquals(Nivel.NORMAL, Nivel.de("imposible"));
		for (Nivel n : Nivel.values()) {
			assertEquals(n, Nivel.de(n.id()));
		}
		// normal es exactamente lo de siempre
		assertEquals(0, Nivel.NORMAL.modVida());
		assertEquals(0, Nivel.NORMAL.modDano());
		assertEquals(1, Nivel.NORMAL.botin);
		// más difícil, más vida, daño y botín (y fácil, menos)
		for (int i = 1; i < Nivel.values().length; i++) {
			Nivel a = Nivel.values()[i - 1], b = Nivel.values()[i];
			assertTrue(a.vida < b.vida && a.dano < b.dano && a.botin < b.botin, a + " < " + b);
		}
		// botín modesto
		for (Nivel n : Nivel.values()) {
			assertTrue(n.botin >= 0.75 && n.botin <= 1.5, n.toString());
		}
	}

	@Test
	void laOpcionPorDefectoEsNormal() {
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
	void aQuienSeAplica() {
		assertTrue(Dificultad.aplica(Set.of("heraldia_anclado"), true));
		assertTrue(Dificultad.aplica(Set.of("heraldia_guardian", "heraldia_guardian.castillo"), true));
		assertTrue(Dificultad.aplica(Set.of("heraldia_refuerzo", "heraldia_anclado", "heraldia_adulto"), true), "refuerzo de un jefe");
		assertTrue(Dificultad.aplica(Set.of("heraldia_refuerzo"), true));
		assertEquals(io.github.albertosa23.heraldia.jefes.Fases.REFUERZO, Dificultad.REFUERZO);
		assertEquals(io.github.albertosa23.heraldia.jefes.Fases.GUARDIAN, Dificultad.GUARDIAN);
		assertEquals(io.github.albertosa23.heraldia.comun.Anclaje.TAG, Dificultad.ANCLADO);
		assertFalse(Dificultad.aplica(Set.of("heraldia_anclado"), false), "un gato o un lobo anclado no");
		assertFalse(Dificultad.aplica(Set.of(), true));
		assertFalse(Dificultad.aplica(Set.of("heraldia_adulto", "otra"), true));
	}

	@Test
	void modificadoresIdempotentesYRecalculados() {
		AttributeInstance a = vida(20);
		DificultadMobs.poner(a, DificultadMobs.VIDA, Nivel.HEROICA.modVida());
		assertEquals(40, a.getValue(), 1e-9);
		DificultadMobs.poner(a, DificultadMobs.VIDA, Nivel.HEROICA.modVida());
		DificultadMobs.poner(a, DificultadMobs.VIDA, Nivel.HEROICA.modVida());
		assertEquals(40, a.getValue(), 1e-9, "aplicarlo varias veces (cada carga) no acumula");
		assertEquals(1, a.getModifiers().size());
		// cambia la opción: se recalcula al cargar
		DificultadMobs.poner(a, DificultadMobs.VIDA, Nivel.FACIL.modVida());
		assertEquals(15, a.getValue(), 1e-9);
		DificultadMobs.poner(a, DificultadMobs.VIDA, Nivel.DIFICIL.modVida());
		assertEquals(30, a.getValue(), 1e-9);
		// normal: se quita, vuelve a la vida de siempre y sin modificadores
		DificultadMobs.poner(a, DificultadMobs.VIDA, Nivel.NORMAL.modVida());
		assertEquals(20, a.getValue(), 1e-9);
		assertTrue(a.getModifiers().isEmpty());
		// en normal, un mob que nunca tuvo modificador queda igual
		AttributeInstance b = vida(33);
		DificultadMobs.poner(b, DificultadMobs.VIDA, 0);
		assertEquals(33, b.getValue(), 1e-9);
		assertTrue(b.getModifiers().isEmpty());
		DificultadMobs.poner(null, DificultadMobs.DANO, 0.5); // un mob sin el atributo (sin daño cuerpo a cuerpo): nada
	}

	@Test
	void seSumanALosDeOtrosSinPisarlos() {
		AttributeInstance a = vida(20);
		Identifier jefe = Identifier.fromNamespaceAndPath("heraldia", "jefe_fase");
		a.addPermanentModifier(new AttributeModifier(jefe, 10, AttributeModifier.Operation.ADD_VALUE));
		DificultadMobs.poner(a, DificultadMobs.VIDA, Nivel.HEROICA.modVida());
		DificultadMobs.poner(a, DificultadMobs.JUGADORES, Dificultad.extraJugadores(3));
		assertEquals((20 + 10) * (1 + 1.0) * (1 + 0.5), a.getValue(), 1e-9);
		assertEquals(3, a.getModifiers().size());
		DificultadMobs.poner(a, DificultadMobs.VIDA, 0);
		DificultadMobs.poner(a, DificultadMobs.JUGADORES, 0);
		assertEquals(30, a.getValue(), 1e-9);
		assertEquals(10, a.getModifier(jefe).amount(), "el modificador ajeno sigue");
		assertNull(a.getModifier(DificultadMobs.VIDA));
		assertEquals(0, DificultadMobs.cantidad(a, DificultadMobs.VIDA));
	}

	@Test
	void identificadoresPropios() {
		assertEquals(Heraldia.MOD_ID, DificultadMobs.VIDA.getNamespace());
		assertEquals(3, Set.of(DificultadMobs.VIDA, DificultadMobs.DANO, DificultadMobs.JUGADORES).size());
		for (Identifier id : Set.of(DificultadMobs.VIDA, DificultadMobs.DANO, DificultadMobs.JUGADORES)) {
			assertTrue(id.getPath().startsWith("dificultad_"), id.toString());
		}
	}

	@Test
	void extraPorJugadores() {
		assertEquals(0, Dificultad.extraJugadores(0));
		assertEquals(0, Dificultad.extraJugadores(1));
		assertEquals(0.25, Dificultad.extraJugadores(2));
		assertEquals(0.75, Dificultad.extraJugadores(4));
		assertEquals(1.0, Dificultad.extraJugadores(5));
		assertEquals(1.0, Dificultad.extraJugadores(40));
	}

	@Test
	void vidaConservaLaProporcion() {
		assertEquals(40f, Dificultad.reajustarVida(20f, 20, 40));    // entero sigue entero
		assertEquals(15f, Dificultad.reajustarVida(20f, 20, 15));
		assertEquals(20f, Dificultad.reajustarVida(10f, 20, 40));    // a media vida sigue a media vida
		assertEquals(20f, Dificultad.reajustarVida(20f, 20, 20));
		assertEquals(12f, Dificultad.reajustarVida(30f, 12, 12), "sin cambio de máxima: no pasa de ella");
		assertTrue(Dificultad.reajustarVida(0.0001f, 100, 1) > 0, "vivo sigue vivo");
		assertEquals(0f, Dificultad.reajustarVida(0f, 20, 40));
		// ida y vuelta: normal -> heroica -> normal deja la vida igual
		float v = Dificultad.reajustarVida(Dificultad.reajustarVida(13f, 20, 40), 40, 20);
		assertEquals(13f, v, 1e-5);
	}

	@Test
	void cantidadDelBotin() {
		assertEquals(5, Dificultad.cantidad(5, 1, 64, 0.0));
		assertEquals(5, Dificultad.cantidad(5, 1, 64, 0.99));
		assertEquals(6, Dificultad.cantidad(4, 1.5, 64, 0.5));
		assertEquals(5, Dificultad.cantidad(4, 1.25, 64, 0.99));
		assertEquals(5, Dificultad.cantidad(3, 1.5, 64, 0.49));   // 4,5: 5 con azar < 0,5
		assertEquals(4, Dificultad.cantidad(3, 1.5, 64, 0.5));
		assertEquals(1, Dificultad.cantidad(1, 0.75, 64, 0.9), "nunca menos de 1");
		assertEquals(16, Dificultad.cantidad(16, 1.5, 16, 0.0), "no pasa del máximo de la pila");
		assertEquals(0, Dificultad.cantidad(0, 1.5, 64, 0.0));
		// en media, el multiplicador
		double total = 0;
		int n = 10000;
		for (int i = 0; i < n; i++) {
			total += Dificultad.cantidad(3, 1.25, 64, (i + 0.5) / n);
		}
		assertEquals(3.75, total / n, 0.01);
	}

	@Test
	void tablasDeCofreDeHeraldia() {
		assertTrue(DificultadMobs.esBotinDeCofre(key("heraldia:cofres/herreria")));
		assertTrue(DificultadMobs.esBotinDeCofre(key("heraldia:unicas/castillo/armeria")));
		assertTrue(DificultadMobs.esBotinDeCofre(key("heraldia:medianas/posada/despensa")));
		assertFalse(DificultadMobs.esBotinDeCofre(key("heraldia:guardianes/castillo/zombie")));
		assertFalse(DificultadMobs.esBotinDeCofre(key("heraldia:trofeos/castillo")));
		assertFalse(DificultadMobs.esBotinDeCofre(key("minecraft:chests/simple_dungeon")));
		assertFalse(DificultadMobs.esBotinDeCofre(null));
	}

	private static ResourceKey<net.minecraft.world.level.storage.loot.LootTable> key(String id) {
		return ResourceKey.create(Registries.LOOT_TABLE, Identifier.parse(id));
	}
}
