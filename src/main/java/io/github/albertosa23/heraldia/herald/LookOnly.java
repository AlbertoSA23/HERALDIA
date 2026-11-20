package io.github.albertosa23.heraldia.herald;

/**
 * A container window opened to look only (the Herald's House area, see {@link HeraldHouse#opened}): every container
 * menu carries this mark (HeraldLookMenuMixin), set once when the window opens and read when its client acts on it.
 */
public interface LookOnly {
	boolean heraldia$lookOnly();

	void heraldia$markLookOnly();
}
