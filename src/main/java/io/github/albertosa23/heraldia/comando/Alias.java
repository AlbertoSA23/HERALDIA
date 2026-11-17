package io.github.albertosa23.heraldia.comando;

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
	public static final Map<String, String> ANTIGUOS = Map.ofEntries(
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
	public interface Aviso<S> {
		void avisar(S fuente, String antigua, String nueva);
	}

	/** Raíz de un alias antiguo: el servidor lo ejecuta, pero no se envía a los clientes (no sale en el autocompletado). */
	public static final class Oculto<S> extends LiteralCommandNode<S> {
		private final CommandNode<S> destino;

		Oculto(String nombre, Command<S> comando, Predicate<S> requisito, CommandNode<S> destino) {
			super(nombre, comando, requisito, null, null, false);
			this.destino = destino;
		}

		/** El nodo con el nombre nuevo del que es alias. */
		public CommandNode<S> destino() {
			return destino;
		}
	}

	/** ¿Se envía este nodo a los clientes? Todos menos los alias antiguos (CommandsMixin). */
	public static boolean visible(CommandNode<?> nodo) {
		return !(nodo instanceof Oculto);
	}

	/**
	 * Añade bajo `raiz` (el nodo /heraldia, ya con todos sus subcomandos) un alias oculto por cada ruta de `antiguos` que
	 * exista: una copia del subárbol con los nombres antiguos, los mismos requisitos y argumentos, y cada orden envuelta
	 * para avisar antes de ejecutarse. Devuelve cuántos alias ha añadido.
	 */
	public static <S> int anadir(CommandNode<S> raiz, Map<String, String> antiguos, Aviso<S> aviso) {
		return recorrer(raiz, "", "/" + raiz.getName(), antiguos, aviso);
	}

	private static <S> int recorrer(CommandNode<S> nodo, String ruta, String orden, Map<String, String> antiguos, Aviso<S> aviso) {
		int n = 0;
		for (CommandNode<S> hijo : List.copyOf(nodo.getChildren())) {
			if (hijo instanceof Oculto) {
				continue;
			}
			String r = ruta.isEmpty() ? hijo.getName() : ruta + " " + hijo.getName();
			boolean literal = hijo instanceof LiteralCommandNode;
			String nueva = literal ? orden + " " + hijo.getName() : orden;
			String viejo = antiguos.get(r);
			if (viejo != null && literal && nodo.getChild(viejo) == null) {
				nodo.addChild(copia(hijo, viejo, r, orden + " " + viejo, nueva, antiguos, aviso, true));
				n++;
			}
			n += recorrer(hijo, r, nueva, antiguos, aviso);
		}
		return n;
	}

	private static <S> CommandNode<S> copia(CommandNode<S> orig, String nombre, String ruta, String antigua, String nueva,
			Map<String, String> antiguos, Aviso<S> aviso, boolean raiz) {
		if (orig.getRedirect() != null) {
			throw new IllegalStateException("Alias: el nodo " + ruta + " redirige a otro; no se sabe copiar");
		}
		Command<S> orden = envolver(orig.getCommand(), antigua, nueva, aviso);
		CommandNode<S> c;
		if (raiz) {
			c = new Oculto<>(nombre, orden, orig.getRequirement(), orig);
		} else if (orig instanceof LiteralCommandNode) {
			c = new LiteralCommandNode<>(nombre, orden, orig.getRequirement(), null, null, false);
		} else {
			ArgumentBuilder<S, ?> b = orig.createBuilder();
			b.executes(orden);
			c = b.build();
		}
		for (CommandNode<S> hijo : orig.getChildren()) {
			String r = ruta + " " + hijo.getName();
			if (hijo instanceof LiteralCommandNode) {
				// con su nombre antiguo y con el nuevo («arena colocar confirmar» y «arena colocar confirm»)
				String viejo = antiguos.get(r);
				if (viejo != null) {
					c.addChild(copia(hijo, viejo, r, antigua + " " + viejo, nueva + " " + hijo.getName(), antiguos, aviso, false));
				}
				c.addChild(copia(hijo, hijo.getName(), r, antigua + " " + hijo.getName(), nueva + " " + hijo.getName(), antiguos, aviso, false));
			} else {
				c.addChild(copia(hijo, hijo.getName(), r, antigua, nueva, antiguos, aviso, false));
			}
		}
		return c;
	}

	private static <S> Command<S> envolver(Command<S> orden, String antigua, String nueva, Aviso<S> aviso) {
		if (orden == null) {
			return null;
		}
		return ctx -> {
			aviso.avisar(ctx.getSource(), antigua, nueva);
			return orden.run(ctx);
		};
	}
}
