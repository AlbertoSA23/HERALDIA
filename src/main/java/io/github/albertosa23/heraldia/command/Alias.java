package io.github.albertosa23.heraldia.command;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.builder.ArgumentBuilder;
import com.mojang.brigadier.tree.CommandNode;
import com.mojang.brigadier.tree.LiteralCommandNode;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Old (Spanish) command names, which keep working as hidden aliases since the commands moved to English
 * (T35b): the server runs them like the new name, warns that they are deprecated and gives the new
 * name, and they are not sent to the clients (CommandsMixin), so they do not show up in autocompletion. They will be
 * removed in a future version (docs/DEVELOPMENT.md). Pure logic over Brigadier: the tests walk it without a server.
 */
public final class Alias {
	/**
	 * Canonical route under /heraldia (segments separated by spaces; arguments, by their name) -> old name of its
	 * last segment. A whole old route ("arena colocar confirmar") and mixes ("arena place confirmar") work.
	 */
	public static final Map<String, String> LEGACY = Map.ofEntries(
			Map.entry("guide", "guia"),
			Map.entry("key", "llave"),
			Map.entry("info nearby", "cerca"),
			Map.entry("info here", "aqui"),
			Map.entry("arena leave", "salir"),
			Map.entry("arena place", "colocar"),
			Map.entry("arena place confirm", "confirmar"),
			Map.entry("arena move", "mover"),
			Map.entry("arena move confirm", "confirmar"),
			Map.entry("arena remove", "quitar"),
			Map.entry("arena remove confirm", "confirmar"),
			Map.entry("arena start", "empezar"),
			Map.entry("arena stop", "parar"));

	private Alias() {
	}

	/** How the use of an old name is reported: old and new routes, with the slash («/heraldia guia», «/heraldia guide»). */
	@FunctionalInterface
	public interface Notice<S> {
		void warn(S source, String old, String fresh);
	}

	/** Root of an old alias: the server runs it, but it is not sent to the clients (it does not show in autocompletion). */
	public static final class Hidden<S> extends LiteralCommandNode<S> {
		private final CommandNode<S> destination;

		Hidden(String name, Command<S> command, Predicate<S> requirement, CommandNode<S> destination) {
			super(name, command, requirement, null, null, false);
			this.destination = destination;
		}

		/** The node with the new name it is an alias of. */
		public CommandNode<S> destination() {
			return destination;
		}
	}

	/** Is this node sent to the clients? All but the old aliases (CommandsMixin). */
	public static boolean visible(CommandNode<?> node) {
		return !(node instanceof Hidden);
	}

	/**
	 * Adds under `root` (the /heraldia node, already with all its subcommands) a hidden alias for each route of `legacyNames` that
	 * exists: a copy of the subtree with the old names, the same requirements and arguments, and each command wrapped
	 * to warn before running. Returns how many aliases it added.
	 */
	public static <S> int add(CommandNode<S> root, Map<String, String> legacyNames, Notice<S> notice) {
		return walk(root, "", "/" + root.getName(), legacyNames, notice);
	}

	private static <S> int walk(CommandNode<S> node, String route, String order, Map<String, String> legacyNames, Notice<S> notice) {
		int n = 0;
		for (CommandNode<S> child : List.copyOf(node.getChildren())) {
			if (child instanceof Hidden) {
				continue;
			}
			String r = route.isEmpty() ? child.getName() : route + " " + child.getName();
			boolean literal = child instanceof LiteralCommandNode;
			String fresh = literal ? order + " " + child.getName() : order;
			String oldValue = legacyNames.get(r);
			if (oldValue != null && literal && node.getChild(oldValue) == null) {
				node.addChild(backup(child, oldValue, r, order + " " + oldValue, fresh, legacyNames, notice, true));
				n++;
			}
			n += walk(child, r, fresh, legacyNames, notice);
		}
		return n;
	}

	private static <S> CommandNode<S> backup(CommandNode<S> orig, String name, String route, String old, String fresh,
			Map<String, String> legacyNames, Notice<S> notice, boolean root) {
		if (orig.getRedirect() != null) {
			throw new IllegalStateException("Alias: el nodo " + route + " redirige a otro; no se sabe copiar");
		}
		Command<S> order = wrap(orig.getCommand(), old, fresh, notice);
		CommandNode<S> c;
		if (root) {
			c = new Hidden<>(name, order, orig.getRequirement(), orig);
		} else if (orig instanceof LiteralCommandNode) {
			c = new LiteralCommandNode<>(name, order, orig.getRequirement(), null, null, false);
		} else {
			ArgumentBuilder<S, ?> b = orig.createBuilder();
			b.executes(order);
			c = b.build();
		}
		for (CommandNode<S> child : orig.getChildren()) {
			String r = route + " " + child.getName();
			if (child instanceof LiteralCommandNode) {
				// with its old name and with the new one ("arena colocar confirmar" and "arena colocar confirm")
				String oldValue = legacyNames.get(r);
				if (oldValue != null) {
					c.addChild(backup(child, oldValue, r, old + " " + oldValue, fresh + " " + child.getName(), legacyNames, notice, false));
				}
				c.addChild(backup(child, child.getName(), r, old + " " + child.getName(), fresh + " " + child.getName(), legacyNames, notice, false));
			} else {
				c.addChild(backup(child, child.getName(), r, old, fresh, legacyNames, notice, false));
			}
		}
		return c;
	}

	private static <S> Command<S> wrap(Command<S> order, String old, String fresh, Notice<S> notice) {
		if (order == null) {
			return null;
		}
		return ctx -> {
			notice.warn(ctx.getSource(), old, fresh);
			return order.run(ctx);
		};
	}
}
