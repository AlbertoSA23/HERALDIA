package io.github.albertosa23.heraldia.command;

import com.mojang.brigadier.Command;
import com.mojang.brigadier.builder.ArgumentBuilder;
import com.mojang.brigadier.tree.CommandNode;
import com.mojang.brigadier.tree.LiteralCommandNode;
import java.util.List;
import java.util.Map;
import java.util.function.Predicate;

/**
 * Nombres antiguos (en español) de los comandos, que siguen funcionando como alias ocultos desde que los comandos pasaron
 * al inglés (T35b): el servidor los ejecuta igual que el nombre nuevo, avisa de que están obsoletos y dice el nombre
 * nuevo, y no se envían a los clientes (CommandsMixin), así que no salen en el autocompletado. Se quitarán en una versión
 * futura (docs/DESARROLLO.md). Lógica pura sobre Brigadier: los tests la recorren sin servidor.
 */
public final class Alias {
	/**
	 * Ruta canónica bajo /heraldia (tramos separados por espacios; los argumentos, por su nombre) -> nombre antiguo de su
	 * último tramo. Una ruta antigua entera («arena colocar confirmar») y las mezclas («arena place confirmar») funcionan.
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

	/** Cómo se avisa de que se ha usado un nombre antiguo: rutas antigua y nueva, con la barra («/heraldia guia», «/heraldia guide»). */
	@FunctionalInterface
	public interface Notice<S> {
		void warn(S source, String old, String fresh);
	}

	/** Raíz de un alias antiguo: el servidor lo ejecuta, pero no se envía a los clientes (no sale en el autocompletado). */
	public static final class Hidden<S> extends LiteralCommandNode<S> {
		private final CommandNode<S> destination;

		Hidden(String name, Command<S> command, Predicate<S> requirement, CommandNode<S> destination) {
			super(name, command, requirement, null, null, false);
			this.destination = destination;
		}

		/** El nodo con el nombre nuevo del que es alias. */
		public CommandNode<S> destination() {
			return destination;
		}
	}

	/** ¿Se envía este nodo a los clientes? Todos menos los alias antiguos (CommandsMixin). */
	public static boolean visible(CommandNode<?> node) {
		return !(node instanceof Hidden);
	}

	/**
	 * Añade bajo `raiz` (el nodo /heraldia, ya con todos sus subcomandos) un alias oculto por cada ruta de `antiguos` que
	 * exista: una copia del subárbol con los nombres antiguos, los mismos requisitos y argumentos, y cada orden envuelta
	 * para avisar antes de ejecutarse. Devuelve cuántos alias ha añadido.
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
				// con su nombre antiguo y con el nuevo («arena colocar confirmar» y «arena colocar confirm»)
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
