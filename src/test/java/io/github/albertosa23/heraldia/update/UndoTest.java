package io.github.albertosa23.heraldia.update;

import static org.junit.jupiter.api.Assertions.assertArrayEquals;
import static org.junit.jupiter.api.Assertions.assertEquals;
import static org.junit.jupiter.api.Assertions.assertFalse;
import static org.junit.jupiter.api.Assertions.assertTrue;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.List;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;

/**
 * Undo of /heraldia update apply (T45, final audit, found by tools/smoke/update_path_b.py): the files that apply creates in
 * the plan's regions (for example the POI file of a region where a placed structure brings beds) are deleted, the backed
 * up ones are put back as they were, and nothing outside region/entities/poi or with another name is ever deleted.
 */
class UndoTest {
	@Test
	void undoRestoresTheCopyAndDeletesWhatApplyCreated(@TempDir Path tmp) throws IOException {
		Path ow = tmp.resolve("world"), dir = tmp.resolve("heraldia");
		Files.createDirectories(ow.resolve("region"));
		Files.createDirectories(ow.resolve("poi"));
		byte[] before = {1, 2, 3};
		Files.write(ow.resolve("region").resolve("r.0.0.mca"), before);
		Plan p = new Plan();
		p.id = "abc123";
		p.backup = true;
		p.place.add(new Plan.Placement("heraldia:medianas/x", 1, 1, new int[]{16, 60, 16, 40, 70, 40}));
		Path backup = dir.resolve("copia-" + p.id);
		assertEquals(1, Execution.copy(p, ow, backup));
		p.backupFolder = backup.toString();
		assertEquals(List.of("entities/r.0.0.mca", "poi/r.0.0.mca"), p.absent);
		// apply: changes the region and creates the entities and POI files
		Files.write(ow.resolve("region").resolve("r.0.0.mca"), new byte[]{9});
		Files.createDirectories(ow.resolve("entities"));
		Files.write(ow.resolve("entities").resolve("r.0.0.mca"), new byte[]{7});
		Files.write(ow.resolve("poi").resolve("r.0.0.mca"), new byte[]{8});
		Files.write(ow.resolve("poi").resolve("r.5.5.mca"), new byte[]{6});   // not in the plan: untouched
		// a tampered plan cannot make undo delete anything else
		p.absent.add("../level.dat");
		p.absent.add("region/level.dat");
		Files.write(tmp.resolve("level.dat"), new byte[]{5});
		Files.createDirectories(dir);
		Files.writeString(dir.resolve("deshacer.json"), "{}");
		Execution.restore(Plan.read(save(p, dir)).orElseThrow(), dir, ow);
		assertArrayEquals(before, Files.readAllBytes(ow.resolve("region").resolve("r.0.0.mca")));
		assertFalse(Files.exists(ow.resolve("entities").resolve("r.0.0.mca")));
		assertFalse(Files.exists(ow.resolve("poi").resolve("r.0.0.mca")));
		assertTrue(Files.exists(ow.resolve("poi").resolve("r.5.5.mca")));
		assertTrue(Files.exists(tmp.resolve("level.dat")));
		assertTrue(Files.exists(dir.resolve("deshecho-abc123.json")));
	}

	@Test
	void aPlanFromBeforeTheFieldReadsWithNothingToDelete(@TempDir Path tmp) throws IOException {
		Path f = tmp.resolve("hecho.json");
		Files.writeString(f, "{\"id\":\"old\",\"copia\":true}");
		assertEquals(List.of(), Plan.read(f).orElseThrow().absent);
	}

	private static Path save(Plan p, Path dir) throws IOException {
		Path f = dir.resolve("plan-test.json");
		p.save(f);
		return f;
	}
}
