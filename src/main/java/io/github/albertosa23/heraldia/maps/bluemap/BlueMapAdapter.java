package io.github.albertosa23.heraldia.maps.bluemap;

import de.bluecolored.bluemap.api.AssetStorage;
import de.bluecolored.bluemap.api.BlueMapAPI;
import de.bluecolored.bluemap.api.BlueMapMap;
import de.bluecolored.bluemap.api.BlueMapWorld;
import de.bluecolored.bluemap.api.markers.MarkerSet;
import de.bluecolored.bluemap.api.markers.POIMarker;
import io.github.albertosa23.heraldia.maps.Layer;
import io.github.albertosa23.heraldia.maps.Icons;
import io.github.albertosa23.heraldia.maps.WebMap;
import io.github.albertosa23.heraldia.maps.WebMaps;
import io.github.albertosa23.heraldia.maps.MapMarker;
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
public final class BlueMapAdapter implements WebMap {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	private final WebMaps.Context ctx;
	private volatile @Nullable BlueMapAPI api;
	private volatile @Nullable Map<Layer, String> layers;
	private volatile @Nullable Map<Layer, List<MapMarker>> markers;
	private final Consumer<BlueMapAPI> onEnable = this::enable;
	private final Consumer<BlueMapAPI> onDisable = a -> api = null;

	public BlueMapAdapter(WebMaps.Context ctx) {
		this.ctx = ctx;
		BlueMapAPI.onEnable(onEnable);
		BlueMapAPI.onDisable(onDisable);
	}

	@Override
	public String name() {
		return "BlueMap";
	}

	private void enable(BlueMapAPI a) {
		api = a;
		Map<Layer, String> c = layers;
		Map<Layer, List<MapMarker>> m = markers;
		if (c != null && m != null) {
			apply(a, c, m);
		}
	}

	@Override
	public boolean publish(Map<Layer, String> names, Map<Layer, List<MapMarker>> byLayer) {
		layers = names;
		markers = byLayer;
		BlueMapAPI a = api;
		if (a == null) {
			return false;
		}
		apply(a, names, byLayer);
		return true;
	}

	private void apply(BlueMapAPI a, Map<Layer, String> names, Map<Layer, List<MapMarker>> byLayer) {
		Optional<BlueMapWorld> w = a.getWorld(ctx.overworld());
		if (w.isEmpty()) {
			return;
		}
		for (BlueMapMap map : w.get().getMaps()) {
			Map<Layer, String> icons = icons(map);
			for (Layer layer : Layer.values()) {
				List<MapMarker> list = byLayer.get(layer);
				if (list == null) {
					map.getMarkerSets().remove(layer.mapId());
					continue;
				}
				MarkerSet set = map.getMarkerSets().computeIfAbsent(layer.mapId(), k -> MarkerSet.builder()
						.label(names.get(layer)).toggleable(true).defaultHidden(false).sorting(layer.ordinal()).build());
				set.setLabel(names.get(layer));
				Map<String, POIMarker> fresh = new HashMap<>();
				for (MapMarker m : list) {
					POIMarker.Builder b = POIMarker.builder().label(m.name()).position(m.x() + 0.5, m.y(), m.z() + 0.5).detail(m.html());
					String icon = icons.get(layer);
					fresh.put(m.id(), (icon != null ? b.icon(icon, Icons.SIDE / 2, Icons.SIDE / 2) : b.defaultIcon()).build());
				}
				set.getMarkers().keySet().retainAll(fresh.keySet());
				set.getMarkers().putAll(fresh);
			}
		}
	}

	/** Escribe (una vez por mapa) los iconos en los recursos del mapa y devuelve su dirección. */
	private static Map<Layer, String> icons(BlueMapMap map) {
		Map<Layer, String> out = new EnumMap<>(Layer.class);
		AssetStorage st = map.getAssetStorage();
		for (Layer c : Layer.values()) {
			String name = "heraldia/" + c.id() + ".png";
			try {
				if (!st.assetExists(name)) {
					try (OutputStream o = st.writeAsset(name)) {
						o.write(Icons.png(c));
					}
				}
				out.put(c, st.getAssetUrl(name));
			} catch (IOException e) {
				LOGGER.warn("Heraldia: mapas web: BlueMap: no se pudo escribir el icono {}: {}", name, e.getMessage());
			}
		}
		return out;
	}

	@Override
	public void close() {
		BlueMapAPI.unregisterListener(onEnable);
		BlueMapAPI.unregisterListener(onDisable);
	}
}
