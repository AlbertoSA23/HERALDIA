package io.github.albertosa23.heraldia.events;

import java.util.ArrayList;
import java.util.Comparator;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;

/**
 * Where an event goes in the square (pure logic). The village square (tools/gen/streets.py, {@code plaza}) is 23 × 23
 * with the fountain in the middle; an avenue leaves from the middle of each side. Each side has a <b>bay</b>: the strip
 * between the square's edge and the fountain, around the avenue's entrance, framed by the planters and the benches. An
 * event is laid out in bay coordinates ({@code dx} across the bay, -4..4, 0 on the avenue's axis; {@code dz} from the
 * square's edge towards the fountain, 2..7) and turned to whichever bay is used. The square is symmetric, so the
 * piece's own rotation does not matter; the job board, which is not, is looked up in the world and kept clear.
 * <p>
 * Nothing is ever placed on a cell that is not free <i>now</i> (air, standing on a sturdy floor, no entity there): a
 * player's build, a missing square piece, the bell, the benches or another mod's block only make the event smaller
 * (optional pieces and figures are dropped) or move it to another bay, or it does not happen ({@link #plan} returns null).
 * The cells of the reputation decorations ({@code welcome/Spots}: banners at the avenue entrances, flowers on the
 * fountain's rim, the job board's surroundings) are never used, even when they are free: they are kept for that system.
 */
public final class Layout {
	/** The square: side and centre. */
	public static final int N = 23, C = N / 2;
	/** How far from the centre the bays reach (Chebyshev distance): from the fountain's walk to one cell short of the edge. */
	static final int MIN_RING = 4, MAX_RING = 9;

	private Layout() {
	}

	/** What a prop is (the game side turns it into a block; see VillageEvents.state). */
	public enum Prop {
		/** A stall or maypole post: an upright stripped log (oak at the market, birch at the wedding and the festival). */
		POST_OAK, POST_BIRCH,
		/** Stall awning: red and white wool. */
		AWNING_RED, AWNING_WHITE,
		/** What a stall sells, on its counter (variant: hay bale, pumpkin, melon, beehive-free honey block... see VillageEvents). */
		GOODS,
		/** Wedding: the arch's lintel and the aisle. */
		WOOL_WHITE, WOOL_PINK, CARPET_WHITE,
		/** A lantern standing on the floor. */
		LANTERN,
		/** Funeral: the bier (a dark oak log lying along the bay's depth), its black pall and two soul lanterns. */
		BIER, PALL, SOUL_LANTERN,
		/** Festival: the bonfire and the maypoles' tops. */
		CAMPFIRE, WOOL_RED, WOOL_YELLOW
	}

	/** Who a figure is. */
	public enum Role {
		MERCHANT, SHOPPER, CLERIC, BRIDE, GROOM, GUEST, CHILD, WIDOW, MOURNER, MUSICIAN, DANCER, HOST
	}

	/** A prop cell in bay coordinates: {@code y} is the height above the floor (1: standing on it). */
	public record Cell(Prop prop, int variant, int dx, int y, int dz) {
	}

	/** A group of props placed all or nothing (a stall, the arch); {@code required}: the bay is no good without it. */
	public record Piece(List<Cell> cells, boolean required) {
	}

	/** Where figures of a role may stand (in order of preference), what they look at, and how many (at least, at most).
	 *  {@code piece}: they only stand there if that piece of the same bay was placed (-1: always). */
	public record Spots(Role role, List<int[]> cells, int tx, int tz, int min, int max, int piece) {
	}

	/** One bay's template for a kind. */
	public record Bay(List<Piece> pieces, List<Spots> figures) {
	}

	/** A prop in square coordinates (local x, y above the floor, local z), in placing order; {@code alongX}: a lying log runs along x. */
	public record Placed(Prop prop, int variant, int x, int y, int z, boolean alongX) {
	}

	/** A figure in square coordinates, with the cell it looks at; {@code variant}: for a trader, what its stall sells
	 *  (the stall's goods variant), otherwise the index of its bay in the plan. */
	public record Figure(Role role, int x, int z, int tx, int tz, int variant) {
	}

	/** The event as it will be laid out: its props in placing order (lower first), its figures and the bays used. */
	public record Plan(List<Placed> props, List<Figure> figures, List<Integer> bays) {
		public long count(Role r) {
			return figures.stream().filter(f -> f.role() == r).count();
		}
	}

