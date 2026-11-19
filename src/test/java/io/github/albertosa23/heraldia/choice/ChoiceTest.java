package io.github.albertosa23.heraldia.choice;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.netty.buffer.Unpooled;
import java.util.List;
import java.util.Map;
import net.minecraft.SharedConstants;
import net.minecraft.core.RegistryAccess;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.Component;
import net.minecraft.server.Bootstrap;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * The choice windows without a server: what a reply may name (the server's only defence against a modified client),
 * which presentation a player gets, the menu's layout and lore, the texts in the player's language, and the payloads'
 * round trip and limits (a payload too big to decode is refused, never half read).
 */
class ChoiceTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	private static Choice.Prompt prompt(String... ids) {
		List<Choice.Option> options = java.util.Arrays.stream(ids).map(id -> new Choice.Option(id, id.toUpperCase(), Choice.WHITE, ""))
				.toList();
		return new Choice.Prompt(Component.literal("Librarian"), List.of(new Choice.Line("Hello.", Choice.WHITE, false)), options);
	}

	@Test
	void aReplyCountsOnlyForTheCurrentSessionAndAnOptionOnOffer() {
		Choice.Offer offer = new Choice.Offer(7, prompt("more", "trade", "bye").ids());
		assertTrue(offer.accepts(7, "more"));
		assertTrue(offer.accepts(7, "bye"));
		assertTrue(offer.accepts(7, Choice.CLOSED), "closing the window is always allowed");
		assertFalse(offer.accepts(7, "rumor"), "an option that was not on screen (already asked)");
		assertFalse(offer.accepts(6, "more"), "a reply to an earlier window");
		assertFalse(offer.accepts(8, "more"), "a session that does not exist yet");
		assertFalse(offer.accepts(7, null));
		assertFalse(offer.accepts(7, "MORE"), "ids are exact");
		Choice.Offer waiting = new Choice.Offer(9, List.of());
		assertFalse(waiting.accepts(9, "more"), "while the answer is coming, nothing can be picked");
		assertTrue(waiting.accepts(9, Choice.CLOSED));
	}

	@Test
	void presentation() {
		assertEquals(Choice.Presentation.SCREEN, Choice.Presentation.of(true, true, true));
		assertEquals(Choice.Presentation.MENU, Choice.Presentation.of(true, true, false), "a client without the channel");
		assertEquals(Choice.Presentation.CHAT, Choice.Presentation.of(false, true, true), "the option off: as before");
		assertEquals(Choice.Presentation.CHAT, Choice.Presentation.of(false, true, false));
		assertEquals(Choice.Presentation.CHAT, Choice.Presentation.of(true, false, false), "automation's fake players");
	}

	@Test
	void promptLimits() {
		assertThrows(IllegalArgumentException.class, () -> prompt("a", "a"), "repeated ids");
		assertThrows(IllegalArgumentException.class, () -> new Choice.Option("", "x", 0, ""), "the empty id means closed");
		assertThrows(IllegalArgumentException.class, () -> new Choice.Option("x".repeat(Choice.MAX_ID + 1), "x", 0, ""));
		assertThrows(IllegalArgumentException.class, () -> prompt("1", "2", "3", "4", "5", "6", "7", "8", "9", "10"));
		assertEquals(Choice.MAX_TEXT, new Choice.Line("x".repeat(5000), 0, false).text().length(), "long texts are cut");
	}

	@Test
	void menuRow() {
		assertArrayEquals(new int[]{4}, Choice.row(1));
		assertArrayEquals(new int[]{3, 5}, Choice.row(2));
		assertArrayEquals(new int[]{2, 4, 6}, Choice.row(3));
		assertArrayEquals(new int[]{1, 3, 5, 7}, Choice.row(4));
		assertArrayEquals(new int[]{2, 3, 4, 5, 6}, Choice.row(5));
		assertArrayEquals(new int[]{0, 1, 2, 3, 4, 5, 6, 7, 8}, Choice.row(9));
		for (int n = 0; n <= 9; n++) {
			for (int slot : Choice.row(n)) {
				assertTrue(slot >= 0 && slot < 9);
			}
		}
	}

	@Test
	void wrapAndBrackets() {
		assertEquals(List.of("one two", "three"), Choice.wrap("one two three", 7));
		assertEquals(List.of("abcdefghij", "k"), Choice.wrap("abcdefghij k", 4), "a long word keeps its own line");
		assertEquals(List.of("a", "", "b"), Choice.wrap("a\n\nb", 10));
		for (String line : Choice.wrap("Your compass and the sun will tell you the rest: it is a hint, not a map.", 40)) {
			assertTrue(line.length() <= 40, line);
		}
		assertEquals("Keep talking", Choice.unbracket("[Keep talking]"));
		assertEquals("¿Qué se cuenta?", Choice.unbracket(" [¿Qué se cuenta?] "));
		assertEquals("Trade", Choice.unbracket("Trade"));
		assertEquals("[]", Choice.unbracket("[]"));
	}

	@Test
	void formatLikeTheGame() {
		assertEquals("a b", Choice.format("%s %s", List.of("a", "b")));
		assertEquals("b a", Choice.format("%2$s %1$s", List.of("a", "b")));
		assertEquals("100 %", Choice.format("%s %%", List.of("100")));
		assertEquals("x ", Choice.format("x %s", List.of()));
		assertEquals("50%", Choice.format("50%", List.of()));
	}

	@Test
	void textsInThePlayersLanguage() {
		Map<String, String> fr = Map.of("heraldia.x.linea", "%s : « %s »", "heraldia.x.nombre", "Maison du Héraut");
		Component line = Component.translatableWithFallback("heraldia.x.linea", "%s: “%s”", Component.literal("Ana"),
				Component.translatableWithFallback("heraldia.x.nombre", "Casa del Heraldo"));
		assertEquals("Ana : « Maison du Héraut »", Choices.text(line, fr));
		assertEquals("Ana: “Casa del Heraldo”", Choices.text(line, Map.of()), "without the key: its fallback");
		assertEquals("Ana and 3", Choices.text(Component.literal("Ana").append(" and ").append(Component.literal("3")), Map.of()));
	}

	@Test
	void payloadsRoundTrip() {
		Choice.Prompt p = new Choice.Prompt(Component.translatable("entity.minecraft.villager.librarian"),
				List.of(new Choice.Line("Hello.", Choice.WHITE, false), new Choice.Line("Sneak to trade.", Choice.GRAY, true)),
				List.of(new Choice.Option("more", "Keep talking", Choice.AQUA, ""), new Choice.Option("coop", "Co-op", Choice.GREEN, "help")));
		RegistryFriendlyByteBuf buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), RegistryAccess.EMPTY);
		ChoicePayloads.Open.CODEC.encode(buf, new ChoicePayloads.Open(42, p));
		ChoicePayloads.Open back = ChoicePayloads.Open.CODEC.decode(buf);
		assertEquals(42, back.session());
		assertEquals(p, back.prompt());
		assertEquals(0, buf.readableBytes());

		buf = new RegistryFriendlyByteBuf(Unpooled.buffer(), RegistryAccess.EMPTY);
		ChoicePayloads.Pick.CODEC.encode(buf, new ChoicePayloads.Pick(42, Choice.CLOSED));
		assertEquals(new ChoicePayloads.Pick(42, ""), ChoicePayloads.Pick.CODEC.decode(buf));

		// a modified client's pick with an id longer than any option: refused while decoding (the connection drops it)
		RegistryFriendlyByteBuf bad = new RegistryFriendlyByteBuf(Unpooled.buffer(), RegistryAccess.EMPTY);
		bad.writeVarInt(1);
		bad.writeUtf("x".repeat(200));
		assertThrows(Exception.class, () -> ChoicePayloads.Pick.CODEC.decode(bad));
	}

	@Test
	void channelsCarryTheProtocol() {
		assertEquals("heraldia:choice_v" + ChoicePayloads.PROTOCOL, ChoicePayloads.Open.TYPE.id().toString());
		assertEquals("heraldia:choice_close_v" + ChoicePayloads.PROTOCOL, ChoicePayloads.Close.TYPE.id().toString());
		assertEquals("heraldia:choice_pick_v" + ChoicePayloads.PROTOCOL, ChoicePayloads.Pick.TYPE.id().toString());
	}
}
