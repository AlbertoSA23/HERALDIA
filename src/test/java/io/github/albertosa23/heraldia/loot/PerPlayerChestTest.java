package io.github.albertosa23.heraldia.loot;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.mojang.serialization.DynamicOps;
import net.minecraft.SharedConstants;
import net.minecraft.core.NonNullList;
import net.minecraft.core.component.DataComponents;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.network.chat.Component;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.SimpleContainer;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Dos jugadores simulados contra la lógica del cofre por jugador (la misma que usa el juego al abrirlo): cada uno saca
 * su copia entera una vez, lo que deja se le guarda, el cofre real queda vacío y los datos sobreviven a una vuelta
 * por NBT (como al guardar y cargar el chunk).
 */
class PerPlayerChestTest {
	private static final DynamicOps<Tag> OPS = NbtOps.INSTANCE;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		// Sin servidor no se cargan los componentes por defecto de los objetos (los liga ReloadableServerResources):
		// bastan los comunes para los objetos de la prueba.
		for (Item item : new Item[]{Items.TRIDENT, Items.DIAMOND, Items.HEART_OF_THE_SEA}) {
			if (!item.builtInRegistryHolder().areComponentsBound()) {
				item.builtInRegistryHolder().bindComponents(DataComponents.COMMON_ITEM_COMPONENTS);
			}
		}
	}

	private static SimpleContainer premium() {
		SimpleContainer chest = new SimpleContainer(27);
		ItemStack trident = new ItemStack(Items.TRIDENT);
		trident.set(DataComponents.CUSTOM_NAME, Component.literal("Tridente de Poseidón"));
		chest.setItem(0, trident);
		chest.setItem(1, new ItemStack(Items.DIAMOND, 12));
		chest.setItem(5, new ItemStack(Items.HEART_OF_THE_SEA, 3));
		return chest;
	}

	private static int count(NonNullList<ItemStack> items) {
		return items.stream().mapToInt(ItemStack::getCount).sum();
	}

	@Test
	void eachPlayerTakesTheirCopyOnce() {
		SimpleContainer chest = premium();
		CompoundTag data = new CompoundTag();
		data.putString(PerPlayerChest.MARK, "atlantida");

		// A abre: recibe todo, el cofre real queda vacío
		NonNullList<ItemStack> a = PerPlayerChest.open(data, chest, "A", OPS);
		assertEquals(16, count(a));
		assertEquals("Tridente de Poseidón", a.get(0).get(DataComponents.CUSTOM_NAME).getString());
		assertTrue(chest.isEmpty(), "el contenido pasa a la plantilla y el cofre queda vacío");

		// A se lleva el tridente y los diamantes y deja los corazones
		SimpleContainer copyA = new SimpleContainer(27);
		copyA.setItem(5, a.get(5).copy());
		PerPlayerChest.save(data, "A", copyA, OPS);

		// vuelta por NBT (guardar y cargar el chunk)
		data = (CompoundTag) data.copy();

		// B abre: su copia entera, aunque A ya sacó la suya
		NonNullList<ItemStack> b = PerPlayerChest.open(data, chest, "B", OPS);
		assertEquals(16, count(b));
		PerPlayerChest.save(data, "B", new SimpleContainer(27), OPS);

		// A vuelve: solo lo que dejó; B vuelve: nada; la plantilla sigue entera
		assertEquals(3, count(PerPlayerChest.open(data, chest, "A", OPS)));
		assertEquals(0, count(PerPlayerChest.open(data, chest, "B", OPS)));
		assertEquals(16, count(PerPlayerChest.read(data.getListOrEmpty(PerPlayerChest.TEMPLATE), OPS)));
		// un tercero también recibe la suya
		assertEquals(16, count(PerPlayerChest.open(data, chest, "C", OPS)));
		assertTrue(chest.isEmpty());
	}

	@Test
	void disabledReturnsTheContentsOnce() {
		SimpleContainer chest = premium();
		CompoundTag data = new CompoundTag();
		PerPlayerChest.open(data, chest, "A", OPS);
		assertTrue(chest.isEmpty());
		assertTrue(PerPlayerChest.restore(data, chest, OPS));
		assertEquals(16, chest.getItem(0).getCount() + chest.getItem(1).getCount() + chest.getItem(5).getCount());
		assertTrue(!PerPlayerChest.restore(data, chest, OPS), "solo una vez");
		// reactivada: vuelve a capturar; A conserva su copia, B recibe la suya
		assertEquals(16, count(PerPlayerChest.open(data, chest, "A", OPS)));
		assertEquals(16, count(PerPlayerChest.open(data, chest, "B", OPS)));
	}

	@Test
	void openingWithoutClosingAlreadyCountsAsTaken() {
		SimpleContainer chest = premium();
		CompoundTag data = new CompoundTag();
		PerPlayerChest.open(data, chest, "A", OPS);
		// aunque el servidor se cierre sin guardar la copia al cerrar, A ya tiene la suya apuntada
		assertTrue(data.getCompoundOrEmpty(PerPlayerChest.PLAYERS).contains("A"));
	}
}
