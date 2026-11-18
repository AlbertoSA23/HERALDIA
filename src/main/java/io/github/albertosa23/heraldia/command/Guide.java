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
 * Guía del Heraldo: un libro escrito vanilla que explica el mod y lleva el diario del jugador (qué estructuras únicas ha
 * descubierto, cuántas le faltan y la pista de bioma de cada una que falta, sin coordenadas).
 * <ul>
 * <li>Se da una vez a cada jugador al entrar por primera vez con cada versión del mod (opción guia.entregar_al_entrar);
 * la versión entregada se guarda en el propio jugador (adjunto persistente de Fabric heraldia:guia_entregada, que se
 * conserva al morir).</li>
 * <li>/heraldia guide (cualquier jugador, sin permisos): otra copia al día.</li>
 * </ul>
 * Las páginas son componentes traducibles con el respaldo en el idioma del cliente (los textos del .jar): un cliente sin el
 * mod ve el libro en su idioma (cualquiera de los del .jar; si no lo trae, el de su lengua o el inglés). Los textos, las páginas fijas y cuántas entradas caben en cada página
 * del diario los da el generador (tools/gen/guia.py, heraldia/guia.json), que comprueba que todo cabe. Solo trabaja al
 * entrar un jugador o al pedir la guía: lee sus logros de descubrimiento (heraldia:unicas/&lt;id&gt;/descubrir).
 */
public final class Guide {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String OPTION = "guia.entregar_al_entrar";
	static final String CLAVE = "heraldia.guia.";
	static final Data DATA = Data.read();

	private Guide() {
	}

	/** Lo que el generador escribe en heraldia/guia.json. */
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

	/** El adjunto, aparte para que los tests no registren nada al cargar Guia. */
	static final class Delivery {
		/** Versión del mod de la última guía entregada a este jugador (null: nunca). */
		static final AttachmentType<String> DELIVERED = AttachmentRegistry.create(Heraldia.id("guia_entregada"),
				b -> b.persistent(Codec.STRING).copyOnDeath());

		private Delivery() {
		}
	}

	/** Una estructura única del mundo y si este jugador la ha descubierto. */
	record Unique(String id, boolean discovered) {
	}

	public static void register() {
		LOGGER.debug("Heraldia: adjunto {} registrado", Delivery.DELIVERED.identifier());
		// los textos del .jar se leen al arrancar, no en la primera entrega (en el hilo del servidor)
		for (String language : Texts.languages()) {
			collator(Texts.language(language));
		}
		// En la cola de tareas del servidor, no en el propio JOIN: Carpet (jugadores falsos) carga los datos del jugador
		// después de placeNewPlayer, y sin ellos aún no se sabe si ya tenía la guía. Corre en este mismo tick.
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.schedule(server.wrapRunnable(() -> {
			if (!handler.player.hasDisconnected()) {
				onJoin(handler.player);
			}
		})));
	}

	/** /heraldia guide: sin requisito de permisos (cualquier jugador; lo registra {@link HeraldiaCommands}). */
	static LiteralArgumentBuilder<CommandSourceStack> node() {
		return Commands.literal("guide").executes(ctx -> {
			deliver(ctx.getSource().getPlayerOrException(), true);
			return 1;
		});
	}

	/** ¿Hay que darle la guía al entrar? Si la opción está activada y no tiene la de esta versión. */
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

	/** Da (o cambia por la nueva la copia que ya lleve en el inventario) la guía al día y apunta la versión. */
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
	 * Las únicas que cuentan para este mundo: las del registro de estructuras activadas en la configuración (o de una por
	 * mundo, sin opción) y las que el jugador ya ha descubierto aunque se hayan desactivado después.
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

	/** El libro: written_book con su nombre, la edición en el lore y la marca (custom_data) de la guía. */
	static ItemStack book(Data data, Map<String, String> texts, List<Unique> uniques, String version) {
		return book(data, texts, uniques, version, List.of());
	}

	/** El libro con las páginas del salón de la fama de la arena (T41: título y cuerpo, tras el resumen del diario). */
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
	 * Las páginas: las fijas, el resumen del diario, las descubiertas (por nombre, en orden alfabético) y las pistas de las
	 * que faltan, en páginas de datos.nombresPorPagina() y datos.pistasPorPagina() entradas.
	 */
	static List<Component> pages(Data data, Map<String, String> texts, List<Unique> uniques) {
		return pages(data, texts, uniques, List.of());
	}

	/** Lo mismo con las páginas del salón de la fama de la arena (tras el resumen del diario). */
	static List<Component> pages(Data data, Map<String, String> texts, List<Unique> uniques,
			List<Map.Entry<String, Component>> fame) {
		List<Component> out = new ArrayList<>();
		for (String p : data.pages()) {
			out.add(pagina(texts, CLAVE + "pagina." + p + ".titulo", Texts.t(texts, CLAVE + "pagina." + p)));
		}
		Comparator<String> byName = Comparator.comparing(sid -> texts.getOrDefault(nameKey(sid), sid), collator(texts));
		List<String> done = uniques.stream().filter(Unique::discovered).map(Unique::id).sorted(byName).toList();
		List<String> missing = uniques.stream().filter(u -> !u.discovered()).map(Unique::id).sorted(byName).toList();
		String queue = done.isEmpty() ? "resumen.ninguna" : missing.isEmpty() ? "resumen.todas" : "resumen.faltan";
		out.add(pagina(texts, CLAVE + "resumen.titulo", Component.empty()
				.append(Texts.t(texts, CLAVE + "resumen", done.size(), uniques.size()))
				.append("\n\n")
				.append(Texts.t(texts, CLAVE + queue, missing.size()))));
		for (Map.Entry<String, Component> f : fame) {
			out.add(pagina(texts, f.getKey(), f.getValue()));
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
			out.add(pagina(texts, CLAVE + title, body));
		}
	}

	/** «título (negrita)\n\ncuerpo»: lo que mide tools/gen/guia.lineas_pagina. */
	static Component pagina(Map<String, String> texts, String title, Component body) {
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
