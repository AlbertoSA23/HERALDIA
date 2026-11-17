package io.github.albertosa23.heraldia.caravanas;

/**
 * El viaje de una caravana por su tramo (lógica pura, sin el juego): una máquina de estados que el juego alimenta cada
 * {@link #CADA} ticks con lo que ve ({@link Vista}) y que dice qué hacer ({@link Paso}). Fases: en camino, asaltada y
 * terminada (con su {@link Fin}). Todo por vértices del tramo (0 = salida, {@code vertices - 1} = llegada).
 */
public final class Viaje {
	/** Cada cuántos ticks se mira la caravana activa (1 s). */
	public static final int CADA = 20;
	/** A cuántos bloques del vértice se da por alcanzado. */
	public static final double ALCANZA = 2.5;
	/** Sin ningún jugador a {@link Caravanas#RADIO_JUGADORES} bloques durante este tiempo, la caravana se despide. */
	public static final int LEJOS_TICKS = 30 * 20;
	/** Lo más que dura un viaje (10 min) y un asalto (3 min). */
	public static final int MAX_TICKS = 10 * 60 * 20, ASALTO_MAX_TICKS = 3 * 60 * 20;
	/** Sin acercarse al vértice siguiente durante este tiempo, se salta al siguiente; tras {@link #ATASCOS_MAX}, se despide. */
	public static final int ATASCADA_TICKS = 20 * 20, ATASCOS_MAX = 3;

	public enum Fase { CAMINO, ASALTO, FIN }

	/** Cómo acaba: llegada (con o sin asalto superado), el mercader muerto, o se despide (jugadores lejos, sin camino...). */
	public enum Fin {
		LLEGADA("llegada"), PERDIDA("perdida"), LEJOS("lejos"), SIN_CAMINO("sin_camino"), ATASCADA("atascada"),
		TIEMPO("tiempo"), LIMPIEZA("limpieza");

		public final String id;

		Fin(String id) {
			this.id = id;
		}

		/** ¿Se despide sin más (ni premio ni pérdida)? */
		public boolean despedida() {
			return this != LLEGADA && this != PERDIDA;
		}
	}

	/** Qué tiene que hacer el juego tras un paso. */
	public enum Paso {
		/** Nada nuevo: seguir hacia el vértice {@link #siguiente()}. */
		SIGUE,
		/** Ha alcanzado un vértice: el objetivo pasa a {@link #siguiente()}. */
		AVANZA,
		/** Empieza el asalto: que salgan los bandidos. */
		ASALTO,
		/** Ya no queda ningún bandido vivo: sigue el viaje. */
		SUPERADO,
		/** Se acabó ({@link #fin()}): recompensa, pérdida o despedida, y quitar sus entidades. */
		FIN
	}

	/**
	 * Lo que ve el juego en un paso.
	 *
	 * @param mercaderVivo     el mercader sigue vivo (si murió, la caravana se pierde)
	 * @param cargado          el mercader y el vértice siguiente están en chunks cargados (si no, los jugadores se han ido)
	 * @param distSiguiente    distancia en el plano del mercader al vértice siguiente
	 * @param jugadores        jugadores a {@link Caravanas#RADIO_JUGADORES} bloques del mercader
	 * @param bandidos         bandidos vivos (en el asalto)
	 * @param caminoSiguiente  hay camino en el vértice siguiente (false: en un mundo existente el camino acaba ahí)
	 */
	public record Vista(boolean mercaderVivo, boolean cargado, double distSiguiente, int jugadores, int bandidos, boolean caminoSiguiente) {
	}

	private final int vertices;
	private final int asaltoEn;
	private Fase fase = Fase.CAMINO;
	private Fin fin;
	private int siguiente = 1;
	private int ticks, sinJugadores, enAsalto, atascada, atascos;
	private double mejor = Double.MAX_VALUE;
	private boolean asaltada, superada;

