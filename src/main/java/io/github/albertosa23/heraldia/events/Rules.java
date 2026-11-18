package io.github.albertosa23.heraldia.events;

import java.util.List;
import java.util.Set;
import java.util.UUID;

/**
 * The rules of the village events (pure logic): when one starts, when it ends, what happens along the way and what
 * leaves with it. Random numbers come in as arguments in [0, 1) so the tests can fix them.
 * <p>
 * <b>Cost caps (the owner's, from the play-cost measurements):</b> at most {@link #MAX_ENTITIES} entities per event
 * (figures plus the fireworks in the air at the end), one event per village, at most {@code eventos.max_activos} on the
 * whole server, and everything an event brings leaves when it ends. Nothing ticks without an event: the draw is one check
 * every {@link #DRAW_TICKS}; the running events are updated once a second, and only the festival's tune runs faster
 * (every {@link #MUSIC_TICKS}), and only while a festival is on.
 */
public final class Rules {
	/** A draw every 30 s (offset from the caravans' and the wayfarers' minute marks); running events, once a second. */
	public static final int DRAW_TICKS = 30 * 20, DRAW_OFFSET = 15 * 20 + 7, UPDATE_TICKS = 20, MUSIC_TICKS = 4;
	/** The owner's cap: entities an event may have in the world at once. */
	public static final int MAX_ENTITIES = 25;
	/** Fireworks at the start and at the end of the wedding and the festival (short-lived entities, counted in the cap). */
	public static final int START_FIREWORKS = 1, END_FIREWORKS = 3;
	/** Tags of every entity of an event, and of the ones a player deals with. */
	public static final String TAG = "heraldia_evento", FIGURE = "heraldia_evento.figura";
	/** A player starts an event by being in the village at least this far from the square (so it is not laid out under their nose). */
	public static final double MIN_DISTANCE = 24;
	/** Players within this distance of the square keep its event going; with none for {@link #IDLE_SECONDS}, it ends. */
	public static final double KEEP_RADIUS = 96;
	public static final int IDLE_SECONDS = 60;
	/** Who is told an event has started, who hears what is said in it, and how close a player is greeted. */
	public static final double ANNOUNCE_RADIUS = 160, HEAR_RADIUS = 32, GREET_RADIUS = 8, SOUND_RADIUS = 96, MUSIC_RADIUS = 64;
	/** Reputation for taking part (once per player and event): a gift at a wedding or a funeral, a purchase at the market, a song. */
	public static final int GIFT_REPUTATION = 2, PURCHASE_REPUTATION = 1, SONG_REPUTATION = 1;

	private Rules() {
	}

	/**
	 * Does an event start in a village on this draw? With the system on, below the server's limit and the frequency
	 * ({@code rate} %, 0: only with the command), and the village's own wait over.
	 */
	public static boolean starts(boolean enabled, int active, int maxActive, int rate, long now, long lastEnded, int waitMinutes, double rng) {
		return enabled && active < maxActive && rate > 0 && waited(now, lastEnded, waitMinutes) && rng * 100 < rate;
	}

	/** Has the village rested {@code waitMinutes} since its last event (game time in ticks; a negative last: never had one)? */
	public static boolean waited(long now, long lastEnded, int waitMinutes) {
		return lastEnded < 0 || now < lastEnded || now - lastEnded >= waitMinutes * 60L * 20L;
	}

	/** Why an event ends. */
	public enum End {
		/** It ran its course: its figures say goodbye. */
		DONE("termina"),
		/** No player near for a minute, or its square is no longer loaded: it ends quietly. */
		ABANDONED("abandonado"),
		/** One of its figures was hurt: everyone scatters. */
		SCATTERED("dispersa"),
		/** The system was turned off, an operator stopped it, or the server is stopping. */
		CLEANUP("limpieza");

		public final String id;

		End(String id) {
			this.id = id;
		}
	}

	/** The end due now, or null if it goes on (checked once a second). */
	public static End end(long elapsedTicks, Kind kind, int idleSeconds, boolean loaded, boolean enabled) {
		if (!enabled) {
			return End.CLEANUP;
		}
		if (!loaded || idleSeconds >= IDLE_SECONDS) {
			return End.ABANDONED;
		}
		return elapsedTicks >= kind.ticks() ? End.DONE : null;
	}

	/** Entities an event of this kind may have at its peak: all its figures plus the fireworks in the air at the end. */
	public static int peakEntities(Kind k) {
		return Layout.maxFigures(k) + (fireworks(k) ? Math.max(START_FIREWORKS, END_FIREWORKS) : 0);
	}

