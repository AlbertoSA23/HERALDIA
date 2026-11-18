package io.github.albertosa23.heraldia.chronicle;

import com.mojang.brigadier.exceptions.CommandSyntaxException;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.bosses.Phases;
import io.github.albertosa23.heraldia.command.Guide;
import io.github.albertosa23.heraldia.command.KeyCommand;
import io.github.albertosa23.heraldia.command.Texts;
import io.github.albertosa23.heraldia.config.HeraldiaConfig;
import io.github.albertosa23.heraldia.config.UniqueSeparation;
import io.github.albertosa23.heraldia.dimensions.DimensionStructure;
import io.github.albertosa23.heraldia.quests.Objectives;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.entity.event.v1.ServerLivingEntityEvents;
import net.fabricmc.fabric.api.networking.v1.ServerPlayConnectionEvents;
import net.minecraft.ChatFormatting;
import net.minecraft.advancements.AdvancementHolder;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.core.HolderGetter;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.Registries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.protocol.game.ClientboundSetSubtitleTextPacket;
import net.minecraft.network.protocol.game.ClientboundSetTitleTextPacket;
import net.minecraft.network.protocol.game.ClientboundSetTitlesAnimationPacket;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.server.network.Filterable;
import net.minecraft.world.damagesource.DamageSource;
import net.minecraft.world.entity.LivingEntity;
import net.minecraft.world.entity.player.Inventory;
import net.minecraft.world.item.DyeColor;
import net.minecraft.world.item.ItemStack;
import net.minecraft.world.item.Items;
import net.minecraft.world.item.Rarity;
import net.minecraft.world.item.component.CustomData;
import net.minecraft.world.item.component.ItemLore;
import net.minecraft.world.item.component.WrittenBookContent;
import net.minecraft.world.level.block.entity.BannerPattern;
import net.minecraft.world.level.block.entity.BannerPatternLayers;
import net.minecraft.world.level.block.entity.BannerPatterns;
import net.minecraft.world.level.levelgen.structure.Structure;
import net.minecraft.world.phys.AABB;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * The end of the Chronicle of the Heralds (option guia.final_cronica, on by default): when every guardian of the main world's
 * unique structures has fallen to a player, they get the advancement "Herald of Atlantis" (their title, announced in chat
 * like any challenge and shown on screen), the last leaf (a written book by Ysolda, in their language) and the Standard of
 * the Heralds (a banner that can be placed). With the Nether and End guardians too, "Beyond the Map" and one more page.
 * <ul>
 * <li><b>Per player</b>, like reputation, quests and the journal: what is recorded is the player's own fight. Two world facts
 * are read: the guardian advancements (which every kill earned, also before this version) and the once-per-world guardians
 * already fallen (Atlantis: nobody else could ever defeat it).</li>
 * <li><b>Nothing per tick:</b> it hangs from the guardian's death ({@code AFTER_DEATH}, the same event as the cleared uniques)
 * and from a player joining (for the guardians defeated before this version, or while the option was off), and it reads
 * about twenty advancements from memory.</li>
 * <li><b>Recorded:</b> on each player who took part in a fall, the guardians ({@code heraldia:cronica}, kept on death); on the
 * main world, the once-per-world guardians fallen ({@code heraldia:cronica_mundo}). What was given is the advancement itself:
 * it is never given twice.</li>
 * </ul>
 * See {@link Ending} for the rules (pure logic) and CONTENT, "End of the Chronicle".
 */
public final class ChronicleEnding {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	public static final String OPTION = "guia.final_cronica";
	static final String KEY = "heraldia.cronica.";
	static final Ending.Data DATA = Ending.Data.read();
	static final String BANNER_MARK = "heraldia_estandarte";

	private ChronicleEnding() {
	}

	/** The attachments, kept apart so the tests register nothing when the class loads. */
	static final class Types {
		/** Guardians this player took part in defeating (kept on death). */
		static final AttachmentType<Ending.Fallen> PLAYER = AttachmentRegistry.create(Heraldia.id("cronica"),
				b -> b.persistent(Ending.Fallen.CODEC).copyOnDeath());
		/** On the main world: the once-per-world guardians already fallen to anyone. */
		static final AttachmentType<Ending.Fallen> WORLD = AttachmentRegistry.create(Heraldia.id("cronica_mundo"),
				b -> b.persistent(Ending.Fallen.CODEC));

		private Types() {
		}
	}

