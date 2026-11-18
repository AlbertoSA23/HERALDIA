package io.github.albertosa23.heraldia.events;

import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertNotNull;
import static org.junit.jupiter.api.Assertions.assertTrue;

import io.github.albertosa23.heraldia.events.Layout.Figure;
import io.github.albertosa23.heraldia.events.Layout.Placed;
import io.github.albertosa23.heraldia.events.Layout.Plan;
import io.github.albertosa23.heraldia.events.Layout.Prop;
import io.github.albertosa23.heraldia.events.Layout.Role;
import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.ArrayList;
import java.util.HashMap;
import java.util.List;
import java.util.Map;
import java.util.Set;
import java.util.stream.Stream;
import net.minecraft.SharedConstants;
import net.minecraft.core.BlockPos;
import net.minecraft.core.Direction;
import net.minecraft.core.registries.BuiltInRegistries;
import net.minecraft.nbt.CompoundTag;
import net.minecraft.nbt.ListTag;
import net.minecraft.nbt.NbtAccounter;
import net.minecraft.nbt.NbtIo;
import net.minecraft.nbt.NbtOps;
import net.minecraft.nbt.Tag;
import net.minecraft.server.Bootstrap;
import net.minecraft.world.item.Item;
import net.minecraft.world.item.Items;
import net.minecraft.world.level.block.Blocks;
import net.minecraft.world.level.block.RotatedPillarBlock;
import net.minecraft.world.level.block.state.BlockState;
import net.minecraft.world.level.block.state.properties.BlockStateProperties;
import org.junit.jupiter.api.BeforeAll;
import org.junit.jupiter.api.Test;

/**
 * The village events against the game's own classes: what is saved survives a round trip, the rule that decides whether a
 * block is still ours, the blocks and figures are vanilla and safe to take down, and every kind fits the real square of
 * every style as the generator wrote it.
 */
class EventsGameTest {
	@BeforeAll
	static void bootstrap() {
		SharedConstants.tryDetectVersion();
		Bootstrap.bootStrap();
	}

	@Test
	void recordRoundTrip() {
		BlockState log = Blocks.STRIPPED_DARK_OAK_LOG.defaultBlockState().setValue(RotatedPillarBlock.AXIS, Direction.Axis.X);
		Record r = Record.EMPTY.with(List.of(new Record.Placed(new BlockPos(10, 64, -3).asLong(), log),
				new Record.Placed(new BlockPos(11, 65, -3).asLong(), Blocks.CARPET.black().defaultBlockState())))
				.ended("2,-84", 123456L, "funeral");
		Tag t = Record.CODEC.encodeStart(NbtOps.INSTANCE, r).getOrThrow();
		Record back = Record.CODEC.parse(NbtOps.INSTANCE, t).getOrThrow();
		assertEquals(r, back);
		assertEquals(Direction.Axis.X, back.placed().getFirst().state().getValue(RotatedPillarBlock.AXIS));
		assertEquals(new Record.Village(123456L, "funeral"), back.village("2,-84"));
		// removing what was taken down; nothing left of an empty record
		Record after = back.without(List.of(new BlockPos(10, 64, -3).asLong()));
		assertEquals(1, after.placed().size());
		assertTrue(Record.CODEC.parse(NbtOps.INSTANCE, new CompoundTag()).getOrThrow().isEmpty(), "a world without the attachment");
	}

	@Test
	void stillOursOnlyIfTheSameBlock() {
		BlockState camp = Blocks.CAMPFIRE.defaultBlockState();
		assertTrue(VillageEvents.same(camp, camp.setValue(BlockStateProperties.LIT, false)), "a campfire put out is still ours");
		assertTrue(VillageEvents.same(Blocks.LANTERN.defaultBlockState(), Blocks.LANTERN.defaultBlockState()
				.setValue(BlockStateProperties.WATERLOGGED, true)));
		BlockState z = Blocks.STRIPPED_DARK_OAK_LOG.defaultBlockState().setValue(RotatedPillarBlock.AXIS, Direction.Axis.Z);
		assertFalse(VillageEvents.same(z, z.setValue(RotatedPillarBlock.AXIS, Direction.Axis.X)), "turned: a player's log");
		assertFalse(VillageEvents.same(Blocks.WOOL.red().defaultBlockState(), Blocks.WOOL.white().defaultBlockState()));
		assertFalse(VillageEvents.same(Blocks.HAY_BLOCK.defaultBlockState(), Blocks.AIR.defaultBlockState()));
	}

	@Test
	void propsAreVanillaAndSafeToTakeDown() {
		for (Prop p : Prop.values()) {
			for (int v = 0; v < 4; v++) {
				for (boolean x : new boolean[] {false, true}) {
					BlockState s = VillageEvents.state(new Placed(p, v, 0, 1, 0, x));
					String id = BuiltInRegistries.BLOCK.getKey(s.getBlock()).toString();
					assertTrue(id.startsWith("minecraft:") && !s.isAir(), p + ": " + id);
					// nothing a player can store things in (taking it down would lose them), except the campfire's cooking
					assertTrue(!s.hasBlockEntity() || s.is(Blocks.CAMPFIRE), p + " has a block entity: " + id);
					// no state that follows its neighbours (a fence or a wall would change and then not be "ours" any more)
					assertFalse(s.hasProperty(BlockStateProperties.NORTH) || s.hasProperty(BlockStateProperties.EAST)
							|| s.hasProperty(BlockStateProperties.STAIRS_SHAPE), p + ": " + id);
				}
			}
		}
		assertEquals(Direction.Axis.X, VillageEvents.state(new Placed(Prop.BIER, 0, 0, 1, 0, true)).getValue(RotatedPillarBlock.AXIS));
	}

