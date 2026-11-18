package io.github.albertosa23.heraldia.chronicle;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.Codec;
import com.mojang.serialization.codecs.RecordCodecBuilder;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.List;
import java.util.Set;

/**
 * Pure logic of the end of the Chronicle of the Heralds (option guia.final_cronica), without world classes: which guardians
 * count, when one counts as defeated by a player, what the player is owed and which pages the last leaf has. The game side
 * is {@link ChronicleEnding}.
 * <ul>
 * <li><b>Which guardians:</b> one per unique structure that can still appear in this world (enabled) or whose guardian the
 * player already defeated (even if it was disabled later), as the journal counts them. The main world's are required; the
 * Nether's and the End's are the optional "beyond the map".</li>
 * <li><b>Defeated by a player</b> ({@link #defeated}): they have its guardian advancement (it records every kill since the
 * advancements existed, also before this version: a fact the game wrote, not a guess), or they took part in its fall (they
 * were within the quests' participation radius when a guardian that a player had hurt died, recorded on the player), or it
 * exists once per world (Atlantis) and has already fallen to anyone: nobody else could ever defeat it.</li>
 * </ul>
 */
public final class Ending {
	private Ending() {
	}

	/** A guardian of the catalog: its unique structure, whether it is beyond the main world, enabled, and defeated by the player. */
	public record Guardian(String sid, boolean beyond, boolean enabled, boolean defeated) {
	}

	/** The player's progress: the main world's guardians (required) and those beyond (optional), only those that count. */
	public record Progress(List<Guardian> main, List<Guardian> beyond) {
		public static Progress of(List<Guardian> all) {
			List<Guardian> m = new ArrayList<>(), b = new ArrayList<>();
			for (Guardian g : all) {
				if (g.enabled() || g.defeated()) {
					(g.beyond() ? b : m).add(g);
				}
			}
			return new Progress(List.copyOf(m), List.copyOf(b));
		}

		public int defeated() {
			return count(main);
		}

		public int beyondDefeated() {
			return count(beyond);
		}

		/** Every guardian of the main world has fallen (and there is at least one). */
		public boolean complete() {
			return !main.isEmpty() && defeated() == main.size();
		}

		/** The main world and every guardian beyond (at least one beyond). */
		public boolean beyondComplete() {
			return complete() && !beyond.isEmpty() && beyondDefeated() == beyond.size();
		}

		private static int count(List<Guardian> l) {
			return (int) l.stream().filter(Guardian::defeated).count();
		}
	}

	/** What the player is owed now. */
	public enum Step {
		/** Nothing (not complete, already given, or the option is off). */
		NONE,
		/** The end: the advancement, the title, the last leaf and the standard. */
		FINAL,
		/** Beyond the map: its advancement and the last leaf again, with its new page (the standard only comes once). */
		BEYOND,
		/** Both at once (they had already defeated the Nether and End guardians). */
		BOTH
	}

	public static Step step(boolean option, Progress p, boolean hasFinal, boolean hasBeyond) {
		if (!option || !p.complete()) {
			return Step.NONE;
		}
		boolean beyond = p.beyondComplete() && !hasBeyond;
		if (!hasFinal) {
			return beyond ? Step.BOTH : Step.FINAL;
		}
		return beyond ? Step.BEYOND : Step.NONE;
	}

	/** Has this player defeated this guardian? (see the class) */
	public static boolean defeated(boolean advancement, boolean tookPart, boolean oncePerWorld, boolean fallenInWorld) {
		return advancement || tookPart || (oncePerWorld && fallenInWorld);
	}

	/**
	 * The pages of the last leaf (ids of heraldia.cronica.pagina.*): the fixed ones and, if any guardian beyond counts, its
	 * page: still to go, or done.
	 */
	public static List<String> pages(Data data, Progress p) {
		List<String> out = new ArrayList<>(data.pages());
		if (!p.beyond().isEmpty()) {
			out.add(data.coda(p.beyondDefeated() == p.beyond().size()));
		}
		return out;
	}

	/** Guardians recorded on a player (took part in their fall) or in the world (once-per-world ones fallen): unique ids. */
	public record Fallen(List<String> sids) {
		public static final Fallen EMPTY = new Fallen(List.of());
		public static final Codec<Fallen> CODEC = RecordCodecBuilder.create(i -> i.group(
				Codec.STRING.listOf().optionalFieldOf("guardianes", List.of()).forGetter(Fallen::sids)).apply(i, Fallen::new));

		public Fallen {
			sids = List.copyOf(sids);
		}

		public boolean has(String sid) {
			return sids.contains(sid);
		}

		/** With {@code sid} (unchanged, the same instance, if it was already there). */
		public Fallen with(String sid) {
			if (has(sid)) {
				return this;
			}
			List<String> l = new ArrayList<>(sids);
			l.add(sid);
			return new Fallen(l);
		}
	}

	/** What the generator writes to heraldia/cronica_final.json (tools/gen/chronicle_ending.py). */
	public record Data(List<String> pages, Set<String> titled, String pending, String done, String mark, String author,
			String finalAdvancement, String beyondAdvancement) {
		public String coda(boolean beyondDone) {
			return beyondDone ? done : pending;
		}

		static Data read() {
			String path = "/heraldia/cronica_final.json";
			try (InputStream in = Ending.class.getResourceAsStream(path)) {
				if (in == null) {
					throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
				}
				return of(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
			} catch (IOException e) {
				throw new IllegalStateException("No se pudo leer " + path, e);
			}
		}

		public static Data of(JsonObject o) {
			List<String> pages = new ArrayList<>();
			for (JsonElement e : o.getAsJsonArray("paginas")) {
				pages.add(e.getAsString());
			}
			List<String> titled = new ArrayList<>();
			for (JsonElement e : o.getAsJsonArray("con_titulo")) {
				titled.add(e.getAsString());
			}
			JsonObject coda = o.getAsJsonObject("coda"), adv = o.getAsJsonObject("logros");
			return new Data(List.copyOf(pages), Set.copyOf(titled), coda.get("pendiente").getAsString(), coda.get("hecho").getAsString(),
					o.get("marca").getAsString(), o.get("autor").getAsString(), adv.get("final").getAsString(),
					adv.get("mas_alla").getAsString());
		}
	}
}
