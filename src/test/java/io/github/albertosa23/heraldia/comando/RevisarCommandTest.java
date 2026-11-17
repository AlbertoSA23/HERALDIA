package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.comando.Revision.Parada;
import io.github.albertosa23.heraldia.comando.Revision.Tipo;
import java.util.Map;
import net.minecraft.SharedConstants;
import net.minecraft.resources.Identifier;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.level.block.Blocks;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * La parte de /heraldia review que toca clases del juego sin un mundo: qué estructuras son de cada parada, cómo se
 * clasifica cada bloque para el teletransporte seguro y la lista de qué mirar.
 */
class RevisarCommandTest {
	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static Identifier h(String path) {
		return Identifier.fromNamespaceAndPath("heraldia", path);
	}

	@Test
	void estructurasDeCadaParada() {
		Map<String, String> estilos = Map.of("llanuras_castellana", "llanuras", "bosque_lenadores", "bosque");
		Parada aldea = new Parada("aldea/llanuras", Tipo.ALDEA, "llanuras");
		assertTrue(RevisarCommand.deLaParada(aldea, h("llanuras_castellana"), estilos));
		assertTrue(RevisarCommand.deLaParada(aldea, h("llanuras_castellana_grande"), estilos));
		assertFalse(RevisarCommand.deLaParada(aldea, h("bosque_lenadores"), estilos));
		assertFalse(RevisarCommand.deLaParada(aldea, Identifier.fromNamespaceAndPath("minecraft", "llanuras_castellana"), estilos));
		Parada unica = new Parada("unica/castillo", Tipo.UNICA, "castillo");
		assertTrue(RevisarCommand.deLaParada(unica, h("unicas/castillo"), estilos));
		assertFalse(RevisarCommand.deLaParada(unica, h("unicas/castillo_negro"), estilos));
		Parada mediana = new Parada("mediana/posada", Tipo.MEDIANA, "posada");
		assertTrue(RevisarCommand.deLaParada(mediana, h("medianas/posada/llanura"), estilos));
		assertFalse(RevisarCommand.deLaParada(mediana, h("medianas/posadas/llanura"), estilos));
		Parada mina = new Parada("mina/pequena", Tipo.MINA, "pequena");
		assertTrue(RevisarCommand.deLaParada(mina, h("minas/pequena/roca/a"), estilos));
		assertFalse(RevisarCommand.deLaParada(mina, h("minas/mediana/roca/a"), estilos));
		assertFalse(RevisarCommand.deLaParada(new Parada("arena", Tipo.ARENA, ""), h("arena"), estilos));
	}

	@Test
	void celdasDelTeletransporte() {
		assertEquals(Seguro.Celda.LIBRE, RevisarCommand.celda(Blocks.AIR.defaultBlockState(), false));
		assertEquals(Seguro.Celda.LIBRE, RevisarCommand.celda(Blocks.SHORT_GRASS.defaultBlockState(), false));
		assertEquals(Seguro.Celda.SOLIDO, RevisarCommand.celda(Blocks.STONE.defaultBlockState(), true));
		assertEquals(Seguro.Celda.AGUA, RevisarCommand.celda(Blocks.WATER.defaultBlockState(), false));
		assertEquals(Seguro.Celda.PELIGRO, RevisarCommand.celda(Blocks.LAVA.defaultBlockState(), false));
		assertEquals(Seguro.Celda.PELIGRO, RevisarCommand.celda(Blocks.FIRE.defaultBlockState(), false));
		assertEquals(Seguro.Celda.PELIGRO, RevisarCommand.celda(Blocks.MAGMA_BLOCK.defaultBlockState(), true));
		assertEquals(Seguro.Celda.PELIGRO, RevisarCommand.celda(Blocks.CACTUS.defaultBlockState(), true));
		assertEquals(Seguro.Celda.PELIGRO, RevisarCommand.celda(Blocks.POWDER_SNOW.defaultBlockState(), false));
		assertEquals(Seguro.Celda.PELIGRO, RevisarCommand.celda(Blocks.CAMPFIRE.defaultBlockState(), true));
		assertEquals(Seguro.Celda.PELIGRO, RevisarCommand.celda(Blocks.SOUL_FIRE.defaultBlockState(), false));
		assertEquals(Seguro.Celda.SOLIDO, RevisarCommand.celda(Blocks.OAK_LEAVES.defaultBlockState(), true));
		// un bloque anegado con colisión sostiene (no es agua donde flotar)
		assertEquals(Seguro.Celda.SOLIDO, RevisarCommand.celda(Blocks.OAK_STAIRS.defaultBlockState()
				.setValue(net.minecraft.world.level.block.state.properties.BlockStateProperties.WATERLOGGED, true), true));
		assertEquals(Seguro.Celda.AGUA, RevisarCommand.celda(Blocks.SEAGRASS.defaultBlockState(), false), "hierba marina: agua");
	}

	@Test
	void listaDeQueMirar() {
		assertEquals(4, RevisarCommand.puntos(new Parada("unica/castillo", Tipo.UNICA, "castillo")).size());
		assertEquals("heraldia.revisar.mirar.unica.atlantida",
				RevisarCommand.puntos(new Parada("unica/atlantida", Tipo.UNICA, "atlantida")).getLast());
		assertEquals(3, RevisarCommand.puntos(new Parada("camino", Tipo.CAMINO, "")).size());
		for (Tipo t : Tipo.values()) {
			assertTrue(RevisarCommand.PUNTOS.containsKey(t), t.toString());
		}
	}

	@Test
	void textosDeLaRutaEnElJar() {
		Map<String, String> es = Textos.idioma(Textos.ES);
		for (Tipo t : Tipo.values()) {
			for (String k : RevisarCommand.puntos(new Parada("x", t, "atlantida"))) {
				assertTrue(es.containsKey(k), k);
			}
		}
		for (Revision.Marca m : Revision.Marca.values()) {
			assertTrue(es.containsKey("heraldia.revisar.estado." + m.name().toLowerCase(java.util.Locale.ROOT)), m.toString());
		}
		assertEquals("Un tramo de camino", RevisarCommand.nombreEs(new Parada("camino", Tipo.CAMINO, "")));
		assertTrue(RevisarCommand.nombreEs(new Parada("aldea/llanuras", Tipo.ALDEA, "llanuras")).contains("Aldea"));
	}
}