	/** What the square is like now, in square coordinates. */
	public interface Ground {
		/** Air (or nothing solid: a cell a prop or a figure may take) at height {@code y} above the floor. */
		boolean air(int x, int y, int z);

		/** The floor under (x, z) has a sturdy top face (paving). */
		boolean floor(int x, int z);

		/** Some entity is in that cell already (the bailiff, a villager, a player, an item frame...). */
		boolean occupied(int x, int y, int z);

		/** Kept for something else (the job board and its surroundings). */
		boolean reserved(int x, int z);
	}

	// --- templates ---

	private static int[] at(int dx, int dz) {
		return new int[] {dx, dz};
	}

	private static List<Cell> stall(int dx, int variant) {
		Prop post = Prop.POST_OAK;
		return List.of(new Cell(post, 0, dx, 1, 3), new Cell(post, 0, dx, 2, 3), new Cell(post, 0, dx, 1, 5), new Cell(post, 0, dx, 2, 5),
				new Cell(Prop.GOODS, variant, dx, 1, 4),
				new Cell(Prop.AWNING_RED, 0, dx, 3, 3), new Cell(Prop.AWNING_WHITE, 0, dx, 3, 4), new Cell(Prop.AWNING_RED, 0, dx, 3, 5));
	}

	private static List<Cell> column(Prop post, int dx, int dz, int height, Prop top) {
		List<Cell> l = new ArrayList<>();
		for (int y = 1; y <= height; y++) {
			l.add(new Cell(post, 0, dx, y, dz));
		}
		l.add(new Cell(top, 0, dx, height + 1, dz));
		return l;
	}

	static final Map<Kind, Bay> BAYS = Map.of(
			Kind.MARKET, new Bay(
					List.of(new Piece(stall(-3, 0), false), new Piece(stall(3, 1), false)),
					List.of(new Spots(Role.MERCHANT, List.of(at(-4, 4)), 0, 4, 0, 1, 0),
							new Spots(Role.MERCHANT, List.of(at(4, 4)), 0, 4, 0, 1, 1),
							new Spots(Role.SHOPPER, List.of(at(-2, 4), at(-1, 5)), -3, 4, 0, 2, 0),
							new Spots(Role.SHOPPER, List.of(at(2, 4), at(1, 3)), 3, 4, 0, 2, 1))),
			Kind.WEDDING, new Bay(
					List.of(new Piece(arch(), true),
							new Piece(List.of(new Cell(Prop.CARPET_WHITE, 0, 0, 1, 3), new Cell(Prop.CARPET_WHITE, 0, 0, 1, 4),
									new Cell(Prop.CARPET_WHITE, 0, 0, 1, 5), new Cell(Prop.CARPET_WHITE, 0, 0, 1, 6)), false),
							new Piece(List.of(new Cell(Prop.LANTERN, 0, -1, 1, 6)), false),
							new Piece(List.of(new Cell(Prop.LANTERN, 0, 1, 1, 6)), false)),
					List.of(new Spots(Role.CLERIC, List.of(at(0, 2)), 0, 6, 1, 1, -1),
							new Spots(Role.BRIDE, List.of(at(-1, 3)), 0, 2, 1, 1, -1),
							new Spots(Role.GROOM, List.of(at(1, 3)), 0, 2, 1, 1, -1),
							new Spots(Role.GUEST, List.of(at(-2, 4), at(2, 4), at(-3, 4), at(3, 4), at(-2, 5), at(2, 5), at(-3, 5), at(3, 5),
									at(-3, 6), at(3, 6), at(-1, 7), at(1, 7)), 0, 3, 4, 10, -1),
							new Spots(Role.CHILD, List.of(at(0, 7), at(-2, 7), at(2, 7)), 0, 3, 0, 2, -1))),
			Kind.FUNERAL, new Bay(
					List.of(new Piece(List.of(new Cell(Prop.BIER, 0, 0, 1, 4), new Cell(Prop.BIER, 0, 0, 1, 5),
									new Cell(Prop.PALL, 0, 0, 2, 4), new Cell(Prop.PALL, 0, 0, 2, 5)), true),
							new Piece(List.of(new Cell(Prop.SOUL_LANTERN, 0, 0, 1, 3)), false),
							new Piece(List.of(new Cell(Prop.SOUL_LANTERN, 0, 0, 1, 6)), false)),
					List.of(new Spots(Role.CLERIC, List.of(at(0, 2)), 0, 4, 1, 1, -1),
							new Spots(Role.WIDOW, List.of(at(-1, 4), at(1, 4)), 0, 4, 1, 1, -1),
							new Spots(Role.MOURNER, List.of(at(1, 5), at(-1, 5), at(-2, 4), at(2, 4), at(-2, 5), at(2, 5), at(-1, 6), at(1, 6),
									at(-3, 4), at(3, 4), at(0, 7)), 0, 4, 3, 8, -1))),
			Kind.FESTIVAL, new Bay(
					List.of(new Piece(List.of(new Cell(Prop.CAMPFIRE, 0, 0, 1, 5)), true),
							new Piece(column(Prop.POST_BIRCH, -3, 3, 3, Prop.WOOL_RED), false),
							new Piece(column(Prop.POST_BIRCH, 3, 3, 3, Prop.WOOL_YELLOW), false)),
					List.of(new Spots(Role.MUSICIAN, List.of(at(0, 2), at(-1, 2), at(1, 2)), 0, 5, 1, 3, -1),
							new Spots(Role.DANCER, List.of(at(-2, 4), at(2, 4), at(-2, 5), at(2, 5), at(-1, 7), at(1, 7), at(-1, 3), at(1, 3),
									at(0, 7), at(-2, 6), at(2, 6)), 0, 5, 3, 8, -1),
							new Spots(Role.HOST, List.of(at(-4, 5), at(4, 5), at(-4, 4), at(4, 4)), 0, 5, 0, 1, -1))));

