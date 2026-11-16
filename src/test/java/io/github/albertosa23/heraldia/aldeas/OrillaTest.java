package io.github.albertosa23.heraldia.aldeas;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.List;
import net.minecraft.SharedConstants;
import net.minecraft.core.Direction;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * Elección de la orilla del puerto ({@link Orilla}) con mapas de alturas sintéticos y las piezas de la aldea como cajas
 * (con el mismo {@code AldeaStructure.displaced} que en el juego): orilla junto a la plaza, calle bajo la punta,
 * ensenada, sin agua, risco, poco fondo y preferencia por las orillas libres.
 */
class OrillaTest {
	private static final int SEA = 63, LARGO = 18, ALCANCE = 80;
	private static final int TIERRA = SEA + 1, FONDO = SEA - 12;

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Pieza de la aldea: caja, calle (terrain_matching) y ruta de plantilla. */
	private record P(String name, BoundingBox box, boolean street, String path) {
	}

	private static P rigid(String name, String path, int x0, int z0, int x1, int z1) {
		return new P(name, new BoundingBox(x0, 60, z0, x1, 72, z1), false, path);
	}

	private static P street(int x0, int z0, int x1, int z1) {
		return new P("calle", new BoundingBox(x0, 60, z0, x1, 62, z1), true, "costa_pescadores/streets/s0");
	}

	/** Caja en planta (y de 60 a 72) de dos esquinas en cualquier orden. */
	private static BoundingBox box(int ax, int az, int bx, int bz) {
		return new BoundingBox(Math.min(ax, bx), 60, Math.min(az, bz), Math.max(ax, bx), 72, Math.max(az, bz));
	}

	/** Caseta 9 x 9 en tierra con su unión (centro de la cara del mar) en la orilla; muelle 9 x 18 desde un bloque mar adentro. */
	private static BoundingBox[] cajas(Orilla.Shore s) {
		Direction d = s.sea(), l = d.getClockWise();
		int x = s.x(), z = s.z();
		BoundingBox caseta = box(x - l.getStepX() * 4 - d.getStepX() * 8, z - l.getStepZ() * 4 - d.getStepZ() * 8,
				x + l.getStepX() * 4, z + l.getStepZ() * 4);
		BoundingBox muelle = box(x - l.getStepX() * 4 + d.getStepX(), z - l.getStepZ() * 4 + d.getStepZ(),
				x + l.getStepX() * 4 + d.getStepX() * LARGO, z + l.getStepZ() * 4 + d.getStepZ() * LARGO);
		return new BoundingBox[]{caseta, muelle};
	}

	private static Orilla.Eleccion<List<P>> elegir(Orilla.Fondo fondo, List<P> village) {
		return Orilla.elegir(fondo, SEA, 0, 0, ALCANCE, LARGO, s -> {
			BoundingBox[] c = cajas(s);
			return AldeaStructure.displaced(village, P::box, P::street, q -> AldeaStructure.removable(q.path), c[0], c[1],
					AldeaStructure.marLibre(c[1], s.sea()));
		}, List::isEmpty);
	}

	/** Mar al sur a partir de z = costa (fondo a 12 bajo el mar), playa baja al norte. */
	private static Orilla.Fondo marAlSur(int costa) {
		return (x, z) -> z >= costa ? FONDO : TIERRA;
	}

	/** La orilla elegida está en tierra baja junto al agua y su muelle tiene mar debajo, en la punta y a la mitad. */
	private static void enLaOrilla(Orilla.Fondo f, Orilla.Shore s) {
		assertNotNull(s);
		assertTrue(f.en(s.x(), s.z()) >= SEA && f.en(s.x(), s.z()) <= SEA + Orilla.BAJA, "la orilla es tierra baja: " + s);
		Direction d = s.sea();
		assertTrue(f.en(s.x() + d.getStepX() * LARGO, s.z() + d.getStepZ() * LARGO) <= SEA - 2, "agua en la punta: " + s);
		assertTrue(f.en(s.x() + d.getStepX() * LARGO / 2, s.z() + d.getStepZ() * LARGO / 2) < SEA, "agua a la mitad: " + s);
		assertTrue(Orilla.mar(f, SEA, s, LARGO));
	}

	@Test
	void laOrillaLibreMasCercana() {
		Orilla.Fondo f = marAlSur(40);
		Orilla.Eleccion<List<P>> e = elegir(f, List.of());
		Orilla.Shore s = e.shore();
		enLaOrilla(f, s);
		assertEquals(Direction.SOUTH, s.sea());
		assertEquals(0, s.x());
		assertEquals(38, s.z());              // última tierra con paso 2 (la 39 también lo es)
		assertEquals(List.of(), e.gone());
	}