	@Test
	void figuresHaveVanillaGearAndModestTrades() {
		for (Role r : Role.values()) {
			for (int v = 0; v < 4; v++) {
				Figure f = new Figure(r, 3, 4, 0, 0, v);
				assertNotNull(VillageEvents.profession(f), r.name());
				Item held = VillageEvents.held(f, 0);
				assertTrue(held == null || held != Items.AIR, r.name());
				List<VillageEvents.Trade> t = VillageEvents.trades(f);
				assertEquals(r == Role.MERCHANT || r == Role.HOST, !t.isEmpty(), r + " trades");
				for (VillageEvents.Trade x : t) {
					assertTrue(x.count() >= 1 && x.count() <= 64 && x.amount() >= 1 && x.amount() <= 64 && x.uses() > 0, r + ": " + x);
					assertTrue(x.cost() == Items.EMERALD || x.result() == Items.EMERALD, "every trade is in emeralds: " + x);
					if (x.cost() == Items.EMERALD) {
						assertTrue(x.count() <= 3, "modest prices: " + x);
					}
				}
			}
		}
		assertTrue(VillageEvents.held(new Figure(Role.BRIDE, 0, 0, 0, 0, 0), 0) == Items.ALLIUM, "the bride holds flowers");
	}

	// --- the real square of every style ---

	/** Template blocks by "x,y,z" → block id. */
	static Map<String, String> blocks(Path f) throws IOException {
		CompoundTag t = NbtIo.readCompressed(f, NbtAccounter.unlimitedHeap());
		ListTag palette = t.getListOrEmpty("palette");
		Map<String, String> m = new HashMap<>();
		for (Tag b : t.getListOrEmpty("blocks")) {
			CompoundTag c = (CompoundTag) b;
			ListTag pos = c.getListOrEmpty("pos");
			CompoundTag entry = palette.getCompoundOrEmpty(c.getIntOr("state", 0));
			m.put(pos.getIntOr(0, 0) + "," + pos.getIntOr(1, 0) + "," + pos.getIntOr(2, 0), entry.getStringOr("id", entry.getStringOr("Name", "")));
		}
		return m;
	}

	static boolean empty(String id) {
		return id == null || id.equals("minecraft:air") || id.equals("minecraft:structure_void");
	}

	/** The square as generated, with the job board kept clear around its slot and the golems standing on theirs. */
	static Layout.Ground square(Map<String, String> b) {
		Set<String> golems = Set.of("3,8", "19,14", "14,3");
		return new Layout.Ground() {
			@Override
			public boolean air(int x, int y, int z) {
				return empty(b.get(x + "," + y + "," + z));
			}

			@Override
			public boolean floor(int x, int z) {
				String id = b.get(x + ",0," + z);
				return !empty(id) && !id.equals("minecraft:water");
			}

			@Override
			public boolean occupied(int x, int y, int z) {
				return golems.contains(x + "," + z) || (x == 1 && z == 1);     // the golems and the centre marker
			}

			@Override
			public boolean reserved(int x, int z) {
				return Math.abs(x - 14) <= 3 && Math.abs(z - 18) <= 3;         // the board slot (tools/gen/board.py SLOT) ± its box
			}
		};
	}

	@Test
	void everyKindFitsTheRealSquareOfEveryStyle() throws IOException {
		Path root = Path.of(System.getProperty("heraldia.generated"), "data/heraldia/structure");
		List<Path> files = new ArrayList<>();
		try (Stream<Path> s = Files.walk(root)) {
			s.filter(p -> p.toString().endsWith("/plaza/std.nbt") || p.toString().endsWith("/plaza/grande.nbt")).forEach(files::add);
		}
		assertTrue(files.size() >= 60, "squares found: " + files.size());
		List<String> bad = new ArrayList<>();
		Map<Kind, Integer> figures = new HashMap<>();
		for (Path f : files) {
			Map<String, String> b = blocks(f);
			Layout.Ground g = square(b);
			for (Kind k : Kind.values()) {
				for (int first = 0; first < 4; first++) {
					Plan p = Layout.plan(k, g, List.of(first, (first + 1) % 4, (first + 2) % 4, (first + 3) % 4));
					if (p == null || !VillageEvents.enough(k, p)) {
						bad.add(root.relativize(f) + ": no " + k.id + " from bay " + first);
						continue;
					}
					figures.merge(k, p.figures().size(), Math::min);
					for (Placed c : p.props()) {
						String at = b.get(c.x() + "," + c.y() + "," + c.z());
						if (!empty(at)) {
							bad.add(root.relativize(f) + ": " + k.id + " " + c.prop() + " on the template's " + at);
						}
					}
				}
			}
		}
		assertTrue(bad.isEmpty(), String.join("\n", bad));
		// even in the most crowded bay each event keeps most of its people (the square's benches and planters take a few)
		assertTrue(figures.get(Kind.WEDDING) >= 10 && figures.get(Kind.FUNERAL) >= 6 && figures.get(Kind.FESTIVAL) >= 7
				&& figures.get(Kind.MARKET) >= 5, figures.toString());
	}
}
