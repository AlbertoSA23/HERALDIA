package io.github.albertosa23.heraldia.mapas.dynmap;

import io.github.albertosa23.heraldia.mapas.Capa;
import io.github.albertosa23.heraldia.mapas.Iconos;
import io.github.albertosa23.heraldia.mapas.MapaWeb;
import io.github.albertosa23.heraldia.mapas.MapasWeb;
import io.github.albertosa23.heraldia.mapas.Marcador;
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
 * Dynmap (DynmapCoreAPI 3.x): un conjunto de marcadores (no persistente: se rehace al arrancar) por capa, con iconos
 * propios, en el mundo del Overworld (Dynmap lo nombra con el nombre del nivel). Solo se carga si Dynmap está
 * (MapasWeb.ADAPTADORES). La API de marcadores de Dynmap no es segura entre hilos: todo se aplica en el hilo del servidor
 * (unas decenas o centenares de marcadores, al descubrir algo).
 */
public final class DynmapAdaptador extends DynmapCommonAPIListener implements MapaWeb {
	private final MapasWeb.Contexto ctx;
	private volatile @Nullable MarkerAPI markers;
	private volatile @Nullable Map<Capa, String> capas;
	private volatile @Nullable Map<Capa, List<Marcador>> marcadores;

	public DynmapAdaptador(MapasWeb.Contexto ctx) {
		this.ctx = ctx;
		DynmapCommonAPIListener.register(this);
	}

	@Override
	public String nombre() {
		return "Dynmap";
	}

	@Override
	public void apiEnabled(DynmapCommonAPI api) {
		markers = api.getMarkerAPI();
		Map<Capa, String> c = capas;
		Map<Capa, List<Marcador>> m = marcadores;
		if (c != null && m != null) {
			ctx.hiloServidor().execute(() -> aplicar(c, m));
		}
	}

	@Override
	public boolean publicar(Map<Capa, String> nombres, Map<Capa, List<Marcador>> porCapa) {
		capas = nombres;
		marcadores = porCapa;
		if (markers == null) {
			return false;
		}
		ctx.hiloServidor().execute(() -> aplicar(nombres, porCapa));
		return true;
	}

	private void aplicar(Map<Capa, String> nombres, Map<Capa, List<Marcador>> porCapa) {
		MarkerAPI api = markers;
		if (api == null) {
			return;
		}
		for (Capa c : Capa.values()) {
			MarkerSet set = api.getMarkerSet(c.idMapa());
			List<Marcador> lista = porCapa.get(c);
			if (lista == null) {
				if (set != null) {
					set.deleteMarkerSet();
				}
				continue;
			}
			if (set == null) {
				set = api.createMarkerSet(c.idMapa(), nombres.get(c), null, false);
				if (set == null) {
					continue;
				}
			}
			set.setMarkerSetLabel(nombres.get(c));
			set.setHideByDefault(false);
			set.setLayerPriority(10 + c.ordinal());
			MarkerIcon icono = api.getMarkerIcon(c.idMapa());
			if (icono == null) {
				icono = api.createMarkerIcon(c.idMapa(), nombres.get(c), new ByteArrayInputStream(Iconos.png(c)));
			}
			Set<String> nuevos = new HashSet<>();
			for (Marcador m : lista) {
				String id = clave(m.id());
				nuevos.add(id);
				Marker viejo = set.findMarker(id);
				if (viejo != null) {
					viejo.deleteMarker();
				}
				Marker mk = set.createMarker(id, m.nombre(), false, ctx.nombreNivel(), m.x() + 0.5, m.y(), m.z() + 0.5, icono, false);
				if (mk != null) {
					mk.setDescription(m.html());
				}
			}
			for (Marker mk : List.copyOf(set.getMarkers())) {
				if (!nuevos.contains(mk.getMarkerID())) {
					mk.deleteMarker();
				}
			}
		}
	}

	static String clave(String id) {
		return "heraldia_" + id.replaceAll("[^A-Za-z0-9_]", "_");
	}

	@Override
	public void cerrar() {
		DynmapCommonAPIListener.unregister(this);
	}
}
