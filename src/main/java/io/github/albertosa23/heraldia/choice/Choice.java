package io.github.albertosa23.heraldia.choice;

import java.util.ArrayList;
import java.util.List;
import java.util.Objects;
import net.minecraft.network.chat.Component;

/**
 * A choice put to one player in the middle of the screen (pure logic: only the title is a game text component): who speaks, what they say and
 * the options to pick from. The server decides all of it; the presentation only shows it and sends back which option
 * was picked, and the server checks that reply against what it offered ({@link Offer}).
 * <p>Two presentations carry the same {@link Prompt}: the mod's own screen on a client that has Heraldia (a speech
 * panel with buttons, see the client's ChoiceScreen) and a container menu on any other client (a chest-like window whose
 * slots are the options, see {@link ChoiceMenu}). The chat buttons stay as the last resort ({@link Presentation#CHAT}).
 * Texts arrive already in the player's language, as plain strings with a colour: the same strings feed both
 * presentations, so they cannot drift apart.
 */
public final class Choice {
	/** Limits of a prompt (also those of the network payload: a bigger one is a bug, not something to send). */
	public static final int MAX_LINES = 12, MAX_OPTIONS = 9, MAX_TEXT = 1024, MAX_ID = 32;
	/** The option id a reply carries when the player closed the window without picking anything. */
	public static final String CLOSED = "";
	/** The chat's colours (0xRRGGBB), the ones the options and lines use. */
	public static final int WHITE = 0xFFFFFF, GRAY = 0xAAAAAA, GOLD = 0xFFAA00, AQUA = 0x55FFFF, PURPLE = 0xFF55FF,
			GREEN = 0x55FF55, YELLOW = 0xFFFF55, RED = 0xFF5555;

	private Choice() {
	}

	/** A line of the speaker (or a note, in italics) with its colour (0xRRGGBB). */
	public record Line(String text, int color, boolean italic) {
		public Line {
			text = clip(text);
		}
	}

	/** An option: its id (what the reply names), its label, its colour and a hint (tooltip, or lore in the menu). */
	public record Option(String id, String label, int color, String hint) {
		public Option {
			if (id.isEmpty() || id.length() > MAX_ID) {
				throw new IllegalArgumentException("option id: '" + id + "'");
			}
			label = clip(label);
			hint = clip(hint);
		}
	}

	/**
	 * What is shown: the speaker (title), their lines and the options, top to bottom. The title stays a text component
	 * (a villager's name is a vanilla translation key, which the client translates in both presentations); everything
	 * else is already in the player's language.
	 */
	public record Prompt(Component title, List<Line> lines, List<Option> options) {
		public Prompt {
			if (lines.size() > MAX_LINES || options.size() > MAX_OPTIONS) {
				throw new IllegalArgumentException(lines.size() + " lines, " + options.size() + " options");
			}
			Objects.requireNonNull(title);
			lines = List.copyOf(lines);
			options = List.copyOf(options);
			if (options.stream().map(Option::id).distinct().count() != options.size()) {
				throw new IllegalArgumentException("repeated option id");
			}
		}

		public List<String> ids() {
			return options.stream().map(Option::id).toList();
		}
	}

	/**
	 * What one player has been offered, the only thing a reply is checked against: the session (each new prompt to a
	 * player gets a new one, so a reply to an earlier window does nothing) and the ids of the options on screen. A reply
	 * naming anything else is refused; {@link #CLOSED} is always accepted for the current session.
	 */
	public record Offer(int session, List<String> ids) {
		public Offer {
			ids = List.copyOf(ids);
		}

		public boolean accepts(int replySession, String id) {
			return replySession == session && id != null && (CLOSED.equals(id) || ids.contains(id));
		}
	}

	/** How a prompt reaches a player. */
	public enum Presentation {
		/** The mod's screen (the client has Heraldia with the same protocol). */
		SCREEN,
		/** A container menu (any client: vanilla, or another version of Heraldia). */
		MENU,
		/** The chat with clickable buttons (the old way: on purpose with the option off, or when nothing else can open). */
		CHAT;

