package io.github.albertosa23.heraldia.tesoro;

import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import net.minecraft.core.BlockPos;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.Tag;

/**
 * La cadena de una pista del tesoro, guardada en el propio objeto (custom_data {@value #MARCA}): la semilla que la eligió,
 * los destinos en orden (estructuras y, al final, el tesoro), el paso en curso (el destino que marca el mapa ahora;
 * {@code paso == destinos.size()}: completada, con el cofre ya colocado en {@code cofre}) y cuántas veces se ha movido
 * el tesoro porque su sitio no era seguro; (ox, oz), dónde se descifró (para la dirección de la primera pista). Un fragmento sin descifrar solo lleva {@code {v: 1}} (sin semilla).
 * Lógica pura: se prueba sin juego (CadenaTest).
 */
public record Cadena(long semilla, int ox, int oz, int paso, List<Destino> destinos, Optional<BlockPos> cofre, int movido) {
	public static final String MARCA = "heraldia_busqueda";
	static final int VERSION = 1;

	public Cadena {
		destinos = List.copyOf(destinos);
		if (destinos.isEmpty() || destinos.getLast().tipo() != Destino.Tipo.TESORO) {
			throw new IllegalArgumentException("la cadena tiene que acabar en el tesoro: " + destinos);
		}
		if (paso < 0 || paso > destinos.size()) {
			throw new IllegalArgumentException("paso fuera de la cadena: " + paso);
		}
	}

	public static Cadena nueva(long semilla, int ox, int oz, List<Destino> destinos) {
		return new Cadena(semilla, ox, oz, 0, destinos, Optional.empty(), 0);
	}

	public boolean completada() {
		return paso >= destinos.size();
	}

	/** De dónde se sale hacia el destino {@code i}: el origen o el destino anterior. */
	public int[] desde(int i) {
		return i == 0 ? new int[]{ox, oz} : new int[]{destinos.get(i - 1).x(), destinos.get(i - 1).z()};
	}

	/** El destino que marca el mapa ahora (en una completada, el tesoro). */
	public Destino actual() {
		return destinos.get(Math.min(paso, destinos.size() - 1));
	}

	public int marcas() {
		return destinos.size();
	}

	/** Al llegar a una estructura: el siguiente destino. */
	public Cadena avanzar() {
		if (completada() || actual().tipo() == Destino.Tipo.TESORO) {
			throw new IllegalStateException("no se avanza desde el tesoro: se coloca el cofre");
		}
		return new Cadena(semilla, ox, oz, paso + 1, destinos, cofre, movido);
	}

	/** El cofre colocado: la cadena queda completada (una sola vez). */
	public Cadena conCofre(BlockPos pos) {
		if (completada() || actual().tipo() != Destino.Tipo.TESORO) {
			throw new IllegalStateException("el cofre solo se coloca en el tesoro");
		}
		return new Cadena(semilla, ox, oz, paso + 1, destinos, Optional.of(pos.immutable()), movido);
	}

	/** El tesoro en otro sitio (el suyo no era seguro). */
	public Cadena conTesoro(Destino nuevo) {
		List<Destino> d = new ArrayList<>(destinos);
		d.set(d.size() - 1, nuevo);
		return new Cadena(semilla, ox, oz, paso, d, cofre, movido + 1);
	}

	public CompoundTag aTag() {
		CompoundTag t = new CompoundTag();
		t.putInt("v", VERSION);
		t.putLong("semilla", semilla);
		t.putIntArray("origen", new int[]{ox, oz});
		t.putInt("paso", paso);
		ListTag l = new ListTag();
		for (Destino d : destinos) {
			l.add(d.aTag());
		}
		t.put("destinos", l);
		cofre.ifPresent(p -> t.putIntArray("cofre", new int[]{p.getX(), p.getY(), p.getZ()}));
		if (movido > 0) {
			t.putInt("movido", movido);
		}
		return t;
	}

	/** La cadena de una marca {@value #MARCA}; vacío si es un fragmento sin descifrar (o una marca ilegible). */
	public static Optional<Cadena> deTag(CompoundTag t) {
		if (t.getLong("semilla").isEmpty()) {
			return Optional.empty();
		}
		List<Destino> d = new ArrayList<>();
		for (Tag e : t.getListOrEmpty("destinos")) {
			e.asCompound().ifPresent(c -> d.add(Destino.deTag(c)));
		}
		try {
			Optional<BlockPos> cofre = t.getIntArray("cofre").filter(a -> a.length == 3).map(a -> new BlockPos(a[0], a[1], a[2]));
			int[] o = t.getIntArray("origen").filter(a -> a.length == 2).orElse(new int[2]);
			return Optional.of(new Cadena(t.getLongOr("semilla", 0), o[0], o[1], t.getIntOr("paso", 0), d, cofre, t.getIntOr("movido", 0)));
		} catch (IllegalArgumentException e) {
			return Optional.empty();
		}
	}

	/** La marca de un fragmento sin descifrar (lo que pone la tabla heraldia:tesoro/fragmento). */
	public static CompoundTag fragmento() {
		CompoundTag t = new CompoundTag();
		t.putInt("v", VERSION);
		return t;
	}
}
