package io.github.albertosa23.heraldia.comando;

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
import net.fabricmc.fabric.api.command.v2.CommandRegistrationCallback;
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
 * <li>/heraldia guia (cualquier jugador, sin permisos): otra copia al día.</li>
 * </ul>
 * Las páginas son componentes traducibles con el respaldo en el idioma del cliente (los textos del .jar): un cliente sin el
 * mod ve el libro en su idioma (español o inglés). Los textos, las páginas fijas y cuántas entradas caben en cada página
 * del diario los da el generador (tools/gen/guia.py, heraldia/guia.json), que comprueba que todo cabe. Solo trabaja al
 * entrar un jugador o al pedir la guía: lee sus logros de descubrimiento (heraldia:unicas/&lt;id&gt;/descubrir).
 */
public final class Guia {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String OPCION = "guia.entregar_al_entrar";
	static final String CLAVE = "heraldia.guia.";
	static final Datos DATOS = Datos.leer();

	private Guia() {
	}

	/** Lo que el generador escribe en heraldia/guia.json. */
	record Datos(List<String> paginas, int nombresPorPagina, int pistasPorPagina, String marca, String autor) {
		static Datos leer() {
			String path = "/heraldia/guia.json";
			try (InputStream in = Guia.class.getResourceAsStream(path)) {
				if (in == null) {
					throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
				}
				return de(JsonParser.parseReader(new InputStreamReader(in, StandardCharsets.UTF_8)).getAsJsonObject());
			} catch (IOException e) {
				throw new IllegalStateException("No se pudo leer " + path, e);
			}
		}

		static Datos de(JsonObject o) {
			List<String> paginas = new ArrayList<>();
			for (JsonElement e : o.getAsJsonArray("paginas")) {
				paginas.add(e.getAsString());
			}
			return new Datos(List.copyOf(paginas), o.get("nombres_por_pagina").getAsInt(), o.get("pistas_por_pagina").getAsInt(),
					o.get("marca").getAsString(), o.get("autor").getAsString());
		}
	}

	/** El adjunto, aparte para que los tests no registren nada al cargar Guia. */
	static final class Entrega {
		/** Versión del mod de la última guía entregada a este jugador (null: nunca). */
		static final AttachmentType<String> ENTREGADA = AttachmentRegistry.create(Heraldia.id("guia_entregada"),
				b -> b.persistent(Codec.STRING).copyOnDeath());

		private Entrega() {
		}
	}

	/** Una estructura única del mundo y si este jugador la ha descubierto. */
	record Unica(String id, boolean descubierta) {
	}

