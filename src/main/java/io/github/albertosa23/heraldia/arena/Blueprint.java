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
 * Plano de la arena: lo que el generador (tools/gen/arena_oleadas.py) escribe en heraldia/arena.json. Posiciones
 * relativas a la esquina mínima de la plantilla. Sin clases del juego: lo prueban los tests.
 *
 * @param plantilla  id de la plantilla (heraldia:arena/arena)
 * @param tamano     lado x, alto y lado z de la plantilla
 * @param suelo      y de la plantilla que va a la altura del terreno
 * @param centro     centro del ruedo (columna y altura de los pies)
 * @param radio      radio del ruedo
 * @param ruedoY     alturas (pies) entre las que se está en el ruedo
 * @param puntos     puntos de aparición de los mobs (pies)
 * @param campana    la campana que empieza la partida
 * @param puerta     esquinas mínima y máxima de la puerta (rejas mientras dura una partida)
 * @param reaparicion sitio (pies) donde reaparece quien cae y adonde va quien sale
 * @param jefes      nombres de mini-jefe que hay (heraldia.arena.jefe.0..n-1)
 * @param fama       sitios (pies) de los carteles del salón de la fama, uno por modo en el orden de {@link Mode} (T41;
 *                   vacío en un plano anterior)
 * @param famaRotacion rotación (0-15) de esos carteles de pie
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

	/** El del .jar (heraldia/arena.json). */
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
