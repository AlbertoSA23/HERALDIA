package io.github.albertosa23.heraldia.client;

import com.terraformersmc.modmenu.api.ConfigScreenFactory;
import com.terraformersmc.modmenu.api.ModMenuApi;
import net.fabricmc.api.EnvType;
import net.fabricmc.api.Environment;

/** Botón de configuración en la lista de Mod Menu. Si Mod Menu no está, Fabric no carga esta clase. */
@Environment(EnvType.CLIENT)
public final class ModMenuIntegration implements ModMenuApi {
	@Override
	public ConfigScreenFactory<?> getModConfigScreenFactory() {
		return ConfigScreen::new;
	}
}