		/**
		 * @param onScreen   the server's option (dialogos.en_pantalla): false keeps everything in the chat
		 * @param canOpen    false for players that cannot see a window at all (automation's fake players)
		 * @param hasChannel the client registered this protocol's channel (it has the same Heraldia)
		 */
		public static Presentation of(boolean onScreen, boolean canOpen, boolean hasChannel) {
			if (!onScreen || !canOpen) {
				return CHAT;
			}
			return hasChannel ? SCREEN : MENU;
		}
	}

	// --- helpers shared by both presentations ---

	static String clip(String s) {
		Objects.requireNonNull(s);
		return s.length() <= MAX_TEXT ? s : s.substring(0, MAX_TEXT - 1) + "…";
	}

	/** "[Keep talking]" → "Keep talking": the chat's buttons wear brackets; a real button does not need them. */
	public static String unbracket(String s) {
		String t = s.strip();
		return t.length() > 2 && t.startsWith("[") && t.endsWith("]") ? t.substring(1, t.length() - 1).strip() : t;
	}

	/**
	 * Splits a text into lines of at most {@code width} characters at spaces (a longer word gets a line of its own):
	 * for the item lore of the menu, which the game never wraps.
	 */
	public static List<String> wrap(String text, int width) {
		List<String> out = new ArrayList<>();
		for (String paragraph : text.split("\n", -1)) {
			StringBuilder line = new StringBuilder();
			for (String word : paragraph.split(" ")) {
				if (word.isEmpty()) {
					continue;
				}
				if (!line.isEmpty() && line.length() + 1 + word.length() > width) {
					out.add(line.toString());
					line.setLength(0);
				}
				if (!line.isEmpty()) {
					line.append(' ');
				}
				line.append(word);
			}
			out.add(line.toString());
		}
		return out;
	}

	/**
	 * The menu's slots for {@code n} options in one row of nine, centred and spread out (1: the middle; 2: 3 and 5;
	 * 3: 2, 4 and 6; 4: 1, 3, 5 and 7; 5 to 9 side by side).
	 */
	public static int[] row(int n) {
		if (n < 0 || n > 9) {
			throw new IllegalArgumentException("options: " + n);
		}
		int[] out = new int[n];
		boolean spread = n <= 4;
		int first = spread ? 4 - (n - 1) : (9 - n) / 2;
		for (int i = 0; i < n; i++) {
			out[i] = first + (spread ? 2 * i : i);
		}
		return out;
	}

	/**
	 * Fills a translation pattern ("%s", "%1$s", "%%") with already-flattened arguments, as the game's
	 * TranslatableContents does: used to turn a translatable text into the player's language on the server.
	 */
	public static String format(String pattern, List<String> args) {
		StringBuilder out = new StringBuilder();
		int next = 0;
		for (int i = 0; i < pattern.length(); i++) {
			char c = pattern.charAt(i);
			if (c != '%' || i + 1 >= pattern.length()) {
				out.append(c);
				continue;
			}
			char d = pattern.charAt(i + 1);
			if (d == '%') {
				out.append('%');
				i++;
			} else if (d == 's') {
				out.append(next < args.size() ? args.get(next) : "");
				next++;
				i++;
			} else if (Character.isDigit(d)) {
				int j = i + 1;
				while (j < pattern.length() && Character.isDigit(pattern.charAt(j))) {
					j++;
				}
				if (j + 1 < pattern.length() && pattern.charAt(j) == '$' && pattern.charAt(j + 1) == 's') {
					int k = Integer.parseInt(pattern.substring(i + 1, j)) - 1;
					out.append(k >= 0 && k < args.size() ? args.get(k) : "");
					i = j + 1;
				} else {
					out.append(c);
				}
			} else {
				out.append(c);
			}
		}
		return out.toString();
	}
}
