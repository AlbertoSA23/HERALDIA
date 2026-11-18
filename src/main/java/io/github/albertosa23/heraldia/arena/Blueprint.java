package io.github.albertosa23.heraldia.arena;

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
import java.util.List;

/**
 * Arena blueprint: what the generator (tools/gen/arena_oleadas.py) writes to heraldia/arena.json. Positions
 * relative to the template's minimum corner. No game classes: the tests check it.
 *
 * @param template   template id (heraldia:arena/arena)
 * @param size       x side, height and z side of the template
 * @param ground     template y that goes at terrain height
 * @param center     center of the ring (column and feet height)
 * @param radius     radius of the ring
 * @param ringY      heights (feet) between which one is in the ring
 * @param points     mob spawn points (feet)
 * @param bell       the bell that starts the match
 * @param gate       minimum and maximum corners of the gate (bars while a match lasts)
 * @param respawn    spot (feet) where whoever falls respawns and where whoever leaves goes
 * @param bosses     mini-boss names there are (heraldia.arena.jefe.0..n-1)
 * @param fame       spots (feet) of the hall of fame signs, one per mode in the order of {@link Mode} (T41;
 *                   empty in an older blueprint)
 * @param fameRotation rotation (0-15) of those standing signs
 */
public record Blueprint(String template, int[] size, int ground, int[] center, int radius, int[] ringY, List<int[]> points,
		int[] bell, int[][] gate, int[] respawn, int bosses, List<int[]> fame, int fameRotation) {

	public static Blueprint read(Reader r) {
		JsonObject o = JsonParser.parseReader(r).getAsJsonObject();
		List<int[]> points = new ArrayList<>();
		for (JsonElement e : o.getAsJsonArray("puntos")) {
			points.add(ints(e.getAsJsonArray()));
		}
		JsonArray gate = o.getAsJsonArray("puerta");
		List<int[]> fame = new ArrayList<>();
		if (o.has("fama")) {
			for (JsonElement e : o.getAsJsonArray("fama")) {
				fame.add(ints(e.getAsJsonArray()));
			}
		}
		return new Blueprint(o.get("plantilla").getAsString(), ints(o.getAsJsonArray("tamano")), o.get("suelo").getAsInt(),
				ints(o.getAsJsonArray("centro")), o.get("radio_ruedo").getAsInt(), ints(o.getAsJsonArray("ruedo_y")),
				List.copyOf(points), ints(o.getAsJsonArray("campana")),
				new int[][] {ints(gate.get(0).getAsJsonArray()), ints(gate.get(1).getAsJsonArray())},
				ints(o.getAsJsonArray("reaparicion")), o.has("jefes") ? o.get("jefes").getAsInt() : 1, List.copyOf(fame),
				o.has("fama_rotacion") ? o.get("fama_rotacion").getAsInt() : 0);
	}

	/** The one in the .jar (heraldia/arena.json). */
	public static Blueprint fromJar() {
		String path = "/heraldia/arena.json";
		try (InputStream in = Blueprint.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			return read(new InputStreamReader(in, StandardCharsets.UTF_8));
		} catch (IOException e) {
			throw new IllegalStateException("No se pudo leer " + path, e);
		}
	}

	private static int[] ints(JsonArray a) {
		int[] out = new int[a.size()];
		for (int i = 0; i < out.length; i++) {
			out[i] = a.get(i).getAsInt();
		}
		return out;
	}
}
