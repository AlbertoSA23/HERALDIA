package io.github.albertosa23.heraldia.treasure;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;

/**
 * La cadena de una pista del tesoro, guardada en el propio objeto (custom_data {@value #MARK}): la semilla que la eligió,
 * los destinos en orden (estructuras y, al final, el tesoro), el paso en curso (el destino que marca el mapa ahora;
 * {@code step == destinations.size()}: completada, con el cofre ya colocado en {@code chest}) y cuántas veces se ha movido
 * el tesoro porque su sitio no era seguro; (ox, oz), dónde se descifró (para la dirección de la primera pista). Un fragmento sin descifrar solo lleva {@code {v: 1}} (sin semilla).
 * Lógica pura: se prueba sin juego (CadenaTest).
 */
public record Chain(long seed, int ox, int oz, int step, List<Destination> destinations, Optional<BlockPos> chest, int moved) {
	public static final String MARK = "heraldia_busqueda";
	static final int VERSION = 1;

	public Chain {
		destinations = List.copyOf(destinations);
		if (destinations.isEmpty() || destinations.getLast().type() != Destination.Type.TREASURE) {
			throw new IllegalArgumentException("la cadena tiene que acabar en el tesoro: " + destinations);
		}
		if (step < 0 || step > destinations.size()) {
			throw new IllegalArgumentException("paso fuera de la cadena: " + step);
		}
	}

	public static Chain fresh(long seed, int ox, int oz, List<Destination> destinations) {
		return new Chain(seed, ox, oz, 0, destinations, Optional.empty(), 0);
	}

	public boolean completed() {
		return step >= destinations.size();
	}

	/** De dónde se sale hacia el destino {@code i}: el origen o el destino anterior. */
	public int[] from(int i) {
		return i == 0 ? new int[]{ox, oz} : new int[]{destinations.get(i - 1).x(), destinations.get(i - 1).z()};
	}

	/** El destino que marca el mapa ahora (en una completada, el tesoro). */
	public Destination actual() {
		return destinations.get(Math.min(step, destinations.size() - 1));
	}

	public int marks() {
		return destinations.size();
	}

	/** Al llegar a una estructura: el siguiente destino. */
	public Chain advance() {
		if (completed() || actual().type() == Destination.Type.TREASURE) {
			throw new IllegalStateException("no se avanza desde el tesoro: se coloca el cofre");
		}
		return new Chain(seed, ox, oz, step + 1, destinations, chest, moved);
	}

	/** El cofre colocado: la cadena queda completada (una sola vez). */
	public Chain withChest(BlockPos pos) {
		if (completed() || actual().type() != Destination.Type.TREASURE) {
			throw new IllegalStateException("el cofre solo se coloca en el tesoro");
		}
		return new Chain(seed, ox, oz, step + 1, destinations, Optional.of(pos.immutable()), moved);
	}

	/** El tesoro en otro sitio (el suyo no era seguro). */
	public Chain withTreasure(Destination newValue) {
		List<Destination> d = new ArrayList<>(destinations);
		d.set(d.size() - 1, newValue);
		return new Chain(seed, ox, oz, step, d, chest, moved + 1);
	}

	public CompoundTag toTag() {
		CompoundTag t = new CompoundTag();
		t.putInt("v", VERSION);
		t.putLong("semilla", seed);
		t.putIntArray("origen", new int[]{ox, oz});
		t.putInt("paso", step);
		ListTag l = new ListTag();
		for (Destination d : destinations) {
			l.add(d.toTag());
		}
		t.put("destinos", l);
		chest.ifPresent(p -> t.putIntArray("cofre", new int[]{p.getX(), p.getY(), p.getZ()}));
		if (moved > 0) {
			t.putInt("movido", moved);
		}
		return t;
	}

	/** La cadena de una marca {@value #MARK}; vacío si es un fragmento sin descifrar (o una marca ilegible). */
	public static Optional<Chain> fromTag(CompoundTag t) {
		if (t.getLong("semilla").isEmpty()) {
			return Optional.empty();
		}
		List<Destination> d = new ArrayList<>();
		for (Tag e : t.getListOrEmpty("destinos")) {
			e.asCompound().ifPresent(c -> d.add(Destination.fromTag(c)));
		}
		try {
			Optional<BlockPos> chest = t.getIntArray("cofre").filter(a -> a.length == 3).map(a -> new BlockPos(a[0], a[1], a[2]));
			int[] o = t.getIntArray("origen").filter(a -> a.length == 2).orElse(new int[2]);
			return Optional.of(new Chain(t.getLongOr("semilla", 0), o[0], o[1], t.getIntOr("paso", 0), d, chest, t.getIntOr("movido", 0)));
		} catch (IllegalArgumentException e) {
			return Optional.empty();
		}
	}

	/** La marca de un fragmento sin descifrar (lo que pone la tabla heraldia:tesoro/fragmento). */
	public static CompoundTag fragment() {
		CompoundTag t = new CompoundTag();
		t.putInt("v", VERSION);
		return t;
	}
}
