package io.github.albertosa23.heraldia.uniques.atlantis;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertTrue;

import net.minecraft.SharedConstants;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * BasePiece.hash and wallHeight must be identical to the generator's (Python) urbanismo.dispersion and alto_muro: the wall
 * the Java places has to match the one the generator audits. The checksums come from Python and the same
 * computation is in tools/gen/tests/test_atlantida.py: if one side changes, its test fails.
 */
class BasePieceTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void hashLikeInPython() {
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
	void wallLikeInPython() {
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
