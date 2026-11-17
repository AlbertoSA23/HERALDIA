package io.github.albertosa23.heraldia.version;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Una vez por sesión del servidor y por versión a cada operador. */
class AvisadosTest {
	@Test
	void unaVezPorJugadorYVersion() {
		Avisados a = new Avisados();
		UUID ana = UUID.randomUUID(), luis = UUID.randomUUID();
		assertTrue(a.marcar(ana, "0.2.0"));
		assertFalse(a.marcar(ana, "0.2.0"), "al volver a entrar en la misma sesión no se repite");
		assertTrue(a.marcar(luis, "0.2.0"));
		assertFalse(a.marcar(luis, "0.2.0"));
		// sale otra más nueva: se avisa otra vez a todos, una vez
		assertTrue(a.marcar(ana, "0.3.0"));
		assertFalse(a.marcar(ana, "0.3.0"));
		assertTrue(a.marcar(luis, "0.3.0"));
		// una sesión nueva del servidor empieza de cero
		assertTrue(new Avisados().marcar(ana, "0.3.0"));
	}
}
