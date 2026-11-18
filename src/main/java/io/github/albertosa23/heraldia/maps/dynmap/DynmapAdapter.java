package io.github.albertosa23.heraldia.maps.dynmap;

import io.github.albertosa23.heraldia.maps.Layer;
import io.github.albertosa23.heraldia.maps.Icons;
import io.github.albertosa23.heraldia.maps.WebMap;
import io.github.albertosa23.heraldia.maps.WebMaps;
import io.github.albertosa23.heraldia.maps.MapMarker;
import java.io.ByteArrayInputStream;
import java.util.HashSet;
import java.util.List;
import java.util.Map;
import java.util.Set;
import org.dynmap.DynmapCommonAPI;
import org.dynmap.DynmapCommonAPIListener;
import org.dynmap.markers.Marker;
import org.dynmap.markers.MarkerAPI;
import org.dynmap.markers.MarkerIcon;
import org.dynmap.markers.MarkerSet;
import org.jspecify.annotations.Nullable;

/**
 * Dynmap (DynmapCoreAPI 3.x): one marker set (not persistent: rebuilt at startup) per layer, with own
 * icons, in the Overworld's world (Dynmap names it with the level name). Only loaded if Dynmap is there
 * (WebMaps.ADAPTERS). Dynmap's marker API is not thread-safe: everything is applied on the server thread
 * (a few dozen or hundred markers, when something is discovered).
 */
public final class DynmapAdapter extends DynmapCommonAPIListener implements WebMap {
	private final WebMaps.Context ctx;
	private volatile @Nullable MarkerAPI markers;
	private volatile @Nullable Map<Layer, String> layers;
	private volatile @Nullable Map<Layer, List<MapMarker>> ourMarkers;

	public DynmapAdapter(WebMaps.Context ctx) {
		this.ctx = ctx;
		DynmapCommonAPIListener.register(this);
	}

	@Override
	public String name() {
		return "Dynmap";
	}

	@Override
	public void apiEnabled(DynmapCommonAPI api) {
		markers = api.getMarkerAPI();
		Map<Layer, String> c = layers;
		Map<Layer, List<MapMarker>> m = ourMarkers;
		if (c != null && m != null) {
			ctx.serverThread().execute(() -> apply(c, m));
		}
	}

	@Override
	public boolean publish(Map<Layer, String> names, Map<Layer, List<MapMarker>> byLayer) {
		layers = names;
		ourMarkers = byLayer;
		if (markers == null) {
			return false;
		}
		ctx.serverThread().execute(() -> apply(names, byLayer));
		return true;
	}

	private void apply(Map<Layer, String> names, Map<Layer, List<MapMarker>> byLayer) {
		MarkerAPI api = markers;
		if (api == null) {
			return;
		}
		for (Layer c : Layer.values()) {
			MarkerSet set = api.getMarkerSet(c.mapId());
			List<MapMarker> list = byLayer.get(c);
			if (list == null) {
				if (set != null) {
					set.deleteMarkerSet();
				}
				continue;
			}
			if (set == null) {
				set = api.createMarkerSet(c.mapId(), names.get(c), null, false);
				if (set == null) {
					continue;
				}
			}
			set.setMarkerSetLabel(names.get(c));
			set.setHideByDefault(false);
			set.setLayerPriority(10 + c.ordinal());
			MarkerIcon icon = api.getMarkerIcon(c.mapId());
			if (icon == null) {
				icon = api.createMarkerIcon(c.mapId(), names.get(c), new ByteArrayInputStream(Icons.png(c)));
			}
			Set<String> fresh = new HashSet<>();
			for (MapMarker m : list) {
				String id = key(m.id());
				fresh.add(id);
				Marker oldValue = set.findMarker(id);
				if (oldValue != null) {
					oldValue.deleteMarker();
				}
				Marker mk = set.createMarker(id, m.name(), false, ctx.levelName(), m.x() + 0.5, m.y(), m.z() + 0.5, icon, false);
				if (mk != null) {
					mk.setDescription(m.html());
				}
			}
			for (Marker mk : List.copyOf(set.getMarkers())) {
				if (!fresh.contains(mk.getMarkerID())) {
					mk.deleteMarker();
				}
			}
		}
	}

	static String key(String id) {
		return "heraldia_" + id.replaceAll("[^A-Za-z0-9_]", "_");
	}

	@Override
	public void close() {
		DynmapCommonAPIListener.unregister(this);
	}
}
