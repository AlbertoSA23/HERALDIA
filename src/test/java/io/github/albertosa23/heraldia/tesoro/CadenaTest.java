package io.github.albertosa23.heraldia.tesoro;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtAccounter;
import java.io.ByteArrayInputStream;
import java.io.ByteArrayOutputStream;
import java.io.DataInputStream;
import java.io.DataOutputStream;
import java.io.IOException;
import org.junit.jupiter.api.Test;

/** La cadena guardada en el objeto: ida y vuelta por NBT (también en binario, como se guarda), pasos y cofre una sola vez. */
class CadenaTest {
	static final Destino MEDIANA = new Destino(Destino.Tipo.MEDIANA, "heraldia:medianas/posada/llanuras", 400, -120, true, "minecraft:plains");
	static final Destino MINA = new Destino(Destino.Tipo.MINA, "heraldia:minas/pequena/taiga/a", 900, 300, false, "minecraft:taiga");
	static final Destino TESORO = new Destino(Destino.Tipo.TESORO, "", 980, 360, false, "minecraft:taiga");

	static Cadena cadena() {
		return Cadena.nueva(-1234567890123L, 10, -20, List.of(MEDIANA, MINA, TESORO));
	}

	@Test
	void idaYVueltaPorNbt() throws IOException {
		Cadena c = cadena().avanzar();
		CompoundTag t = c.aTag();
		assertEquals(Optional.of(c), Cadena.deTag(t));
		ByteArrayOutputStream bytes = new ByteArrayOutputStream();
		NbtIo.write(t, new DataOutputStream(bytes));
		CompoundTag leida = NbtIo.read(new DataInputStream(new ByteArrayInputStream(bytes.toByteArray())), NbtAccounter.unlimitedHeap());
		assertEquals(Optional.of(c), Cadena.deTag(leida));
	}

	@Test
	void conCofreYMovidoTambienSeGuardan() {
		Cadena c = cadena().avanzar().avanzar().conTesoro(new Destino(Destino.Tipo.TESORO, "", 1000, 400, false, "minecraft:snowy_taiga"))
				.conCofre(new BlockPos(1001, 70, 402));
		Cadena leida = Cadena.deTag(c.aTag()).orElseThrow();
		assertEquals(c, leida);
		assertEquals(Optional.of(new BlockPos(1001, 70, 402)), leida.cofre());
		assertEquals(1, leida.movido());
		assertTrue(leida.completada());
	}

	@Test
	void fragmentoSinDescifrarNoTieneCadena() {
		assertTrue(Cadena.deTag(Cadena.fragmento()).isEmpty());
		assertTrue(Cadena.deTag(new CompoundTag()).isEmpty());
		assertEquals(1, Cadena.fragmento().getIntOr("v", 0));
	}

	@Test
	void marcaIlegibleNoRompe() {
		CompoundTag t = cadena().aTag();
		t.remove("destinos");   // sin destinos: no acaba en el tesoro
		assertTrue(Cadena.deTag(t).isEmpty());
		CompoundTag u = cadena().aTag();
		u.putInt("paso", 9);
		assertTrue(Cadena.deTag(u).isEmpty());
	}

	@Test
	void avanzaPasoAPasoYElCofreSoloUnaVez() {
		Cadena c = cadena();
		assertEquals(MEDIANA, c.actual());
		assertEquals(3, c.marcas());
		assertEquals(10, c.desde(0)[0]);
		c = c.avanzar();
		assertEquals(MINA, c.actual());
		assertEquals(MEDIANA.x(), c.desde(1)[0]);
		c = c.avanzar();
		assertEquals(TESORO, c.actual());
		Cadena enTesoro = c;
		assertThrows(IllegalStateException.class, enTesoro::avanzar);
		c = c.conCofre(new BlockPos(1, 2, 3));
		assertTrue(c.completada());
		Cadena hecha = c;
		assertThrows(IllegalStateException.class, () -> hecha.conCofre(new BlockPos(4, 5, 6)));
		assertThrows(IllegalStateException.class, hecha::avanzar);
		assertEquals(TESORO, hecha.actual());
	}

	@Test
	void elCofreNoSeColocaEnUnaEstructura() {
		assertThrows(IllegalStateException.class, () -> cadena().conCofre(BlockPos.ZERO));
	}

	@Test
	void tieneQueAcabarEnElTesoro() {
		assertThrows(IllegalArgumentException.class, () -> Cadena.nueva(1, 0, 0, List.of(MEDIANA, MINA)));
		assertThrows(IllegalArgumentException.class, () -> Cadena.nueva(1, 0, 0, List.of()));
		assertFalse(Cadena.nueva(1, 0, 0, List.of(TESORO)).completada());
	}

	@Test
	void destinoSinEstructuraNoGuardaElCampo() {
		CompoundTag t = TESORO.aTag();
		assertFalse(t.contains("estructura"));
		assertEquals(TESORO, Destino.deTag(t));
		assertEquals(MEDIANA, Destino.deTag(MEDIANA.aTag()));
	}
}
