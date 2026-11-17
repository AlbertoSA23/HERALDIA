package io.github.albertosa23.heraldia.mapas;

import java.util.List;
import java.util.Map;

/**
 * Un mapa web (BlueMap, Dynmap o squaremap). Cada uno va en su propio paquete y solo se carga si su mod está
 * ({@link MapasWeb#ADAPTADORES}): esta interfaz y el resto del paquete no nombran ninguna clase de los mapas.
 */
public interface MapaWeb {
	/** Nombre para el log y el comando (p. ej. «BlueMap»). */
	String nombre();

	/**
	 * Sustituye los marcadores de Heraldia por estos: una capa por entrada (las que no estén, se quitan del mapa). Se llama
	 * desde el hilo de los mapas web; cada adaptador pasa al hilo que pida su API.
	 *
	 * @param capas      nombre traducido de cada capa
	 * @param marcadores los marcadores de cada capa activada (lista vacía: la capa sale sin marcadores)
	 * @return false si el mapa aún no está listo (su API no ha arrancado): se vuelve a intentar más tarde
	 */
	boolean publicar(Map<Capa, String> capas, Map<Capa, List<Marcador>> marcadores);

	/** Al parar el servidor. */
	default void cerrar() {
	}
}
