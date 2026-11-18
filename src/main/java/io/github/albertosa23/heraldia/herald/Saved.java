package io.github.albertosa23.heraldia.herald;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import io.github.albertosa23.heraldia.Heraldia;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import java.util.UUID;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.minecraft.core.BlockPos;
import net.minecraft.core.UUIDUtil;

/**
 * What is saved of the Herald's House in the overworld (new persistent attachment heraldia:casa_heraldo): the origin of
 * the placed house (if any), whether it was already decided to build it on its own (in a new world) or not (in an existing
 * one), the stall tenancies and the return barrels assigned to a player. A world without it reads as {@link #EMPTY}.
 */
public record Saved(Optional<BlockPos> origin, boolean decided, List<Tenancy> tenancies, List<Return> returns) {

	/**
	 * A rented stall: its number, the tenant, the tick it is paid until, and the last warning given for that
	 * {@code paidUntil} (0 none, 1 due soon, 2 in the grace), so each warning is given once per period.
	 */
	public record Tenancy(int stall, UUID owner, String name, long paidUntil, int warned) {
		static final Codec<Tenancy> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.INT.fieldOf("puesto").forGetter(Tenancy::stall),
				UUIDUtil.CODEC.fieldOf("inquilino").forGetter(Tenancy::owner),
				Codec.STRING.optionalFieldOf("nombre", "").forGetter(Tenancy::name),
				Codec.LONG.fieldOf("pagado_hasta").forGetter(Tenancy::paidUntil),
				Codec.INT.optionalFieldOf("avisado", 0).forGetter(Tenancy::warned)).apply(i, Tenancy::new));

		Tenancy paid(long until) {
			return new Tenancy(stall, owner, name, until, 0);
		}

		Tenancy warn(int stage) {
			return new Tenancy(stall, owner, name, paidUntil, stage);
		}
	}

	/** A return barrel (its index in the blueprint) holding a former tenant's things; {@code told}: they were told where. */
	public record Return(int barrel, UUID owner, String name, boolean told) {
		static final Codec<Return> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.INT.fieldOf("barril").forGetter(Return::barrel),
				UUIDUtil.CODEC.fieldOf("dueno").forGetter(Return::owner),
				Codec.STRING.optionalFieldOf("nombre", "").forGetter(Return::name),
				Codec.BOOL.optionalFieldOf("avisado", false).forGetter(Return::told)).apply(i, Return::new));
	}

	public static final Codec<Saved> CODEC = RecordCodecBuilder.create(i -> i.group(
			BlockPos.CODEC.optionalFieldOf("origen").forGetter(Saved::origin),
			Codec.BOOL.optionalFieldOf("decidida", false).forGetter(Saved::decided),
			Tenancy.CODEC.listOf().optionalFieldOf("puestos", List.of()).forGetter(Saved::tenancies),
			Return.CODEC.listOf().optionalFieldOf("devoluciones", List.of()).forGetter(Saved::returns)).apply(i, Saved::new));
	public static final Saved EMPTY = new Saved(Optional.empty(), false, List.of(), List.of());

	public Saved withOrigin(BlockPos o) {
		return new Saved(Optional.ofNullable(o), true, tenancies, returns);
	}

	public Saved decide() {
		return new Saved(origin, true, tenancies, returns);
	}

	public Optional<Tenancy> tenancy(int stall) {
		return tenancies.stream().filter(t -> t.stall() == stall).findFirst();
	}

	public Optional<Tenancy> tenancyOf(UUID owner) {
		return tenancies.stream().filter(t -> t.owner().equals(owner)).findFirst();
	}

	/** With that stall's tenancy replaced (or removed, if {@code t} is null). */
	public Saved withTenancy(int stall, @org.jspecify.annotations.Nullable Tenancy t) {
		List<Tenancy> out = new ArrayList<>();
		for (Tenancy x : tenancies) {
			if (x.stall() != stall) {
				out.add(x);
			}
		}
		if (t != null) {
			out.add(t);
		}
		return new Saved(origin, decided, List.copyOf(out), returns);
	}

	public Optional<Return> returnAt(int barrel) {
		return returns.stream().filter(r -> r.barrel() == barrel).findFirst();
	}

	/** With that barrel's record replaced (or removed, if {@code r} is null). */
	public Saved withReturn(int barrel, @org.jspecify.annotations.Nullable Return r) {
		List<Return> out = new ArrayList<>();
		for (Return x : returns) {
			if (x.barrel() != barrel) {
				out.add(x);
			}
		}
		if (r != null) {
			out.add(r);
		}
		return new Saved(origin, decided, tenancies, List.copyOf(out));
	}

	/** The attachment, kept apart so the tests register nothing when the class loads. */
	static final class Type {
		static final AttachmentType<Saved> HOUSE = AttachmentRegistry.create(Heraldia.id("casa_heraldo"), b -> b.persistent(CODEC));

		private Type() {
		}
	}
}