	@Test
	void orillaJuntoALaPlaza() {
		// la plaza llega hasta la orilla delante del centro: el puerto va a lo largo de la costa, no encima
		Orilla.Fondo f = marAlSur(40);
		P plaza = rigid("plaza", "costa_pescadores/plaza/std", -15, -15, 15, 38);
		Orilla.Shore s = elegir(f, List.of(plaza)).shore();
		enLaOrilla(f, s);
		assertEquals(Direction.SOUTH, s.sea());
		BoundingBox[] c = cajas(s);
		assertFalse(c[0].intersects(plaza.box()) || c[1].intersects(plaza.box()), "el puerto no pisa la plaza: " + s);
		assertEquals(24, Math.abs(s.x()));   // la línea de al lado del nudo de 16 (a 16 la caseta, de 9, aún toca la plaza)
	}

	@Test
	void calleBajoLaPunta() {
		// la avenida baja hacia el sur y entra en el mar (tablas sobre el agua): el muelle no puede ir encima
		Orilla.Fondo f = marAlSur(40);
		P avenida = street(-2, -80, 2, 80);
		Orilla.Eleccion<List<P>> e = elegir(f, List.of(avenida));
		Orilla.Shore s = e.shore();
		enLaOrilla(f, s);
		assertFalse(cajas(s)[1].intersects(avenida.box().minX(), avenida.box().minZ(), avenida.box().maxX(), avenida.box().maxZ()));
		assertEquals(8, Math.abs(s.x()));    // la línea de al lado de la del centro: el muelle (9 de ancho) ya no la pisa
		assertTrue(e.bloqueadas() + e.descartadas() >= 1);
	}

	@Test
	void edificiosQueNoSeQuitanEnTodaLaCosta() {
		Orilla.Fondo f = marAlSur(40);
		P iglesia = rigid("iglesia", "costa_pescadores/specials/church", -200, 20, 200, 39);
		Orilla.Eleccion<List<P>> e = elegir(f, List.of(iglesia));
		assertNull(e.shore());
		assertEquals(e.candidatas(), e.bloqueadas());
		assertTrue(e.descartadas() > 3, "se descartan por las piezas las direcciones hacia la costa: " + e.descartadas());
	}

	@Test
	void unaPiezaEnElAguaPasadaLaPunta() {
		// el mercado está sobre el agua frente a la orilla más cercana: su terreno taparía la punta
		Orilla.Fondo f = marAlSur(40);
		P mercado = rigid("mercado", "costa_pescadores/specials/market_b", -12, 58, 12, 70);
		Orilla.Shore s = elegir(f, List.of(mercado)).shore();
		enLaOrilla(f, s);
		assertFalse(AldeaStructure.marLibre(cajas(s)[1], s.sea()).intersects(mercado.box()), s.toString());
	}

	@Test
	void elCentroDeLaAldeaNoGastaConsultas() {
		// la plaza y los edificios especiales tapan todo el centro: sus nudos no consultan el fondo
		Orilla.Fondo f = marAlSur(76);
		P centro = rigid("centro", "costa_pescadores/specials/church", -50, -50, 50, 50);
		Orilla.Eleccion<List<P>> libre = elegir(f, List.of());
		Orilla.Eleccion<List<P>> tapado = elegir(f, List.of(centro));
		assertNotNull(tapado.shore());
		assertTrue(tapado.descartadas() > 0);
		int nudosDentro = (int) Orilla.nudos(ALCANCE / Orilla.PASO).stream()
				.filter(n -> Math.abs(n[0] * Orilla.PASO) <= 34 && Math.abs(n[1] * Orilla.PASO) <= 34).count();
		assertTrue(nudosDentro > 0);
		assertTrue(tapado.consultas() <= libre.consultas(), tapado.consultas() + " <= " + libre.consultas());
	}

	@Test
	void prefiereUnaOrillaLibreADesplazarCasas() {
		Orilla.Fondo f = marAlSur(40);
		P casa = rigid("casa", "costa_pescadores/houses/small_0", -10, 25, 10, 39);
		Orilla.Eleccion<List<P>> e = elegir(f, List.of(casa));
		enLaOrilla(f, e.shore());
		assertEquals(List.of(), e.gone());
		assertTrue(Math.abs(e.shore().x()) >= 16);
		// casas en toda la costa: se quitan las de la orilla más cercana
		P hilera = rigid("hilera", "costa_pescadores/houses/large_0", -200, 25, 200, 39);
		P torre = rigid("torre", "costa_pescadores/terminators/tower", -200, 41, 200, 45);    // en el agua, bajo el muelle
		Orilla.Eleccion<List<P>> e2 = elegir(f, List.of(hilera, torre));
		enLaOrilla(f, e2.shore());
		assertEquals(0, e2.shore().x());
		assertEquals(List.of(hilera, torre), e2.gone());
	}

