package io.github.albertosa23.heraldia.inhabitants;

import static org.junit.jupiter.api.Assertions.assertEquals;

import io.github.albertosa23.heraldia.inhabitants.Inhabitants.Action;
import java.util.Set;
import org.junit.jupiter.api.Test;

class InhabitantsTest {
	private static final String TAG = Inhabitants.TAG;

	@Test
	void notAnInhabitant() {
		assertEquals(Action.NONE, Inhabitants.decide(Set.of(), true));
		assertEquals(Action.NONE, Inhabitants.decide(Set.of("heraldia_mediana", "heraldia_anclado"), false));
	}

	@Test
	void onTheyLive() {
		assertEquals(Action.LIVE, Inhabitants.decide(Set.of(TAG), true));
		assertEquals(Action.LIVE, Inhabitants.decide(Set.of(TAG, Inhabitants.STILL_BEFORE), true));
	}

	@Test
	void offTheOldFiguresStayStillAndTheNewOnesGo() {
		assertEquals(Action.STILL, Inhabitants.decide(Set.of(TAG, Inhabitants.STILL_BEFORE), false));
		assertEquals(Action.REMOVE, Inhabitants.decide(Set.of(TAG), false));
	}

	@Test
	void onceSeenNeverTouchedAgain() {
		for (boolean on : new boolean[] {true, false}) {
			assertEquals(Action.NONE, Inhabitants.decide(Set.of(TAG, Inhabitants.SEEN), on));
			assertEquals(Action.NONE, Inhabitants.decide(Set.of(TAG, Inhabitants.STILL_BEFORE, Inhabitants.SEEN), on));
		}
	}

	@Test
	void sameTagsAsTheGenerator() {
		// tools/gen/mediums/_inhabitants.py: TAG, STILL_BEFORE and SEEN
		assertEquals("heraldia_habitante", TAG);
		assertEquals("heraldia_habitante.quieto_antes", Inhabitants.STILL_BEFORE);
		assertEquals("heraldia_habitante.visto", Inhabitants.SEEN);
	}
}
