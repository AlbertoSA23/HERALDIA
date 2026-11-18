package io.github.albertosa23.heraldia.version;

import java.util.HashSet;
import java.util.Set;
import java.util.UUID;

/**
 * Who has already been notified of the new version (pure logic): each operator, once per server session and per
 * version; if a newer one appears, everyone is notified again. Nothing is saved: after a restart they are notified again.
 */
public final class Notified {
	private String version;
	private final Set<UUID> already = new HashSet<>();

	/** True if `player` must be notified of `version` now (and records it). */
	public synchronized boolean shouldNotify(UUID player, String version) {
		if (!version.equals(this.version)) {
			this.version = version;
			already.clear();
		}
		return already.add(player);
	}
}
