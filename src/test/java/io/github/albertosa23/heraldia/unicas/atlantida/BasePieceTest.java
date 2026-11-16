package io.github.albertosa23.heraldia.unicas.atlantida;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * BasePiece.hash y wallHeight deben ser idénticas a urbanismo.dispersion y alto_muro del generador (Python): la muralla
 * que pone el Java tiene que coincidir con la que audita el generador. Las sumas de control salen de Python y la misma
 * cuenta está en tools/gen/tests/test_atlantida.py: si cambia un lado, falla su prueba.
 */
class BasePieceTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void hashComoEnPython() {
		assertEquals(0, BasePiece.hash(0, 0, 0));
		assertEquals(1914873318, BasePiece.hash(1, 2, 3));
		assertEquals(1252417215, BasePiece.hash(-5, 7, 1));
		assertEquals(2096724523, BasePiece.hash(100, -100, 2));
		assertEquals(706372064, BasePiece.hash(123456, -654321, 9));
		long h = 0;
		for (int x = -300; x <= 300; x += 7) {
			for (int z = -300; z <= 300; z += 11) {
				h = (h * 31 + BasePiece.hash(x, z, x ^ z)) & 0xFFFFFFFFL;
			}
		}
		assertEquals(935813057L, h);
	}

	@Test
	void murallaComoEnPython() {
		assertEquals(13, BasePiece.wallHeight(10, 0));
		assertEquals(6, BasePiece.wallHeight(0, 10));
		long s = 0;
		for (int x = -300; x <= 300; x += 7) {
			for (int z = -300; z <= 300; z += 11) {
				int w = BasePiece.wallHeight(x, z);
				assertTrue(w == BasePiece.WALL_HEIGHT || 3 <= w && w <= 7, "altura " + w);
				s = (s * 31 + w) & 0xFFFFFFFFL;
			}
		}
		assertEquals(4003156210L, s);
	}
}
