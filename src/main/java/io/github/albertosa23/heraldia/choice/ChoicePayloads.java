package io.github.albertosa23.heraldia.choice;

import io.github.albertosa23.heraldia.Heraldia;
import java.util.List;
import net.fabricmc.fabric.api.networking.v1.PayloadTypeRegistry;
import net.minecraft.network.RegistryFriendlyByteBuf;
import net.minecraft.network.chat.ComponentSerialization;
import net.minecraft.network.codec.ByteBufCodecs;
import net.minecraft.network.codec.StreamCodec;
import net.minecraft.network.protocol.common.custom.CustomPacketPayload;

/**
 * The network side of a {@link Choice}: three custom payloads, registered on both sides (common code).
 * <p><b>Versioned by channel:</b> the protocol number is part of every channel id ({@code heraldia:choice_v1}...). A
 * client only registers the channels of its own protocol, so the server sends the screen only to a client whose
 * Heraldia speaks the same one ({@code ServerPlayNetworking.canSend}); any other client (vanilla, or an older or newer
 * Heraldia) simply lacks the channel and gets the container menu: no payload of another shape is ever decoded, so a
 * version mismatch cannot crash or desync anything. A change to any of these codecs <b>must</b> raise {@link #PROTOCOL}.
 * <ul>
 * <li>{@link Open} (server → client): show this prompt, or replace the one on screen (same window, new page).</li>
 * <li>{@link Close} (server → client): the choice is over (the client closes it if it is still that session).</li>
 * <li>{@link Pick} (client → server): the player picked an option ({@link Choice#CLOSED}: closed the window). The server
 * trusts nothing in it: see {@link Choices#reply}.</li>
 * </ul>
 */
public final class ChoicePayloads {
	public static final int PROTOCOL = 1;

	private ChoicePayloads() {
	}

	private static <T extends CustomPacketPayload> CustomPacketPayload.Type<T> type(String name) {
		return new CustomPacketPayload.Type<>(Heraldia.id(name + "_v" + PROTOCOL));
	}

	static final StreamCodec<RegistryFriendlyByteBuf, Choice.Line> LINE = StreamCodec.composite(
			ByteBufCodecs.stringUtf8(Choice.MAX_TEXT), Choice.Line::text,
			ByteBufCodecs.INT, Choice.Line::color,
			ByteBufCodecs.BOOL, Choice.Line::italic,
			Choice.Line::new);
	static final StreamCodec<RegistryFriendlyByteBuf, Choice.Option> OPTION = StreamCodec.composite(
			ByteBufCodecs.stringUtf8(Choice.MAX_ID), Choice.Option::id,
			ByteBufCodecs.stringUtf8(Choice.MAX_TEXT), Choice.Option::label,
			ByteBufCodecs.INT, Choice.Option::color,
			ByteBufCodecs.stringUtf8(Choice.MAX_TEXT), Choice.Option::hint,
			Choice.Option::new);
	static final StreamCodec<RegistryFriendlyByteBuf, Choice.Prompt> PROMPT = StreamCodec.composite(
			ComponentSerialization.STREAM_CODEC, Choice.Prompt::title,
			LINE.apply(ByteBufCodecs.list(Choice.MAX_LINES)), Choice.Prompt::lines,
			OPTION.apply(ByteBufCodecs.list(Choice.MAX_OPTIONS)), Choice.Prompt::options,
			Choice.Prompt::new);

	/** Show {@code prompt} as choice {@code session} (server → client). */
	public record Open(int session, Choice.Prompt prompt) implements CustomPacketPayload {
		public static final Type<Open> TYPE = ChoicePayloads.type("choice");
		public static final StreamCodec<RegistryFriendlyByteBuf, Open> CODEC = StreamCodec.composite(
				ByteBufCodecs.VAR_INT, Open::session, PROMPT, Open::prompt, Open::new);

		@Override
		public Type<Open> type() {
			return TYPE;
		}

		public List<String> ids() {
			return prompt.ids();
		}
	}

	/** Choice {@code session} is over (server → client). */
	public record Close(int session) implements CustomPacketPayload {
		public static final Type<Close> TYPE = ChoicePayloads.type("choice_close");
		public static final StreamCodec<RegistryFriendlyByteBuf, Close> CODEC = StreamCodec.composite(
				ByteBufCodecs.VAR_INT, Close::session, Close::new);

		@Override
		public Type<Close> type() {
			return TYPE;
		}
	}

	/** The player picked {@code option} of choice {@code session} (client → server). */
	public record Pick(int session, String option) implements CustomPacketPayload {
		public static final Type<Pick> TYPE = ChoicePayloads.type("choice_pick");
		public static final StreamCodec<RegistryFriendlyByteBuf, Pick> CODEC = StreamCodec.composite(
				ByteBufCodecs.VAR_INT, Pick::session, ByteBufCodecs.stringUtf8(Choice.MAX_ID), Pick::option, Pick::new);

		@Override
		public Type<Pick> type() {
			return TYPE;
		}
	}

	/** The payload types, once, from Heraldia.onInitialize (both sides need them before the first connection). */
	static void register() {
		PayloadTypeRegistry.clientboundPlay().register(Open.TYPE, Open.CODEC);
		PayloadTypeRegistry.clientboundPlay().register(Close.TYPE, Close.CODEC);
		PayloadTypeRegistry.serverboundPlay().register(Pick.TYPE, Pick.CODEC);
	}
}
