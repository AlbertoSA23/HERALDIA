package io.github.albertosa23.heraldia.command;

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

/** The hidden aliases of the old names (pure logic over Brigadier, with a test tree). */
class AliasTest {
	/** Test source: whether it is an operator and what was run and warned. */
	record Source(boolean op, List<String> log) {
	}

	private static final Predicate<Source> OP = Source::op;

	private static LiteralArgumentBuilder<Source> lit(String n) {
		return LiteralArgumentBuilder.literal(n);
	}

	private static LiteralArgumentBuilder<Source> order(String n, String what) {
		return LiteralArgumentBuilder.<Source>literal(n).executes(ctx -> {
			ctx.getSource().log().add(what);
			return 1;
		});
	}

	/** /heraldia guide, info [nearby [radius] | here], arena [place [confirm] | stop] (the arena ones, for operators). */
	static CommandDispatcher<Source> tree() {
		CommandDispatcher<Source> d = new CommandDispatcher<>();
		d.register(lit("heraldia")
				.then(order("guide", "guide"))
				.then(lit("info").then(order("nearby", "nearby")
								.then(RequiredArgumentBuilder.<Source, Integer>argument("radius", IntegerArgumentType.integer(16, 10000))
										.executes(ctx -> {
											ctx.getSource().log().add("nearby " + IntegerArgumentType.getInteger(ctx, "radius"));
											return 1;
										})))
						.then(order("here", "here")))
				.then(lit("arena").then(order("place", "place").requires(OP).then(order("confirm", "place confirm")))
						.then(order("stop", "stop").requires(OP))));
		int n = Alias.add(d.getRoot().getChild("heraldia"), Alias.LEGACY,
				(f, old, fresh) -> f.log().add("aviso " + old + " -> " + fresh));
		// guia, cerca, aqui, colocar, confirmar (under place) and parar
		assertEquals(6, n);
		return d;
	}

	private static List<String> execute(CommandDispatcher<Source> d, String order, boolean op) throws CommandSyntaxException {
		Source f = new Source(op, new ArrayList<>());
		d.execute(order, f);
		return f.log();
	}

	@Test
	void newNameDoesNotWarn() throws CommandSyntaxException {
		CommandDispatcher<Source> d = tree();
		assertEquals(List.of("guide"), execute(d, "heraldia guide", false));
		assertEquals(List.of("nearby 500"), execute(d, "heraldia info nearby 500", false));
		assertEquals(List.of("place confirm"), execute(d, "heraldia arena place confirm", true));
	}

	@Test
	void oldNameDoesTheSameAndWarnsWithNewName() throws CommandSyntaxException {
		CommandDispatcher<Source> d = tree();
		assertEquals(List.of("aviso /heraldia guia -> /heraldia guide", "guide"), execute(d, "heraldia guia", false));
		assertEquals(List.of("aviso /heraldia info cerca -> /heraldia info nearby", "nearby"), execute(d, "heraldia info cerca", false));
		// with arguments: the notice names the command, not the arguments
		assertEquals(List.of("aviso /heraldia info cerca -> /heraldia info nearby", "nearby 700"), execute(d, "heraldia info cerca 700", false));
		assertEquals(List.of("aviso /heraldia info aqui -> /heraldia info here", "here"), execute(d, "heraldia info aqui", false));
		assertEquals(List.of("aviso /heraldia arena colocar -> /heraldia arena place", "place"), execute(d, "heraldia arena colocar", true));
		assertEquals(List.of("aviso /heraldia arena parar -> /heraldia arena stop", "stop"), execute(d, "heraldia arena parar", true));
	}

	@Test
	void oldRoutesWholeAndMixed() throws CommandSyntaxException {
		CommandDispatcher<Source> d = tree();
		assertEquals(List.of("aviso /heraldia arena colocar confirmar -> /heraldia arena place confirm", "place confirm"),
				execute(d, "heraldia arena colocar confirmar", true));
		assertEquals(List.of("aviso /heraldia arena place confirmar -> /heraldia arena place confirm", "place confirm"),
				execute(d, "heraldia arena place confirmar", true));
		assertEquals(List.of("aviso /heraldia arena colocar confirm -> /heraldia arena place confirm", "place confirm"),
				execute(d, "heraldia arena colocar confirm", true));
	}

	@Test
	void samePermissionsAsNewName() {
		CommandDispatcher<Source> d = tree();
		assertThrows(CommandSyntaxException.class, () -> execute(d, "heraldia arena colocar", false));
		assertThrows(CommandSyntaxException.class, () -> execute(d, "heraldia arena colocar confirmar", false));
		CommandNode<Source> arena = d.getRoot().getChild("heraldia").getChild("arena");
		assertSame(arena.getChild("place").getRequirement(), arena.getChild("colocar").getRequirement());
	}

