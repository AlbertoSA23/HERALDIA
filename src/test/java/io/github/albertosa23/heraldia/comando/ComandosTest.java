package io.github.albertosa23.heraldia.comando;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertInstanceOf;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertSame;
import static org.junit.jupiter.api.Assertions.assertTrue;

import com.mojang.brigadier.CommandDispatcher;
import com.mojang.brigadier.ParseResults;
import com.mojang.brigadier.context.ParsedCommandNode;
import com.mojang.brigadier.tree.ArgumentCommandNode;
import com.mojang.brigadier.tree.CommandNode;
import com.mojang.brigadier.tree.LiteralCommandNode;
import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.TreeSet;
import java.util.regex.Matcher;
import java.util.regex.Pattern;
import net.minecraft.SharedConstants;
import net.minecraft.commands.CommandSourceStack;
import net.minecraft.commands.Commands;
import net.minecraft.server.Bootstrap;
import net.minecraft.server.permissions.LevelBasedPermissionSet;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * El árbol real de /heraldia (Comandos.arbol, sin servidor): todos los nombres canónicos en inglés y ASCII (los mismos
 * que tools/gen/comandos.py), cada nombre antiguo resuelve al mismo nodo con los mismos permisos y avisa, y ningún alias
 * sale en el árbol que recibe el cliente (las sugerencias).
 */
class ComandosTest {
	private static CommandDispatcher<CommandSourceStack> d;
	private static CommandSourceStack op, jugador;

