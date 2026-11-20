package io.github.albertosa23.heraldia.herald;

import com.google.gson.JsonArray;
import com.google.gson.JsonElement;
import com.google.gson.JsonObject;
import com.google.gson.JsonParser;
import java.io.IOException;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.Reader;
import java.nio.charset.StandardCharsets;
import java.util.ArrayList;
import java.util.LinkedHashMap;
import java.util.List;
import java.util.Map;

/**
 * Blueprint of the Herald's House: what the generator (tools/gen/herald_house.py) writes to heraldia/casa_heraldo.json.
 * Positions relative to the template's minimum corner. No game classes: the tests check it.
 *
 * @param template  template id (heraldia:casa_heraldo/casa)
 * @param size      x side, height and z side
 * @param ground    template y that goes at terrain height
 * @param spawn     the world spawn on the plaza (feet)
 * @param bell      the bell
 * @param gates     gate centers (x, z on the wall) by side (north, south, west, east)
 * @param road      road offsets across its axis, relative to the gate center (min, max)
 * @param portal    the portal frame's minimum and maximum corners
 * @param stalls    the market stalls
 * @param returns   the return barrels
 * @param dock      the dock template and its size (width, height, length)
 * @param style     the village style the villagers' conversations use
 * @param version   the template's version (1: the 96 x 96 town of the first release; 2: the 128 x 128 one)
 * @param square    the village-event square in the plaza (minimum corner x, floor y, z, side), or null (version 1 has none)
 * @param exterior  the part of the template outside the wall (x0, z0, x1, z1: the forecourt), whose bare ground takes the
 *                  land's own surface when the town is placed, or null (blueprints written before it)
 */
public record HousePlan(String template, int[] size, int ground, int[] spawn, int[] bell, Map<String, int[]> gates, int[] road,
		int[][] portal, List<Stall> stalls, List<int[]> returns, String dockTemplate, int[] dockSize, String style, int version,
		int @org.jspecify.annotations.Nullable [] square, int @org.jspecify.annotations.Nullable [] exterior) {

	/** A stall: its number, the box the tenant may use (min and max corners) and its sign. */
	public record Stall(int id, int[] min, int[] max, int[] sign) {
	}

	/** The current blueprint (the one a new placement uses). */
	public static HousePlan read(Reader r) {
		return parse(JsonParser.parseReader(r).getAsJsonObject());
	}

	/**
	 * Every version of the blueprint the .jar knows, by version: the current one and the earlier ones it carries
	 * ({@code anteriores}), so a world that placed an earlier town keeps its protection, stalls and barrels where they are.
	 */
	public static Map<Integer, HousePlan> readAll(Reader r) {
		JsonObject o = JsonParser.parseReader(r).getAsJsonObject();
		Map<Integer, HousePlan> out = new LinkedHashMap<>();
		HousePlan current = parse(o);
		out.put(current.version(), current);
		if (o.has("anteriores")) {
			for (Map.Entry<String, JsonElement> e : o.getAsJsonObject("anteriores").entrySet()) {
				HousePlan p = parse(e.getValue().getAsJsonObject());
				out.putIfAbsent(p.version(), p);
			}
		}
		return Map.copyOf(out);
	}

	private static HousePlan parse(JsonObject o) {
		Map<String, int[]> gates = new LinkedHashMap<>();
		for (Map.Entry<String, JsonElement> e : o.getAsJsonObject("puertas").entrySet()) {
			gates.put(e.getKey(), ints(e.getValue().getAsJsonArray()));
		}
		List<Stall> stalls = new ArrayList<>();
		for (JsonElement e : o.getAsJsonArray("puestos")) {
			JsonObject s = e.getAsJsonObject();
			JsonArray box = s.getAsJsonArray("caja");
			stalls.add(new Stall(s.get("id").getAsInt(), ints(box.get(0).getAsJsonArray()), ints(box.get(1).getAsJsonArray()),
					ints(s.getAsJsonArray("cartel"))));
		}
		List<int[]> returns = new ArrayList<>();
		for (JsonElement e : o.getAsJsonArray("devolucion")) {
			returns.add(ints(e.getAsJsonArray()));
		}
		JsonArray portal = o.getAsJsonArray("portal");
		JsonObject dock = o.getAsJsonObject("muelle");
		return new HousePlan(o.get("plantilla").getAsString(), ints(o.getAsJsonArray("tamano")), o.get("suelo").getAsInt(),
				ints(o.getAsJsonArray("aparicion")), ints(o.getAsJsonArray("campana")), Map.copyOf(gates),
				ints(o.getAsJsonArray("camino")),
				new int[][] {ints(portal.get(0).getAsJsonArray()), ints(portal.get(1).getAsJsonArray())}, List.copyOf(stalls),
				List.copyOf(returns), dock.get("plantilla").getAsString(), ints(dock.getAsJsonArray("tamano")),
				o.get("estilo").getAsString(), o.has("version") ? o.get("version").getAsInt() : 1,
				o.has("plaza_eventos") ? ints(o.getAsJsonArray("plaza_eventos")) : null,
				o.has("exterior") ? ints(o.getAsJsonArray("exterior")) : null);
	}

	/** The current one in the .jar (heraldia/casa_heraldo.json). */
	public static HousePlan fromJar() {
		Map<Integer, HousePlan> all = allFromJar();
		return all.values().stream().max(java.util.Comparator.comparingInt(HousePlan::version)).orElseThrow();
	}

	/** Every version in the .jar, by version. */
	public static Map<Integer, HousePlan> allFromJar() {
		String path = "/heraldia/casa_heraldo.json";
		try (InputStream in = HousePlan.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Missing " + path + " in the Heraldia .jar");
			}
			return readAll(new InputStreamReader(in, StandardCharsets.UTF_8));
		} catch (IOException e) {
			throw new IllegalStateException("Could not read " + path, e);
		}
	}

	public @org.jspecify.annotations.Nullable Stall stall(int id) {
		for (Stall s : stalls) {
			if (s.id() == id) {
				return s;
			}
		}
		return null;
	}

	private static int[] ints(JsonArray a) {
		int[] out = new int[a.size()];
		for (int i = 0; i < out.length; i++) {
			out[i] = a.get(i).getAsInt();
		}
		return out;
	}
}