	private static List<Cell> arch() {
		List<Cell> l = new ArrayList<>();
		for (int dx : new int[] {-2, 2}) {
			for (int y = 1; y <= 3; y++) {
				l.add(new Cell(Prop.POST_BIRCH, 0, dx, y, 2));
			}
		}
		for (int dx = -2; dx <= 2; dx++) {
			l.add(new Cell(Math.abs(dx) % 2 == 1 ? Prop.WOOL_PINK : Prop.WOOL_WHITE, 0, dx, 4, 2));
		}
		return l;
	}

	public static Bay bay(Kind k) {
		return BAYS.get(k);
	}

	// --- geometry ---

	/** Bay coordinates → square coordinates, for bay {@code b} (0 north edge, 1 east, 2 south, 3 west). */
	public static int[] toSquare(int b, int dx, int dz) {
		int x = C + dx, z = dz;
		return switch (Math.floorMod(b, 4)) {
			case 1 -> new int[] {N - 1 - z, x};
			case 2 -> new int[] {N - 1 - x, N - 1 - z};
			case 3 -> new int[] {z, N - 1 - x};
			default -> new int[] {x, z};
		};
	}

	/** Chebyshev distance of a square cell from the centre (the fountain is 3, the edge 11). */
	public static int ring(int x, int z) {
		return Math.max(Math.abs(x - C), Math.abs(z - C));
	}

	/**
	 * The cells the reputation decorations may use in the square (welcome/Spots): the banners at the avenue entrances
	 * (two blocks high) and the flower pots on the fountain's rim. Never used by an event, free or not.
	 */
	public static boolean keptForWelcome(int x, int z) {
		int r = ring(x, z);
		if (r <= 3) {
			return true;                       // the fountain and its rim
		}
		boolean entranceRow = x == 1 || x == N - 2 || z == 1 || z == N - 2;
		boolean entranceCol = Math.abs(x - C) == 3 || Math.abs(z - C) == 3;
		return entranceRow && entranceCol;
	}

	/** May an event use that square cell at all (inside the bays' ring and not kept for anything else)? */
	static boolean usable(int x, int z, Ground g) {
		int r = ring(x, z);
		return r >= MIN_RING && r <= MAX_RING && !keptForWelcome(x, z) && !g.reserved(x, z);
	}

	/**
	 * The plan of an event: its bays in order of preference ({@code order}, e.g. the bay facing the player first), each one
	 * with its required pieces and its figures' minimums, as many optional pieces and figures as fit. {@code bays} of the
	 * kind are used (the market takes two). Null if not even one bay fits: the event does not happen there.
	 */
	public static Plan plan(Kind kind, Ground g, List<Integer> order) {
		Bay template = bay(kind);
		List<Placed> props = new ArrayList<>();
		List<Figure> figures = new ArrayList<>();
		List<Integer> used = new ArrayList<>();
		Set<Long> taken = new HashSet<>();
		for (int b : order) {
			if (used.size() >= kind.bays) {
				break;
			}
			List<Placed> bp = new ArrayList<>();
			List<Figure> bf = new ArrayList<>();
			Set<Long> bt = new HashSet<>(taken);
			if (fit(template, b, used.size(), g, bp, bf, bt)) {
				props.addAll(bp);
				figures.addAll(bf);
				taken = bt;
				used.add(b);
			}
		}
		if (used.isEmpty()) {
			return null;
		}
		props.sort(Comparator.comparingInt(Placed::y));          // lower first: a post before the awning that rests on it
		return new Plan(List.copyOf(props), List.copyOf(figures), List.copyOf(used));
	}