	public static void register() {
		LOGGER.debug("Heraldia: adjunto {} registrado", Entrega.ENTREGADA.identifier());
		// los textos del .jar se leen al arrancar, no en la primera entrega (en el hilo del servidor)
		collator(Textos.idioma(Textos.EN));
		collator(Textos.idioma(Textos.ES));
		// En la cola de tareas del servidor, no en el propio JOIN: Carpet (jugadores falsos) carga los datos del jugador
		// después de placeNewPlayer, y sin ellos aún no se sabe si ya tenía la guía. Corre en este mismo tick.
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.schedule(server.wrapRunnable(() -> {
			if (!handler.player.hasDisconnected()) {
				alEntrar(handler.player);
			}
		})));
		CommandRegistrationCallback.EVENT.register((dispatcher, access, environment) -> dispatcher.register(comando()));
	}

	/** /heraldia guia: sin requisito de permisos (cualquier jugador). */
	static LiteralArgumentBuilder<CommandSourceStack> comando() {
		return Commands.literal("heraldia").then(Commands.literal("guia").executes(ctx -> {
			entregar(ctx.getSource().getPlayerOrException(), true);
			return 1;
		}));
	}

	/** ¿Hay que darle la guía al entrar? Si la opción está activada y no tiene la de esta versión. */
	static boolean debeEntregar(boolean opcion, String entregada, String version) {
		return opcion && !version.equals(entregada);
	}

	static String version() {
		return FabricLoader.getInstance().getModContainer(Heraldia.MOD_ID)
				.map(c -> c.getMetadata().getVersion().getFriendlyString()).orElse("?");
	}

	private static void alEntrar(ServerPlayer player) {
		if (debeEntregar(HeraldiaConfig.get().getBool(OPCION), player.getAttached(Entrega.ENTREGADA), version())) {
			entregar(player, false);
		}
	}

	/** Da (o cambia por la nueva la copia que ya lleve en el inventario) la guía al día y apunta la versión. */
	static void entregar(ServerPlayer player, boolean pedida) {
		long t0 = System.nanoTime();
		Map<String, String> textos = Textos.idioma(player.clientInformation().language());
		String version = version();
		ItemStack libro = libro(DATOS, textos, unicas(player), version);
		Inventory inv = player.getInventory();
		boolean cambiada = false;
		for (int i = 0; i < inv.getContainerSize() && !cambiada; i++) {
			if (esGuia(inv.getItem(i))) {
				inv.setItem(i, libro);
				cambiada = true;
			}
		}
		if (!cambiada) {
			LlaveCommand.give(player, libro);
		}
		player.setAttached(Entrega.ENTREGADA, version);
		player.sendSystemMessage(Textos.t(textos, CLAVE + (pedida ? "copia" : "entregada")).withStyle(ChatFormatting.GOLD));
		LOGGER.info("Heraldia: Guía del Heraldo ({}, {}) entregada a {} en {} µs", version, player.clientInformation().language(),
				player.getGameProfile().name(), (System.nanoTime() - t0) / 1000);
	}

	static boolean esGuia(ItemStack stack) {
		CustomData data = stack.get(DataComponents.CUSTOM_DATA);
		return stack.is(Items.WRITTEN_BOOK) && data != null && data.copyTag().contains(DATOS.marca());
	}

	/**
	 * Las únicas que cuentan para este mundo: las del registro de estructuras activadas en la configuración (o de una por
	 * mundo, sin opción) y las que el jugador ya ha descubierto aunque se hayan desactivado después.
	 */
	static List<Unica> unicas(ServerPlayer player) {
		MinecraftServer server = player.level().getServer();
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<Unica> out = new ArrayList<>();
		for (Identifier id : server.registryAccess().lookupOrThrow(Registries.STRUCTURE).keySet()) {
			if (Heraldia.MOD_ID.equals(id.getNamespace()) && UniqueSeparation.isUnique(id)) {
				String sid = id.getPath().substring("unicas/".length());
				AdvancementHolder adv = server.getAdvancements().get(Heraldia.id("unicas/" + sid + "/descubrir"));
				boolean hecho = adv != null && player.getAdvancements().getOrStartProgress(adv).isDone();
				if (hecho || InfoCommand.uniqueEnabled(cfg, sid)) {
					out.add(new Unica(sid, hecho));
				}
			}
		}
		return out;
	}

	/** El libro: written_book con su nombre, la edición en el lore y la marca (custom_data) de la guía. */
	static ItemStack libro(Datos datos, Map<String, String> textos, List<Unica> unicas, String version) {
		ItemStack stack = new ItemStack(Items.WRITTEN_BOOK);
		List<Filterable<Component>> paginas = paginas(datos, textos, unicas).stream().map(Filterable::passThrough).toList();
		String titulo = textos.getOrDefault(CLAVE + "nombre", "Guía del Heraldo");
		stack.set(DataComponents.WRITTEN_BOOK_CONTENT, new WrittenBookContent(Filterable.passThrough(titulo), datos.autor(), 0,
				paginas, true));
		MutableComponent nombre = Textos.t(textos, CLAVE + "nombre");
		stack.set(DataComponents.ITEM_NAME, nombre);
		stack.set(DataComponents.CUSTOM_NAME, nombre.copy().withStyle(s -> s.withItalic(false)));
		stack.set(DataComponents.LORE, new ItemLore(List.of(Textos.t(textos, CLAVE + "lore", version)
				.withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GRAY)))));
		stack.set(DataComponents.RARITY, Rarity.UNCOMMON);
		CompoundTag marca = new CompoundTag();
		marca.putString(datos.marca(), version);
		stack.set(DataComponents.CUSTOM_DATA, CustomData.of(marca));
		return stack;
	}

	/**
	 * Las páginas: las fijas, el resumen del diario, las descubiertas (por nombre, en orden alfabético) y las pistas de las
	 * que faltan, en páginas de datos.nombresPorPagina() y datos.pistasPorPagina() entradas.
	 */
	static List<Component> paginas(Datos datos, Map<String, String> textos, List<Unica> unicas) {
		List<Component> out = new ArrayList<>();
		for (String p : datos.paginas()) {
			out.add(pagina(textos, CLAVE + "pagina." + p + ".titulo", Textos.t(textos, CLAVE + "pagina." + p)));
		}
		Comparator<String> porNombre = Comparator.comparing(sid -> textos.getOrDefault(nombreClave(sid), sid), collator(textos));
		List<String> hechas = unicas.stream().filter(Unica::descubierta).map(Unica::id).sorted(porNombre).toList();
		List<String> faltan = unicas.stream().filter(u -> !u.descubierta()).map(Unica::id).sorted(porNombre).toList();
		String cola = hechas.isEmpty() ? "resumen.ninguna" : faltan.isEmpty() ? "resumen.todas" : "resumen.faltan";
		out.add(pagina(textos, CLAVE + "resumen.titulo", Component.empty()
				.append(Textos.t(textos, CLAVE + "resumen", hechas.size(), unicas.size()))
				.append("\n\n")
				.append(Textos.t(textos, CLAVE + cola, faltan.size()))));
		lista(out, textos, "descubiertas", hechas, datos.nombresPorPagina(),
				sid -> Textos.t(textos, CLAVE + "descubierta", Textos.t(textos, nombreClave(sid))));
		lista(out, textos, "pistas", faltan, datos.pistasPorPagina(),
				sid -> Textos.t(textos, CLAVE + "pista", Textos.t(textos, "heraldia.historia." + sid + ".pista")));
		return out;
	}

	private static void lista(List<Component> out, Map<String, String> textos, String titulo, List<String> ids, int porPagina,
			java.util.function.Function<String, Component> entrada) {
		for (int i = 0; i < ids.size(); i += porPagina) {
			MutableComponent cuerpo = Component.empty();
			for (int j = i; j < Math.min(ids.size(), i + porPagina); j++) {
				if (j > i) {
					cuerpo.append("\n");
				}
				cuerpo.append(entrada.apply(ids.get(j)));
			}
			out.add(pagina(textos, CLAVE + titulo, cuerpo));
		}
	}

	/** «título (negrita)\n\ncuerpo»: lo que mide tools/gen/guia.lineas_pagina. */
	private static Component pagina(Map<String, String> textos, String titulo, Component cuerpo) {
		return Component.empty()
				.append(Textos.t(textos, titulo).withStyle(ChatFormatting.BOLD, ChatFormatting.DARK_RED))
				.append("\n\n")
				.append(cuerpo);
	}

	private static String nombreClave(String sid) {
		return "heraldia.unicas." + sid + ".nombre";
	}

	private static Comparator<String> collator(Map<String, String> textos) {
		Collator c = Collator.getInstance(Locale.forLanguageTag(textos == Textos.idioma(Textos.ES) ? "es" : "en"));
		c.setStrength(Collator.PRIMARY);
		return c::compare;
	}
}
