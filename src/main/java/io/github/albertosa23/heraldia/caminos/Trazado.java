package io.github.albertosa23.heraldia.caminos;

import java.util.ArrayList;
import java.util.List;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Trazado de los caminos entre aldeas (lógica pura, sin clases del juego: la prueban los tests unitarios).
 * <p>Todo sale de la semilla y de la rejilla de las aldeas, sin mirar chunks: cada chunk calcula por su cuenta qué tramos
 * lo cruzan y los pinta en sus 16 x 16 columnas, así que dos chunks vecinos siempre coinciden en la frontera, se generen
 * en el orden que sea y en el hilo que sea.
 * <ul>
 * <li>Aldeas: una por casilla de la rejilla como mucho ({@link Aldeas}, en el juego con las mismas reglas que la
 * generación). Se unen dos aldeas a menos de la distancia máxima si ninguna tercera está más cerca de las dos que ellas
 * entre sí (grafo de vecindad relativa): sin triángulos ni caminos que se crucen, y la misma respuesta desde las dos.</li>
 * <li>Ruta: de la aldea de menor clave a la de mayor (así A→B y B→A son la misma), opcionalmente por un punto de paso
 * junto a una estructura ({@link Hitos}), con un serpenteo suave que sale de la semilla y se anula en los extremos.
 * Vértices cada {@link #PASO} bloques.</li>
 * <li>Agua: cada vértice puede pedir la altura del fondo ({@link Fondo}, en el juego el ruido del terreno) para saber si
 * cae en el agua; un tramo de agua corto es un puente, uno de poca profundidad una pasarela y uno largo y hondo se corta.
 * Solo se pregunta donde el chunk ve agua de verdad, y queda en memoria en la ruta.</li>
 * </ul>
 * Memorias en {@link ConcurrentHashMap} (los hilos de generación consultan a la vez); los vectores de la ruta se rellenan
 * con valores deterministas, así que dos hilos que calculan el mismo hueco escriben lo mismo.
 */
public final class Trazado {
	public static final long NONE = Long.MIN_VALUE;
	/** Separación entre vértices de una ruta, en bloques. */
	public static final int PASO = 16;
	/** Cada cuántos vértices hay una farola (unos 48 bloques) y a qué distancia de cada aldea va su cartel (fuera de las piezas de una aldea grande, que llegan a 116 bloques de la plaza). */
	public static final int FAROLA_CADA = 3, CARTEL_A = 160;
	/** Agua: tramo más largo que se cruza con un puente y profundidad máxima de una pasarela, en bloques. */
	public static final int PUENTE_MAX = 64, PASARELA_PROFUNDIDAD = 2, PASARELA_MAX = 320;
	static final int CACHE_MAX = 1 << 13;
	private static final org.slf4j.Logger LOGGER = org.slf4j.LoggerFactory.getLogger("heraldia");
	/** Las primeras rutas de cada arranque van al log (las lee la prueba de servidor). */
	private static final int LOG_MAX = 64;
	private static final java.util.concurrent.atomic.AtomicInteger LOGGED = new java.util.concurrent.atomic.AtomicInteger();

	/** Centro de la aldea de la casilla (gx, gz) en bloques, empaquetado con {@link #pack}, o {@link #NONE}. */
	@FunctionalInterface
	public interface Aldeas {
		long en(int gx, int gz);
	}

	/** Punto de paso entre dos aldeas (junto a una estructura) empaquetado, o {@link #NONE}. Recibe el orden canónico. */
	@FunctionalInterface
	public interface Hitos {
		long entre(int ax, int az, int bx, int bz);

		Hitos NINGUNO = (ax, az, bx, bz) -> NONE;
	}

	/** Altura del fondo (sin contar el agua) en una columna. */
	@FunctionalInterface
	public interface Fondo {
		int en(int x, int z);
	}

	/** Qué hace la ruta en el agua alrededor de un vértice. */
	public enum Agua { TIERRA, PUENTE, PASARELA, CORTE }

	private final long seed;
	private final int cell;          // tamaño de la casilla de la rejilla, en bloques
	private final int maxDist;
	private final long maxDistSq;
	private final int reach;         // casillas alrededor en las que puede estar una vecina
	private final int pad;           // margen de la caja de una ruta (serpenteo, ancho, postes)
	private final Aldeas aldeas;
	private final Hitos hitos;
	private final ConcurrentHashMap<Long, Long> aldeaMemo = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<Long, long[]> vecinasMemo = new ConcurrentHashMap<>();
	private final ConcurrentHashMap<Clave, Ruta> rutaMemo = new ConcurrentHashMap<>();

	/** cellBlocks: lado de la casilla de la rejilla de las aldeas (bloques); maxDist: distancia máxima entre aldeas. */
	public Trazado(long seed, int cellBlocks, int maxDist, Aldeas aldeas, Hitos hitos) {
		this.seed = seed;
		this.cell = cellBlocks;
		this.maxDist = maxDist;
		this.maxDistSq = (long) maxDist * maxDist;
		this.reach = (maxDist + cellBlocks - 1) / cellBlocks + 1;
		this.pad = MAX_SERPENTEO + 16;
		this.aldeas = aldeas;
		this.hitos = hitos;
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
	long aldea(int gx, int gz) {
		long key = pack(gx, gz);
		Long v = aldeaMemo.get(key);
		if (v == null) {
			v = aldeas.en(gx, gz);
			if (aldeaMemo.size() > CACHE_MAX) {
				aldeaMemo.clear();
			}
			aldeaMemo.put(key, v);
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
	public long[] vecinas(int gx, int gz) {
		long key = pack(gx, gz);
		long[] v = vecinasMemo.get(key);
		if (v != null) {
			return v;
		}
		long a = aldea(gx, gz);
		List<Long> near = new ArrayList<>();
		if (a != NONE) {
			for (int x = gx - reach; x <= gx + reach; x++) {
				for (int z = gz - reach; z <= gz + reach; z++) {
					long c = (x == gx && z == gz) ? NONE : aldea(x, z);
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
		if (vecinasMemo.size() > CACHE_MAX) {
			vecinasMemo.clear();
		}
		vecinasMemo.put(key, v);
		return v;
	}

	private int cellOf(int block) {
		return Math.floorDiv(block, cell);
	}

	/** Rutas cuya caja (con margen) toca el chunk. Barato: cuentas con las casillas cercanas, todo en memoria. */
	public List<Ruta> rutas(int chunkX, int chunkZ) {
		int x0 = chunkX * 16, z0 = chunkZ * 16, x1 = x0 + 15, z1 = z0 + 15;
		int r = maxDist + pad;
		List<Ruta> out = null;
		// una casilla de más a cada lado: la rejilla puede tener el origen desplazado (las aldeas no)
		for (int gx = cellOf(x0 - r) - 1, gxMax = cellOf(x1 + r) + 1; gx <= gxMax; gx++) {
			for (int gz = cellOf(z0 - r) - 1, gzMax = cellOf(z1 + r) + 1; gz <= gzMax; gz++) {
				long a = aldea(gx, gz);
				if (a == NONE) {
					continue;
				}
				for (long b : vecinas(gx, gz)) {
					if (Long.compare(a, b) >= 0) {
						continue; // cada ruta una vez: desde su aldea de menor clave
					}
					// caja de la recta con margen: descarta casi todo sin construir la ruta
					int minX = Math.min(px(a), px(b)) - pad, maxX = Math.max(px(a), px(b)) + pad;
					int minZ = Math.min(pz(a), pz(b)) - pad, maxZ = Math.max(pz(a), pz(b)) + pad;
					if (maxX < x0 || minX > x1 || maxZ < z0 || minZ > z1) {
						continue;
					}
					Ruta ruta = ruta(a, b);
					if (ruta.toca(x0, z0, x1, z1)) {
						if (out == null) {
							out = new ArrayList<>(2);
						}
						out.add(ruta);
					}
				}
			}
		}
		return out == null ? List.of() : out;
	}

	private record Clave(long a, long b) {
	}

	/**
	 * Punto medio (el vértice central) de la ruta más cercana a (x, z) de las que salen de las aldeas de las casillas a
	 * {@code casillas} o menos de la suya; {@link #NONE} si no hay ninguna. Para /heraldia review: solo calcula (las
	 * aldeas y las rutas, en memoria), sin tocar el mundo.
	 */
	public long tramoCercano(int x, int z, int casillas) {
		long origen = pack(x, z), mejor = NONE, mejorD = Long.MAX_VALUE;
		int gx0 = cellOf(x), gz0 = cellOf(z);
		for (int gx = gx0 - casillas; gx <= gx0 + casillas; gx++) {
			for (int gz = gz0 - casillas; gz <= gz0 + casillas; gz++) {
				long a = aldea(gx, gz);
				if (a == NONE) {
					continue;
				}
				for (long b : vecinas(gx, gz)) {
					Ruta r = ruta(a, b);
					int m = r.vertices() / 2;
					long p = pack((int) Math.round(r.x(m)), (int) Math.round(r.z(m)));
					long d = distSq(p, origen);
					if (d < mejorD || d == mejorD && p < mejor) {
						mejor = p;
						mejorD = d;
					}
				}
			}
		}
		return mejor;
	}

	/** Ruta entre dos aldeas (en cualquier orden: la misma). */
	public Ruta ruta(long a, long b) {
		long lo = Math.min(a, b), hi = Math.max(a, b);
		Clave k = new Clave(lo, hi);
		Ruta r = rutaMemo.get(k);
		if (r == null) {
			r = new Ruta(lo, hi, hitos.entre(px(lo), pz(lo), px(hi), pz(hi)), seed);
			if (rutaMemo.size() > CACHE_MAX) {
				rutaMemo.clear();
			}
			Ruta prev = rutaMemo.putIfAbsent(k, r);
			if (prev != null) {
				r = prev;
			} else if (LOGGED.getAndIncrement() < LOG_MAX) {
				LOGGER.info("Heraldia: camino entre las aldeas de {} {} y {} {}: {} bloques, {} vértices, {}", px(lo), pz(lo), px(hi), pz(hi),
						Math.round(r.longitud()), r.vertices(), r.farol ? "faroles" : "antorchas");
			}
		}
		return r;
	}

	/** Margen alrededor del eje que puede tocar una ruta: medio ancho máximo, los postes y el redondeo. */
	static final int MARGEN = 8;

	/** Amplitud máxima del serpenteo a cada lado de la recta, en bloques. */
	static final int MAX_SERPENTEO = 40;

	static long mix(long z) {
		z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
		z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
		return z ^ (z >>> 31);
	}

	/** Número en [0, 1) que solo depende de la semilla y de los argumentos. */
	static double azar(long seed, long a, long b) {
		return (mix(seed ^ mix(a * 0x9E3779B97F4A7C15L ^ mix(b + 0x632BE59BD9B4E019L))) >>> 11) * 0x1.0p-53;
	}

	/** Camino entre dos aldeas: vértices cada {@link #PASO} bloques, longitud acumulada y memoria del agua. */
	public static final class Ruta {
		public final long desde, hasta;
		final double[] xs, zs, s;
		final int minX, minZ, maxX, maxZ;
		/** Estilo de las farolas de esta ruta: farol sobre poste o antorcha. */
		public final boolean farol;
		private final int[] fondo;     // altura del fondo por vértice (Integer.MIN_VALUE = sin calcular)
		private final byte[] agua;     // Agua.ordinal() + 1 por vértice (0 = sin calcular)

		Ruta(long desde, long hasta, long hito, long seed) {
			this.desde = desde;
			this.hasta = hasta;
			long h = mix(seed ^ mix(desde) ^ mix(hasta * 31));
			this.farol = (h & 1) == 0;
			List<double[]> pts = new ArrayList<>();
			if (hito == NONE) {
				tramo(pts, px(desde), pz(desde), px(hasta), pz(hasta), h, true);
			} else {
				tramo(pts, px(desde), pz(desde), px(hito), pz(hito), h, true);
				tramo(pts, px(hito), pz(hito), px(hasta), pz(hasta), mix(h + 1), false);
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
			int m = MARGEN;
			minX = (int) Math.floor(mnx) - m;
			minZ = (int) Math.floor(mnz) - m;
			maxX = (int) Math.ceil(mxx) + m;
			maxZ = (int) Math.ceil(mxz) + m;
			fondo = new int[n];
			java.util.Arrays.fill(fondo, Integer.MIN_VALUE);
			agua = new byte[n];
		}

		/** Vértices de un tramo recto con serpenteo (dos senos de fase y frecuencia al azar, nulo en los extremos). */
		private static void tramo(List<double[]> pts, int ax, int az, int bx, int bz, long h, boolean first) {
			double dx = bx - ax, dz = bz - az, len = Math.hypot(dx, dz);
			int n = Math.max(1, (int) Math.round(len / PASO));
			double nx = len == 0 ? 0 : -dz / len, nz = len == 0 ? 0 : dx / len;
			double amp = Math.min(MAX_SERPENTEO, len * 0.05);
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
		public double arco(int i) {
			return s[i];
		}

		public double longitud() {
			return s[s.length - 1];
		}

		/** Algún tramo pasa (con el margen del ancho y los postes) por la caja: primero la caja entera, luego tramo a tramo. */
		boolean toca(int x0, int z0, int x1, int z1) {
			if (maxX < x0 || minX > x1 || maxZ < z0 || minZ > z1) {
				return false;
			}
			for (int i = 0; i + 1 < xs.length; i++) {
				if (Math.max(xs[i], xs[i + 1]) + MARGEN >= x0 && Math.min(xs[i], xs[i + 1]) - MARGEN <= x1
						&& Math.max(zs[i], zs[i + 1]) + MARGEN >= z0 && Math.min(zs[i], zs[i + 1]) - MARGEN <= z1) {
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
		public Agua agua(int k, Fondo f, int sea) {
			byte v = agua[k];
			if (v != 0) {
				return Agua.values()[v - 1];
			}
			Agua a = clasificar(k, f, sea);
			agua[k] = (byte) (a.ordinal() + 1);
			return a;
		}

		private int fondo(int i, Fondo f) {
			int v = fondo[i];
			if (v == Integer.MIN_VALUE) {
				v = f.en((int) Math.floor(xs[i]), (int) Math.floor(zs[i]));
				fondo[i] = v;
			}
			return v;
		}

		/**
		 * Agua en un vértice: fondo bajo el nivel del mar. Se recorre la ruta hacia los dos lados hasta tierra: si el
		 * tramo de agua mide hasta {@link #PUENTE_MAX}, puente; si es más largo pero nunca más hondo que
		 * {@link #PASARELA_PROFUNDIDAD} (marismas, pantanos), pasarela hasta {@link #PASARELA_MAX}; si no, se corta.
		 * Solo se miran los vértices necesarios para decidir.
		 */
		Agua clasificar(int k, Fondo f, int sea) {
			if (fondo(k, f) >= sea) {
				return Agua.TIERRA;
			}
			int lo = k, hi = k, deepest = sea - fondo(k, f);
			double limit = PASARELA_MAX;
			while (lo > 0 && fondo(lo - 1, f) < sea && s[k] - s[lo - 1] <= limit) {
				lo--;
				deepest = Math.max(deepest, sea - fondo(lo, f));
				if (deepest > PASARELA_PROFUNDIDAD) {
					limit = PUENTE_MAX;
				}
			}
			while (hi < xs.length - 1 && fondo(hi + 1, f) < sea && s[hi + 1] - s[k] <= limit) {
				hi++;
				deepest = Math.max(deepest, sea - fondo(hi, f));
				if (deepest > PASARELA_PROFUNDIDAD) {
					limit = PUENTE_MAX;
				}
			}
			// largo del agua: entre los vértices de tierra de los dos lados (o el extremo de la ruta)
			boolean openLo = lo > 0 && fondo(lo - 1, f) < sea, openHi = hi < xs.length - 1 && fondo(hi + 1, f) < sea;
			double len = s[Math.min(hi + 1, xs.length - 1)] - s[Math.max(lo - 1, 0)];
			if (deepest <= PASARELA_PROFUNDIDAD) {
				return !openLo && !openHi && len <= PASARELA_MAX ? Agua.PASARELA : Agua.CORTE;
			}
			return !openLo && !openHi && len <= PUENTE_MAX + PASO ? Agua.PUENTE : Agua.CORTE;
		}
	}

	// --- pintar un chunk ---

	/** Medio ancho que nunca se mella: lo justo para que el camino siga unido por las caras de sus columnas. */
	static final double NUCLEO = 0.75;

	/** Columna del camino: la ruta más cercana, su vértice más cercano, la longitud recorrida y la distancia al eje. */
	public record Celda(Ruta ruta, int vertice, double arco, double dist) {
	}

	/**
	 * Columnas del chunk que son camino, en orden x * 16 + z (null = no). Una columna lo es si su centro está a menos de
	 * medio ancho del eje; en el borde (el último medio bloque, fuera del núcleo {@link #NUCLEO}) solo a veces (azar por columna), para que no quede recto.
	 * Depende solo de la columna y de las rutas, no del chunk: los vecinos casan en la frontera.
	 */
	public Celda[] pintar(List<Ruta> rutas, int chunkX, int chunkZ, int ancho) {
		Celda[] out = new Celda[256];
		// con medio ancho de 0,71 o más (raíz de 2 entre 2) las columnas del camino quedan unidas por sus caras en
		// cualquier dirección: se puede andar sin pasar en diagonal entre dos esquinas
		double half = Math.max(ancho / 2.0, NUCLEO);
		int x0 = chunkX * 16, z0 = chunkZ * 16;
		for (Ruta r : rutas) {
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
						Celda prev = out[idx];
						if (prev == null || d < prev.dist) {
							out[idx] = new Celda(r, t < 0.5 ? i : i + 1, r.s[i] + t * Math.sqrt(l2), d);
						}
					}
				}
			}
		}
		for (int idx = 0; idx < 256; idx++) {
			Celda c = out[idx];
			if (c != null && c.dist > Math.max(half - 0.5, NUCLEO) && azar(seed, pack(x0 + idx / 16, z0 + idx % 16), 7) < 0.35) {
				out[idx] = null; // borde mellado
			}
		}
		return out;
	}

	/** Farola o cartel junto al camino. Cartel: hacia qué aldea apunta, cuánto falta y la rotación (0-15) del letrero. */
	public record Marca(boolean cartel, int x, int z, Ruta ruta, int vertice, long destino, int distancia, int rotacion, boolean derecha) {
	}

	/**
	 * Farolas (cada {@link #FAROLA_CADA} vértices, alternando lado, lejos de las aldeas) y los dos carteles de la ruta
	 * (a {@link #CARTEL_A} bloques de cada aldea, en el lado contrario a la farola de ese vértice), de las columnas del
	 * chunk. La columna sale de la ruta, no del chunk.
	 */
	public List<Marca> marcas(List<Ruta> rutas, int chunkX, int chunkZ, int ancho) {
		List<Marca> out = new ArrayList<>();
		int x0 = chunkX * 16, z0 = chunkZ * 16;
		double off = ancho / 2.0 + 1.0;
		for (Ruta r : rutas) {
			int n = r.xs.length;
			int first = -1, last = -1;
			for (int i = 0; i < n; i++) {
				if (first < 0 && r.s[i] >= CARTEL_A) {
					first = i;
				}
				if (r.s[i] <= r.longitud() - CARTEL_A) {
					last = i;
				}
			}
			for (int i = 0; i < n; i++) {
				// fuera del chunk: solo cuentas
				if (r.xs[i] < x0 - off - 2 || r.xs[i] > x0 + 16 + off + 2 || r.zs[i] < z0 - off - 2 || r.zs[i] > z0 + 16 + off + 2) {
					continue;
				}
				double[] nrm = r.normal(i);
				int lado = (i / FAROLA_CADA) % 2 == 0 ? 1 : -1;
				boolean lejos = r.s[i] >= CARTEL_A / 2.0 && r.s[i] <= r.longitud() - CARTEL_A / 2.0;
				if (i % FAROLA_CADA == 0 && lejos) {
					add(out, false, r, i, nrm, lado * off, x0, z0, NONE, 0, 0, false);
				}
				if ((i == first || i == last) && first >= 0 && first < last) {
					boolean haciaHasta = i == first; // el primero (cerca de «desde») señala «hasta»
					long destino = haciaHasta ? r.hasta : r.desde;
					int dist = (int) Math.round(haciaHasta ? r.longitud() - r.s[i] : r.s[i]);
					double sideOff = -(i % FAROLA_CADA == 0 ? lado : 1) * off;
					// el letrero mira al camino; la flecha dice a qué mano queda el destino para quien lo lee
					double fx = -Math.signum(sideOff) * nrm[0], fz = -Math.signum(sideOff) * nrm[1];
					int rot = Math.floorMod((int) Math.round(Math.toDegrees(Math.atan2(-fx, fz)) / 22.5), 16);
					double tx = haciaHasta ? r.xs[Math.min(n - 1, i + 1)] - r.xs[i] : r.xs[Math.max(0, i - 1)] - r.xs[i];
					double tz = haciaHasta ? r.zs[Math.min(n - 1, i + 1)] - r.zs[i] : r.zs[Math.max(0, i - 1)] - r.zs[i];
					// lector mirando al letrero (dirección -f): su derecha es (f.z, -f.x)
					boolean derecha = tx * fz - tz * fx > 0;
					add(out, true, r, i, nrm, sideOff, x0, z0, destino, dist, rot, derecha);
				}
			}
		}
		return out;
	}

	private static void add(List<Marca> out, boolean cartel, Ruta r, int i, double[] nrm, double off, int x0, int z0, long destino,
							int dist, int rot, boolean derecha) {
		int x = (int) Math.floor(r.xs[i] + nrm[0] * off), z = (int) Math.floor(r.zs[i] + nrm[1] * off);
		if (x >= x0 && x < x0 + 16 && z >= z0 && z < z0 + 16) {
			out.add(new Marca(cartel, x, z, r, i, destino, dist, rot, derecha));
		}
	}
}
