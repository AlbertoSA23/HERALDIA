package io.github.albertosa23.heraldia.actualizar;

import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.context.CommandContext;
import com.mojang.serialization.Codec;
import io.github.albertosa23.heraldia.Heraldia;
import io.github.albertosa23.heraldia.comando.Textos;
import java.io.IOException;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.Set;
import java.util.concurrent.atomic.AtomicBoolean;
import net.fabricmc.fabric.api.attachment.v1.AttachmentRegistry;
import net.fabricmc.fabric.api.attachment.v1.AttachmentType;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerEntityEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerLifecycleEvents;
import net.fabricmc.fabric.api.event.lifecycle.v1.ServerTickEvents;
import net.fabricmc.loader.api.FabricLoader;
import net.minecraft.ChatFormatting;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.core.Holder;
import net.minecraft.core.component.DataComponents;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.network.chat.ClickEvent;
import net.minecraft.network.chat.Component;
import net.minecraft.network.chat.HoverEvent;
import net.minecraft.network.chat.MutableComponent;
import net.minecraft.network.chat.contents.TranslatableContents;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.dialog.ActionButton;
import net.minecraft.server.dialog.CommonButtonData;
import net.minecraft.server.dialog.CommonDialogData;
import net.minecraft.server.dialog.DialogAction;
import net.minecraft.server.dialog.MultiActionDialog;
import net.minecraft.server.dialog.action.StaticAction;
import net.minecraft.server.dialog.body.DialogBody;
import net.minecraft.server.dialog.body.PlainMessage;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.item.ItemStack;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Actualizaciones seguras (T46): la versión del mod con la que se generó el mundo ({@link VersionMundo}), los arreglos
 * por versión aplicados de forma perezosa ({@link Arreglos}, {@link ArreglosMobs}) y llevar lo nuevo a un mundo existente
 * ({@link Analisis}, {@link Ejecucion}). Comandos de operador bajo /heraldia update (en inglés, en comando/Comandos):
 * <ul>
 * <li>{@code analyze}: informe de lo que se protegería, regeneraría y colocaría; no cambia nada;</li>
 * <li>{@code apply}: el mismo análisis y un diálogo para confirmar, con o sin copia de seguridad (sin copia, otra
 * confirmación del riesgo); al confirmar, avisa a los jugadores y para el servidor, que el administrador vuelve a
 * arrancar a mano: el trabajo se hace al arrancar;</li>
 * <li>{@code undo}: restaura la copia del último apply (también al arrancar);</li>
 * <li>{@code repair [dry-run]}: fuerza los arreglos en todo lo cargado (o solo dice qué cambiaría).</li>
 * </ul>
 * Una línea en Heraldia.onInitialize.
 */
public final class Actualizar {
	private static final Logger LOGGER = LoggerFactory.getLogger(Heraldia.MOD_ID);
	/** Un mundo es nuevo (se da por generado con esta versión) si al arrancar por primera vez no ha pasado este tiempo. */
	static final long MUNDO_NUEVO_TICKS = 1200;
	/** Lo que dura un análisis para apply: pasado esto, hay que repetirlo. */
	static final long VALIDEZ_MS = 15 * 60_000;
	/** Ticks entre el aviso a los jugadores y la parada del servidor. */
	static final int AVISO_TICKS = 200;
	private static final AtomicBoolean ANALIZANDO = new AtomicBoolean();
	private static volatile Analisis.Informe ultimo;
	private static volatile long ultimoMs;
	private static int parada = -1;

	private Actualizar() {
	}

	/** Marca de arreglos de cada mob revisado (el nivel de {@link ArreglosMobs#REGISTRO}); aparte para los tests. */
	static final class Tipo {
		static final AttachmentType<Integer> ARREGLOS = AttachmentRegistry.create(Heraldia.id("arreglos"), b -> b.persistent(Codec.INT));

		private Tipo() {
		}
	}