	/** Does it end (and start) with fireworks? */
	public static boolean fireworks(Kind k) {
		return k == Kind.WEDDING || k == Kind.FESTIVAL;
	}

	/** An entity with the event tag that does not belong to a running event is a leftover (a crash, an unloaded chunk). */
	public static boolean orphan(Set<String> tags, UUID uuid, Set<UUID> running) {
		return !tags.isEmpty() && tags.contains(TAG) && !running.contains(uuid);
	}

	/** May a placed block be taken down? Only while it is still exactly ours and nothing rests on it (a player's torch, a carpet). */
	public static boolean removable(boolean stillOurs, boolean nothingOnTop) {
		return stillOurs && nothingOnTop;
	}

	// --- what happens along the way ---

	/** Something said or done at a given second of an event. */
	public enum Beat {
		/** The focus figure (cleric, merchant, host) says the next line of {@code event.<kind>.<pool>} to those nearby. */
		SPEAK,
		/** The wedding's "yes": hearts, the bell and fireworks. */
		VOWS,
		/** The bell: three strikes (wedding) or one slow toll (funeral). */
		BELL
	}

	/** A beat: at {@code second}, {@code beat} with its line pool ({@code event.<kind>.<pool>}) and line id ("" for a random one). */
	public record Step(int second, Beat beat, String pool, String line) {
	}

	/** The beats of each kind, in order (the funeral's toll and the market's calls repeat: see {@link #repeats}). */
	public static List<Step> steps(Kind k) {
		return switch (k) {
			case WEDDING -> List.of(new Step(2, Beat.BELL, "", ""), new Step(25, Beat.SPEAK, "ceremony", "1"),
					new Step(55, Beat.SPEAK, "ceremony", "2"), new Step(85, Beat.SPEAK, "ceremony", "3"), new Step(88, Beat.VOWS, "", ""));
			case FUNERAL -> List.of(new Step(20, Beat.SPEAK, "eulogy", "1"), new Step(60, Beat.SPEAK, "eulogy", "2"),
					new Step(100, Beat.SPEAK, "eulogy", "3"));
			case MARKET, FESTIVAL -> List.of();
		};
	}

	/** What repeats every {@code every} seconds from {@code first}: the funeral's toll, the market's and the festival's calls. */
	public record Repeat(int first, int every, Beat beat, String pool) {
	}

	public static List<Repeat> repeats(Kind k) {
		return switch (k) {
			case MARKET -> List.of(new Repeat(10, 45, Beat.SPEAK, "call"));
			case FESTIVAL -> List.of(new Repeat(15, 60, Beat.SPEAK, "call"));
			case FUNERAL -> List.of(new Repeat(1, 8, Beat.BELL, ""));
			case WEDDING -> List.of();
		};
	}

	/** Is a repeat due at this second? */
	public static boolean due(Repeat r, int second) {
		return second >= r.first() && (second - r.first()) % r.every() == 0;
	}

	// --- the festival's tunes ---

	/**
	 * The band's tunes: each a list of notes in {@link #MUSIC_TICKS}-tick steps, as semitones above F#3 (note block
	 * pitch 0.5 is 0, 1.0 is 12, 2.0 is 24); -1 is a rest. Original melodies in the style of a village dance, a jig
	 * and a slower round, so a player who asks for a song notices the change.
	 */
	public static final List<int[]> TUNES = List.of(
			new int[] {12, -1, 16, -1, 19, -1, 16, -1, 14, -1, 17, -1, 21, -1, 17, -1, 16, 16, 19, -1, 24, -1, 19, -1,
					17, -1, 14, -1, 12, -1, -1, -1},
			new int[] {19, 17, 16, 17, 19, -1, 19, -1, 17, 16, 14, 16, 17, -1, 17, -1, 16, 14, 12, 14, 16, -1, 19, -1,
					17, 16, 14, 12, 12, -1, -1, -1},
			new int[] {12, -1, -1, 14, 16, -1, -1, 12, 17, -1, -1, 16, 14, -1, -1, -1, 16, -1, -1, 17, 19, -1, -1, 16,
					14, -1, 12, -1, 12, -1, -1, -1});

	/** Note block pitch (0.5 to 2.0) of a semitone (0 to 24). */
	public static float pitch(int semitone) {
		return (float) Math.pow(2.0, (semitone - 12) / 12.0);
	}

	/** The bass under step {@code i} of a tune: the root on each bar's first beat, the fifth on its third (-1: none). */
	public static int bass(int step) {
		int s = Math.floorMod(step, 8);
		return s == 0 ? 0 : s == 4 ? 7 : -1;
	}
}