	@Test
	void ensenadaSinMarAbierto() {
		// una ría estrecha (7 de ancho) que entra hacia el centro: los botes no caben y el muelle acabaría en tierra
		Orilla.Fondo ria = (x, z) -> z >= 20 && Math.abs(x) <= 3 ? FONDO : TIERRA;
		Orilla.Eleccion<List<P>> e = elegir(ria, List.of());
		assertNull(e.shore());
		assertTrue(e.sinFondo() > 0, "la ría da orillas, pero sin mar abierto");
		// la misma ría con el mar abierto más allá: el puerto va al mar, no a la ría
		Orilla.Fondo conMar = (x, z) -> z >= 72 || (z >= 20 && Math.abs(x) <= 3) ? FONDO : TIERRA;
		Orilla.Shore s = elegir(conMar, List.of()).shore();
		enLaOrilla(conMar, s);
		assertEquals(Direction.SOUTH, s.sea());
		assertTrue(s.z() >= 64 && Math.abs(s.x()) > 3, "en la costa del mar abierto: " + s);
	}

	@Test
	void sinAgua() {
		java.util.Set<Long> columnas = new java.util.HashSet<>();
		Orilla.Eleccion<List<P>> e = elegir((x, z) -> {
			columnas.add(((long) x << 32) ^ (z & 0xFFFFFFFFL));
			return SEA + 8;
		}, List.of());
		assertNull(e.shore());
		assertEquals(0, e.candidatas());
		// tierra alta: una columna por nudo de la malla y nada más (en el juego la caché de Alturas sirve las repetidas)
		assertEquals(Orilla.nudos(ALCANCE / Orilla.PASO).size(), columnas.size());
	}

	@Test
	void unRiscoJuntoAlAguaNoEsOrilla() {
		Orilla.Fondo risco = (x, z) -> z >= 40 ? FONDO : SEA + 10;
		Orilla.Eleccion<List<P>> e = elegir(risco, List.of());
		assertNull(e.shore());
		assertEquals(0, e.candidatas());
		// playa baja con un escalón alto justo antes del agua: el punto afinado ya no es tierra baja
		Orilla.Fondo escalon = (x, z) -> z >= 40 ? FONDO : z >= 34 ? SEA + 9 : TIERRA;
		assertNull(elegir(escalon, List.of()).shore());
	}

	@Test
	void pocoFondoNoSirve() {
		Orilla.Fondo bajio = (x, z) -> z >= 40 ? SEA - 1 : TIERRA;
		Orilla.Eleccion<List<P>> e = elegir(bajio, List.of());
		assertNull(e.shore());
		assertEquals(e.candidatas(), e.sinFondo());
	}

	@Test
	void costaEnDiagonal() {
		Orilla.Fondo f = (x, z) -> x + z >= 60 ? FONDO : TIERRA;
		Orilla.Shore s = elegir(f, List.of()).shore();
		enLaOrilla(f, s);
		assertTrue(s.sea() == Direction.SOUTH || s.sea() == Direction.EAST, s.toString());
	}

	@Test
	void seBuscaDeDentroAfueraYSeParaAlEncontrar() {
		List<int[]> n = Orilla.nudos(5);
		assertEquals(81, n.size());
		assertEquals(0, n.get(0)[0]);
		assertEquals(0, n.get(0)[1]);
		for (int i = 1; i < n.size(); i++) {
			int a = n.get(i - 1)[0] * n.get(i - 1)[0] + n.get(i - 1)[1] * n.get(i - 1)[1];
			assertTrue(a <= n.get(i)[0] * n.get(i)[0] + n.get(i)[1] * n.get(i)[1]);
		}
		// con la orilla cerca no se mira toda la malla
		Orilla.Eleccion<List<P>> cerca = elegir(marAlSur(24), List.of());
		Orilla.Eleccion<List<P>> lejos = elegir(marAlSur(76), List.of());
		assertNotNull(cerca.shore());
		assertNotNull(lejos.shore());
		assertTrue(cerca.consultas() < lejos.consultas(), cerca.consultas() + " < " + lejos.consultas());
	}

	@Test
	void afinarConPaso2() {
		Orilla.Shore s = Orilla.afinar(marAlSur(40), SEA, 0, 32, TIERRA, Direction.SOUTH);
		assertEquals(new Orilla.Shore(0, 38, TIERRA, Direction.SOUTH), s);
		Orilla.Shore n = Orilla.afinar((x, z) -> z <= -40 ? FONDO : TIERRA, SEA, 16, -32, TIERRA, Direction.NORTH);
		assertEquals(new Orilla.Shore(16, -38, TIERRA, Direction.NORTH), n);
	}
}
