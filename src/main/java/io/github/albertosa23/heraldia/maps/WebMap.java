package io.github.albertosa23.heraldia.maps;

import java.util.List;
import java.util.Map;

/**
 * A web map (BlueMap, Dynmap or squaremap). Each one lives in its own package and is only loaded if its mod is there
 * ({@link WebMaps#ADAPTERS}): this interface and the rest of the package name no map class.
 */
public interface WebMap {
	/** Name for the log and the command (e.g. "BlueMap"). */
	String name();

	/**
	 * Replaces Heraldia's markers with these: one layer per entry (those not present are removed from the map). Called
	 * from the web maps' thread; each adapter hops to the thread its API asks for.
	 *
	 * @param layers  translated name of each layer
	 * @param markers the markers of each enabled layer (empty list: the layer shows without markers)
	 * @return false if the map is not ready yet (its API has not started): it is retried later
	 */
	boolean publish(Map<Layer, String> layers, Map<Layer, List<MapMarker>> markers);

	/** When the server stops. */
	default void close() {
	}
}
