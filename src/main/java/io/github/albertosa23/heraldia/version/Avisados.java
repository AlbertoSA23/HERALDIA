package io.github.albertosa23.heraldia.version;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/**
 * A quién se ha avisado ya de la versión nueva (lógica pura): a cada operador, una vez por sesión del servidor y por
 * versión; si aparece otra más nueva, se vuelve a avisar a todos. No se guarda nada: al reiniciar se avisa otra vez.
 */
public final class Avisados {
	private String version;
	private final Set<UUID> ya = new HashSet<>();

	/** True si hay que avisar ahora a `jugador` de `version` (y lo apunta). */
	public synchronized boolean marcar(UUID jugador, String version) {
		if (!version.equals(this.version)) {
			this.version = version;
			ya.clear();
		}
		return ya.add(jugador);
	}
}
