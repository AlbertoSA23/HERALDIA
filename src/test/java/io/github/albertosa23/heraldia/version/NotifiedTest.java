package io.github.albertosa23.heraldia.version;

import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.util.UUID;
import org.junit.jupiter.api.Test;

/** Once per server session and per version to each operator. */
class NotifiedTest {
	@Test
	void oncePerPlayerAndVersion() {
		Notified a = new Notified();
		UUID ana = UUID.randomUUID(), luis = UUID.randomUUID();
		assertTrue(a.shouldNotify(ana, "0.2.0"));
		assertFalse(a.shouldNotify(ana, "0.2.0"), "al volver a entrar en la misma sesión no se repite");
		assertTrue(a.shouldNotify(luis, "0.2.0"));
		assertFalse(a.shouldNotify(luis, "0.2.0"));
		// a newer one comes out: everyone is notified again, once
		assertTrue(a.shouldNotify(ana, "0.3.0"));
		assertFalse(a.shouldNotify(ana, "0.3.0"));
		assertTrue(a.shouldNotify(luis, "0.3.0"));
		// a new server session starts from scratch
		assertTrue(new Notified().shouldNotify(ana, "0.3.0"));
	}
}
