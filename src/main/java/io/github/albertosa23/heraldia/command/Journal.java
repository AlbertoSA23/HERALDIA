package io.github.albertosa23.heraldia.command;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.coast.Coast;
import io.github.albertosa23.heraldia.common.MediumStructures;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.dimensions.DimensionStructure;
import io.github.albertosa23.heraldia.mines.Mines;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.advancements.AdvancementProgress;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.registries.Registries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.level.levelgen.structure.Structure;
import org.jspecify.annotations.Nullable;

/**
 * /heraldia journal [section] (any player, no permissions): the player's own journal of what they have found and what is
 * still missing, by kind: village families, unique structures, medium structure types, mine entrance sizes, the coast
 * (lighthouse and shipwreck) and the Nether and End content. Without a section, one line per kind with a progress bar
 * and the overall total (each line, clickable, opens its section; its hover lists what is missing); with a section, the
 * names found and missing.
 * <p>Everything is read from the player's advancements (the same ones the Advancements screen shows): nothing is saved
 * and nothing runs until somebody asks. Which ids belong to each kind also comes from the advancements (the criteria of
 * aldeas/todas, unicas/todas, medianas/todas, medianas/nether and medianas/end) and, for the dimension of a unique
 * structure, from the structure registry. It never gives coordinates or location clues: those belong to the maps, the
 * quests and the Herald's Guide (which the footer points to). Chat only, so it works on vanilla clients.
 */
public final class Journal {
	/** The sections in display order: also the literal of /heraldia journal &lt;section&gt;. */
	public static final List<String> SECTIONS = List.of("villages", "uniques", "mediums", "mines", "coast", "nether", "end");
	static final String KEY = "heraldia.diario.";
	/** Cells of the progress bar. */
	static final int BAR = 10;
	static final String FULL = "■", EMPTY = "□";

	private Journal() {
	}

	/** Something that can be found: its id, the key of its name and how to tell if it was found (advancement, or one criterion). */
	record Candidate(String id, String nameKey, String advancement, @Nullable String criterion, boolean enabled) {
	}

	/** An entry of the journal: found or still missing. */
	record Item(String id, String nameKey, boolean found) {
	}

	/** A kind of structure with its entries. */
	record Section(String id, List<Item> items) {
		int found() {
			return (int) items.stream().filter(Item::found).count();
		}

		int total() {
			return items.size();
		}

		List<Item> missing() {
			return items.stream().filter(i -> !i.found()).toList();
		}

		List<Item> foundItems() {
			return items.stream().filter(Item::found).toList();
		}
	}

	static LiteralArgumentBuilder<CommandSourceStack> node() {
		LiteralArgumentBuilder<CommandSourceStack> n = Commands.literal("journal").executes(ctx -> show(ctx.getSource(), null));
		for (String s : SECTIONS) {
			n.then(Commands.literal(s).executes(ctx -> show(ctx.getSource(), s)));
		}
		return n;
	}

	private static int show(CommandSourceStack src, @Nullable String section) throws CommandSyntaxException {
		ServerPlayer player = src.getPlayerOrException();
		MinecraftServer server = src.getServer();
		State.Achievements progress = progress(server, player);
		Map<String, String> l = Texts.language(player);
		List<Section> sections = sort(sections(catalog(server, HeraldiaConfig.get()), progress), l);
		List<Component> out = section == null ? overview(l, player.getGameProfile().name(), sections) : detail(l, sections, section);
		out.forEach(c -> src.sendSuccess(() -> c, false));
		return sections.stream().mapToInt(Section::found).sum();
	}

	/** This player's Heraldia advancements, from memory (on the server thread: no file is read). */
	static State.Achievements progress(MinecraftServer server, ServerPlayer player) {
		State.Achievements out = new State.Achievements();
		out.player();
		for (AdvancementHolder a : server.getAdvancements().getAllAdvancements()) {
			if (Heraldia.MOD_ID.equals(a.id().getNamespace())) {
				AdvancementProgress pr = player.getAdvancements().getOrStartProgress(a);
				if (pr.hasProgress()) {
					out.add(a.id().toString(), pr.isDone(), pr.getCompletedCriteria());
				}
			}
		}
		return out;
	}

