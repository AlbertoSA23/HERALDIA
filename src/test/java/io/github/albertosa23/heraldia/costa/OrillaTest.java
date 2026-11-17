package io.github.albertosa23.heraldia.costa;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.function.IntBinaryOperator;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Rotation;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * La orilla de los faros y naufragios ({@link Orilla}) con mapas de alturas sintéticos: una costa recta en cada una de
 * las cuatro direcciones (el ancla en el último bloque de tierra y el +z de la plantilla hacia el mar), sin costa, risco,
 * desnivel, un río estrecho, la profundidad que pide cada variante, la preferencia del faro por los cabos y las formas del
 * datapack generado (las huellas de verdad: el faro sobre tierra, su embarcadero y la popa o el casco sobre el agua).
 */
class OrillaTest {
	private static final int SEA = 63;
	private static final Orilla.Forma FARO = new Orilla.Forma(Orilla.Modo.FARO, new int[]{-7, -20, 7, -1}, new int[]{-1, 2, 1, 10});
	private static final Orilla.Forma ENCALLADO = new Orilla.Forma(Orilla.Modo.ENCALLADO, new int[]{-3, -14, 3, -3}, new int[]{-3, 3, 3, 16});
	private static final Orilla.Forma HUNDIDO = new Orilla.Forma(Orilla.Modo.HUNDIDO, new int[]{-2, -6, 2, -2}, new int[]{-4, 8, 4, 38});

	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	/** Terreno: suelo(x, z); agua donde el suelo queda bajo el mar. */
	private static Orilla.Terreno terreno(IntBinaryOperator suelo) {
		return new Orilla.Terreno() {
			@Override
			public int suelo(int x, int z) {
				return suelo.applyAsInt(x, z);
			}

			@Override
			public boolean agua(int x, int z) {
				return suelo.applyAsInt(x, z) < SEA;
			}
		};
	}

	/** Costa recta: tierra a `tierra` hasta la orilla (a 10 bloques del centro hacia d) y mar de `hondo` después. */
	private static Orilla.Terreno recta(Direction d, int tierra, int hondo) {
		return terreno((x, z) -> x * d.getStepX() + z * d.getStepZ() < 10 ? tierra : SEA - hondo);
	}

	@Test
	void costaRectaEnCadaDireccion() {
		for (Direction d : Direction.Plane.HORIZONTAL) {
			Orilla.Sitio s = Orilla.buscar(recta(d, SEA + 2, 6), SEA, 0, 0, FARO);
			assertNotNull(s, "faro hacia el " + d);
			assertEquals(d, s.mar(), "el +z de la plantilla mira al mar");
			assertEquals(9, s.x() * d.getStepX() + s.z() * d.getStepZ(), "el ancla en el último bloque de tierra");
			assertEquals(SEA + 1, s.y(), "la plataforma a ras de lo más alto (suelo - 1)");
			Rotation r = CostaStructure.giro(d);
			BlockPos v = new BlockPos(0, 0, 1).rotate(r);
			assertEquals(d.getStepX(), v.getX());
			assertEquals(d.getStepZ(), v.getZ());
			BlockPos ancho = new BlockPos(1, 0, 0).rotate(r);
			assertEquals(d.getCounterClockWise().getStepX(), ancho.getX(), "el +x de la plantilla, como en la búsqueda");
			assertEquals(d.getCounterClockWise().getStepZ(), ancho.getZ());
		}
	}

	@Test
	void sinCostaNoHaySitio() {
		assertNull(Orilla.buscar(terreno((x, z) -> SEA + 3), SEA, 0, 0, FARO), "todo tierra");
		assertNull(Orilla.buscar(terreno((x, z) -> SEA - 20), SEA, 0, 0, FARO), "todo mar");
		assertNull(Orilla.buscar(terreno((x, z) -> SEA - 20), SEA, 0, 0, HUNDIDO), "todo mar, tampoco el naufragio");
		// la orilla lejos del centro (más allá del alcance de la búsqueda)
		assertNull(Orilla.buscar(terreno((x, z) -> z < 90 ? SEA + 2 : SEA - 6), SEA, 0, 0, FARO));
	}

	@Test
	void farosSoloEnTierraFirmeYBaja() {
		assertNull(Orilla.buscar(recta(Direction.SOUTH, SEA + 12, 6), SEA, 0, 0, FARO), "un risco: la tierra está demasiado alta");
		assertNull(Orilla.buscar(terreno((x, z) -> z >= 10 ? SEA - 6 : z > -10 ? SEA + 1 : SEA + 6), SEA, 0, 0, FARO),
				"más de 4 bloques de desnivel en la huella");
		Orilla.Sitio s = Orilla.buscar(terreno((x, z) -> z >= 10 ? SEA - 6 : z > -5 ? SEA + 1 : SEA + 4), SEA, 0, 0, FARO);
		assertNotNull(s, "con 3 de desnivel sí");
		assertEquals(SEA + 3, s.y(), "a la altura de lo más alto (lo demás con cimientos)");
		assertNull(Orilla.buscar(recta(Direction.SOUTH, SEA + 2, 1), SEA, 0, 0, FARO), "sin fondo para el embarcadero");
	}

	@Test
	void unRioEstrechoNoEsCosta() {
		// tierra a los dos lados de un canal de 4 bloques: no hay mar para el embarcadero ni para la popa
		Orilla.Terreno rio = terreno((x, z) -> z >= 10 && z < 14 ? SEA - 4 : SEA + 2);
		assertNull(Orilla.buscar(rio, SEA, 0, 0, FARO));
		assertNull(Orilla.buscar(rio, SEA, 0, 0, ENCALLADO));
		assertNull(Orilla.buscar(rio, SEA, 0, 0, HUNDIDO));
	}