	@Test
	void eachAliasPointsToItsNode() {
		CommandNode<Source> h = tree().getRoot().getChild("heraldia");
		assertSame(h.getChild("guide"), ((Alias.Hidden<Source>) h.getChild("guia")).destination());
		assertSame(h.getChild("info").getChild("nearby"), ((Alias.Hidden<Source>) h.getChild("info").getChild("cerca")).destination());
		CommandNode<Source> place = h.getChild("arena").getChild("place");
		assertSame(place.getChild("confirm"), ((Alias.Hidden<Source>) place.getChild("confirmar")).destination());
		// inside the copy, the children are not alias roots (their parent hides them)
		assertFalse(h.getChild("arena").getChild("colocar").getChild("confirmar") instanceof Alias.Hidden);
		assertNotNull(h.getChild("arena").getChild("colocar").getChild("confirm"));
	}

	@Test
	void addingTwiceDoesNotDuplicate() {
		CommandDispatcher<Source> d = tree();
		assertEquals(0, Alias.add(d.getRoot().getChild("heraldia"), Alias.LEGACY, (f, a, b) -> {
		}));
	}

	/** The tree the client receives, like Commands.fillUsableCommands with CommandsMixin: without the aliases. */
	static <S> RootCommandNode<S> fromClient(CommandNode<S> root, S source) {
		RootCommandNode<S> out = new RootCommandNode<>();
		copy(root, out, source);
		return out;
	}

	private static <S> void copy(CommandNode<S> of, CommandNode<S> a, S source) {
		for (CommandNode<S> child : of.getChildren()) {
			if (Alias.visible(child) && child.canUse(source)) {
				CommandNode<S> c = child.createBuilder().build();
				a.addChild(c);
				copy(child, c, source);
			}
		}
	}

	static List<String> suggestions(CommandDispatcher<?> d, String text, Object source) {
		@SuppressWarnings("unchecked")
		CommandDispatcher<Object> dd = (CommandDispatcher<Object>) d;
		return dd.getCompletionSuggestions(dd.parse(text, source)).join().getList().stream().map(Suggestion::getText).toList();
	}

	@Test
	void noAliasInClientSuggestions() {
		CommandDispatcher<Source> d = tree();
		Source op = new Source(true, new ArrayList<>());
		CommandDispatcher<Source> client = new CommandDispatcher<>(fromClient(d.getRoot(), op));
		assertEquals(List.of("arena", "guide", "info"), suggestions(client, "heraldia ", op));
		assertEquals(List.of("place", "stop"), suggestions(client, "heraldia arena ", op));
		assertEquals(List.of("confirm"), suggestions(client, "heraldia arena place ", op));
		assertEquals(List.of(), suggestions(client, "heraldia gu", op).stream().filter(s -> s.equals("guia")).toList());
		// the server does know them (without the filter, they show)
		assertTrue(suggestions(d, "heraldia ", op).contains("guia"));
	}

	@Test
	void mapUsesOnlyEnglishAndDistinctOldNames() {
		for (Map.Entry<String, String> e : Alias.LEGACY.entrySet()) {
			assertTrue(e.getKey().matches("[a-z]+( [a-z]+)*"), e.getKey());
			assertTrue(e.getValue().matches("[a-z]+"), e.getValue());
			assertFalse(e.getKey().endsWith(" " + e.getValue()) || e.getKey().equals(e.getValue()), e.getKey());
		}
	}

	@Test
	void redirectNodeIsNotCopied() {
		CommandDispatcher<Source> d = new CommandDispatcher<>();
		LiteralCommandNode<Source> h = d.register(lit("heraldia").then(order("guide", "x")));
		h.getChild("guide").addChild(lit("again").redirect(h).build());
		try {
			Alias.add(h, Alias.LEGACY, (f, a, b) -> {
			});
		} catch (IllegalStateException e) {
			assertTrue(e.getMessage().contains("redirige"));
			return;
		}
		throw new AssertionError("debía fallar");
	}

	@Test
	void hiddenIsALiteral() {
		CommandNode<Source> guide = tree().getRoot().getChild("heraldia").getChild("guia");
		assertInstanceOf(LiteralCommandNode.class, guide);
		assertFalse(Alias.visible(guide));
		assertTrue(Alias.visible(tree().getRoot().getChild("heraldia").getChild("guide")));
	}

	static List<ParsedCommandNode<Source>> nodes(CommandDispatcher<Source> d, String s, Source f) {
		return d.parse(s, f).getContext().getNodes();
	}
}