	/**
	 * @param vertices vértices del tramo (al menos 2)
	 * @param asaltoEn vértice del tramo en el que la asaltan (entre 1 y {@code vertices - 2}), o -1 si no hay asalto
	 */
	public Viaje(int vertices, int asaltoEn) {
		if (vertices < 2) {
			throw new IllegalArgumentException("un tramo tiene al menos 2 vértices");
		}
		this.vertices = vertices;
		this.asaltoEn = asaltoEn;
	}

	/** Vértice del tramo en el que conviene poner el asalto: hacia la mitad (entre el 40 y el 60 % según {@code azar}). */
	public static int puntoDeAsalto(int vertices, double azar) {
		int k = (int) Math.round((vertices - 1) * (0.4 + 0.2 * azar));
		return Math.max(1, Math.min(vertices - 2, k));
	}

	public Fase fase() {
		return fase;
	}

	public Fin fin() {
		return fin;
	}

	/** Vértice del tramo hacia el que va. */
	public int siguiente() {
		return siguiente;
	}

	public int vertices() {
		return vertices;
	}

	public int asaltoEn() {
		return asaltoEn;
	}

	public boolean asaltada() {
		return asaltada;
	}

	/** Hubo asalto y no quedó ningún bandido vivo. */
	public boolean superada() {
		return superada;
	}

	public int ticks() {
		return ticks;
	}

	/** Un paso de {@link #CADA} ticks. */
	public Paso paso(Vista v) {
		if (fase == Fase.FIN) {
			return Paso.FIN;
		}
		if (!v.mercaderVivo()) {
			return terminar(Fin.PERDIDA);
		}
		if (!v.cargado()) {
			return terminar(Fin.LEJOS);
		}
		ticks += CADA;
		sinJugadores = v.jugadores() > 0 ? 0 : sinJugadores + CADA;
		if (sinJugadores >= LEJOS_TICKS) {
			return terminar(Fin.LEJOS);
		}
		if (fase == Fase.ASALTO) {
			if (v.bandidos() <= 0) {
				superada = true;
				fase = Fase.CAMINO;
				mejor = Double.MAX_VALUE;
				atascada = 0;
				return Paso.SUPERADO;
			}
			enAsalto += CADA;
			return enAsalto >= ASALTO_MAX_TICKS ? terminar(Fin.TIEMPO) : Paso.SIGUE;
		}
		if (ticks >= MAX_TICKS) {
			return terminar(Fin.TIEMPO);
		}
		if (!v.caminoSiguiente()) {
			return terminar(Fin.SIN_CAMINO);
		}
		if (v.distSiguiente() <= ALCANZA) {
			if (siguiente >= vertices - 1) {
				return terminar(Fin.LLEGADA);
			}
			int alcanzado = siguiente;
			siguiente++;
			mejor = Double.MAX_VALUE;
			atascada = 0;
			if (alcanzado == asaltoEn && !asaltada) {
				return empezarAsalto();
			}
			return Paso.AVANZA;
		}
		if (v.distSiguiente() < mejor - 0.5) {
			mejor = v.distSiguiente();
			atascada = 0;
			return Paso.SIGUE;
		}
		atascada += CADA;
		if (atascada >= ATASCADA_TICKS) {
			atascos++;
			if (atascos > ATASCOS_MAX || siguiente >= vertices - 1) {
				return terminar(Fin.ATASCADA);
			}
			siguiente++;
			mejor = Double.MAX_VALUE;
			atascada = 0;
			return Paso.AVANZA;
		}
		return Paso.SIGUE;
	}

	/** Asalto ya (/heraldia caravan raid): solo en camino y si aún no la han asaltado. */
	public boolean forzarAsalto() {
		if (fase != Fase.CAMINO || asaltada) {
			return false;
		}
		empezarAsalto();
		return true;
	}

	private Paso empezarAsalto() {
		asaltada = true;
		fase = Fase.ASALTO;
		enAsalto = 0;
		return Paso.ASALTO;
	}

	/** Termina ya (el mercader muerto, una limpieza o el servidor que se para). */
	public Paso terminar(Fin f) {
		if (fase != Fase.FIN) {
			fase = Fase.FIN;
			fin = f;
		}
		return Paso.FIN;
	}
}
