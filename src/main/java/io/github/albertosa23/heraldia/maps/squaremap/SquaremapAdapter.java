package io.github.albertosa23.heraldia.maps.squaremap;

import io.github.albertosa23.heraldia.maps.Layer;
import io.github.albertosa23.heraldia.maps.Icons;
import io.github.albertosa23.heraldia.maps.WebMap;
import io.github.albertosa23.heraldia.maps.WebMaps;
import io.github.albertosa23.heraldia.maps.MapMarker;
import java.util.EnumMap;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Optional;
import xyz.jpenilla.squaremap.api.Key;
import xyz.jpenilla.squaremap.api.MapWorld;
import xyz.jpenilla.squaremap.api.Point;
import xyz.jpenilla.squaremap.api.SimpleLayerProvider;
import xyz.jpenilla.squaremap.api.Squaremap;
import xyz.jpenilla.squaremap.api.SquaremapProvider;
import xyz.jpenilla.squaremap.api.WorldIdentifier;
import xyz.jpenilla.squaremap.api.marker.Marker;
import xyz.jpenilla.squaremap.api.marker.MarkerOptions;

/**
 * squaremap (API 1.x): one layer (SimpleLayerProvider) per structure kind in the Overworld, with icons registered in
 * its icon registry. Only loaded if squaremap is there (WebMaps.ADAPTERS). Its layers are thread-safe
 * (ConcurrentHashMap) and squaremap writes them to its web output by itself every few seconds.
 */
public final class SquaremapAdapter implements WebMap {
	private static final WorldIdentifier OVERWORLD = WorldIdentifier.create("minecraft", "overworld");
	private final Map<Layer, SimpleLayerProvider> layers = new EnumMap<>(Layer.class);
	private boolean icons;

	public SquaremapAdapter(WebMaps.Context ctx) {
	}

	@Override
	public String name() {
		return "squaremap";
	}

	private static Key icon(Layer c) {
		return Key.of(c.mapId());
	}

	@Override
	public synchronized boolean publish(Map<Layer, String> names, Map<Layer, List<MapMarker>> byLayer) {
		Squaremap api;
		try {
			api = SquaremapProvider.get();
		} catch (IllegalStateException e) {
			return false;           // squaremap has not started yet
		}
		Optional<MapWorld> w = api.getWorldIfEnabled(OVERWORLD);
		if (w.isEmpty()) {
			return true;            // the Overworld has no map: nothing to do
		}
		if (!icons) {
			for (Layer c : Layer.values()) {
				if (!api.iconRegistry().hasEntry(icon(c))) {
					api.iconRegistry().register(icon(c), Icons.image(c));
				}
			}
			icons = true;
		}
		MapWorld world = w.get();
		for (Layer c : Layer.values()) {
			Key k = Key.of(c.mapId());
			List<MapMarker> list = byLayer.get(c);
			if (list == null) {
				if (world.layerRegistry().hasEntry(k)) {
					world.layerRegistry().unregister(k);
				}
				layers.remove(c);
				continue;
			}
			SimpleLayerProvider layer = layers.get(c);
			if (layer == null || !names.get(c).equals(layer.getLabel()) || !world.layerRegistry().hasEntry(k)) {
				if (world.layerRegistry().hasEntry(k)) {
					world.layerRegistry().unregister(k);
				}
				layer = SimpleLayerProvider.builder(names.get(c)).showControls(true).defaultHidden(false)
						.layerPriority(10 + c.ordinal()).zIndex(250 + c.ordinal()).build();
				world.layerRegistry().register(k, layer);
				layers.put(c, layer);
			}
			Map<Key, Marker> fresh = new HashMap<>();
			for (MapMarker m : list) {
				fresh.put(Key.of(key(m.id())), Marker.icon(Point.of(m.x() + 0.5, m.z() + 0.5), icon(c), Icons.SIDE)
						.markerOptions(MarkerOptions.builder().hoverTooltip(MapMarker.escape(m.name())).clickTooltip(m.html()).build()));
			}
			for (Key oldValue : List.copyOf(layer.registeredMarkers().keySet())) {
				if (!fresh.containsKey(oldValue)) {
					layer.removeMarker(oldValue);
				}
			}
			fresh.forEach(layer::addMarker);
		}
		return true;
	}

	/** squaremap keys only allow [a-z0-9._-]. */
	static String key(String id) {
		return "heraldia_" + id.toLowerCase(java.util.Locale.ROOT).replaceAll("[^a-z0-9._-]", "_");
	}
}