	public static void registrar() {
		VersionMundo.Tipo.VERSION.identifier();
		Tipo.ARREGLOS.identifier();
		io.github.albertosa23.heraldia.comando.Preferencias.registrar();
		ServerEntityEvents.ENTITY_LOAD.register((entity, level) -> alCargar(entity));
		ServerLifecycleEvents.SERVER_STARTING.register(Ejecucion::alEmpezar);
		ServerLifecycleEvents.SERVER_STARTED.register(Actualizar::alArrancar);
		ServerLifecycleEvents.SERVER_STARTED.register(Ejecucion::alArrancar);
		ServerTickEvents.END_SERVER_TICK.register(Actualizar::tick);
	}

	// ------------------------------------------------------------------ versión del mundo

	static String version() {
		return FabricLoader.getInstance().getModContainer(Heraldia.MOD_ID).map(c -> c.getMetadata().getVersion().getFriendlyString()).orElse("?");
	}

	private static void alArrancar(MinecraftServer server) {
		ServerLevel ow = server.overworld();
		Optional<VersionMundo> antes = Optional.ofNullable(ow.getAttached(VersionMundo.Tipo.VERSION));
		String actual = version();
		VersionMundo ahora = VersionMundo.alArrancar(antes, actual, ow.getGameTime(), MUNDO_NUEVO_TICKS, ArreglosMobs.REGISTRO.nivel());
		if (VersionMundo.retrocede(antes, actual)) {
			LOGGER.warn("Heraldia: el mundo se abrió antes con la versión {}, más nueva que esta ({}): lo nuevo de aquella no se deshace",
					antes.get().ultima(), actual);
		}
		ow.setAttached(VersionMundo.Tipo.VERSION, ahora);
		LOGGER.info("Heraldia: mundo generado con la versión {}, abierto antes con {}, ahora con {} (nivel de arreglos {})",
				ahora.generado(), antes.map(VersionMundo::ultima).orElse("ninguna"), actual, ArreglosMobs.REGISTRO.nivel());
	}

	/** La versión guardada del mundo (para /heraldia status y las pruebas). */
	public static Optional<VersionMundo> versionMundo(MinecraftServer server) {
		return Optional.ofNullable(server.overworld().getAttached(VersionMundo.Tipo.VERSION));
	}

	// ------------------------------------------------------------------ arreglos perezosos

	/** Al cargar una entidad: si es un mob de plantilla sin la marca del nivel actual, sus arreglos pendientes. */
	static void alCargar(Entity entity) {
		if (!(entity instanceof Mob mob) || mob.entityTags().isEmpty() && !mob.hasCustomName()) {
			return;                       // salida temprana: casi todas las entidades
		}
		VistaMob v = new VistaMob(mob);
		if (!ArreglosMobs.dePlantilla(v)) {
			return;
		}
		Integer marca = mob.getAttached(Tipo.ARREGLOS);
		int m = marca == null ? 0 : marca;
		if (!ArreglosMobs.REGISTRO.pendiente(m)) {
			return;
		}
		Map<String, Arreglos.Efecto> e = ArreglosMobs.REGISTRO.ejecutar(v, m, false, false);
		mob.setAttached(Tipo.ARREGLOS, ArreglosMobs.REGISTRO.nivel());
		if (!e.isEmpty()) {
			LOGGER.info("Heraldia: arreglos {} en {} ({}) en {} {} {}", e, BuiltInRegistries.ENTITY_TYPE.getKey(mob.getType()),
					mob.getUUID(), mob.getBlockX(), mob.getBlockY(), mob.getBlockZ());
		}
	}

