package io.github.albertosa23.heraldia.dialogue;

import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.util.ArrayList;
import java.util.List;

/**
 * What the conversations keep (P9a), immutable.
 * <ul>
 * <li>{@link Villager}, in each Heraldia villager that has talked (Fabric persistent attachment, saved with the entity):
 * when it last started a conversation (the per-villager wait) and whether it has already told its one hint, so it is
 * never told twice in its life however many times anyone clicks.</li>
 * <li>{@link Player}, in each player's file: the keys of the last lines they heard, from any villager, so the same line
 * does not come up twice in a row.</li>
 * </ul>
 */
public final class Memory {
	private Memory() {
	}

	/** @param lastTalk game tick of its last conversation (Long.MIN_VALUE: never) */
	public record Villager(long lastTalk, boolean hintTold) {
		public static final Villager EMPTY = new Villager(Long.MIN_VALUE, false);
		public static final Codec<Villager> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.LONG.optionalFieldOf("ultima_charla", Long.MIN_VALUE).forGetter(Villager::lastTalk),
				Codec.BOOL.optionalFieldOf("pista_contada", false).forGetter(Villager::hintTold)).apply(i, Villager::new));

		/** Is it still resting from its last conversation? {@code wait} in ticks (0: never). */
		public boolean resting(long now, long wait) {
			return wait > 0 && lastTalk != Long.MIN_VALUE && now >= lastTalk && now - lastTalk < wait;
		}

		/** Ticks left until it talks again (0 if it can). */
		public long left(long now, long wait) {
			return resting(now, wait) ? wait - (now - lastTalk) : 0;
		}

		public Villager talks(long now) {
			return new Villager(now, hintTold);
		}

		public Villager tellsHint() {
			return new Villager(lastTalk, true);
		}
	}

	/** @param recent keys of the last lines heard, oldest first, at most {@link #RECENT} */
	public record Player(List<String> recent) {
		/** How many recent lines are remembered: more than a long conversation, fewer than a small pool's worth. */
		public static final int RECENT = 24;
		public static final Player EMPTY = new Player(List.of());
		public static final Codec<Player> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.STRING.listOf().optionalFieldOf("recientes", List.of()).forGetter(Player::recent)).apply(i, Player::new));

		public Player {
			recent = List.copyOf(recent);
		}

		/** Remembers a line just heard (moves it to the end if it was already there). */
		public Player heard(String key) {
			List<String> l = new ArrayList<>(recent);
			l.remove(key);
			l.add(key);
			while (l.size() > RECENT) {
				l.remove(0);
			}
			return new Player(l);
		}
	}
}
