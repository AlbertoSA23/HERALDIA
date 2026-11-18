package io.github.albertosa23.heraldia.treasure;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;

/**
 * The chain of a treasure clue, saved in the item itself (custom_data {@value #MARK}): the seed that chose it,
 * the destinations in order (structures and, at the end, the treasure), the current step (the destination the map marks now;
 * {@code step == destinations.size()}: completed, with the chest already placed at {@code chest}) and how many times the
 * treasure has been moved because its spot was not safe; (ox, oz), where it was deciphered (for the direction of the first clue).
 * An undeciphered fragment only carries {@code {v: 1}} (no seed).
 * Pure logic: tested without the game (ChainTest).
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

	/** Where one leaves from towards destination {@code i}: the origin or the previous destination. */
	public int[] from(int i) {
		return i == 0 ? new int[]{ox, oz} : new int[]{destinations.get(i - 1).x(), destinations.get(i - 1).z()};
	}

	/** The destination the map marks now (in a completed one, the treasure). */
	public Destination actual() {
		return destinations.get(Math.min(step, destinations.size() - 1));
	}

	public int marks() {
		return destinations.size();
	}

	/** On reaching a structure: the next destination. */
	public Chain advance() {
		if (completed() || actual().type() == Destination.Type.TREASURE) {
			throw new IllegalStateException("no se avanza desde el tesoro: se coloca el cofre");
		}
		return new Chain(seed, ox, oz, step + 1, destinations, chest, moved);
	}

	/** The chest is placed: the chain is completed (only once). */
	public Chain withChest(BlockPos pos) {
		if (completed() || actual().type() != Destination.Type.TREASURE) {
			throw new IllegalStateException("el cofre solo se coloca en el tesoro");
		}
		return new Chain(seed, ox, oz, step + 1, destinations, Optional.of(pos.immutable()), moved);
	}

	/** The treasure somewhere else (its spot was not safe). */
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

	/** The chain of a {@value #MARK} mark; empty if it is an undeciphered fragment (or an unreadable mark). */
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

	/** The mark of an undeciphered fragment (what the heraldia:tesoro/fragmento table sets). */
	public static CompoundTag fragment() {
		CompoundTag t = new CompoundTag();
		t.putInt("v", VERSION);
		return t;
	}
}
