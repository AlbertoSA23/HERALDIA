package io.github.albertosa23.heraldia.roads;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Trazado de los caminos entre aldeas (lógica pura, sin clases del juego: la prueban los tests unitarios).
 * <p>Todo sale de la semilla y de la rejilla de las aldeas, sin mirar chunks: cada chunk calcula por su cuenta qué tramos
 * lo cruzan y los pinta en sus 16 x 16 columnas, así que dos chunks vecinos siempre coinciden en la frontera, se generen
 * en el orden que sea y en el hilo que sea.
 * <ul>
 * <li>Aldeas: una por casilla de la rejilla como mucho ({@link Villages}, en el juego con las mismas reglas que la
 * generación). Se unen dos aldeas a menos de la distancia máxima si ninguna tercera está más cerca de las dos que ellas
 * entre sí (grafo de vecindad relativa): sin triángulos ni caminos que se crucen, y la misma respuesta desde las dos.</li>
 * <li>Ruta: de la aldea de menor clave a la de mayor (así A→B y B→A son la misma), opcionalmente por un punto de paso
 * junto a una estructura ({@link Milestones}), con un serpenteo suave que sale de la semilla y se anula en los extremos.
 * Vértices cada {@link #STEP} bloques.</li>
 * <li>Agua: cada vértice puede pedir la altura del fondo ({@link Seabed}, en el juego el ruido del terreno) para saber si
 * cae en el agua; un tramo de agua corto es un puente, uno de poca profundidad una pasarela y uno largo y hondo se corta.
 * Solo se pregunta donde el chunk ve agua de verdad, y queda en memoria en la ruta.</li>
 * </ul>
 * Memorias en {@link ConcurrentHashMap} (los hilos de generación consultan a la vez); los vectores de la ruta se rellenan
 * con valores deterministas, así que dos hilos que calculan el mismo hueco escriben lo mismo.
 */
public final class RoadLayout {
	public static final long NONE = Long.MIN_VALUE;
	/** Separación entre vértices de una ruta, en bloques. */
	public static final int STEP = 16;
	/** Cada cuántos vértices hay una farola (unos 48 bloques) y a qué distancia de cada aldea va su cartel (fuera de las piezas de una aldea grande, que llegan a 116 bloques de la plaza). */
	public static final int LAMP_EVERY = 3, SIGN_A = 160;
	/** Agua: tramo más largo que se cruza con un puente y profundidad máxima de una pasarela, en bloques. */
	public static final int MAX_BRIDGE = 64, WALKWAY_DEPTH = 2, MAX_WALKWAY = 320;
	static final int CACHE_MAX = 1 << 13;
	private static final org.slf4j.Logger LOGGER = org.slf4j.LoggerFactory.getLogger("heraldia");
	/** Las primeras rutas de cada arranque van al log (las lee la prueba de servidor). */
	private static final int LOG_MAX = 64;
	private static final java.util.concurrent.atomic.AtomicInteger LOGGED = new java.util.concurrent.atomic.AtomicInteger();

	/** Centro de la aldea de la casilla (gx, gz) en bloques, empaquetado con {@link #pack}, o {@link #NONE}. */
	@FunctionalInterface
	public interface Villages {
		long en(int gx, int gz);
	}

	/** Punto de paso entre dos aldeas (junto a una estructura) empaquetado, o {@link #NONE}. Recibe el orden canónico. */
	@FunctionalInterface
	public interface Milestones {
		long between(int ax, int az, int bx, int bz);

		Milestones NO_MILESTONES = (ax, az, bx, bz) -> NONE;
	}

	/** Altura del fondo (sin contar el agua) en una columna. */
	@FunctionalInterface
	public interface Seabed {
		int en(int x, int z);
	}

	/** Qué hace la ruta en el agua alrededor de un vértice. */
	public enum Water { LAND, BRIDGE, WALKWAY, CUT }

	private final long seed;
	private final int cell;          // tamaño de la casilla de la rejilla, en bloques
	private final int maxDist;
	private final long maxDistSq;
	private final int reach;         // casillas alrededor en las que puede estar una vecina
	private final int pad;           // margen de la caja de una ruta (serpenteo, ancho, postes)
	private final Villages villages;
	private final Milestones milestones;
	private final ConcurrentHashMap<Long, Long> villageMemo = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<Long, long[]> neighborMemo = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<Key, Route> routeMemo = new ConcurrentHashMap<>();

	/** cellBlocks: lado de la casilla de la rejilla de las aldeas (bloques); maxDist: distancia máxima entre aldeas. */
	public RoadLayout(long seed, int cellBlocks, int maxDist, Villages villages, Milestones milestones) {
		this.seed = seed;
		this.cell = cellBlocks;
		this.maxDist = maxDist;
		this.maxDistSq = (long) maxDist * maxDist;
		this.reach = (maxDist + cellBlocks - 1) / cellBlocks + 1;
		this.pad = MAX_MEANDER + 16;
		this.villages = villages;
		this.milestones = milestones;
	}

	public static long pack(int x, int z) {
		return (long) x << 32 | (z & 0xFFFFFFFFL);
	}

	public static int px(long p) {
		return (int) (p >> 32);
	}

	public static int pz(long p) {
		return (int) p;
	}

	public int maxDist() {
		return maxDist;
	}

	/** Aldea de la casilla, en memoria. */
	long village(int gx, int gz) {
		long key = pack(gx, gz);
		Long v = villageMemo.get(key);
		if (v == null) {
			v = villages.en(gx, gz);
			if (villageMemo.size() > CACHE_MAX) {
				villageMemo.clear();
			}
			villageMemo.put(key, v);
		}
		return v;
	}

	private static long distSq(long a, long b) {
		long dx = (long) px(a) - px(b), dz = (long) pz(a) - pz(b);
		return dx * dx + dz * dz;
	}

	/**
	 * Aldeas unidas con la de la casilla (gx, gz): a menos de la distancia máxima y sin una tercera más cerca de las dos
	 * (vecindad relativa). Cualquier tercera que lo impida está a menos de la distancia máxima de las dos, así que la
	 * respuesta es la misma calculada desde cualquiera de ellas. Vacío si la casilla no tiene aldea.
	 */
	public long[] neighbors(int gx, int gz) {
		long key = pack(gx, gz);
		long[] v = neighborMemo.get(key);
		if (v != null) {
			return v;
		}
		long a = village(gx, gz);
		List<Long> near = new ArrayList<>();
		if (a != NONE) {
			for (int x = gx - reach; x <= gx + reach; x++) {
				for (int z = gz - reach; z <= gz + reach; z++) {
					long c = (x == gx && z == gz) ? NONE : village(x, z);
					if (c != NONE && distSq(a, c) <= maxDistSq) {
						near.add(c);
					}
				}
			}
		}
		List<Long> out = new ArrayList<>();
		for (long b : near) {
			long ab = distSq(a, b);
			boolean ok = true;
			for (long c : near) {
				if (c != b && Math.max(distSq(a, c), distSq(b, c)) < ab) {
					ok = false;
					break;
				}
			}
			if (ok) {
				out.add(b);
			}
		}
		v = out.stream().mapToLong(Long::longValue).toArray();
		if (neighborMemo.size() > CACHE_MAX) {
			neighborMemo.clear();
		}
		neighborMemo.put(key, v);
		return v;
	}

	/**
	 * Vecinas (como {@link #neighbors}) de la aldea con la plaza en (bx, bz) bloques (el centro del chunk de su inicio):
	 * busca su casilla entre las de alrededor. Vacío si ahí no sale ninguna aldea de la rejilla. Para los encargos de
	 * viaje del tablón (T38); en memoria, como lo demás.
	 */
	public long[] neighborsOf(int bx, int bz) {
		long p = pack(bx, bz);
		int gx = cellOf(bx), gz = cellOf(bz);
		for (int x = gx - 2; x <= gx + 2; x++) {
			for (int z = gz - 2; z <= gz + 2; z++) {
				if (village(x, z) == p) {
					return neighbors(x, z);
				}
			}
		}
		return new long[0];
	}

	private int cellOf(int block) {
		return Math.floorDiv(block, cell);
	}

	/** Rutas cuya caja (con margen) toca el chunk. Barato: cuentas con las casillas cercanas, todo en memoria. */
	public List<Route> routes(int chunkX, int chunkZ) {
		int x0 = chunkX * 16, z0 = chunkZ * 16;
		return routesIn(x0, z0, x0 + 15, z0 + 15);
	}

	/**
	 * Rutas que pasan (con el margen del ancho) por la caja de bloques [x0, x1] × [z0, z1]; lo mismo que
	 * {@link #routes(int, int)} con una caja cualquiera (las caravanas de T39 buscan así el camino junto a un jugador).
	 */
	public List<Route> routesIn(int x0, int z0, int x1, int z1) {
		int r = maxDist + pad;
		List<Route> out = null;
		// una casilla de más a cada lado: la rejilla puede tener el origen desplazado (las aldeas no)
		for (int gx = cellOf(x0 - r) - 1, gxMax = cellOf(x1 + r) + 1; gx <= gxMax; gx++) {
			for (int gz = cellOf(z0 - r) - 1, gzMax = cellOf(z1 + r) + 1; gz <= gzMax; gz++) {
				long a = village(gx, gz);
				if (a == NONE) {
					continue;
				}
				for (long b : neighbors(gx, gz)) {
					if (Long.compare(a, b) >= 0) {
						continue; // cada ruta una vez: desde su aldea de menor clave
					}
					// caja de la recta con margen: descarta casi todo sin construir la ruta
					int minX = Math.min(px(a), px(b)) - pad, maxX = Math.max(px(a), px(b)) + pad;
					int minZ = Math.min(pz(a), pz(b)) - pad, maxZ = Math.max(pz(a), pz(b)) + pad;
					if (maxX < x0 || minX > x1 || maxZ < z0 || minZ > z1) {
						continue;
					}
					Route route = route(a, b);
					if (route.touches(x0, z0, x1, z1)) {
						if (out == null) {
							out = new ArrayList<>(2);
						}
						out.add(route);
					}
				}
			}
		}
		return out == null ? List.of() : out;
	}

	private record Key(long a, long b) {
	}

	/**
	 * Punto medio (el vértice central) de la ruta más cercana a (x, z) de las que salen de las aldeas de las casillas a
	 * {@code cells} o menos de la suya; {@link #NONE} si no hay ninguna. Para /heraldia review: solo calcula (las
	 * aldeas y las rutas, en memoria), sin tocar el mundo.
	 */
	public long nearestSegment(int x, int z, int cells) {
		long origin = pack(x, z), best = NONE, bestD = Long.MAX_VALUE;
		int gx0 = cellOf(x), gz0 = cellOf(z);
		for (int gx = gx0 - cells; gx <= gx0 + cells; gx++) {
			for (int gz = gz0 - cells; gz <= gz0 + cells; gz++) {
				long a = village(gx, gz);
				if (a == NONE) {
					continue;
				}
				for (long b : neighbors(gx, gz)) {
					Route r = route(a, b);
					int m = r.vertices() / 2;
					long p = pack((int) Math.round(r.x(m)), (int) Math.round(r.z(m)));
					long d = distSq(p, origin);
					if (d < bestD || d == bestD && p < best) {
						best = p;
						bestD = d;
					}
				}
			}
		}
		return best;
	}

	/** Ruta entre dos aldeas (en cualquier orden: la misma). */
	public Route route(long a, long b) {
		long lo = Math.min(a, b), hi = Math.max(a, b);
		Key k = new Key(lo, hi);
		Route r = routeMemo.get(k);
		if (r == null) {
			r = new Route(lo, hi, milestones.between(px(lo), pz(lo), px(hi), pz(hi)), seed);
			if (routeMemo.size() > CACHE_MAX) {
				routeMemo.clear();
			}
			Route prev = routeMemo.putIfAbsent(k, r);
			if (prev != null) {
				r = prev;
			} else if (LOGGED.getAndIncrement() < LOG_MAX) {
				LOGGER.info("Heraldia: camino entre las aldeas de {} {} y {} {}: {} bloques, {} vértices, {}", px(lo), pz(lo), px(hi), pz(hi),
						Math.round(r.length()), r.vertices(), r.lantern ? "faroles" : "antorchas");
			}
		}
		return r;
	}

	/** Margen alrededor del eje que puede tocar una ruta: medio ancho máximo, los postes y el redondeo. */
	static final int MARGIN = 8;

	/** Amplitud máxima del serpenteo a cada lado de la recta, en bloques. */
	static final int MAX_MEANDER = 40;

	static long mix(long z) {
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}

	/** Número en [0, 1) que solo depende de la semilla y de los argumentos. */
	static double rng(long seed, long a, long b) {
		return (mix(seed ^ mix(a * 0x9E3779B97F4A7C15L ^ mix(b + 0x632BE59BD9B4E019L))) >>> 11) * 0x1.0p-53;
	}

	/** Camino entre dos aldeas: vértices cada {@link #STEP} bloques, longitud acumulada y memoria del agua. */
	public static final class Route {
		public final long from, until;
		final double[] xs, zs, s;
		final int minX, minZ, maxX, maxZ;
		/** Estilo de las farolas de esta ruta: farol sobre poste o antorcha. */
		public final boolean lantern;
		private final int[] depth;     // altura del fondo por vértice (Integer.MIN_VALUE = sin calcular)
		private final byte[] water;     // Agua.ordinal() + 1 por vértice (0 = sin calcular)

		Route(long from, long until, long milestone, long seed) {
			this.from = from;
			this.until = until;
			long h = mix(seed ^ mix(from) ^ mix(until * 31));
			this.lantern = (h & 1) == 0;
			List<double[]> pts = new ArrayList<>();
			if (milestone == NONE) {
				segment(pts, px(from), pz(from), px(until), pz(until), h, true);
			} else {
				segment(pts, px(from), pz(from), px(milestone), pz(milestone), h, true);
				segment(pts, px(milestone), pz(milestone), px(until), pz(until), mix(h + 1), false);
			}
			int n = pts.size();
			xs = new double[n];
			zs = new double[n];
			s = new double[n];
			double mnx = Double.MAX_VALUE, mnz = Double.MAX_VALUE, mxx = -Double.MAX_VALUE, mxz = -Double.MAX_VALUE;
			for (int i = 0; i < n; i++) {
				xs[i] = pts.get(i)[0];
				zs[i] = pts.get(i)[1];
				if (i > 0) {
					s[i] = s[i - 1] + Math.hypot(xs[i] - xs[i - 1], zs[i] - zs[i - 1]);
				}
				mnx = Math.min(mnx, xs[i]);
				mnz = Math.min(mnz, zs[i]);
				mxx = Math.max(mxx, xs[i]);
				mxz = Math.max(mxz, zs[i]);
			}
			int m = MARGIN;
			minX = (int) Math.floor(mnx) - m;
			minZ = (int) Math.floor(mnz) - m;
			maxX = (int) Math.ceil(mxx) + m;
			maxZ = (int) Math.ceil(mxz) + m;
			depth = new int[n];
			java.util.Arrays.fill(depth, Integer.MIN_VALUE);
			water = new byte[n];
		}

		/** Vértices de un tramo recto con serpenteo (dos senos de fase y frecuencia al azar, nulo en los extremos). */
		private static void segment(List<double[]> pts, int ax, int az, int bx, int bz, long h, boolean first) {
			double dx = bx - ax, dz = bz - az, len = Math.hypot(dx, dz);
			int n = Math.max(1, (int) Math.round(len / STEP));
			double nx = len == 0 ? 0 : -dz / len, nz = len == 0 ? 0 : dx / len;
			double amp = Math.min(MAX_MEANDER, len * 0.05);
			double f1 = 1 + (h >>> 8 & 1), f2 = 3 + (h >>> 9 & 3);
			double p1 = ((h >>> 16) & 0xFFFF) / 65536.0 * 2 * Math.PI, p2 = ((h >>> 32) & 0xFFFF) / 65536.0 * 2 * Math.PI;
			for (int i = first ? 0 : 1; i <= n; i++) {
				double t = (double) i / n;
				double off = amp * Math.sin(Math.PI * t) * (0.7 * Math.sin(2 * Math.PI * f1 * t + p1) + 0.3 * Math.sin(2 * Math.PI * f2 * t + p2));
				pts.add(new double[]{ax + dx * t + nx * off, az + dz * t + nz * off});
			}
		}

		public int vertices() {
			return xs.length;
		}

		public double x(int i) {
			return xs[i];
		}

		public double z(int i) {
			return zs[i];
		}

		/** Longitud acumulada hasta el vértice i. */
		public double arc(int i) {
			return s[i];
		}

		public double length() {
			return s[s.length - 1];
		}

		/** Algún tramo pasa (con el margen del ancho y los postes) por la caja: primero la caja entera, luego tramo a tramo. */
		boolean touches(int x0, int z0, int x1, int z1) {
			if (maxX < x0 || minX > x1 || maxZ < z0 || minZ > z1) {
				return false;
			}
			for (int i = 0; i + 1 < xs.length; i++) {
				if (Math.max(xs[i], xs[i + 1]) + MARGIN >= x0 && Math.min(xs[i], xs[i + 1]) - MARGIN <= x1
						&& Math.max(zs[i], zs[i + 1]) + MARGIN >= z0 && Math.min(zs[i], zs[i + 1]) - MARGIN <= z1) {
					return true;
				}
			}
			return false;
		}

		/** Normal unitaria (izquierda del sentido desde → hasta) en el vértice i. */
		public double[] normal(int i) {
			int a = Math.max(0, i - 1), b = Math.min(xs.length - 1, i + 1);
			double dx = xs[b] - xs[a], dz = zs[b] - zs[a], len = Math.hypot(dx, dz);
			return len == 0 ? new double[]{0, 0} : new double[]{-dz / len, dx / len};
		}

		/** Qué hace la ruta en el agua junto al vértice k (en memoria). */
		public Water water(int k, Seabed f, int sea) {
			byte v = water[k];
			if (v != 0) {
				return Water.values()[v - 1];
			}
			Water a = classify(k, f, sea);
			water[k] = (byte) (a.ordinal() + 1);
			return a;
		}

		private int depth(int i, Seabed f) {
			int v = depth[i];
			if (v == Integer.MIN_VALUE) {
				v = f.en((int) Math.floor(xs[i]), (int) Math.floor(zs[i]));
				depth[i] = v;
			}
			return v;
		}

		/**
		 * Agua en un vértice: fondo bajo el nivel del mar. Se recorre la ruta hacia los dos lados hasta tierra: si el
		 * tramo de agua mide hasta {@link #MAX_BRIDGE}, puente; si es más largo pero nunca más hondo que
		 * {@link #WALKWAY_DEPTH} (marismas, pantanos), pasarela hasta {@link #MAX_WALKWAY}; si no, se corta.
		 * Solo se miran los vértices necesarios para decidir.
		 */
		Water classify(int k, Seabed f, int sea) {
			if (depth(k, f) >= sea) {
				return Water.LAND;
			}
			int lo = k, hi = k, deepest = sea - depth(k, f);
			double limit = MAX_WALKWAY;
			while (lo > 0 && depth(lo - 1, f) < sea && s[k] - s[lo - 1] <= limit) {
				lo--;
				deepest = Math.max(deepest, sea - depth(lo, f));
				if (deepest > WALKWAY_DEPTH) {
					limit = MAX_BRIDGE;
				}
			}
			while (hi < xs.length - 1 && depth(hi + 1, f) < sea && s[hi + 1] - s[k] <= limit) {
				hi++;
				deepest = Math.max(deepest, sea - depth(hi, f));
				if (deepest > WALKWAY_DEPTH) {
					limit = MAX_BRIDGE;
				}
			}
			// largo del agua: entre los vértices de tierra de los dos lados (o el extremo de la ruta)
			boolean openLo = lo > 0 && depth(lo - 1, f) < sea, openHi = hi < xs.length - 1 && depth(hi + 1, f) < sea;
			double len = s[Math.min(hi + 1, xs.length - 1)] - s[Math.max(lo - 1, 0)];
			if (deepest <= WALKWAY_DEPTH) {
				return !openLo && !openHi && len <= MAX_WALKWAY ? Water.WALKWAY : Water.CUT;
			}
			return !openLo && !openHi && len <= MAX_BRIDGE + STEP ? Water.BRIDGE : Water.CUT;
		}
	}

	// --- pintar un chunk ---

	/** Medio ancho que nunca se mella: lo justo para que el camino siga unido por las caras de sus columnas. */
	static final double CORE = 0.75;

	/** Columna del camino: la ruta más cercana, su vértice más cercano, la longitud recorrida y la distancia al eje. */
	public record Cell(Route route, int vertex, double arc, double dist) {
	}

	/**
	 * Columnas del chunk que son camino, en orden x * 16 + z (null = no). Una columna lo es si su centro está a menos de
	 * medio ancho del eje; en el borde (el último medio bloque, fuera del núcleo {@link #CORE}) solo a veces (azar por columna), para que no quede recto.
	 * Depende solo de la columna y de las rutas, no del chunk: los vecinos casan en la frontera.
	 */
	public Cell[] paint(List<Route> routes, int chunkX, int chunkZ, int width) {
		Cell[] out = new Cell[256];
		// con medio ancho de 0,71 o más (raíz de 2 entre 2) las columnas del camino quedan unidas por sus caras en
		// cualquier dirección: se puede andar sin pasar en diagonal entre dos esquinas
		double half = Math.max(width / 2.0, CORE);
		int x0 = chunkX * 16, z0 = chunkZ * 16;
		for (Route r : routes) {
			for (int i = 0; i + 1 < r.xs.length; i++) {
				double ax = r.xs[i], az = r.zs[i], bx = r.xs[i + 1], bz = r.zs[i + 1];
				int sx0 = Math.max(x0, (int) Math.floor(Math.min(ax, bx) - half - 1)), sx1 = Math.min(x0 + 15, (int) Math.ceil(Math.max(ax, bx) + half + 1));
				int sz0 = Math.max(z0, (int) Math.floor(Math.min(az, bz) - half - 1)), sz1 = Math.min(z0 + 15, (int) Math.ceil(Math.max(az, bz) + half + 1));
				if (sx0 > sx1 || sz0 > sz1) {
					continue;
				}
				double dx = bx - ax, dz = bz - az, l2 = dx * dx + dz * dz;
				for (int x = sx0; x <= sx1; x++) {
					for (int z = sz0; z <= sz1; z++) {
						double cx = x + 0.5, cz = z + 0.5;
						double t = l2 == 0 ? 0 : Math.clamp(((cx - ax) * dx + (cz - az) * dz) / l2, 0, 1);
						double d = Math.hypot(cx - (ax + dx * t), cz - (az + dz * t));
						if (d > half) {
							continue;
						}
						int idx = (x - x0) * 16 + (z - z0);
						Cell prev = out[idx];
						if (prev == null || d < prev.dist) {
							out[idx] = new Cell(r, t < 0.5 ? i : i + 1, r.s[i] + t * Math.sqrt(l2), d);
						}
					}
				}
			}
		}
		for (int idx = 0; idx < 256; idx++) {
			Cell c = out[idx];
			if (c != null && c.dist > Math.max(half - 0.5, CORE) && rng(seed, pack(x0 + idx / 16, z0 + idx % 16), 7) < 0.35) {
				out[idx] = null; // borde mellado
			}
		}
		return out;
	}

	/** Farola o cartel junto al camino. Cartel: hacia qué aldea apunta, cuánto falta y la rotación (0-15) del letrero. */
	public record Mark(boolean signpost, int x, int z, Route route, int vertex, long destination, int distance, int rotation, boolean right) {
	}

	/**
	 * Farolas (cada {@link #LAMP_EVERY} vértices, alternando lado, lejos de las aldeas) y los dos carteles de la ruta
	 * (a {@link #SIGN_A} bloques de cada aldea, en el lado contrario a la farola de ese vértice), de las columnas del
	 * chunk. La columna sale de la ruta, no del chunk.
	 */
	public List<Mark> marks(List<Route> routes, int chunkX, int chunkZ, int width) {
		List<Mark> out = new ArrayList<>();
		int x0 = chunkX * 16, z0 = chunkZ * 16;
		double off = width / 2.0 + 1.0;
		for (Route r : routes) {
			int n = r.xs.length;
			int first = -1, last = -1;
			for (int i = 0; i < n; i++) {
				if (first < 0 && r.s[i] >= SIGN_A) {
					first = i;
				}
				if (r.s[i] <= r.length() - SIGN_A) {
					last = i;
				}
			}
			for (int i = 0; i < n; i++) {
				// fuera del chunk: solo cuentas
				if (r.xs[i] < x0 - off - 2 || r.xs[i] > x0 + 16 + off + 2 || r.zs[i] < z0 - off - 2 || r.zs[i] > z0 + 16 + off + 2) {
					continue;
				}
				double[] nrm = r.normal(i);
				int side = (i / LAMP_EVERY) % 2 == 0 ? 1 : -1;
				boolean far = r.s[i] >= SIGN_A / 2.0 && r.s[i] <= r.length() - SIGN_A / 2.0;
				if (i % LAMP_EVERY == 0 && far) {
					add(out, false, r, i, nrm, side * off, x0, z0, NONE, 0, 0, false);
				}
				if ((i == first || i == last) && first >= 0 && first < last) {
					boolean towardsUntil = i == first; // el primero (cerca de «desde») señala «hasta»
					long destination = towardsUntil ? r.until : r.from;
					int dist = (int) Math.round(towardsUntil ? r.length() - r.s[i] : r.s[i]);
					double sideOff = -(i % LAMP_EVERY == 0 ? side : 1) * off;
					// el letrero mira al camino; la flecha dice a qué mano queda el destino para quien lo lee
					double fx = -Math.signum(sideOff) * nrm[0], fz = -Math.signum(sideOff) * nrm[1];
					int rot = Math.floorMod((int) Math.round(Math.toDegrees(Math.atan2(-fx, fz)) / 22.5), 16);
					double tx = towardsUntil ? r.xs[Math.min(n - 1, i + 1)] - r.xs[i] : r.xs[Math.max(0, i - 1)] - r.xs[i];
					double tz = towardsUntil ? r.zs[Math.min(n - 1, i + 1)] - r.zs[i] : r.zs[Math.max(0, i - 1)] - r.zs[i];
					// lector mirando al letrero (dirección -f): su derecha es (f.z, -f.x)
					boolean right = tx * fz - tz * fx > 0;
					add(out, true, r, i, nrm, sideOff, x0, z0, destination, dist, rot, right);
				}
			}
		}
		return out;
	}

	private static void add(List<Mark> out, boolean signpost, Route r, int i, double[] nrm, double off, int x0, int z0, long destination,
							int dist, int rot, boolean right) {
		int x = (int) Math.floor(r.xs[i] + nrm[0] * off), z = (int) Math.floor(r.zs[i] + nrm[1] * off);
		if (x >= x0 && x < x0 + 16 && z >= z0 && z < z0 + 16) {
			out.add(new Mark(signpost, x, z, r, i, destination, dist, rot, right));
		}
	}
}
