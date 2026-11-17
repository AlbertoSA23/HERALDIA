package io.github.albertosa23.heraldia.mapas.bluemap;

import de.bluecolored.bluemap.api.AssetStorage;
import de.bluecolored.bluemap.api.BlueMapAPI;
import de.bluecolored.bluemap.api.BlueMapMap;
import de.bluecolored.bluemap.api.BlueMapWorld;
import de.bluecolored.bluemap.api.markers.MarkerSet;
import de.bluecolored.bluemap.api.markers.POIMarker;
import io.github.albertosa23.heraldia.mapas.Capa;
import io.github.albertosa23.heraldia.mapas.Iconos;
import io.github.albertosa23.heraldia.mapas.MapaWeb;
import io.github.albertosa23.heraldia.mapas.MapasWeb;
import io.github.albertosa23.heraldia.mapas.Marcador;
import java.io.IOException;
import java.io.OutputStream;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import java.util.function.Consumer;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * BlueMap (API 2.x): un conjunto de marcadores por capa en cada mapa del Overworld, con marcadores de punto (POI) y el
 * icono de la capa guardado en los recursos del mapa. Solo se carga si BlueMap está (MapasWeb.ADAPTADORES). BlueMap
 * arranca su API aparte (puede ser después que el servidor): se publica al activarse y en cada actualización. Sus
 * conjuntos de marcadores son seguros entre hilos (ConcurrentHashMap).
 */
public final class BlueMapAdaptador implements MapaWeb {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private final MapasWeb.Contexto ctx;
	private volatile @Nullable BlueMapAPI api;
	private volatile @Nullable Map<Capa, String> capas;
	private volatile @Nullable Map<Capa, List<Marcador>> marcadores;
	private final Consumer<BlueMapAPI> alActivar = this::activar;
	private final Consumer<BlueMapAPI> alDesactivar = a -> api = null;

	public BlueMapAdaptador(MapasWeb.Contexto ctx) {
		this.ctx = ctx;
		BlueMapAPI.onEnable(alActivar);
		BlueMapAPI.onDisable(alDesactivar);
	}

	@Override
	public String nombre() {
		return "BlueMap";
	}

	private void activar(BlueMapAPI a) {
		api = a;
		Map<Capa, String> c = capas;
		Map<Capa, List<Marcador>> m = marcadores;
		if (c != null && m != null) {
			aplicar(a, c, m);
		}
	}

	@Override
	public boolean publicar(Map<Capa, String> nombres, Map<Capa, List<Marcador>> porCapa) {
		capas = nombres;
		marcadores = porCapa;
		BlueMapAPI a = api;
		if (a == null) {
			return false;
		}
		aplicar(a, nombres, porCapa);
		return true;
	}

	private void aplicar(BlueMapAPI a, Map<Capa, String> nombres, Map<Capa, List<Marcador>> porCapa) {
		Optional<BlueMapWorld> w = a.getWorld(ctx.overworld());
		if (w.isEmpty()) {
			return;
		}
		for (BlueMapMap map : w.get().getMaps()) {
			Map<Capa, String> iconos = iconos(map);
			for (Capa capa : Capa.values()) {
				List<Marcador> lista = porCapa.get(capa);
				if (lista == null) {
					map.getMarkerSets().remove(capa.idMapa());
					continue;
				}
				MarkerSet set = map.getMarkerSets().computeIfAbsent(capa.idMapa(), k -> MarkerSet.builder()
						.label(nombres.get(capa)).toggleable(true).defaultHidden(false).sorting(capa.ordinal()).build());
				set.setLabel(nombres.get(capa));
				Map<String, POIMarker> nuevos = new HashMap<>();
				for (Marcador m : lista) {
					POIMarker.Builder b = POIMarker.builder().label(m.nombre()).position(m.x() + 0.5, m.y(), m.z() + 0.5).detail(m.html());
					String icono = iconos.get(capa);
					nuevos.put(m.id(), (icono != null ? b.icon(icono, Iconos.LADO / 2, Iconos.LADO / 2) : b.defaultIcon()).build());
				}
				set.getMarkers().keySet().retainAll(nuevos.keySet());
				set.getMarkers().putAll(nuevos);
			}
		}
	}

	/** Escribe (una vez por mapa) los iconos en los recursos del mapa y devuelve su dirección. */
	private static Map<Capa, String> iconos(BlueMapMap map) {
		Map<Capa, String> out = new EnumMap<>(Capa.class);
		AssetStorage st = map.getAssetStorage();
		for (Capa c : Capa.values()) {
			String nombre = "heraldia/" + c.id() + ".png";
			try {
				if (!st.assetExists(nombre)) {
					try (OutputStream o = st.writeAsset(nombre)) {
						o.write(Iconos.png(c));
					}
				}
				out.put(c, st.getAssetUrl(nombre));
			} catch (IOException e) {
				LOGGER.warn("Heraldia: mapas web: BlueMap: no se pudo escribir el icono {}: {}", nombre, e.getMessage());
			}
		}
		return out;
	}

	@Override
	public void cerrar() {
		BlueMapAPI.unregisterListener(alActivar);
		BlueMapAPI.unregisterListener(alDesactivar);
	}
}
