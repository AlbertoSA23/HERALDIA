package io.github.albertosa23.heraldia.quests;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonElement;
import com.mojang.serialization.JsonOps;
import java.util.List;
import java.util.Map;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import org.junit.jupiter.api.Test;

/** Los datos del jugador y del mundo: aceptar, cumplir, entregar y su persistencia (los códecs del adjunto). */
class DataTest {
	static Quest e(int gap, Type t) {
		return new Quest(5, -7, 2, gap, t, t == Type.BRING ? "minecraft:bread" : "castillo", t == Type.BRING ? 16 : 0, 100, 200, 3, 20);
	}

	@Test
	void acceptAndWhyNot() {
		Data d = Data.EMPTY;
		assertNull(d.notAcceptable(e(0, Type.BRING)));
		d = d.accept(e(0, Type.BRING));
		assertTrue(d.has(e(0, Type.BRING).id()));
		assertEquals("ya", d.notAcceptable(e(0, Type.BRING)));
		for (int i = 1; i < Data.MAX_ACTIVE; i++) {
			d = d.accept(e(i, Type.GUARDIAN));
		}
		assertEquals(Data.MAX_ACTIVE, d.active().size());
		assertEquals("lleno", d.notAcceptable(new Quest(1, 1, 0, 0, Type.ARENA, "", 3, 0, 0, 4, 30)));
		Data delivered = Data.EMPTY.accept(e(0, Type.BRING)).deliver(e(0, Type.BRING).id(), true);
		assertEquals("hecho", delivered.notAcceptable(e(0, Type.BRING)), "no se cobra dos veces");
	}

	@Test
	void abandon() {
		Data d = Data.EMPTY.accept(e(0, Type.BRING)).accept(e(1, Type.GUARDIAN));
		Data without = d.abandon(0);
		assertEquals(1, without.active().size());
		assertEquals(Type.GUARDIAN, without.active().get(0).quest().type());
		assertSame(d, d.abandon(5));
		assertSame(d, d.abandon(-1));
		assertNull(without.notAcceptable(e(0, Type.BRING)), "abandonado se puede volver a aceptar");
	}

	@Test
	void completeOnlyWhatIsMet() {
		Data d = Data.EMPTY.accept(e(0, Type.BRING)).accept(e(1, Type.GUARDIAN));
		Data c = d.complete(x -> Objectives.guardian(x, "castillo", 110, 190));
		assertFalse(c.active().get(0).met());
		assertTrue(c.active().get(1).met());
		assertSame(c, c.complete(x -> Objectives.guardian(x, "castillo", 110, 190)), "ya cumplido: sin cambios");
		assertSame(d, d.complete(x -> false));
	}

	@Test
	void deliveringGivesReputationWithItsVillage() {
		Quest g = e(1, Type.GUARDIAN);
		Data d = Data.EMPTY.accept(g).complete(x -> true).deliver(g.id(), true);
		assertEquals(0, d.active().size());
		assertEquals(1, d.completed());
		assertEquals(List.of(g.id()), d.finished());
		assertEquals(Type.GUARDIAN.reputation, d.reputation("5,-7"));
		assertEquals(0, d.reputation("0,0"));
		Data without = Data.EMPTY.accept(g).deliver(g.id(), false);
		assertEquals(0, without.reputation("5,-7"), "con la reputación desactivada no sube");
		assertEquals(1, without.completed());
		assertSame(d, d.deliver("no.existe.0.0", true));
	}

	@Test
	void boundedDone() {
		Data d = Data.EMPTY;
		for (int i = 0; i < Data.MAX_DONE + 20; i++) {
			Quest x = new Quest(i, 0, 0, 0, Type.BRING, "minecraft:bread", 1, 0, 0, 1, 1);
			d = d.accept(x).deliver(x.id(), true);
		}
		assertEquals(Data.MAX_DONE, d.finished().size());
		assertEquals(Data.MAX_DONE + 20, d.completed());
		assertFalse(d.done("0.0.0.0"), "los más viejos se olvidan");
		assertTrue(d.done((Data.MAX_DONE + 19) + ".0.0.0"));
	}

