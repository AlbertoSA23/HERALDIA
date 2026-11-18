package io.github.albertosa23.heraldia.arena;

import io.github.albertosa23.heraldia.command.Texts;
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
 * <li>nivelar (la nueva y {@link Site#MARGIN} bloques alrededor): aire sobre la caja hasta lo más alto del terreno y,
 * en el margen, relleno de tierra hasta el suelo;</li>
 * <li>plantilla: la plantilla del chunk ({@code StructurePlaceSettings.setBoundingBox}), con sus formas al día.</li>
 * </ol>
 * Al acabar, los objetos sueltos de la caja se quitan y las demás entidades van a la reaparición (no se quedan dentro
 * de un muro), y la arena se guarda en el mundo y empieza a protegerse. Una obra a la vez.
 */
final class Works {
	private static final Logger LOGGER = LoggerFactory.getLogger("heraldia");
	/**
	 * Sin avisar a los vecinos (nada de física en cadena) ni cambiar sus formas: con las formas, una planta del terreno
	 * que pierde su otra mitad o su suelo se rompe y suelta su objeto (la actualización de forma de los vecinos no
	 * respeta UPDATE_SUPPRESS_DROPS). La plantilla pone bien las formas de sus propios bloques.
	 */
	private static final int FLAGS = Block.UPDATE_CLIENTS | Block.UPDATE_KNOWN_SHAPE | Block.UPDATE_SUPPRESS_DROPS;

	private enum Phase { LOAD, CLEAR, LEVEL, TEMPLATE }

	private record Step(Phase phase, int cx, int cz) {
	}

	private record Work(ServerLevel level, @Nullable Zone old, @Nullable Zone fresh, @Nullable ServerPlayer who,
			List<Step> steps, StructureTemplate template) {
	}

	private static @Nullable Work actual;
	private static int index, ticks;
	private static long nanos;

	private Works() {
	}

	static boolean occupied() {
		return actual != null;
	}

	/** Empieza una obra (quitar {@code old}, colocar {@code fresh}, o las dos). Falso si falta la plantilla. */
	static boolean start(ServerLevel level, @Nullable Zone old, @Nullable Zone fresh, @Nullable ServerPlayer who) {
		Identifier id = Identifier.parse(Arena.plan().template());
		Optional<StructureTemplate> t = level.getStructureTemplateManager().get(id);
		if (t.isEmpty()) {
			LOGGER.error("Heraldia: arena: falta la plantilla {}", id);
			return false;
		}
		List<Step> steps = new ArrayList<>();
		if (old != null) {
			chunks(steps, Phase.CLEAR, old, 0);
		}
		if (fresh != null) {
			// antes, los chunks de alrededor ya generados: la decoración de un chunk que se genera después escribe en
			// sus vecinos (manchas de flores sobre el suelo de la arena, que saltan como objetos)
			chunks(steps, Phase.LOAD, fresh, Site.MARGIN + 16);
			chunks(steps, Phase.LEVEL, fresh, Site.MARGIN);
			chunks(steps, Phase.TEMPLATE, fresh, 0);
		}
		actual = new Work(level, old, fresh, who, steps, t.get());
		index = ticks = 0;
		nanos = 0;
		Arena.setZone(null);           // mientras dura la obra no hay arena (ni protección ni partidas)
		return true;
	}

	private static void chunks(List<Step> steps, Phase phase, Zone z, int m) {
		for (int cx = (z.minX() - m) >> 4; cx <= (z.maxX() + m) >> 4; cx++) {
			for (int cz = (z.minZ() - m) >> 4; cz <= (z.maxZ() + m) >> 4; cz++) {
				steps.add(new Step(phase, cx, cz));
			}
		}
	}

	static void tick(MinecraftServer server) {
		Work o = actual;
		if (o == null) {
			return;
		}
		long t0 = System.nanoTime();
		ticks++;
		if (index < o.steps().size()) {
			Step p = o.steps().get(index++);
			LevelChunk chunk = o.level().getChunk(p.cx(), p.cz());
			switch (p.phase()) {
				case LOAD -> {
				}
				case CLEAR -> clear(o.level(), chunk, o.old());
				case LEVEL -> levelGround(o.level(), chunk, o.fresh());
				case TEMPLATE -> template(o.level(), p, o.fresh(), o.template());
			}
			nanos += System.nanoTime() - t0;
			return;
		}
		actual = null;
		finish(o);
		nanos += System.nanoTime() - t0;
		LOGGER.info("Heraldia: arena: obra terminada en {} ticks ({} ms en el hilo del servidor, como mucho un chunk por tick)",
				ticks, nanos / 1_000_000);
	}

	private static void clear(ServerLevel level, LevelChunk chunk, Zone z) {
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		BlockState stone = Blocks.STONE.defaultBlockState(), land = Blocks.DIRT.defaultBlockState(),
				grass = Blocks.GRASS_BLOCK.defaultBlockState(), air = Blocks.AIR.defaultBlockState();
		int ground = z.groundY();
		for (int x = Math.max(z.minX(), chunk.getPos().getMinBlockX()); x <= Math.min(z.maxX(), chunk.getPos().getMaxBlockX()); x++) {
			for (int zz = Math.max(z.minZ(), chunk.getPos().getMinBlockZ()); zz <= Math.min(z.maxZ(), chunk.getPos().getMaxBlockZ()); zz++) {
				for (int y = z.minY(); y <= z.maxY(); y++) {
					BlockState s = y > ground ? air : y == ground ? grass : y >= ground - 2 ? land : stone;
					level.setBlock(pos.set(x, y, zz), s, FLAGS);
				}
			}
		}
	}

	private static void levelGround(ServerLevel level, LevelChunk chunk, Zone z) {
		BlockPos.MutableBlockPos pos = new BlockPos.MutableBlockPos();
		BlockState air = Blocks.AIR.defaultBlockState(), land = Blocks.DIRT.defaultBlockState(),
				grass = Blocks.GRASS_BLOCK.defaultBlockState();
		int m = Site.MARGIN, ground = z.groundY();
		for (int x = Math.max(z.minX() - m, chunk.getPos().getMinBlockX()); x <= Math.min(z.maxX() + m, chunk.getPos().getMaxBlockX()); x++) {
			for (int zz = Math.max(z.minZ() - m, chunk.getPos().getMinBlockZ()); zz <= Math.min(z.maxZ() + m, chunk.getPos().getMaxBlockZ()); zz++) {
				boolean inside = x >= z.minX() && x <= z.maxX() && zz >= z.minZ() && zz <= z.maxZ();
				int top = chunk.getHeight(Heightmap.Types.WORLD_SURFACE, x & 15, zz & 15);
				for (int y = (inside ? z.maxY() : ground) + 1; y <= top + 1; y++) {
					if (!level.getBlockState(pos.set(x, y, zz)).isAir()) {
						level.setBlock(pos, air, FLAGS);
					}
				}
				if (!inside) {
					for (int y = ground; y > ground - 16; y--) {
						BlockState s = level.getBlockState(pos.set(x, y, zz));
						if (!s.isAir() && s.getFluidState().isEmpty() && !s.canBeReplaced()) {
							break;
						}
						level.setBlock(pos, y == ground ? grass : land, FLAGS);
					}
				}
			}
		}
	}

	private static void template(ServerLevel level, Step p, Zone z, StructureTemplate t) {
		BoundingBox bb = new BoundingBox(Math.max(z.minX(), p.cx() << 4), z.minY(), Math.max(z.minZ(), p.cz() << 4),
				Math.min(z.maxX(), (p.cx() << 4) + 15), z.maxY(), Math.min(z.maxZ(), (p.cz() << 4) + 15));
		BlockPos origin = new BlockPos(z.ox(), z.oy(), z.oz());
		t.placeInWorld(level, origin, origin, new StructurePlaceSettings().setBoundingBox(bb).setIgnoreEntities(true),
				level.getRandom(), FLAGS);
	}

	private static void finish(Work o) {
		Zone z = o.fresh();
		if (z == null) {
			Arena.save(o.level(), null);
			LOGGER.info("Heraldia: arena: quitada de {} {} {}", o.old().columnX(), o.old().groundY(), o.old().columnZ());
			warn(o, Texts.t("heraldia.arena.quitada").withStyle(ChatFormatting.GOLD));
			return;
		}
		AABB box = new AABB(z.minX(), z.minY(), z.minZ(), z.maxX() + 1, z.maxY() + 1, z.maxZ() + 1);
		int[] r = z.respawn();
		// lo que soltaron las plantas del margen al quedarse sin suelo (las formas de los vecinos no respetan SUPPRESS_DROPS)
		for (Entity e : o.level().getEntities((Entity) null, box.inflate(Site.MARGIN + 4, 16, Site.MARGIN + 4),
				e -> e instanceof ItemEntity || e instanceof ExperienceOrb)) {
			e.discard();
		}
		for (Entity e : o.level().getEntities((Entity) null, box, e -> !(e instanceof Player))) {
			if (e instanceof ItemEntity || e instanceof ExperienceOrb || (e instanceof Mob m && !m.isPersistenceRequired())) {
				e.discard();
			} else {
				e.teleportTo(r[0] + 0.5, r[1], r[2] + 0.5);
			}
		}
		for (ServerPlayer p : o.level().players()) {
			if (z.mentions(p.getBlockX(), p.getBlockY(), p.getBlockZ())) {
				p.teleportTo(r[0] + 0.5, r[1], r[2] + 0.5);
			}
		}
		Arena.save(o.level(), z);
		LOGGER.info("Heraldia: arena: colocada en {} {} {} (caja {} {} {} a {} {} {})", z.columnX(), z.groundY(), z.columnZ(),
				z.minX(), z.minY(), z.minZ(), z.maxX(), z.maxY(), z.maxZ());
		warn(o, Texts.t("heraldia.arena.colocada", z.columnX(), z.groundY() + 1, z.columnZ()).withStyle(ChatFormatting.GOLD));
	}

	private static void warn(Work o, Component c) {
		if (o.who() != null && !o.who().hasDisconnected()) {
			o.who().sendSystemMessage(c);
		}
	}
}