	/** What can be found in this world, by section (from the advancements and the structure registry). */
	static Map<String, List<Candidate>> catalog(MinecraftServer server, HeraldiaConfig cfg) {
		Map<String, List<Candidate>> out = new LinkedHashMap<>();
		SECTIONS.forEach(s -> out.put(s, new ArrayList<>()));
		// villages: the families of aldeas/todas that have some enabled style in the registry
		Set<Identifier> structures = server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet();
		Map<String, String> styles = ReviewCommand.familyStyle(cfg);
		for (String fam : criteria(server, "aldeas/todas")) {
			boolean enabled = option(cfg, "aldeas.familias." + fam) && styles.entrySet().stream()
					.anyMatch(e -> e.getValue().equals(fam) && option(cfg, "aldeas.estilos." + e.getKey())
							&& (structures.contains(Heraldia.id(e.getKey())) || structures.contains(Heraldia.id(e.getKey() + "_grande"))));
			out.get("villages").add(new Candidate(fam, "heraldia.familia." + fam, State.NS + "aldeas/" + fam, null, enabled));
		}
		// unique structures: those of unicas/todas, in the section of their dimension
		var registry = server.registryAccess().lookupOrThrow(Registries.STRUCTURE);
		for (String sid : criteria(server, "unicas/todas")) {
			Identifier id = Heraldia.id("unicas/" + sid);
			if (!UniqueSeparation.isUnique(id)) {
				continue;
			}
			Structure s = registry.getValue(id);
			String where = s instanceof DimensionStructure d ? d.mode() == DimensionStructure.Mode.NETHER ? "nether" : "end" : "uniques";
			out.get(where).add(new Candidate(sid, "heraldia.unicas." + sid + ".nombre", State.NS + "unicas/" + sid + "/descubrir", null,
					s != null && InfoCommand.uniqueEnabled(cfg, sid)));
		}
		// medium structures: one criterion per type in the walker advancement of each dimension
		boolean mediums = option(cfg, MediumStructures.ENABLED);
		for (String[] d : new String[][] {{"medianas/todas", "mediums"}, {"medianas/nether", "nether"}, {"medianas/end", "end"}}) {
			for (String tid : criteria(server, d[0])) {
				out.get(d[1]).add(new Candidate(tid, "heraldia.medianas." + tid + ".nombre", State.NS + d[0], tid,
						mediums && option(cfg, "medianas." + tid + ".activada")));
			}
		}
		// mine entrances (by size) and the coast: one advancement each
		for (String size : Revision.SIZES) {
			if (server.getAdvancements().get(Heraldia.id("minas/" + size)) != null) {
				out.get("mines").add(new Candidate(size, "heraldia.minas." + size + ".nombre", State.NS + "minas/" + size, null,
						option(cfg, Mines.ENABLED)));
			}
		}
		for (String c : Coast.TYPES) {
			if (server.getAdvancements().get(Heraldia.id("costa/" + c)) != null) {
				String o = Coast.option(c);
				out.get("coast").add(new Candidate(c, "heraldia.costa." + c + ".nombre", State.NS + "costa/" + c, null,
						o == null || option(cfg, o + ".activado")));
			}
		}
		return out;
	}

	private static boolean option(HeraldiaConfig cfg, String key) {
		return !cfg.has(key) || cfg.getBool(key);
	}

	/** The criteria (ids) of a Heraldia advancement, or none if it does not exist. */
	private static Set<String> criteria(MinecraftServer server, String path) {
		AdvancementHolder a = server.getAdvancements().get(Heraldia.id(path));
		return a == null ? Set.of() : a.value().criteria().keySet();
	}

	/**
	 * The sections with what the player found: an entry counts if it was found (even if it was disabled later) or if it
	 * can still be found (enabled); empty sections are left out.
	 */
	static List<Section> sections(Map<String, List<Candidate>> catalog, State.Achievements progress) {
		List<Section> out = new ArrayList<>();
		for (String s : SECTIONS) {
			List<Item> items = new ArrayList<>();
			for (Candidate c : catalog.getOrDefault(s, List.of())) {
				boolean found = c.criterion() == null ? progress.done(c.advancement()) : progress.criterion(c.advancement(), c.criterion());
				if (found || c.enabled()) {
					items.add(new Item(c.id(), c.nameKey(), found));
				}
			}
			if (!items.isEmpty()) {
				out.add(new Section(s, List.copyOf(items)));
			}
		}
		return out;
	}

	/** The same sections with their entries in the alphabetical order of the player's language (mines keep their size order). */
	static List<Section> sort(List<Section> sections, Map<String, String> l) {
		Comparator<Item> byName = Comparator.comparing(i -> l.getOrDefault(i.nameKey(), i.id()), Guide.collator(l));
		return sections.stream().map(s -> s.id().equals("mines") ? s
				: new Section(s.id(), s.items().stream().sorted(byName).toList())).toList();
	}

	/** Filled cells of a bar of {@code width}: at least one if something was found, all only when everything was. */
	static int filled(int found, int total, int width) {
		if (total <= 0 || found <= 0) {
			return 0;
		}
		if (found >= total) {
			return width;
		}
		return Math.clamp((long) found * width / total, 1, width - 1);
	}

	/** The progress bar: filled cells in green (gold if complete), empty ones in dark gray. */
	static MutableComponent bar(int found, int total) {
		int f = filled(found, total, BAR);
		ChatFormatting color = found >= total && total > 0 ? ChatFormatting.GOLD : ChatFormatting.GREEN;
		return Component.empty()
				.append(Component.literal(FULL.repeat(f)).withStyle(color))
				.append(Component.literal(EMPTY.repeat(BAR - f)).withStyle(ChatFormatting.DARK_GRAY));
	}

