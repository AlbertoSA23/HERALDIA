package io.github.albertosa23.heraldia.maps;

/**
 * Un marcador listo para cualquier mapa web: id estable (único en su capa), capa, posición, nombre y descripción ya
 * traducidos (texto plano) y el HTML de su ventana (nombre en negrita y descripción, escapados).
 */
public record MapMarker(String id, Layer layer, int x, int y, int z, String name, String description) {
	/** HTML de la ventana del marcador: «&lt;b&gt;nombre&lt;/b&gt;&lt;br&gt;descripción». */
	public String html() {
		return "<b>" + escape(name) + "</b><br>" + escape(description);
	}

	/** Escapa los caracteres especiales de HTML. */
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
