package io.github.albertosa23.heraldia.comando;

import com.mojang.brigadier.arguments.StringArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.serialization.Codec;
import io.github.albertosa23.heraldia.Heraldia;
import java.util.Collection;
import java.util.Map;
import java.util.Optional;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.commands.SharedSuggestionProvider;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.server.level.ServerPlayer;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Preferencias personales mínimas de cada jugador (T46): el idioma de los textos de Heraldia. /heraldia language (para
 * todos) dice el idioma en uso y da un botón por idioma; /heraldia language &lt;código&gt; lo fija y
 * /heraldia language auto vuelve al del cliente. Se guarda con el jugador (adjunto persistente de Fabric API, también
 * tras morir) y manda sobre el idioma del cliente en {@link Textos#idioma(ServerPlayer)}. Un cliente sin el mod ve los
 * textos de respaldo, que ya van en el idioma elegido; uno con el mod traduce las claves con su propio idioma.
 */
public final class Preferencias {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Valor del argumento que vuelve al idioma del cliente (en inglés: es un literal que se escribe). */
	public static final String AUTO = "auto";

	private Preferencias() {
	}

	/** El adjunto, aparte para que los tests no registren nada al cargar la clase. */
	static final class Tipo {
		static final AttachmentType<String> IDIOMA = AttachmentRegistry.create(Heraldia.id("idioma"),
				b -> b.persistent(Codec.STRING).copyOnDeath());

		private Tipo() {
		}
	}

	public static void registrar() {
		Tipo.IDIOMA.identifier();
	}

	/** El idioma que eligió el jugador, si eligió alguno (y el .jar lo trae). */
	public static Optional<String> idioma(ServerPlayer p) {
		String v = p.getAttached(Tipo.IDIOMA);
		return v != null && Textos.idiomas().contains(v) ? Optional.of(v) : Optional.empty();
	}

	/**
	 * Lo que se guarda para lo que escribe el jugador (lógica pura): {@link #AUTO} (o vacío) borra la preferencia; un
	 * código del .jar (en cualquier caso de letra) se guarda tal cual; cualquier otra cosa no vale.
	 */
	static Optional<Optional<String>> elegir(String texto, Collection<String> disponibles) {
		String t = texto == null ? "" : texto.strip().toLowerCase(java.util.Locale.ROOT);
		if (t.isEmpty() || AUTO.equals(t)) {
			return Optional.of(Optional.empty());
		}
		return disponibles.contains(t) ? Optional.of(Optional.of(t)) : Optional.empty();
	}

	/** /heraldia language [auto|&lt;código&gt;] (lo cuelga {@link Comandos#arbol}): para todos los jugadores. */
	static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("language")
				.executes(Preferencias::mostrar)
				.then(Commands.argument("language", StringArgumentType.word())
						.suggests((c, b) -> SharedSuggestionProvider.suggest(
								java.util.stream.Stream.concat(java.util.stream.Stream.of(AUTO), Textos.idiomas().stream()), b))
						.executes(c -> fijar(c, StringArgumentType.getString(c, "language"))));
	}

	private static int mostrar(CommandContext<CommandSourceStack> ctx) {
		ServerPlayer p = ctx.getSource().getPlayer();
		if (p == null) {
			ctx.getSource().sendFailure(Textos.t("heraldia.idioma.solo_jugadores"));
			return 0;
		}
		Map<String, String> l = Textos.idioma(p);
		p.sendSystemMessage(Textos.t(l, idioma(p).isPresent() ? "heraldia.idioma.actual" : "heraldia.idioma.actual_cliente",
				nombre(l, Textos.codigo(p))).withStyle(ChatFormatting.GOLD));
		MutableComponent fila = Component.empty();
		for (String c : Textos.idiomas()) {
			fila.append(boton(Component.literal("[" + nombre(l, c) + "]"), "/heraldia language " + c, c)).append(" ");
		}
		fila.append(boton(Textos.t(l, "heraldia.idioma.auto"), "/heraldia language " + AUTO, AUTO));
		p.sendSystemMessage(fila);
		return 1;
	}

	private static int fijar(CommandContext<CommandSourceStack> ctx, String texto) {
		ServerPlayer p = ctx.getSource().getPlayer();
		if (p == null) {
			ctx.getSource().sendFailure(Textos.t("heraldia.idioma.solo_jugadores"));
			return 0;
		}
		Optional<Optional<String>> eleccion = elegir(texto, Textos.idiomas());
		if (eleccion.isEmpty()) {
			ctx.getSource().sendFailure(Textos.t(Textos.idioma(p), "heraldia.idioma.no_existe", texto, String.join(", ", Textos.idiomas())));
			return 0;
		}
		if (eleccion.get().isPresent()) {
			p.setAttached(Tipo.IDIOMA, eleccion.get().get());
		} else {
			p.removeAttached(Tipo.IDIOMA);
		}
		Map<String, String> l = Textos.idioma(p);
		p.sendSystemMessage(Textos.t(l, eleccion.get().isPresent() ? "heraldia.idioma.fijado" : "heraldia.idioma.automatico",
				nombre(l, Textos.codigo(p))).withStyle(ChatFormatting.GREEN));
		LOGGER.info("Heraldia: idioma de {}: {}", p.getGameProfile().name(), eleccion.get().orElse(AUTO));
		return 1;
	}

	/** Nombre del idioma en sí mismo («Français»), el mismo en todos los idiomas (heraldia.idioma.nombre.&lt;código&gt;). */
	private static Component nombre(Map<String, String> l, String codigo) {
		return Textos.t(l, "heraldia.idioma.nombre." + codigo);
	}

	private static Component boton(Component texto, String cmd, String hover) {
		return texto.copy().withStyle(s -> s.withColor(ChatFormatting.AQUA).withClickEvent(new ClickEvent.RunCommand(cmd))
				.withHoverEvent(new HoverEvent.ShowText(Component.literal(hover))));
	}
}