	/** /heraldia update repair: los arreglos en todos los mobs cargados, sin mirar la marca. */
	static Arreglos.Cuenta reparar(MinecraftServer server, boolean prueba) {
		Arreglos.Cuenta cuenta = new Arreglos.Cuenta();
		for (ServerLevel level : server.getAllLevels()) {
			List<Mob> mobs = new ArrayList<>();
			for (Entity e : level.getAllEntities()) {
				if (e instanceof Mob m) {
					mobs.add(m);
				}
			}
			for (Mob mob : mobs) {
				VistaMob v = new VistaMob(mob);
				if (!ArreglosMobs.dePlantilla(v)) {
					continue;
				}
				cuenta.sumar(ArreglosMobs.REGISTRO.ejecutar(v, 0, prueba, true));
				if (!prueba) {
					mob.setAttached(Tipo.ARREGLOS, ArreglosMobs.REGISTRO.nivel());
				}
			}
		}
		LOGGER.info("Heraldia: update repair{}: {} mobs de plantilla revisados, {} cambios {}", prueba ? " dry-run" : "",
				cuenta.revisados(), cuenta.cambios(), resumen(cuenta));
		return cuenta;
	}

	static String resumen(Arreglos.Cuenta c) {
		StringBuilder sb = new StringBuilder("{");
		c.porId().forEach((id, v) -> sb.append(sb.length() > 1 ? ", " : "").append(id).append('=').append(v[0]).append('/').append(v[1]));
		return sb.append('}').toString();
	}

	/** {@link ArreglosMobs.Mob} sobre un mob de verdad. */
	record VistaMob(Mob mob) implements ArreglosMobs.Mob {
		private static String ruta(Entity e) {
			return BuiltInRegistries.ENTITY_TYPE.getKey(e.getType()).getPath();
		}

		@Override
		public String tipo() {
			return ruta(mob);
		}

		@Override
		public Set<String> etiquetas() {
			return mob.entityTags();
		}

		@Override
		public void etiquetar(String etiqueta) {
			mob.addTag(etiqueta);
		}

		@Override
		public String claveNombre() {
			Component n = mob.getCustomName();
			return n != null && n.getContents() instanceof TranslatableContents t ? t.getKey() : null;
		}

		@Override
		public boolean persistente() {
			return mob.isPersistenceRequired();
		}

		@Override
		public boolean bebe() {
			return mob.isBaby();
		}

		@Override
		public void hacerAdulto() {
			mob.setBaby(false);
		}

		@Override
		public String montura() {
			Entity v = mob.getVehicle();
			return v == null ? null : ruta(v);
		}

		@Override
		public boolean monturaPropia() {
			Entity v = mob.getVehicle();
			return v != null && (v.hasCustomName() || v.getPassengers().size() > 1);
		}

		@Override
		public void quitarMontura() {
			Entity v = mob.getVehicle();
			mob.stopRiding();
			if (v != null) {
				v.discard();
			}
		}

		@Override
		public boolean recoge() {
			return mob.canPickUpLoot();
		}

		@Override
		public void noRecoger() {
			mob.setCanPickUpLoot(false);
		}

		@Override
		public String arma() {
			ItemStack s = mob.getMainHandItem();
			return s.isEmpty() ? null : BuiltInRegistries.ITEM.getKey(s.getItem()).getPath();
		}

		@Override
		public boolean armaEspecial() {
			ItemStack s = mob.getMainHandItem();
			return s.isEnchanted() || s.has(DataComponents.CUSTOM_NAME);
		}
	}

	// ------------------------------------------------------------------ comandos

	/** /heraldia update analyze | apply ... | undo ... | repair [dry-run] (se suma al «update» de AvisoVersion). */
	public static LiteralArgumentBuilder<CommandSourceStack> nodo() {
		return Commands.literal("update")
				.requires(Commands.hasPermission(Commands.LEVEL_GAMEMASTERS))
				.then(Commands.literal("analyze").executes(c -> analizar(c, false)))
				.then(Commands.literal("apply").executes(c -> analizar(c, true))
						.then(Commands.literal("confirm").then(Commands.argument("id", com.mojang.brigadier.arguments.StringArgumentType.word())
								.then(Commands.literal("backup").executes(c -> confirmar(c, true, false)))
								.then(Commands.literal("nobackup").executes(c -> confirmar(c, false, false))
										.then(Commands.literal("risk").executes(c -> confirmar(c, false, true)))))))
				.then(Commands.literal("undo").executes(Actualizar::deshacer)
						.then(Commands.literal("confirm").then(Commands.argument("id", com.mojang.brigadier.arguments.StringArgumentType.word())
								.executes(Actualizar::confirmarDeshacer))))
				.then(Commands.literal("repair").executes(c -> reparar(c, false))
						.then(Commands.literal("dry-run").executes(c -> reparar(c, true))));
	}