	@Test
	void profundidadDeCadaNaufragio() {
		assertNotNull(Orilla.buscar(recta(Direction.EAST, SEA + 1, 3), SEA, 0, 0, ENCALLADO), "encallado: playa y bajío");
		assertNull(Orilla.buscar(recta(Direction.EAST, SEA + 1, 14), SEA, 0, 0, ENCALLADO), "encallado: mar hondo, no");
		assertNull(Orilla.buscar(recta(Direction.EAST, SEA + 6, 3), SEA, 0, 0, ENCALLADO), "encallado: la proa no sube a un risco");
		assertNotNull(Orilla.buscar(recta(Direction.EAST, SEA + 2, 6), SEA, 0, 0, HUNDIDO), "semihundido: aguas de 6");
		assertNull(Orilla.buscar(recta(Direction.EAST, SEA + 2, 1), SEA, 0, 0, HUNDIDO), "semihundido: demasiado poco hondo");
		assertNull(Orilla.buscar(recta(Direction.EAST, SEA + 2, 16), SEA, 0, 0, HUNDIDO), "semihundido: demasiado hondo");
		assertEquals(-1, Orilla.buscar(recta(Direction.EAST, SEA + 2, 6), SEA, 0, 0, HUNDIDO).y(), "la altura la da la fila del mar");
	}

	@Test
	void algunaRocaEnElBajioNoImporta() {
		// una muestra de mar de 20 seca (un islote de 1 x 1): el 80 % basta
		Orilla.Terreno t = terreno((x, z) -> x == 1 && z == 22 ? SEA + 1 : z < 10 ? SEA + 1 : SEA - 5);
		assertNotNull(Orilla.evaluar(t, SEA, 0, 9, Direction.SOUTH, HUNDIDO));
		Orilla.Terreno muchas = terreno((x, z) -> z >= 20 && z <= 40 && Math.floorMod(x, 2) == 0 ? SEA + 1 : z < 10 ? SEA + 1 : SEA - 5);
		assertNull(Orilla.evaluar(muchas, SEA, 0, 9, Direction.SOUTH, HUNDIDO), "un arrecife entero, no");
	}

	@Test
	void elFaroPrefiereLosCabos() {
		// una esquina de costa: mar al sur (z >= 24) y al este (x >= 24); cerca de la esquina hay más agua alrededor
		Orilla.Terreno esquina = terreno((x, z) -> z >= 24 || x >= 24 && z >= -40 ? SEA - 8 : SEA + 2);
		Orilla.Sitio s = Orilla.buscar(esquina, SEA, 0, 0, FARO);
		assertNotNull(s);
		Orilla.Sitio recta = Orilla.evaluar(terreno((x, z) -> z >= 24 ? SEA - 8 : SEA + 2), SEA, 0, 23, Direction.SOUTH, FARO);
		assertNotNull(recta);
		assertTrue(s.nota() > recta.nota(), "más agua alrededor que en la costa recta: " + s + " / " + recta);
		assertTrue(s.x() > 0 && s.z() > 0, "hacia la esquina: " + s);
	}

	@Test
	void formasDelDatapackGenerado() throws IOException {
		Path dir = Path.of(System.getProperty("heraldia.generated", "build/generated/heraldia"), "data", "heraldia", "worldgen", "structure", "costa");
		if (!Files.isDirectory(dir)) {
			return;                                       // sin generar (la prueba unitaria sola)
		}
		List<Path> fs = new ArrayList<>();
		try (var w = Files.walk(dir)) {
			w.filter(p -> p.toString().endsWith(".json")).forEach(fs::add);
		}
		assertEquals(16, fs.size(), "2 tipos x 4 estilos x 2 variantes");
		for (Path f : fs) {
			JsonObject o = JsonParser.parseString(Files.readString(f)).getAsJsonObject();
			Orilla.Modo modo = Orilla.Modo.de(o.get("modo").getAsString());
			int[] tierra = arr(o, "tierra"), mar = arr(o, "mar");
			assertTrue(tierra[3] < 0 && mar[1] > 0, f + ": la tierra detrás del ancla y el mar delante");
			Orilla.Forma forma = new Orilla.Forma(modo, tierra, mar);
			int hondo = modo == Orilla.Modo.HUNDIDO ? 6 : modo == Orilla.Modo.ENCALLADO ? 3 : 5;
			assertNotNull(Orilla.buscar(recta(Direction.NORTH, SEA + 1, hondo), SEA, 0, 0, forma), f + " en una costa normal");
			assertTrue(f.toString().contains("/faro/") == (modo == Orilla.Modo.FARO), f.toString());
			assertTrue(o.get("fila_mar").getAsInt() >= (modo == Orilla.Modo.FARO ? -1 : 0));
			assertEquals(o.getAsJsonArray("climas").isEmpty(), false, f + ": sin climas");
		}
	}

	private static int[] arr(JsonObject o, String k) {
		var a = o.getAsJsonArray(k);
		int[] out = new int[a.size()];
		for (int i = 0; i < out.length; i++) {
			out[i] = a.get(i).getAsInt();
		}
		return out;
	}

	@Test
	void cuantasMuestras() {
		assertEquals(4 * 5, Orilla.cuantas(new int[]{-7, -20, 7, -1}), "15 x 20 cada 5: 4 x 5 muestras (con el borde)");
		assertEquals(1, Orilla.cuantas(new int[]{0, 0, 0, 0}));
	}
}