	public static void register() {
		Types.PLAYER.identifier();   // registered at startup: otherwise the saved record is dropped when the world loads
		Types.WORLD.identifier();
		ServerLivingEntityEvents.AFTER_DEATH.register((entity, source) -> {
			if (Phases.isGuardian(entity.entityTags())) {
				guardianDied(entity, source);
			}
		});
		// on the task queue, as the Guide does: Carpet's fake players load their data after JOIN
		ServerPlayConnectionEvents.JOIN.register((handler, sender, server) -> server.schedule(server.wrapRunnable(() -> {
			if (!handler.player.hasDisconnected()) {
				onJoin(handler.player);
			}
		})));
	}

	static boolean enabled() {
		return HeraldiaConfig.get().getBool(OPTION);
	}

	/** A unique structure of the catalog: where it is and whether it exists only once per world. */
	record Entry(String sid, boolean beyond, boolean enabled, boolean oncePerWorld, AdvancementHolder guardian) {
	}

	/**
	 * The unique structures with a guardian advancement, from the unicas/todas criteria and the structure registry (the
	 * dimension); once per world = without its own enabled option, as /heraldia info shows it (Atlantis).
	 */
	static List<Entry> catalog(MinecraftServer server) {
		HeraldiaConfig cfg = HeraldiaConfig.get();
		List<Entry> out = new ArrayList<>();
		AdvancementHolder all = server.getAdvancements().get(Heraldia.id("unicas/todas"));
		if (all == null) {
			return out;
		}
		var registry = server.registryAccess().lookupOrThrow(Registries.STRUCTURE);
		for (String sid : all.value().criteria().keySet().stream().sorted().toList()) {
			Identifier id = Heraldia.id("unicas/" + sid);
			AdvancementHolder g = server.getAdvancements().get(Heraldia.id("unicas/" + sid + "/guardian"));
			if (g == null || !UniqueSeparation.isUnique(id)) {
				continue;
			}
			Structure s = registry.getValue(id);
			String option = "unicas." + sid + ".activada";
			out.add(new Entry(sid, s instanceof DimensionStructure, s != null && (!cfg.has(option) || cfg.getBool(option)),
					!cfg.has(option), g));
		}
		return out;
	}

	/** This player's progress towards the end (read from memory: their advancements and the two records). */
	public static Ending.Progress progress(ServerPlayer player) {
		MinecraftServer server = player.level().getServer();
		Ending.Fallen mine = player.getAttachedOrElse(Types.PLAYER, Ending.Fallen.EMPTY);
		Ending.Fallen world = server.overworld().getAttachedOrElse(Types.WORLD, Ending.Fallen.EMPTY);
		List<Ending.Guardian> all = new ArrayList<>();
		for (Entry e : catalog(server)) {
			boolean adv = player.getAdvancements().getOrStartProgress(e.guardian()).isDone();
			all.add(new Ending.Guardian(e.sid(), e.beyond(), e.enabled(), Ending.defeated(adv, mine.has(e.sid()), e.oncePerWorld(),
					world.has(e.sid()))));
		}
		return Ending.Progress.of(all);
	}

	/** Has this player earned the title (the end's advancement)? */
	public static boolean isHerald(ServerPlayer player) {
		return done(player, DATA.finalAdvancement());
	}

	private static boolean done(ServerPlayer player, String path) {
		AdvancementHolder a = player.level().getServer().getAdvancements().get(Heraldia.id(path));
		return a != null && player.getAdvancements().getOrStartProgress(a).isDone();
	}

	/**
	 * A guardian has died. It only counts if a player fought it (the one credited with the kill, as for its advancement and
	 * its trophy): then it is recorded on that player and on every player within the quests' participation radius, and in
	 * the world if it exists once per world, and those players (all online ones, for a once-per-world guardian) are checked.
	 */
	static void guardianDied(LivingEntity guardian, DamageSource source) {
		if (!(guardian.level() instanceof ServerLevel level)) {
			return;
		}
		String sid = Phases.unique(guardian.entityTags());
		ServerPlayer killer = source.getEntity() instanceof ServerPlayer p ? p
				: guardian.getLastHurtByPlayer() instanceof ServerPlayer p ? p : null;
		if (sid == null || killer == null) {
			return;    // fell with no player in the fight (the sun, /kill, a trap): it is nobody's victory
		}
		long t0 = System.nanoTime();
		List<ServerPlayer> whom = new ArrayList<>(level.getEntitiesOfClass(ServerPlayer.class,
				new AABB(guardian.blockPosition()).inflate(Objectives.PARTICIPATE_RADIUS), p -> !p.isSpectator()));
		if (!whom.contains(killer)) {
			whom.add(killer);
		}
		for (ServerPlayer p : whom) {
			Ending.Fallen f = p.getAttachedOrElse(Types.PLAYER, Ending.Fallen.EMPTY);
			if (!f.has(sid)) {
				p.setAttached(Types.PLAYER, f.with(sid));
			}
		}
		MinecraftServer server = level.getServer();
		boolean once = catalog(server).stream().anyMatch(e -> e.sid().equals(sid) && e.oncePerWorld());
		if (once && recordWorld(server, sid)) {
			whom = new ArrayList<>(server.getPlayerList().getPlayers());   // it counts for everyone now
		}
		int given = 0;
		for (ServerPlayer p : whom) {
			given += check(p) ? 1 : 0;
		}
		LOGGER.info("Heraldia: chronicle: {} fell ({}): {} players took part{}, {} reached the end ({} µs)", sid,
				killer.getGameProfile().name(), whom.size(), once ? " (once per world)" : "", given, (System.nanoTime() - t0) / 1000);
	}