	private static long key(int x, int y, int z) {
		return ((long) x << 40) ^ ((long) y << 20) ^ z;
	}

	private static boolean fit(Bay t, int b, int u, Ground g, List<Placed> props, List<Figure> figures, Set<Long> taken) {
		boolean[] placed = new boolean[t.pieces().size()];
		int[] goods = new int[t.pieces().size()];
		boolean any = false;
		for (int i = 0; i < t.pieces().size(); i++) {
			Piece p = t.pieces().get(i);
			List<Placed> cells = new ArrayList<>();
			boolean ok = true;
			Set<Long> own = new HashSet<>();
			for (Cell c : p.cells()) {
				own.add(key(c.dx(), c.y(), c.dz()));
			}
			for (Cell c : p.cells()) {
				int[] s = toSquare(b, c.dx(), c.dz());
				// and the cell above free (or the piece's own): nothing may rest on a prop, or it could not be taken down
				boolean top = !own.contains(key(c.dx(), c.y() + 1, c.dz()));
				if (!usable(s[0], s[1], g) || taken.contains(key(s[0], c.y(), s[1])) || !g.air(s[0], c.y(), s[1])
						|| g.occupied(s[0], c.y(), s[1]) || (c.y() == 1 && !g.floor(s[0], s[1]))
						|| (top && (!g.air(s[0], c.y() + 1, s[1]) || taken.contains(key(s[0], c.y() + 1, s[1]))))) {
					ok = false;
					break;
				}
				int variant = c.prop() == Prop.GOODS ? c.variant() + 2 * u : c.variant();
				if (c.prop() == Prop.GOODS) {
					goods[i] = variant;
				}
				cells.add(new Placed(c.prop(), variant, s[0], c.y(), s[1], b % 2 == 1));
			}
			if (!ok) {
				if (p.required()) {
					return false;
				}
				continue;
			}
			for (Placed c : cells) {
				taken.add(key(c.x(), c.y(), c.z()));
			}
			props.addAll(cells);
			placed[i] = true;
			any = true;
		}
		if (!any) {
			return false;
		}
		for (Spots s : t.figures()) {
			if (s.piece() >= 0 && !placed[s.piece()]) {
				continue;
			}
			int n = 0;
			int[] target = toSquare(b, s.tx(), s.tz());
			for (int[] c : s.cells()) {
				if (n >= s.max()) {
					break;
				}
				int[] q = toSquare(b, c[0], c[1]);
				if (usable(q[0], q[1], g) && g.floor(q[0], q[1]) && !taken.contains(key(q[0], 1, q[1])) && !taken.contains(key(q[0], 2, q[1]))
						&& g.air(q[0], 1, q[1]) && g.air(q[0], 2, q[1]) && !g.occupied(q[0], 1, q[1]) && !g.occupied(q[0], 2, q[1])) {
					figures.add(new Figure(s.role(), q[0], q[1], target[0], target[1], s.piece() >= 0 ? goods[s.piece()] : u));
					taken.add(key(q[0], 1, q[1]));
					taken.add(key(q[0], 2, q[1]));
					n++;
				}
			}
			if (n < s.min()) {
				return false;
			}
		}
		return true;
	}

	/** The most figures any kind can bring (the entity budget is checked against this, see Rules.MAX_ENTITIES). */
	public static int maxFigures(Kind k) {
		int n = 0;
		for (Spots s : bay(k).figures()) {
			n += s.max();
		}
		return n * k.bays;
	}

	/** Bays sorted so the one facing a point (in square coordinates; e.g. the arriving player) comes first. */
	public static List<Integer> facing(double x, double z) {
		List<Integer> out = new ArrayList<>(List.of(0, 1, 2, 3));
		out.sort(Comparator.comparingDouble(b -> {
			int[] m = toSquare(b, 0, 2);
			return (m[0] - x) * (m[0] - x) + (m[1] - z) * (m[1] - z);
		}));
		return out;
	}
}
