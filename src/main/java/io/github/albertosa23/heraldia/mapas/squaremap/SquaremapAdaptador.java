package io.github.albertosa23.heraldia.mapas.squaremap;

import io.github.albertosa23.heraldia.mapas.Capa;
import io.github.albertosa23.heraldia.mapas.Iconos;
import io.github.albertosa23.heraldia.mapas.MapaWeb;
import io.github.albertosa23.heraldia.mapas.MapasWeb;
import io.github.albertosa23.heraldia.mapas.Marcador;
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
 * squaremap (API 1.x): una capa (SimpleLayerProvider) por clase de estructura en el Overworld, con iconos registrados en
 * su registro de iconos. Solo se carga si squaremap está (MapasWeb.ADAPTADORES). Sus capas son seguras entre hilos
 * (ConcurrentHashMap) y squaremap las escribe solo en su web cada pocos segundos.
 */
public final class SquaremapAdaptador implements MapaWeb {
	private static final WorldIdentifier OVERWORLD = WorldIdentifier.create("minecraft", "overworld");
	private final Map<Capa, SimpleLayerProvider> capas = new EnumMap<>(Capa.class);
	private boolean iconos;

	public SquaremapAdaptador(MapasWeb.Contexto ctx) {
	}

	@Override
	public String nombre() {
		return "squaremap";
	}

	private static Key icono(Capa c) {
		return Key.of(c.idMapa());
	}

	@Override
	public synchronized boolean publicar(Map<Capa, String> nombres, Map<Capa, List<Marcador>> porCapa) {
		Squaremap api;
		try {
			api = SquaremapProvider.get();
		} catch (IllegalStateException e) {
			return false;           // squaremap aún no ha arrancado
		}
		Optional<MapWorld> w = api.getWorldIfEnabled(OVERWORLD);
		if (w.isEmpty()) {
			return true;            // el Overworld no tiene mapa: nada que hacer
		}
		if (!iconos) {
			for (Capa c : Capa.values()) {
				if (!api.iconRegistry().hasEntry(icono(c))) {
					api.iconRegistry().register(icono(c), Iconos.imagen(c));
				}
			}
			iconos = true;
		}
		MapWorld mundo = w.get();
		for (Capa c : Capa.values()) {
			Key k = Key.of(c.idMapa());
			List<Marcador> lista = porCapa.get(c);
			if (lista == null) {
				if (mundo.layerRegistry().hasEntry(k)) {
					mundo.layerRegistry().unregister(k);
				}
				capas.remove(c);
				continue;
			}
			SimpleLayerProvider capa = capas.get(c);
			if (capa == null || !nombres.get(c).equals(capa.getLabel()) || !mundo.layerRegistry().hasEntry(k)) {
				if (mundo.layerRegistry().hasEntry(k)) {
					mundo.layerRegistry().unregister(k);
				}
				capa = SimpleLayerProvider.builder(nombres.get(c)).showControls(true).defaultHidden(false)
						.layerPriority(10 + c.ordinal()).zIndex(250 + c.ordinal()).build();
				mundo.layerRegistry().register(k, capa);
				capas.put(c, capa);
			}
			Map<Key, Marker> nuevos = new HashMap<>();
			for (Marcador m : lista) {
				nuevos.put(Key.of(clave(m.id())), Marker.icon(Point.of(m.x() + 0.5, m.z() + 0.5), icono(c), Iconos.LADO)
						.markerOptions(MarkerOptions.builder().hoverTooltip(Marcador.escapar(m.nombre())).clickTooltip(m.html()).build()));
			}
			for (Key viejo : List.copyOf(capa.registeredMarkers().keySet())) {
				if (!nuevos.containsKey(viejo)) {
					capa.removeMarker(viejo);
				}
			}
			nuevos.forEach(capa::addMarker);
		}
		return true;
	}

	/** Las claves de squaremap solo admiten [a-z0-9._-]. */
	static String clave(String id) {
		return "heraldia_" + id.toLowerCase(java.util.Locale.ROOT).replaceAll("[^a-z0-9._-]", "_");
	}
}