	/** Records a once-per-world guardian as fallen; true if it was not recorded yet. */
	private static boolean recordWorld(MinecraftServer server, String sid) {
		ServerLevel overworld = server.overworld();
		Ending.Fallen w = overworld.getAttachedOrElse(Types.WORLD, Ending.Fallen.EMPTY);
		if (w.has(sid)) {
			return false;
		}
		overworld.setAttached(Types.WORLD, w.with(sid));
		return true;
	}

	/**
	 * On joining: a once-per-world guardian this player defeated before this version (their advancement says so) is recorded
	 * in the world, and the player is checked (guardians defeated before this version, or while the option was off).
	 */
	private static void onJoin(ServerPlayer player) {
		MinecraftServer server = player.level().getServer();
		for (Entry e : catalog(server)) {
			if (e.oncePerWorld() && player.getAdvancements().getOrStartProgress(e.guardian()).isDone() && recordWorld(server, e.sid())) {
				LOGGER.info("Heraldia: chronicle: {} recorded as fallen in this world ({} had already defeated it)", e.sid(),
						player.getGameProfile().name());
			}
		}
		check(player);
	}

	/** Gives the player what they are owed now (see {@link Ending#step}); true if they reached the end now. */
	static boolean check(ServerPlayer player) {
		if (!enabled()) {
			return false;
		}
		Ending.Progress p = progress(player);
		Ending.Step step = Ending.step(true, p, isHerald(player), done(player, DATA.beyondAdvancement()));
		if (step == Ending.Step.NONE) {
			return false;
		}
		Map<String, String> l = Texts.language(player);
		boolean end = step == Ending.Step.FINAL || step == Ending.Step.BOTH;
		if (end) {
			award(player, DATA.finalAdvancement());
		}
		if (step == Ending.Step.BEYOND || step == Ending.Step.BOTH) {
			award(player, DATA.beyondAdvancement());
		}
		deliver(player, book(l, p), end);
		if (end) {
			KeyCommand.give(player, banner(player, l));
			player.connection.send(new ClientboundSetTitlesAnimationPacket(10, 80, 20));
			player.connection.send(new ClientboundSetSubtitleTextPacket(Texts.t(l, KEY + "titulo.subtitulo").withStyle(ChatFormatting.YELLOW)));
			player.connection.send(new ClientboundSetTitleTextPacket(Texts.t(l, KEY + "titulo").withStyle(ChatFormatting.GOLD)));
			player.sendSystemMessage(Texts.t(l, KEY + "anuncio").withStyle(ChatFormatting.GOLD));
		} else {
			player.sendSystemMessage(Texts.t(l, KEY + "mas_alla").withStyle(ChatFormatting.LIGHT_PURPLE));
		}
		LOGGER.info("Heraldia: chronicle: {} {} ({} of {} guardians; beyond {} of {})", player.getGameProfile().name(),
				step == Ending.Step.BEYOND ? "went beyond the map" : "closed the Chronicle", p.defeated(), p.main().size(),
				p.beyondDefeated(), p.beyond().size());
		return end;
	}

	private static void award(ServerPlayer player, String path) {
		AdvancementHolder a = player.level().getServer().getAdvancements().get(Heraldia.id(path));
		if (a != null) {
			player.getAdvancements().award(a, "hecho");
		}
	}

	/**
	 * /heraldia journal chronicle book: a copy of the last leaf, up to date (with the beyond page as it stands), only for
	 * a Herald of Atlantis. Returns the command result.
	 */
	public static int copy(CommandSourceStack src) throws CommandSyntaxException {
		ServerPlayer player = src.getPlayerOrException();
		Map<String, String> l = Texts.language(player);
		if (!enabled()) {
			src.sendFailure(Texts.t(l, KEY + "desactivado"));
			return 0;
		}
		Ending.Progress p = progress(player);
		if (!isHerald(player)) {
			src.sendFailure(Texts.t(l, KEY + "sin_cerrar", p.main().size() - p.defeated()));
			return 0;
		}
		deliver(player, book(l, p), false);
		src.sendSuccess(() -> Texts.t(l, KEY + "copia").withStyle(ChatFormatting.GOLD), false);
		return 1;
	}

