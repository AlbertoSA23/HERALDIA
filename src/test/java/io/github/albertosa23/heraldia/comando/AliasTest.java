package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertThrows;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.arguments.IntegerArgumentType;
import com.mojang.brigadier.builder.LiteralArgumentBuilder;
import com.mojang.brigadier.builder.RequiredArgumentBuilder;
import com.mojang.brigadier.context.ParsedCommandNode;
import com.mojang.brigadier.exceptions.CommandSyntaxException;
import com.mojang.brigadier.suggestion.Suggestion;
import com.mojang.brigadier.tree.CommandNode;
import com.mojang.brigadier.tree.LiteralCommandNode;
import com.mojang.brigadier.tree.RootCommandNode;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;
import org.junit.jupiter.api.Test;

/** Los alias ocultos de los nombres antiguos (lógica pura sobre Brigadier, con un árbol de prueba). */
class AliasTest {
	/** Fuente de prueba: si es operador y lo que se ha ejecutado y avisado. */
	record Fuente(boolean op, List<String> log) {
	}

	private static final Predicate<Fuente> OP = Fuente::op;

	private static LiteralArgumentBuilder<Fuente> lit(String n) {
		return LiteralArgumentBuilder.literal(n);
	}

	private static LiteralArgumentBuilder<Fuente> orden(String n, String que) {
		return LiteralArgumentBuilder.<Fuente>literal(n).executes(ctx -> {
			ctx.getSource().log().add(que);
			return 1;
		});
	}

	/** /heraldia guide, info [nearby [radius] | here], arena [place [confirm] | stop] (las de arena, de operador). */
	static CommandDispatcher<Fuente> arbol() {
		CommandDispatcher<Fuente> d = new CommandDispatcher<>();
		d.register(lit("heraldia")
				.then(orden("guide", "guide"))
				.then(lit("info").then(orden("nearby", "nearby")
								.then(RequiredArgumentBuilder.<Fuente, Integer>argument("radius", IntegerArgumentType.integer(16, 10000))
										.executes(ctx -> {
											ctx.getSource().log().add("nearby " + IntegerArgumentType.getInteger(ctx, "radius"));
											return 1;
										})))
						.then(orden("here", "here")))
				.then(lit("arena").then(orden("place", "place").requires(OP).then(orden("confirm", "place confirm")))
						.then(orden("stop", "stop").requires(OP))));
		int n = Alias.anadir(d.getRoot().getChild("heraldia"), Alias.ANTIGUOS,
				(f, antigua, nueva) -> f.log().add("aviso " + antigua + " -> " + nueva));
		// guia, cerca, aqui, colocar, confirmar (bajo place) y parar
		assertEquals(6, n);
		return d;
	}

	private static List<String> ejecutar(CommandDispatcher<Fuente> d, String orden, boolean op) throws CommandSyntaxException {
		Fuente f = new Fuente(op, new ArrayList<>());
		d.execute(orden, f);
		return f.log();
	}

	@Test
	void elNombreNuevoNoAvisa() throws CommandSyntaxException {
		CommandDispatcher<Fuente> d = arbol();
		assertEquals(List.of("guide"), ejecutar(d, "heraldia guide", false));
		assertEquals(List.of("nearby 500"), ejecutar(d, "heraldia info nearby 500", false));
		assertEquals(List.of("place confirm"), ejecutar(d, "heraldia arena place confirm", true));
	}

	@Test
	void elAntiguoHaceLoMismoYAvisaConElNombreNuevo() throws CommandSyntaxException {
		CommandDispatcher<Fuente> d = arbol();
		assertEquals(List.of("aviso /heraldia guia -> /heraldia guide", "guide"), ejecutar(d, "heraldia guia", false));
		assertEquals(List.of("aviso /heraldia info cerca -> /heraldia info nearby", "nearby"), ejecutar(d, "heraldia info cerca", false));
		// con argumentos: el aviso nombra el comando, no los argumentos
		assertEquals(List.of("aviso /heraldia info cerca -> /heraldia info nearby", "nearby 700"), ejecutar(d, "heraldia info cerca 700", false));
		assertEquals(List.of("aviso /heraldia info aqui -> /heraldia info here", "here"), ejecutar(d, "heraldia info aqui", false));
		assertEquals(List.of("aviso /heraldia arena colocar -> /heraldia arena place", "place"), ejecutar(d, "heraldia arena colocar", true));
		assertEquals(List.of("aviso /heraldia arena parar -> /heraldia arena stop", "stop"), ejecutar(d, "heraldia arena parar", true));
	}

	@Test
	void rutasAntiguasEnterasYMezcladas() throws CommandSyntaxException {
		CommandDispatcher<Fuente> d = arbol();
		assertEquals(List.of("aviso /heraldia arena colocar confirmar -> /heraldia arena place confirm", "place confirm"),
				ejecutar(d, "heraldia arena colocar confirmar", true));
		assertEquals(List.of("aviso /heraldia arena place confirmar -> /heraldia arena place confirm", "place confirm"),
				ejecutar(d, "heraldia arena place confirmar", true));
		assertEquals(List.of("aviso /heraldia arena colocar confirm -> /heraldia arena place confirm", "place confirm"),
				ejecutar(d, "heraldia arena colocar confirm", true));
	}