	private static Map<String, String> idioma(CommandSourceStack src) {
		ServerPlayer p = src.getPlayer();
		return p != null ? Textos.idioma(p) : Textos.idioma("es_es");
	}

	private static int analizar(CommandContext<CommandSourceStack> ctx, boolean aplicar) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		if (aplicar && !Analisis.protecciones().isEmpty()) {
			src.sendFailure(Textos.t(l, "heraldia.actualizar.protecciones", String.join(", ", Analisis.protecciones())));
			return 0;
		}
		if (!ANALIZANDO.compareAndSet(false, true)) {
			src.sendFailure(Textos.t(l, "heraldia.actualizar.ocupado"));
			return 0;
		}
		src.sendSuccess(() -> Textos.t(l, "heraldia.actualizar.analizando").withStyle(ChatFormatting.GRAY), true);
		MinecraftServer server = src.getServer();
		Analisis.empezar(server, m -> LOGGER.info("Heraldia: update analyze: {}", m)).whenComplete((inf, err) -> server.execute(() -> {
			ANALIZANDO.set(false);
			if (err != null) {
				src.sendFailure(Textos.t(l, "heraldia.actualizar.error", String.valueOf(err.getMessage())));
				return;
			}
			ultimo = inf;
			ultimoMs = System.currentTimeMillis();
			lineas(l, inf).forEach(t -> src.sendSuccess(() -> t, true));
			if (aplicar) {
				ofrecer(src, l, inf);
			}
		}));
		return 1;
	}

	/** El resumen del análisis en líneas traducibles. */
	static List<Component> lineas(Map<String, String> l, Analisis.Informe i) {
		Detector.Resultado r = i.resultado();
		List<Component> out = new ArrayList<>();
		out.add(Textos.t(l, "heraldia.actualizar.titulo", i.chunks(), i.margen()).withStyle(ChatFormatting.GOLD));
		out.add(Textos.t(l, "heraldia.actualizar.protegidos", r.construcciones().size(), r.cuenta(Detector.Clase.CONSTRUCCION),
				r.cuenta(Detector.Clase.PROTEGIDO)).withStyle(ChatFormatting.YELLOW));
		out.add(Textos.t(l, "heraldia.actualizar.regenerar", i.regenerar().size(), r.cuenta(Detector.Clase.VIRGEN), i.virgenesCortadas())
				.withStyle(ChatFormatting.GREEN));
		out.add(Textos.t(l, "heraldia.actualizar.colocar", i.colocar().size(), i.colocacionesInseguras()).withStyle(ChatFormatting.AQUA));
		if (!i.protecciones().isEmpty()) {
			out.add(Textos.t(l, "heraldia.actualizar.protecciones", String.join(", ", i.protecciones())).withStyle(ChatFormatting.RED));
		}
		out.add(Textos.t(l, "heraldia.actualizar.informe", i.fichero().toString(), i.mapaPng().getFileName().toString()).withStyle(ChatFormatting.GRAY));
		out.add(Textos.t(l, "heraldia.actualizar.nada_cambia").withStyle(ChatFormatting.GRAY));
		return out;
	}

	/** apply: el diálogo (o las órdenes, en la consola) para confirmar, con o sin copia. */
	private static void ofrecer(CommandSourceStack src, Map<String, String> l, Analisis.Informe i) {
		if (i.regenerar().isEmpty() && i.colocar().isEmpty()) {
			src.sendSuccess(() -> Textos.t(l, "heraldia.actualizar.nada_que_hacer").withStyle(ChatFormatting.GREEN), true);
			return;
		}
		String base = "heraldia update apply confirm " + i.id() + " ";
		ServerPlayer p = src.getPlayer();
		if (p == null) {
			src.sendSuccess(() -> Textos.t(l, "heraldia.actualizar.confirmar_consola", base + "backup", base + "nobackup risk"), false);
			return;
		}
		List<DialogBody> cuerpo = new ArrayList<>();
		lineas(l, i).forEach(t -> cuerpo.add(new PlainMessage(t, 300)));
		cuerpo.add(new PlainMessage(Textos.t(l, "heraldia.actualizar.aviso_parada").withStyle(ChatFormatting.RED), 300));
		List<ActionButton> b = List.of(
				boton(Textos.t(l, "heraldia.actualizar.boton.copia"), Textos.t(l, "heraldia.actualizar.boton.copia.ayuda"), base + "backup"),
				boton(Textos.t(l, "heraldia.actualizar.boton.sin_copia"), Textos.t(l, "heraldia.actualizar.boton.sin_copia.ayuda"), base + "nobackup"));
		p.openDialog(Holder.direct(new MultiActionDialog(new CommonDialogData(Textos.t(l, "heraldia.actualizar.dialogo"), Optional.empty(),
				true, false, DialogAction.CLOSE, cuerpo, List.of()), b,
				Optional.of(new ActionButton(new CommonButtonData(Textos.t(l, "heraldia.actualizar.boton.cancelar"), 150), Optional.empty())), 2)));
	}

	private static ActionButton boton(Component texto, Component ayuda, String cmd) {
		return new ActionButton(new CommonButtonData(texto, Optional.of(ayuda), 150), Optional.of(new StaticAction(new ClickEvent.RunCommand(cmd))));
	}

	private static int confirmar(CommandContext<CommandSourceStack> ctx, boolean copia, boolean riesgo) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		String id = com.mojang.brigadier.arguments.StringArgumentType.getString(ctx, "id");
		Analisis.Informe i = ultimo;
		if (i == null || !i.id().equals(id) || System.currentTimeMillis() - ultimoMs > VALIDEZ_MS) {
			src.sendFailure(Textos.t(l, "heraldia.actualizar.caducado"));
			return 0;
		}
		if (!Analisis.protecciones().isEmpty()) {
			src.sendFailure(Textos.t(l, "heraldia.actualizar.protecciones", String.join(", ", Analisis.protecciones())));
			return 0;
		}
		if (!copia && !riesgo) {         // sin copia: otra confirmación, explícita
			String cmd = "heraldia update apply confirm " + id + " nobackup risk";
			ServerPlayer p = src.getPlayer();
			if (p == null) {
				src.sendSuccess(() -> Textos.t(l, "heraldia.actualizar.riesgo_consola", cmd).withStyle(ChatFormatting.RED), false);
			} else {
				p.openDialog(Holder.direct(new MultiActionDialog(new CommonDialogData(Textos.t(l, "heraldia.actualizar.riesgo.titulo"),
						Optional.empty(), true, false, DialogAction.CLOSE,
						List.of(new PlainMessage(Textos.t(l, "heraldia.actualizar.riesgo").withStyle(ChatFormatting.RED), 300)),
						List.of()), List.of(boton(Textos.t(l, "heraldia.actualizar.boton.riesgo"), Textos.t(l, "heraldia.actualizar.boton.riesgo.ayuda"), cmd)),
						Optional.of(new ActionButton(new CommonButtonData(Textos.t(l, "heraldia.actualizar.boton.cancelar"), 150), Optional.empty())), 1)));
			}
			return 1;
		}
		MinecraftServer server = src.getServer();
		Plan plan = i.plan(copia);
		try {
			plan.guardar(Ejecucion.plan(server));
		} catch (IOException e) {
			src.sendFailure(Textos.t(l, "heraldia.actualizar.error", e.getMessage()));
			return 0;
		}
		ultimo = null;
		LOGGER.info("Heraldia: update apply confirmado por {} ({} copia): {} chunks a regenerar, {} estructuras; el servidor se para en {} s",
				src.getTextName(), copia ? "con" : "sin", plan.regenerar.size(), plan.colocar.size(), AVISO_TICKS / 20);
		src.sendSuccess(() -> Textos.t(l, "heraldia.actualizar.confirmado", AVISO_TICKS / 20).withStyle(ChatFormatting.GOLD), true);
		avisarYParar(server);
		return 1;
	}

	private static void avisarYParar(MinecraftServer server) {
		for (ServerPlayer p : server.getPlayerList().getPlayers()) {
			p.sendSystemMessage(Textos.t(Textos.idioma(p), "heraldia.actualizar.aviso_jugadores", AVISO_TICKS / 20).withStyle(ChatFormatting.RED));
		}
		parada = AVISO_TICKS;
	}

	private static void tick(MinecraftServer server) {
		Ejecucion.tick(server);
		if (parada > 0 && --parada == 0) {
			parada = -1;
			LOGGER.warn("Heraldia: update apply: se para el servidor; vuelve a arrancarlo a mano para hacer el trabajo");
			server.halt(false);
		}
	}

	private static int deshacer(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		Optional<Plan> p = Ejecucion.ultimoConCopia(src.getServer());
		if (p.isEmpty()) {
			src.sendFailure(Textos.t(l, "heraldia.actualizar.sin_copia"));
			return 0;
		}
		String cmd = "heraldia update undo confirm " + p.get().id;
		MutableComponent b = Textos.t(l, "heraldia.actualizar.boton.deshacer").withStyle(s -> s.withColor(ChatFormatting.RED)
				.withClickEvent(new ClickEvent.RunCommand(cmd)).withHoverEvent(new HoverEvent.ShowText(Component.literal("/" + cmd))));
		src.sendSuccess(() -> Textos.t(l, "heraldia.actualizar.deshacer", p.get().id, p.get().fecha, "/" + cmd).append(" ").append(b), false);
		return 1;
	}

	private static int confirmarDeshacer(CommandContext<CommandSourceStack> ctx) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		String id = com.mojang.brigadier.arguments.StringArgumentType.getString(ctx, "id");
		Optional<Plan> p = Ejecucion.ultimoConCopia(src.getServer());
		if (p.isEmpty() || !p.get().id.equals(id)) {
			src.sendFailure(Textos.t(l, "heraldia.actualizar.sin_copia"));
			return 0;
		}
		Plan d = p.get();
		d.fase = Plan.DESHACER;
		try {
			d.guardar(Ejecucion.deshacer(src.getServer()));
		} catch (IOException e) {
			src.sendFailure(Textos.t(l, "heraldia.actualizar.error", e.getMessage()));
			return 0;
		}
		LOGGER.info("Heraldia: update undo {} confirmado por {}; el servidor se para", id, src.getTextName());
		src.sendSuccess(() -> Textos.t(l, "heraldia.actualizar.confirmado", AVISO_TICKS / 20).withStyle(ChatFormatting.GOLD), true);
		avisarYParar(src.getServer());
		return 1;
	}

	private static int reparar(CommandContext<CommandSourceStack> ctx, boolean prueba) {
		CommandSourceStack src = ctx.getSource();
		Map<String, String> l = idioma(src);
		Arreglos.Cuenta c = reparar(src.getServer(), prueba);
		src.sendSuccess(() -> Textos.t(l, prueba ? "heraldia.arreglos.prueba" : "heraldia.arreglos.hecho", c.revisados(), c.cambios())
				.withStyle(ChatFormatting.GOLD), true);
		c.porId().forEach((id, v) -> src.sendSuccess(() -> Textos.t(l, "heraldia.arreglos.linea", Textos.t(l, "heraldia.arreglos." + id), v[0], v[1]), false));
		return c.cambios();
	}
}