	/** The last leaf into the inventory: in place of the copy the player already carries, if any. */
	private static void deliver(ServerPlayer player, ItemStack book, boolean fresh) {
		Inventory inv = player.getInventory();
		if (!fresh) {
			for (int i = 0; i < inv.getContainerSize(); i++) {
				if (isLastLeaf(inv.getItem(i))) {
					inv.setItem(i, book);
					return;
				}
			}
		}
		KeyCommand.give(player, book);
	}

	static boolean isLastLeaf(ItemStack stack) {
		CustomData data = stack.get(DataComponents.CUSTOM_DATA);
		return stack.is(Items.WRITTEN_BOOK) && data != null && data.copyTag().contains(DATA.mark());
	}

	/** The last leaf: a written book by Ysolda in the player's language (the fallback, for vanilla clients), with its mark. */
	static ItemStack book(Map<String, String> l, Ending.Progress p) {
		List<Filterable<Component>> pages = new ArrayList<>();
		for (String id : Ending.pages(DATA, p)) {
			Component body = Texts.t(l, KEY + "pagina." + id);
			pages.add(Filterable.passThrough(DATA.titled().contains(id) ? Guide.page(l, KEY + "pagina." + id + ".titulo", body) : body));
		}
		ItemStack stack = new ItemStack(Items.WRITTEN_BOOK);
		String title = l.getOrDefault(KEY + "libro", "Crónica: el último pliego");
		stack.set(DataComponents.WRITTEN_BOOK_CONTENT, new WrittenBookContent(Filterable.passThrough(title), DATA.author(), 0, pages, true));
		MutableComponent name = Texts.t(l, KEY + "libro");
		stack.set(DataComponents.ITEM_NAME, name);
		stack.set(DataComponents.CUSTOM_NAME, name.copy().withStyle(s -> s.withItalic(false)));
		stack.set(DataComponents.LORE, new ItemLore(List.of(Texts.t(l, KEY + "libro.lore")
				.withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GRAY)))));
		stack.set(DataComponents.RARITY, Rarity.EPIC);
		CompoundTag mark = new CompoundTag();
		mark.putInt(DATA.mark(), 1);
		stack.set(DataComponents.CUSTOM_DATA, CustomData.of(mark));
		return stack;
	}

	/**
	 * The Standard of the Heralds: a blue banner with the sea rising, the waves and the Order's golden seal and border. Its
	 * name, patterns and rarity stay when it is placed and picked up again (the vanilla banner keeps those); the lore with who
	 * raised it stays only on the item that was given.
	 */
	static ItemStack banner(ServerPlayer player, Map<String, String> l) {
		HolderGetter<BannerPattern> patterns = player.level().getServer().registryAccess().lookupOrThrow(Registries.BANNER_PATTERN);
		ItemStack stack = new ItemStack(Items.BANNER.blue());
		stack.set(DataComponents.BANNER_PATTERNS, new BannerPatternLayers.Builder()
				.addIfRegistered(patterns, BannerPatterns.GRADIENT_UP, DyeColor.CYAN)
				.addIfRegistered(patterns, BannerPatterns.TRIANGLES_BOTTOM, DyeColor.LIGHT_BLUE)
				.addIfRegistered(patterns, BannerPatterns.CIRCLE_MIDDLE, DyeColor.YELLOW)
				.addIfRegistered(patterns, BannerPatterns.CURLY_BORDER, DyeColor.YELLOW)
				.build());
		MutableComponent name = Texts.t(l, KEY + "estandarte");
		stack.set(DataComponents.ITEM_NAME, name);
		stack.set(DataComponents.CUSTOM_NAME, name.copy().withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GOLD)));
		stack.set(DataComponents.LORE, new ItemLore(List.of(
				Texts.t(l, KEY + "estandarte.lore").withStyle(s -> s.withItalic(false).withColor(ChatFormatting.GRAY)),
				Texts.t(l, KEY + "estandarte.alzado", player.getGameProfile().name())
						.withStyle(s -> s.withItalic(false).withColor(ChatFormatting.DARK_AQUA)))));
		stack.set(DataComponents.RARITY, Rarity.EPIC);
		CompoundTag mark = new CompoundTag();
		mark.putString(BANNER_MARK, player.getGameProfile().name());
		stack.set(DataComponents.CUSTOM_DATA, CustomData.of(mark));
		return stack;
	}
}