	/** Summary: title with the total, one line per section (clickable) and the footer. */
	static List<Component> overview(Map<String, String> l, String player, List<Section> sections) {
		List<Component> out = new ArrayList<>();
		int found = sections.stream().mapToInt(Section::found).sum(), total = sections.stream().mapToInt(Section::total).sum();
		out.add(Texts.t(l, KEY + "titulo", player).withStyle(ChatFormatting.GOLD, ChatFormatting.BOLD));
		if (sections.isEmpty()) {
			out.add(Texts.t(l, KEY + "vacio").withStyle(ChatFormatting.GRAY));
			return out;
		}
		out.add(Component.empty().append(bar(found, total)).append(" ")
				.append(Texts.t(l, KEY + "total", found, total).withStyle(ChatFormatting.YELLOW)));
		for (Section s : sections) {
			String order = "/heraldia journal " + s.id();
			MutableComponent hover = Texts.t(l, KEY + "ver", order).withStyle(ChatFormatting.AQUA);
			if (!s.missing().isEmpty()) {
				hover = Component.empty().append(Texts.t(l, KEY + "faltan", s.missing().size()).withStyle(ChatFormatting.GRAY))
						.append("\n").append(names(l, s.missing())).append("\n\n").append(hover);
			}
			Component tip = hover;
			MutableComponent line = Component.empty().append(bar(s.found(), s.total())).append(" ")
					.append(Texts.t(l, KEY + "cuenta", s.found(), s.total()).withStyle(ChatFormatting.WHITE)).append(" ")
					.append(Texts.t(l, KEY + "seccion." + s.id()).withStyle(s.found() >= s.total() ? ChatFormatting.GOLD : ChatFormatting.YELLOW));
			if (s.found() >= s.total()) {
				line.append(Component.literal(" ✔").withStyle(ChatFormatting.GOLD));
			}
			out.add(line.withStyle(st -> st.withClickEvent(new ClickEvent.RunCommand(order)).withHoverEvent(new HoverEvent.ShowText(tip))));
		}
		out.add(Texts.t(l, found >= total ? KEY + "completo" : KEY + "pie").withStyle(ChatFormatting.GRAY));
		if (sections.stream().anyMatch(s -> s.id().equals("uniques") && !s.missing().isEmpty())) {
			out.add(Texts.t(l, KEY + "guia", button("/heraldia guide")).withStyle(ChatFormatting.GRAY));
		}
		return out;
	}

	/** One section: title with its bar, the names found and the names missing, and the button back to the summary. */
	static List<Component> detail(Map<String, String> l, List<Section> sections, String id) {
		List<Component> out = new ArrayList<>();
		Section s = sections.stream().filter(x -> x.id().equals(id)).findFirst().orElse(new Section(id, List.of()));
		out.add(Component.empty().append(Texts.t(l, KEY + "seccion." + id).withStyle(ChatFormatting.GOLD, ChatFormatting.BOLD))
				.append(" ").append(bar(s.found(), s.total())).append(" ")
				.append(Texts.t(l, KEY + "cuenta", s.found(), s.total()).withStyle(ChatFormatting.WHITE)));
		if (s.total() == 0) {
			out.add(Texts.t(l, KEY + "vacio").withStyle(ChatFormatting.GRAY));
		} else {
			out.add(Texts.t(l, KEY + "encontradas", s.found()).withStyle(ChatFormatting.GREEN).append(" ")
					.append(s.found() == 0 ? Texts.t(l, KEY + "ninguna").withStyle(ChatFormatting.GRAY)
							: names(l, s.foundItems()).withStyle(ChatFormatting.WHITE)));
			out.add(s.missing().isEmpty() ? Texts.t(l, KEY + "todas").withStyle(ChatFormatting.GOLD)
					: Texts.t(l, KEY + "faltan", s.missing().size()).withStyle(ChatFormatting.RED).append(" ")
							.append(names(l, s.missing()).withStyle(ChatFormatting.GRAY)));
		}
		MutableComponent nav = Component.empty().append(Texts.t(l, KEY + "volver").withStyle(st -> st.withColor(ChatFormatting.AQUA)
				.withClickEvent(new ClickEvent.RunCommand("/heraldia journal"))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal("/heraldia journal")))));
		if (id.equals("uniques") && !s.missing().isEmpty()) {
			nav.append(" ").append(button("/heraldia guide"));
		}
		out.add(nav);
		return out;
	}

	/** "A, B, C" with the names in the player's language. */
	static MutableComponent names(Map<String, String> l, List<Item> items) {
		MutableComponent out = Component.empty();
		for (int i = 0; i < items.size(); i++) {
			if (i > 0) {
				out.append(", ");
			}
			out.append(Texts.t(l, items.get(i).nameKey()));
		}
		return out;
	}

	/** A clickable command (underlined, aqua). */
	private static Component button(String order) {
		return Component.literal(order).withStyle(st -> st.withColor(ChatFormatting.AQUA).withUnderlined(true)
				.withClickEvent(new ClickEvent.RunCommand(order)).withHoverEvent(new HoverEvent.ShowText(Component.literal(order))));
	}

	/** Used by /heraldia status: the line that sends a player to their own journal. */
	static Component statusLine(Map<String, String> l) {
		return Texts.t(l, KEY + "en_estado", button("/heraldia journal")).withStyle(ChatFormatting.GRAY);
	}
}
