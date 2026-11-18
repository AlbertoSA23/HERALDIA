package io.github.albertosa23.heraldia.maps;

/**
 * A marker ready for any web map: stable id (unique within its layer), layer, position, name and description already
 * translated (plain text) and the HTML of its popup (name in bold and description, escaped).
 */
public record MapMarker(String id, Layer layer, int x, int y, int z, String name, String description) {
	/** HTML of the marker's popup: "&lt;b&gt;name&lt;/b&gt;&lt;br&gt;description". */
	public String html() {
		return "<b>" + escape(name) + "</b><br>" + escape(description);
	}

	/** Escapes HTML special characters. */
	public static String escape(String s) {
		StringBuilder b = new StringBuilder(s.length() + 8);
		for (int i = 0; i < s.length(); i++) {
			char c = s.charAt(i);
			switch (c) {
				case '<' -> b.append("&lt;");
				case '>' -> b.append("&gt;");
				case '&' -> b.append("&amp;");
				case '"' -> b.append("&quot;");
				case '\'' -> b.append("&#39;");
				default -> b.append(c);
			}
		}
		return b.toString();
	}
}
