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
 */
public record Plano(String plantilla, int[] tamano, int suelo, int[] centro, int radio, int[] ruedoY, List<int[]> puntos,
		int[] campana, int[][] puerta, int[] reaparicion, int jefes) {

	public static Plano leer(Reader r) {
		JsonObject o = JsonParser.parseReader(r).getAsJsonObject();
		List<int[]> puntos = new ArrayList<>();
		for (JsonElement e : o.getAsJsonArray("puntos")) {
			puntos.add(ints(e.getAsJsonArray()));
		}
		JsonArray puerta = o.getAsJsonArray("puerta");
		return new Plano(o.get("plantilla").getAsString(), ints(o.getAsJsonArray("tamano")), o.get("suelo").getAsInt(),
				ints(o.getAsJsonArray("centro")), o.get("radio_ruedo").getAsInt(), ints(o.getAsJsonArray("ruedo_y")),
				List.copyOf(puntos), ints(o.getAsJsonArray("campana")),
				new int[][] {ints(puerta.get(0).getAsJsonArray()), ints(puerta.get(1).getAsJsonArray())},
				ints(o.getAsJsonArray("reaparicion")), o.has("jefes") ? o.get("jefes").getAsInt() : 1);
	}

	/** El del .jar (heraldia/arena.json). */
	public static Plano delJar() {
		String path = "/heraldia/arena.json";
		try (InputStream in = Plano.class.getResourceAsStream(path)) {
			if (in == null) {
				throw new IllegalStateException("Falta " + path + " en el .jar de Heraldia");
			}
			return leer(new InputStreamReader(in, StandardCharsets.UTF_8));
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
