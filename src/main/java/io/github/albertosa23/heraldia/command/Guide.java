package io.github.albertosa23.heraldia.command;

import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import com.mojang.serialization.Codec;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.nio.charset.StandardCharsets;
import java.text.Collator;
import java.util.ArrayList;
import java.util.Comparator;
import java.util.List;
import java.util.Locale;
import java.util.Map;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.Filterable;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.item.component.ItemLore;
import net.minecraft.world.item.component.WrittenBookContent;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Herald's Guide: a vanilla written book that explains the mod and keeps the player's journal (which unique structures
 * they have discovered, how many are left and the biome clue of each missing one, without coordinates).
 * <ul>
 * <li>It is given once to each player when they first join with each version of the mod (option guia.entregar_al_entrar);
 * the delivered version is saved on the player (Fabric persistent attachment heraldia:guia_entregada, which is
 * kept on death).</li>
 * <li>/heraldia guide (any player, no permissions): another up-to-date copy.</li>
 * </ul>
 * The pages are translatable components with the fallback in the client's language (the .jar's texts): a client without
 * the mod sees the book in its language (any of those in the .jar; if missing, that of its locale's language or English).
 * The texts, the fixed pages and how many entries fit on each journal page come from the generator (tools/gen/guia.py,
 * heraldia/guia.json), which checks that everything fits. It only works when a player joins or asks for the guide: it
 * reads their discovery advancements (heraldia:unicas/&lt;id&gt;/descubrir).
 */
public final class Guide {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String OPTION = "guia.entregar_al_entrar";
	static final String CLAVE = "heraldia.guia.";
	static final Data DATA = Data.read();

	private Guide() {
	}

	/** What the generator writes to heraldia/guia.json. */
	record Data(List<String> pages, int namesPerPage, int cluesPerPage, String mark, String author) {
		static Data read() {
			String path = "/heraldia/guia.json";
			try (InputStream in = Guide.class.getResourceAsStream(path)) {
				if (in == null) {
					throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
				}
				return of(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
			} catch (IOException e) {
				throw new IllegalStateException("No se pudo leer " + path, e);
			}
		}

		static Data of(JsonObject o) {
			List<String> pages = new ArrayList<>();
			for (JsonElement e : o.getAsJsonArray("paginas")) {
				pages.add(e.getAsString());
			}
			return new Data(List.copyOf(pages), o.get("nombres_por_pagina").getAsInt(), o.get("pistas_por_pagina").getAsInt(),
					o.get("marca").getAsString(), o.get("autor").getAsString());
		}
	}

	/** The attachment, kept apart so the tests register nothing when Guide loads. */
	static final class Delivery {
		/** Mod version of the last guide given to this player (null: never). */
		static final AttachmentType<String> DELIVERED = AttachmentRegistry.create(Heraldia.id("guia_entregada"),
				b -> b.persistent(Codec.STRING).copyOnDeath());

		private Delivery() {
		}
	}

	/** A unique structure of the world and whether this player has discovered it. */
	record Unique(String id, boolean discovered) {
	}

	public static void register() {
		LOGGER.debug("Heraldia: adjunto {} registrado", Delivery.DELIVERED.identifier());
		// the .jar's texts are read at startup, not on the first delivery (on the server thread)
		for (String language : Texts.languages()) {
			collator(Texts.language(language));
		}
		// On the server's task queue, not in JOIN itself: Carpet (fake players) loads the player's data
		// after placeNewPlayer, and without it we do not know yet whether they already had the guide. Runs in this same tick.
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.schedule(server.wrapRunnable(() -> {
			if (!handler.player.hasDisconnected()) {
				onJoin(handler.player);
			}
		})));
	}

	/** /heraldia guide: no permission requirement (any player; registered by {@link HeraldiaCommands}). */
	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("guide").executes(ctx -> {
			deliver(ctx.getSource().getPlayerOrException(), true);
			return 1;
		});
	}

	/** Should the guide be given on join? If the option is enabled and they do not have this version's. */
	static boolean shouldDeliver(boolean option, String delivered, String version) {
		return option && !version.equals(delivered);
	}

	static String version() {
		return FabricLoader.getInstance().getModContainer(Heraldia.MOD_ID)
				.map(c -> c.getMetadata().getVersion().getFriendlyString()).orElse("?");
	}

	private static void onJoin(ServerPlayer player) {
		if (shouldDeliver(HeraldiaConfig.get().getBool(OPTION), player.getAttached(Delivery.DELIVERED), version())) {
			deliver(player, false);
		}
	}

	/** Gives the up-to-date guide (or swaps the copy already in the inventory for the new one) and records the version. */
	static void deliver(ServerPlayer player, boolean requested) {
		long t0 = System.nanoTime();
		Map<String, String> texts = Texts.language(player);
		String version = version();
		List<Map.Entry<String, Component>> fame = io.github.albertosa23.heraldia.arena.Fame.pages(player.level().getServer(), texts);
		ItemStack book = book(DATA, texts, uniques(player), version, fame);
		Inventory inv = player.getInventory();
		boolean changed = false;
		for (int i = 0; i < inv.getContainerSize() && !changed; i++) {
			if (isGuide(inv.getItem(i))) {
				inv.setItem(i, book);
				changed = true;
			}
		}
		if (!changed) {
			KeyCommand.give(player, book);
		}
		player.setAttached(Delivery.DELIVERED, version);
		player.sendSystemMessage(Texts.t(texts, CLAVE + (requested ? "copia" : "entregada")).withStyle(ChatFormatting.GOLD));
		LOGGER.info("Heraldia: Guía del Heraldo ({}, {}) entregada a {} en {} µs", version, Texts.code(player),
				player.getGameProfile().name(), (System.nanoTime() - t0) / 1000);
	}

	static boolean isGuide(ItemStack stack) {
		CustomData data = stack.get(DataComponents.CUSTOM_DATA);
		return stack.is(Items.WRITTEN_BOOK) && data != null && data.copyTag().contains(DATA.mark());
	}

	/**
	 * The uniques that count for this world: those in the registry of structures enabled in the configuration (or one per
	 * world, without an option) and those the player has already discovered even if disabled later.
	 */
	static List<Unique> uniques(ServerPlayer player) {
		MinecraftServer server = player.level().getServer();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<Unique> out = new ArrayList<>();
		for (Identifier id : server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet()) {
			if (Heraldia.MOD_ID.equals(id.getNamespace()) && UniqueSeparation.isUnique(id)) {
				String sid = id.getPath().substring("unicas/".length());
				AdvancementHolder adv = server.getAdvancements().get(Heraldia.id("unicas/" + sid + "/descubrir"));
				boolean done = adv != null && player.getAdvancements().getOrStartProgress(adv).isDone();
				if (done || InfoCommand.uniqueEnabled(cfg, sid)) {
					out.add(new Unique(sid, done));
				}
			}
		}
		return out;
	}

	/** The book: written_book with its name, the edition in the lore and the guide's mark (custom_data). */
	static ItemStack book(Data data, Map<String, String> texts, List<Unique> uniques, String version) {
		return book(data, texts, uniques, version, List.of());
	}

	/** The book with the arena hall of fame pages (T41: title and body, after the journal summary). */
	static ItemStack book(Data data, Map<String, String> texts, List<Unique> uniques, String version,
			List<Map.Entry<String, Component>> fame) {
		ItemStack stack = new ItemStack(Items.WRITTEN_BOOK);
		List<Filterable<Component>> pages = pages(data, texts, uniques, fame).stream().map(Filterable::passThrough).toList();
		String title = texts.getOrDefault(CLAVE + "nombre", "Guía del Heraldo");
		stack.set(DataComponents.WRITTEN_BOOK_CONTENT, new WrittenBookContent(Filterable.passThrough(title), data.author(), 0,
				pages, true));
		MutableComponent name = Texts.t(texts, CLAVE + "nombre");
		stack.set(DataComponents.ITEM_NAME, name);
		stack.set(DataComponents.CUSTOM_NAME, name.copy().withStyle(s -> s.withItalic(false)));
		stack.set(DataComponents.LORE, new ItemLore(List.of(Texts.t(texts, CLAVE + "lore", version)
				.withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GRAY)))));
		stack.set(DataComponents.RARITY, Rarity.UNCOMMON);
		CompoundTag mark = new CompoundTag();
		mark.putString(data.mark(), version);
		stack.set(DataComponents.CUSTOM_DATA, CustomData.of(mark));
		return stack;
	}

	/**
	 * The pages: the fixed ones, the journal summary, the discovered ones (by name, in alphabetical order) and the clues of
	 * the missing ones, on pages of data.namesPerPage() and data.cluesPerPage() entries.
	 */
	static List<Component> pages(Data data, Map<String, String> texts, List<Unique> uniques) {
		return pages(data, texts, uniques, List.of());
	}

	/** The same with the arena hall of fame pages (after the journal summary). */
	static List<Component> pages(Data data, Map<String, String> texts, List<Unique> uniques,
			List<Map.Entry<String, Component>> fame) {
		List<Component> out = new ArrayList<>();
		for (String p : data.pages()) {
			out.add(page(texts, CLAVE + "pagina." + p + ".titulo", Texts.t(texts, CLAVE + "pagina." + p)));
		}
		Comparator<String> byName = Comparator.comparing(sid -> texts.getOrDefault(nameKey(sid), sid), collator(texts));
		List<String> done = uniques.stream().filter(Unique::discovered).map(Unique::id).sorted(byName).toList();
		List<String> missing = uniques.stream().filter(u -> !u.discovered()).map(Unique::id).sorted(byName).toList();
		String queue = done.isEmpty() ? "resumen.ninguna" : missing.isEmpty() ? "resumen.todas" : "resumen.faltan";
		out.add(page(texts, CLAVE + "resumen.titulo", Component.empty()
				.append(Texts.t(texts, CLAVE + "resumen", done.size(), uniques.size()))
				.append("\n\n")
				.append(Texts.t(texts, CLAVE + queue, missing.size()))));
		for (Map.Entry<String, Component> f : fame) {
			out.add(page(texts, f.getKey(), f.getValue()));
		}
		list(out, texts, "descubiertas", done, data.namesPerPage(),
				sid -> Texts.t(texts, CLAVE + "descubierta", Texts.t(texts, nameKey(sid))));
		list(out, texts, "pistas", missing, data.cluesPerPage(),
				sid -> Texts.t(texts, CLAVE + "pista", Texts.t(texts, "heraldia.historia." + sid + ".pista")));
		return out;
	}

	private static void list(List<Component> out, Map<String, String> texts, String title, List<String> ids, int perPage,
			java.util.function.Function<String, Component> entry) {
		for (int i = 0; i < ids.size(); i += perPage) {
			MutableComponent body = Component.empty();
			for (int j = i; j < Math.min(ids.size(), i + perPage); j++) {
				if (j > i) {
					body.append("\n");
				}
				body.append(entry.apply(ids.get(j)));
			}
			out.add(page(texts, CLAVE + title, body));
		}
	}

	/** "title (bold)\n\nbody": what tools/gen/guia.lineas_pagina measures. */
	static Component page(Map<String, String> texts, String title, Component body) {
		return Component.empty()
				.append(Texts.t(texts, title).withStyle(ChatFormatting.BOLD, ChatFormatting.DARK_RED))
				.append("\n\n")
				.append(body);
	}

	private static String nameKey(String sid) {
		return "heraldia.unicas." + sid + ".nombre";
	}

	private static Comparator<String> collator(Map<String, String> texts) {
		Collator c = Collator.getInstance(Locale.forLanguageTag(Texts.codeOf(texts).replace('_', '-')));
		c.setStrength(Collator.PRIMARY);
		return c::compare;
	}
}