	@Test
	void levelsPerVillage() {
		Data d = Data.EMPTY.addReputation("1,1", Reputation.FRIEND).addReputation("2,2", Reputation.HERO)
				.addReputation("3,3", -50);
		assertEquals(Reputation.Tier.FRIEND, d.tier("1,1"));
		assertEquals(Reputation.Tier.HERO, d.tier("2,2"));
		assertEquals(Reputation.Tier.UNKNOWN, d.tier("3,3"));
		assertEquals(2, d.villagesWith(Reputation.Tier.FRIEND));
		assertEquals(1, d.villagesWith(Reputation.Tier.HERO));
		assertEquals(Reputation.Tier.HERO, d.bestLevel());
		assertEquals(Reputation.Tier.UNKNOWN, Data.EMPTY.bestLevel());
	}

	@Test
	void persistenceInNbtAndJson() {
		Data d = Data.EMPTY.accept(e(0, Type.BRING)).accept(e(1, Type.GUARDIAN)).complete(x -> x.type() == Type.GUARDIAN)
				.addReputation("5,-7", 42).addReputation("-3,9", -12);
		d = d.accept(e(2, Type.JOURNEY)).deliver(e(2, Type.JOURNEY).id(), true);
		Tag nbt = Data.CODEC.encodeStart(NbtOps.INSTANCE, d).getOrThrow();
		assertEquals(d, Data.CODEC.parse(NbtOps.INSTANCE, nbt).getOrThrow());
		JsonElement json = Data.CODEC.encodeStart(JsonOps.INSTANCE, d).getOrThrow();
		assertEquals(d, Data.CODEC.parse(JsonOps.INSTANCE, json).getOrThrow());
		// un adjunto vacío (o de una versión anterior sin campos) se lee con los valores por defecto
		assertEquals(Data.EMPTY, Data.CODEC.parse(JsonOps.INSTANCE, new com.google.gson.JsonObject()).getOrThrow());
		assertEquals(Map.of("5,-7", 42 + Type.JOURNEY.reputation, "-3,9", -12), d.reputation());
	}

	@Test
	void world() {
		World m = World.EMPTY.isCompleted().isCompleted().falls("castillo", 1000, 1000, 5000);
		assertEquals(2, m.completed());
		assertTrue(m.hasFallen("castillo", 1100, 1000));
		assertFalse(m.hasFallen("castillo", 1000 + Objectives.GUARDIAN_RADIUS + 1, 1000));
		assertFalse(m.hasFallen("catedral", 1000, 1000));
		assertSame(m, m.falls("castillo", 1010, 990, 9000), "el mismo guardián no se apunta dos veces");
		// el tablón de un periodo solo descarta los caídos antes de que empezara (no cambia a mitad de periodo)
		assertTrue(m.fellBefore("castillo", 1000, 1000, 5001));
		assertFalse(m.fellBefore("castillo", 1000, 1000, 5000));
		assertEquals(5000, m.fallen().get(0).tick());
		Tag nbt = World.CODEC.encodeStart(NbtOps.INSTANCE, m).getOrThrow();
		assertEquals(m, World.CODEC.parse(NbtOps.INSTANCE, nbt).getOrThrow());
		World full = World.EMPTY;
		for (int i = 0; i <= World.MAX_FALLEN; i++) {
			full = full.falls("castillo", i * 1000, 0, i);
		}
		assertEquals(World.MAX_FALLEN, full.fallen().size());
	}

	@Test
	void types() {
		for (Type t : Type.values()) {
			assertEquals(t, Type.of(t.id()));
			assertEquals(t.id(), t.id().toLowerCase(java.util.Locale.ROOT));
		}
		assertEquals("traer", Type.BRING.id());
	}
}