	@BeforeAll
	static void juego() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
		d = new CommandDispatcher<>();
		Comandos.arbol(d);
		op = Commands.createCompilationContext(LevelBasedPermissionSet.OWNER);
		jugador = Commands.createCompilationContext(LevelBasedPermissionSet.ALL);
	}

	private static CommandNode<CommandSourceStack> raiz() {
		return d.getRoot().getChild("heraldia");
	}

	/** Rutas de los nodos visibles (sin alias) bajo /heraldia: literales por su nombre, argumentos como &lt;nombre&gt;. */
	private static Set<String> canonicas(CommandNode<CommandSourceStack> n, String ruta, Set<String> out) {
		for (CommandNode<CommandSourceStack> h : n.getChildren()) {
			if (!Alias.visible(h)) {
				continue;
			}
			String nombre = h instanceof ArgumentCommandNode ? "<" + h.getName() + ">" : h.getName();
			String r = ruta.isEmpty() ? nombre : ruta + " " + nombre;
			out.add(r);
			canonicas(h, r, out);
		}
		return out;
	}

	/** CANONICOS de tools/gen/comandos.py (la lista que comprueban también los tests del generador). */
	private static Set<String> deComandosPy() throws IOException {
		String py = Files.readString(Path.of("tools/gen/comandos.py"), StandardCharsets.UTF_8);
		Matcher m = Pattern.compile("CANONICOS = \\[(.*?)\\]", Pattern.DOTALL).matcher(py);
		assertTrue(m.find(), "CANONICOS en comandos.py");
		Set<String> out = new TreeSet<>();
		Matcher s = Pattern.compile("\"([^\"]+)\"").matcher(m.group(1));
		while (s.find()) {
			out.add(s.group(1));
		}
		return out;
	}

	@Test
	void nombresCanonicosEnInglesYAscii() throws IOException {
		Set<String> rutas = canonicas(raiz(), "", new TreeSet<>());
		assertEquals(deComandosPy(), rutas);
		for (String r : rutas) {
			for (String tramo : r.split(" ")) {
				assertTrue(tramo.matches("<?[a-z]+>?"), r);
			}
		}
		Set<String> antiguos = new TreeSet<>(Alias.ANTIGUOS.values());
		for (String r : rutas) {
			for (String tramo : r.split(" ")) {
				assertFalse(antiguos.contains(tramo), "nombre antiguo visible: " + r);
			}
		}
	}

	private static CommandNode<CommandSourceStack> nodo(String ruta) {
		CommandNode<CommandSourceStack> n = raiz();
		for (String t : ruta.split(" ")) {
			n = n.getChild(t);
			assertNotNull(n, ruta);
		}
		return n;
	}

	@Test
	void cadaAliasResuelveAlMismoNodoConLosMismosPermisos() {
		for (Map.Entry<String, String> e : Alias.ANTIGUOS.entrySet()) {
			String ruta = e.getKey();
			int i = ruta.lastIndexOf(' ');
			String padre = i < 0 ? "" : ruta.substring(0, i);
			CommandNode<CommandSourceStack> p = padre.isEmpty() ? raiz() : nodo(padre);
			CommandNode<CommandSourceStack> alias = p.getChild(e.getValue()), canon = nodo(ruta);
			Alias.Oculto<?> o = assertInstanceOf(Alias.Oculto.class, alias, ruta);
			assertSame(canon, o.destino(), ruta);
			assertSame(canon.getRequirement(), alias.getRequirement(), ruta);
			assertEquals(canon.getCommand() == null, alias.getCommand() == null, ruta);
			assertEquals(nombres(canon), nombres(alias), ruta);
		}
	}

	/** Los hijos con su nombre canónico (los de la copia, traducidos con el mapa). */
	private static Set<String> nombres(CommandNode<CommandSourceStack> n) {
		Set<String> out = new TreeSet<>();
		Map<String, String> inverso = new java.util.HashMap<>();
		Alias.ANTIGUOS.forEach((k, v) -> inverso.put(v, k.substring(k.lastIndexOf(' ') + 1)));
		for (CommandNode<CommandSourceStack> h : n.getChildren()) {
			if (h instanceof LiteralCommandNode && !Alias.visible(h)) {
				continue;
			}
			out.add(inverso.getOrDefault(h.getName(), h.getName()));
		}
		return out;
	}

	private static void parsea(String orden, CommandSourceStack src) {
		ParseResults<CommandSourceStack> p = d.parse(orden, src);
		assertFalse(p.getReader().canRead(), orden + ": " + p.getExceptions());
		assertNotNull(p.getContext().getCommand(), orden);
	}

	@Test
	void lasOrdenesAntiguasSeEntiendenEnteras() {
		for (String orden : List.of("heraldia guia", "heraldia info cerca", "heraldia info cerca 500", "heraldia info aqui",
				"heraldia llave @a todas", "heraldia llave @a atlantida", "heraldia arena salir", "heraldia arena colocar",
				"heraldia arena colocar confirmar", "heraldia arena place confirmar", "heraldia arena mover confirmar",
				"heraldia arena quitar confirmar", "heraldia arena empezar", "heraldia arena parar")) {
			parsea(orden, op);
		}
		for (String orden : List.of("heraldia guide", "heraldia info nearby 500", "heraldia info here", "heraldia key @a all",
				"heraldia arena leave", "heraldia arena place confirm", "heraldia arena move confirm", "heraldia arena remove confirm",
				"heraldia arena start", "heraldia arena stop", "heraldia update check", "heraldia review next", "heraldia status 2",
				"heraldia reload")) {
			parsea(orden, op);
		}
		// sin permisos, solo lo que ya era de todos
		parsea("heraldia guia", jugador);
		parsea("heraldia arena salir", jugador);
		assertTrue(d.parse("heraldia arena colocar", jugador).getReader().canRead());
		assertTrue(d.parse("heraldia update check", jugador).getReader().canRead());
	}

	@Test
	void comandosDeLosModosDeLaArena() {
		for (String orden : List.of("heraldia arena start coop", "heraldia arena start timeattack", "heraldia arena start survival",
				"heraldia arena leaderboard", "heraldia arena leaderboard timeattack", "heraldia arena leaderboard survival 3",
				"heraldia arena season", "heraldia arena season reset", "heraldia arena empezar timeattack")) {
			parsea(orden, op);
		}
		for (String orden : List.of("heraldia arena start", "heraldia arena start survival", "heraldia arena leaderboard",
				"heraldia arena leaderboard coop 1")) {
			parsea(orden, jugador);
		}
		// la temporada es de operadores; la semana tiene un tope
		assertTrue(d.parse("heraldia arena season reset", jugador).getReader().canRead());
		assertTrue(d.parse("heraldia arena leaderboard coop 99", op).getExceptions().size() > 0
				|| d.parse("heraldia arena leaderboard coop 99", op).getReader().canRead());
		assertTrue(d.parse("heraldia arena start contrarreloj", op).getReader().canRead(), "los modos, en inglés");
	}

	@Test
	void elUltimoNodoDeUnaOrdenAntiguaEsUnaCopia() {
		List<ParsedCommandNode<CommandSourceStack>> n = d.parse("heraldia arena colocar confirmar", op).getContext().getNodes();
		assertEquals(List.of("heraldia", "arena", "colocar", "confirmar"), n.stream().map(x -> x.getNode().getName()).toList());
		assertFalse(Alias.visible(n.get(2).getNode()));
	}

	@Test
	void ningunAliasEnElArbolDelCliente() {
		var cliente = new CommandDispatcher<>(AliasTest.delCliente(d.getRoot(), op));
		List<String> raiz = AliasTest.sugerencias(cliente, "heraldia ", op);
		assertEquals(List.of("arena", "guide", "info", "key", "profile", "quest", "reload", "review", "status", "treasure", "update", "webmap"), raiz);
		assertEquals(List.of("abandon", "accept", "list", "turnin"), AliasTest.sugerencias(cliente, "heraldia quest ", op));
		assertEquals(List.of("give", "info"), AliasTest.sugerencias(cliente, "heraldia treasure ", op));
		assertEquals(List.of("leaderboard", "leave", "move", "place", "remove", "season", "start", "stop"),
				AliasTest.sugerencias(cliente, "heraldia arena ", op));
		assertEquals(List.of("coop", "survival", "timeattack"), AliasTest.sugerencias(cliente, "heraldia arena start ", op));
		assertEquals(List.of("reset"), AliasTest.sugerencias(cliente, "heraldia arena season ", op));
		assertEquals(List.of("here", "nearby"), AliasTest.sugerencias(cliente, "heraldia info ", op));
		assertEquals(List.of("check"), AliasTest.sugerencias(cliente, "heraldia update ", op));
		// un jugador sin permisos ve solo lo suyo
		var deJugador = new CommandDispatcher<>(AliasTest.delCliente(d.getRoot(), jugador));
		assertEquals(List.of("arena", "guide", "quest", "status"), AliasTest.sugerencias(deJugador, "heraldia ", jugador));
		assertEquals(List.of("abandon", "accept", "list", "turnin"), AliasTest.sugerencias(deJugador, "heraldia quest ", jugador));
		// T41: cualquiera ve la clasificación y start (los botones del menú de modos; el Java pide estar en el ruedo)
		assertEquals(List.of("leaderboard", "leave", "start"), AliasTest.sugerencias(deJugador, "heraldia arena ", jugador));
		assertEquals(List.of("coop", "survival", "timeattack"), AliasTest.sugerencias(deJugador, "heraldia arena leaderboard ", jugador));
		// todos los alias están en el servidor
		List<String> ocultos = new ArrayList<>();
		recoger(raiz(), ocultos);
		assertEquals(Alias.ANTIGUOS.size(), ocultos.size(), ocultos.toString());
	}

	private static void recoger(CommandNode<CommandSourceStack> n, List<String> out) {
		for (CommandNode<CommandSourceStack> h : n.getChildren()) {
			if (!Alias.visible(h)) {
				out.add(h.getName());
			} else {
				recoger(h, out);
			}
		}
	}

	@Test
	void laLlaveTodasEsAll() {
		assertEquals("all", LlaveCommand.opcion("todas"));
		assertEquals("all", LlaveCommand.opcion("all"));
		assertEquals("atlantida", LlaveCommand.opcion("atlantida"));
	}
}
