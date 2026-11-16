package io.github.albertosa23.heraldia.arena;

import io.github.albertosa23.heraldia.comando.Textos;
import java.util.ArrayList;
import java.util.List;
import java.util.Optional;
import net.minecraft.ChatFormatting;
import net.minecraft.core.BlockPos;
import net.minecraft.network.chat.Component;
import net.minecraft.resources.Identifier;
import net.minecraft.server.MinecraftServer;
import net.minecraft.server.level.ServerLevel;
import net.minecraft.server.level.ServerPlayer;
import net.minecraft.world.entity.Entity;
import net.minecraft.world.entity.ExperienceOrb;
import net.minecraft.world.entity.Mob;
import net.minecraft.world.entity.item.ItemEntity;
import net.minecraft.world.entity.player.Player;
import net.minecraft.world.level.block.Block;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.chunk.LevelChunk;
import net.minecraft.world.level.levelgen.Heightmap;
import net.minecraft.world.level.levelgen.structure.BoundingBox;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructurePlaceSettings;
import net.minecraft.world.level.levelgen.structure.templatesystem.StructureTemplate;
import net.minecraft.world.phys.AABB;
import org.jspecify.annotations.Nullable;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Obras de la arena: colocarla, quitarla o moverla (quitar la vieja y colocar la nueva), repartido en ticks para no
 * parar el servidor: cada tick trabaja un solo chunk (unos miles de bloques). Fases:
 * <ol>
 * <li>cargar (y generar, si hace falta) los chunks de la nueva y su anillo de vecinos;</li>
 * <li>quitar (la vieja): su caja queda como terreno llano (piedra, tierra y hierba hasta el suelo, aire encima);</li>
 * <li>nivelar (la nueva y {@link Sitio#MARGEN} bloques alrededor): aire sobre la caja hasta lo más alto del terreno y,
 * en el margen, relleno de tierra hasta el suelo;</li>
 * <li>plantilla: la plantilla del chunk ({@code StructurePlaceSettings.setBoundingBox}), con sus formas al día.</li>
 * </ol>
 * Al acabar, los objetos sueltos de la caja se quitan y las demás entidades van a la reaparición (no se quedan dentro
 * de un muro), y la arena se guarda en el mundo y empieza a protegerse. Una obra a la vez.
 */
final class Obras {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/**
	 * Sin avisar a los vecinos (nada de física en cadena) ni cambiar sus formas: con las formas, una planta del terreno
	 * que pierde su otra mitad o su suelo se rompe y suelta su objeto (la actualización de forma de los vecinos no
	 * respeta UPDATE_SUPPRESS_DROPS). La plantilla pone bien las formas de sus propios bloques.
	 */
	private static final int FLAGS = Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE | Block.UPDATE_SUPPRESS_DROPS;

	private enum Fase { CARGAR, QUITAR, NIVELAR, PLANTILLA }

	private record Paso(Fase fase, int cx, int cz) {
	}

	private record Obra(ServerLevel level, @Nullable Zona vieja, @Nullable Zona nueva, @Nullable ServerPlayer quien,
			List<Paso> pasos, StructureTemplate plantilla) {
	}

	private static @Nullable Obra actual;
	private static int indice, ticks;
	private static long nanos;

	private Obras() {
	}

	static boolean ocupado() {
		return actual != null;
	}

	/** Empieza una obra (quitar {@code vieja}, colocar {@code nueva}, o las dos). Falso si falta la plantilla. */
	static boolean empezar(ServerLevel level, @Nullable Zona vieja, @Nullable Zona nueva, @Nullable ServerPlayer quien) {
		Identifier id = Identifier.parse(Arena.plano().plantilla());
		Optional<StructureTemplate> t = level.getStructureTemplateManager().get(id);
		if (t.isEmpty()) {
			LOGGER.error("Heraldia: arena: falta la plantilla {}", id);
			return false;
		}
		List<Paso> pasos = new ArrayList<>();
		if (vieja != null) {
			chunks(pasos, Fase.QUITAR, vieja, 0);
		}
		if (nueva != null) {
			// antes, los chunks de alrededor ya generados: la decoración de un chunk que se genera después escribe en
			// sus vecinos (manchas de flores sobre el suelo de la arena, que saltan como objetos)
			chunks(pasos, Fase.CARGAR, nueva, Sitio.MARGEN + 16);
			chunks(pasos, Fase.NIVELAR, nueva, Sitio.MARGEN);
			chunks(pasos, Fase.PLANTILLA, nueva, 0);
		}
		actual = new Obra(level, vieja, nueva, quien, pasos, t.get());
		indice = ticks = 0;
		nanos = 0;
		Arena.fijarZona(null);           // mientras dura la obra no hay arena (ni protección ni partidas)
		return true;
	}

	private static void chunks(List<Paso> pasos, Fase fase, Zona z, int m) {
		for (int cx = (z.minX() - m) >> 4; cx <= (z.maxX() + m) >> 4; cx++) {
			for (int cz = (z.minZ() - m) >> 4; cz <= (z.maxZ() + m) >> 4; cz++) {
				pasos.add(new Paso(fase, cx, cz));
			}
		}
	}

	static void tick(MinecraftServer server) {
		Obra o = actual;
		if (o == null) {
			return;
		}
		long t0 = System.nanoTime();
		ticks++;
		if (indice < o.pasos().size()) {
			Paso p = o.pasos().get(indice++);
			LevelChunk chunk = o.level().getChunk(p.cx(), p.cz());
			switch (p.fase()) {
				case CARGAR -> {
				}
				case QUITAR -> quitar(o.level(), chunk, o.vieja());
				case NIVELAR -> nivelar(o.level(), chunk, o.nueva());
				case PLANTILLA -> plantilla(o.level(), p, o.nueva(), o.plantilla());
			}
			nanos += System.nanoTime() - t0;
			return;
		}
		actual = null;
		terminar(o);
		nanos += System.nanoTime() - t0;
		LOGGER.info("Heraldia: arena: obra terminada en {} ticks ({} ms en el hilo del servidor, como mucho un chunk por tick)",
				ticks, nanos / 1_000_000);
	}

	private static void quitar(ServerLevel level, LevelChunk chunk, Zona z) {
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		BlockState piedra = Blocks.STONE.defaultBlockState(), tierra = Blocks.DIRT.defaultBlockState(),
				hierba = Blocks.GRASS_BLOCK.defaultBlockState(), aire = Blocks.AIR.defaultBlockState();
		int suelo = z.sueloY();
		for (int x = Math.max(z.minX(), chunk.getPos().getMinBlockX()); x <= Math.min(z.maxX(), chunk.getPos().getMaxBlockX()); x++) {
			for (int zz = Math.max(z.minZ(), chunk.getPos().getMinBlockZ()); zz <= Math.min(z.maxZ(), chunk.getPos().getMaxBlockZ()); zz++) {
				for (int y = z.minY(); y <= z.maxY(); y++) {
					BlockState s = y > suelo ? aire : y == suelo ? hierba : y >= suelo - 2 ? tierra : piedra;
					level.setBlock(pos.set(x, y, zz), s, FLAGS);
				}
			}
		}
	}

	private static void nivelar(ServerLevel level, LevelChunk chunk, Zona z) {
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		BlockState aire = Blocks.AIR.defaultBlockState(), tierra = Blocks.DIRT.defaultBlockState(),
				hierba = Blocks.GRASS_BLOCK.defaultBlockState();
		int m = Sitio.MARGEN, suelo = z.sueloY();
		for (int x = Math.max(z.minX() - m, chunk.getPos().getMinBlockX()); x <= Math.min(z.maxX() + m, chunk.getPos().getMaxBlockX()); x++) {
			for (int zz = Math.max(z.minZ() - m, chunk.getPos().getMinBlockZ()); zz <= Math.min(z.maxZ() + m, chunk.getPos().getMaxBlockZ()); zz++) {
				boolean dentro = x >= z.minX() && x <= z.maxX() && zz >= z.minZ() && zz <= z.maxZ();
				int top = chunk.getHeight(Heightmap.Types.WORLD_SURFACE, x & 15, zz & 15);
				for (int y = (dentro ? z.maxY() : suelo) + 1; y <= top + 1; y++) {
					if (!level.getBlockState(pos.set(x, y, zz)).isAir()) {
						level.setBlock(pos, aire, FLAGS);
					}
				}
				if (!dentro) {
					for (int y = suelo; y > suelo - 16; y--) {
						BlockState s = level.getBlockState(pos.set(x, y, zz));
						if (!s.isAir() && s.getFluidState().isEmpty() && !s.canBeReplaced()) {
							break;
						}
						level.setBlock(pos, y == suelo ? hierba : tierra, FLAGS);
					}
				}
			}
		}
	}

	private static void plantilla(ServerLevel level, Paso p, Zona z, StructureTemplate t) {
		BoundingBox bb = new BoundingBox(Math.max(z.minX(), p.cx() << 4), z.minY(), Math.max(z.minZ(), p.cz() << 4),
				Math.min(z.maxX(), (p.cx() << 4) + 15), z.maxY(), Math.min(z.maxZ(), (p.cz() << 4) + 15));
		BlockPos origen = new BlockPos(z.ox(), z.oy(), z.oz());
		t.placeInWorld(level, origen, origen, new StructurePlaceSettings().setBoundingBox(bb).setIgnoreEntities(true),
				level.getRandom(), FLAGS);
	}

	private static void terminar(Obra o) {
		Zona z = o.nueva();
		if (z == null) {
			Arena.guardar(o.level(), null);
			LOGGER.info("Heraldia: arena: quitada de {} {} {}", o.vieja().columnaX(), o.vieja().sueloY(), o.vieja().columnaZ());
			avisar(o, Textos.t("heraldia.arena.quitada").withStyle(ChatFormatting.GOLD));
			return;
		}
		AABB caja = new AABB(z.minX(), z.minY(), z.minZ(), z.maxX() + 1, z.maxY() + 1, z.maxZ() + 1);
		int[] r = z.reaparicion();
		// lo que soltaron las plantas del margen al quedarse sin suelo (las formas de los vecinos no respetan SUPPRESS_DROPS)
		for (Entity e : o.level().getEntities((Entity) null, caja.inflate(Sitio.MARGEN + 4, 16, Sitio.MARGEN + 4),
				e -> e instanceof ItemEntity || e instanceof ExperienceOrb)) {
			e.discard();
		}
		for (Entity e : o.level().getEntities((Entity) null, caja, e -> !(e instanceof Player))) {
			if (e instanceof ItemEntity || e instanceof ExperienceOrb || (e instanceof Mob m && !m.isPersistenceRequired())) {
				e.discard();
			} else {
				e.teleportTo(r[0] + 0.5, r[1], r[2] + 0.5);
			}
		}
		for (ServerPlayer p : o.level().players()) {
			if (z.contiene(p.getBlockX(), p.getBlockY(), p.getBlockZ())) {
				p.teleportTo(r[0] + 0.5, r[1], r[2] + 0.5);
			}
		}
		Arena.guardar(o.level(), z);
		LOGGER.info("Heraldia: arena: colocada en {} {} {} (caja {} {} {} a {} {} {})", z.columnaX(), z.sueloY(), z.columnaZ(),
				z.minX(), z.minY(), z.minZ(), z.maxX(), z.maxY(), z.maxZ());
		avisar(o, Textos.t("heraldia.arena.colocada", z.columnaX(), z.sueloY() + 1, z.columnaZ()).withStyle(ChatFormatting.GOLD));
	}

	private static void avisar(Obra o, Component c) {
		if (o.quien() != null && !o.quien().hasDisconnected()) {
			o.quien().sendSystemMessage(c);
		}
	}
}