	@Test
	void mismosPermisosQueElNombreNuevo() {
		CommandDispatcher<Fuente> d = arbol();
		assertThrows(CommandSyntaxException.class, () -> ejecutar(d, "heraldia arena colocar", false));
		assertThrows(CommandSyntaxException.class, () -> ejecutar(d, "heraldia arena colocar confirmar", false));
		CommandNode<Fuente> arena = d.getRoot().getChild("heraldia").getChild("arena");
		assertSame(arena.getChild("place").getRequirement(), arena.getChild("colocar").getRequirement());
	}

	@Test
	void cadaAliasApuntaASuNodo() {
		CommandNode<Fuente> h = arbol().getRoot().getChild("heraldia");
		assertSame(h.getChild("guide"), ((Alias.Oculto<Fuente>) h.getChild("guia")).destino());
		assertSame(h.getChild("info").getChild("nearby"), ((Alias.Oculto<Fuente>) h.getChild("info").getChild("cerca")).destino());
		CommandNode<Fuente> place = h.getChild("arena").getChild("place");
		assertSame(place.getChild("confirm"), ((Alias.Oculto<Fuente>) place.getChild("confirmar")).destino());
		// dentro de la copia, los hijos no son raíces de alias (los oculta su padre)
		assertFalse(h.getChild("arena").getChild("colocar").getChild("confirmar") instanceof Alias.Oculto);
		assertNotNull(h.getChild("arena").getChild("colocar").getChild("confirm"));
	}

	@Test
	void anadirDosVecesNoDuplica() {
		CommandDispatcher<Fuente> d = arbol();
		assertEquals(0, Alias.anadir(d.getRoot().getChild("heraldia"), Alias.ANTIGUOS, (f, a, b) -> {
		}));
	}

	/** El árbol que recibe el cliente, como Commands.fillUsableCommands con CommandsMixin: sin los alias. */
	static <S> RootCommandNode<S> delCliente(CommandNode<S> raiz, S fuente) {
		RootCommandNode<S> out = new RootCommandNode<>();
		copiar(raiz, out, fuente);
		return out;
	}

	private static <S> void copiar(CommandNode<S> de, CommandNode<S> a, S fuente) {
		for (CommandNode<S> hijo : de.getChildren()) {
			if (Alias.visible(hijo) && hijo.canUse(fuente)) {
				CommandNode<S> c = hijo.createBuilder().build();
				a.addChild(c);
				copiar(hijo, c, fuente);
			}
		}
	}

	static List<String> sugerencias(CommandDispatcher<?> d, String texto, Object fuente) {
		@SuppressWarnings("unchecked")
		CommandDispatcher<Object> dd = (CommandDispatcher<Object>) d;
		return dd.getCompletionSuggestions(dd.parse(texto, fuente)).join().getList().stream().map(Suggestion::getText).toList();
	}

	@Test
	void ningunAliasEnLasSugerenciasDelCliente() {
		CommandDispatcher<Fuente> d = arbol();
		Fuente op = new Fuente(true, new ArrayList<>());
		CommandDispatcher<Fuente> cliente = new CommandDispatcher<>(delCliente(d.getRoot(), op));
		assertEquals(List.of("arena", "guide", "info"), sugerencias(cliente, "heraldia ", op));
		assertEquals(List.of("place", "stop"), sugerencias(cliente, "heraldia arena ", op));
		assertEquals(List.of("confirm"), sugerencias(cliente, "heraldia arena place ", op));
		assertEquals(List.of(), sugerencias(cliente, "heraldia gu", op).stream().filter(s -> s.equals("guia")).toList());
		// el servidor sí los conoce (sin el filtro, salen)
		assertTrue(sugerencias(d, "heraldia ", op).contains("guia"));
	}

	@Test
	void elMapaUsaSoloNombresInglesesYAntiguosDistintos() {
		for (Map.Entry<String, String> e : Alias.ANTIGUOS.entrySet()) {
			assertTrue(e.getKey().matches("[a-z]+( [a-z]+)*"), e.getKey());
			assertTrue(e.getValue().matches("[a-z]+"), e.getValue());
			assertFalse(e.getKey().endsWith(" " + e.getValue()) || e.getKey().equals(e.getValue()), e.getKey());
		}
	}

	@Test
	void unNodoConRedireccionNoSeCopia() {
		CommandDispatcher<Fuente> d = new CommandDispatcher<>();
		LiteralCommandNode<Fuente> h = d.register(lit("heraldia").then(orden("guide", "x")));
		h.getChild("guide").addChild(lit("again").redirect(h).build());
		try {
			Alias.anadir(h, Alias.ANTIGUOS, (f, a, b) -> {
			});
		} catch (IllegalStateException e) {
			assertTrue(e.getMessage().contains("redirige"));
			return;
		}
		throw new AssertionError("debía fallar");
	}

	@Test
	void ocultoEsUnLiteral() {
		CommandNode<Fuente> guia = arbol().getRoot().getChild("heraldia").getChild("guia");
		assertInstanceOf(LiteralCommandNode.class, guia);
		assertFalse(Alias.visible(guia));
		assertTrue(Alias.visible(arbol().getRoot().getChild("heraldia").getChild("guide")));
	}

	static List<ParsedCommandNode<Fuente>> nodos(CommandDispatcher<Fuente> d, String s, Fuente f) {
		return d.parse(s, f).getContext().getNodes();
	}
}
