# What runs on the server thread while players are connected

Audit of 21-11-2026. The owner's criterion is that nothing should hold the server thread for more than
100 ms, because a held thread is felt by everyone connected, not only by whoever caused it. This document
records what was looked at, what was measured, what was only read in the code, and what is still unmeasured.

It exists because the measurements were taken in an ephemeral container: without this file they would survive
only as figures in a conversation, and nobody could tell them from guesses six months from now.

## The conclusion in one sentence

**The only place in the mod where the server thread genuinely waits is `/locate` of a Heraldia structure.**

Everything else that looked like a candidate either does not wait, or waits on another thread. That list is
worth as much as the finding, because it says where not to look again:

| place | verdict | how it was established |
| --- | --- | --- |
| `AtlantisAnchor.get` → `future.join()` | waits, but on a **generation worker**: 913 / 307 / 798 ms in three new worlds, once each, no tick warnings | probe logging the thread name |
| the same, in an existing world whose `atlantida.json` was deleted | the search runs again (2,572 ms on its own `heraldia-atlantida` thread) and **nobody waits for it at all** | probe; zero hits |
| `arena/Structures.occupied` → `scanChunk(...).join()` | `Worker-Main-2`, 0-16 ms, **never** the server thread | probe, 8 hits, with the town and arena switched on |
| `treasure/Search.confirm` | guarded by `level.getServer().isSameThread()`: inline when already on the thread, and the off-thread path capped at 10 s | code, every call site |
| `common/SearchCaches` → `jar.join()` | inside a background `supplyAsync` | code |
| `command/InfoCommand.near` (`/heraldia info nearby`) | the expensive part on `Util.backgroundExecutor()`, back on the thread only for already-loaded chunks | code (its on-thread cost is **not** measured here) |
| the web maps' and `/heraldia status` file reads | all three callers of `StatusCommand.readFiles` are on `Util.ioPool()` or the maps' own min-priority thread (`Heraldia mapas web`) | code, every call site |
| the journal (`/heraldia journal`) | **writes no files at all**: it reads advancement progress already in memory | code |
| the nine `END_SERVER_TICK` handlers | every one exits on a field check or a tick modulo before doing work | code, all nine |
| the four `CHUNK_LOAD` handlers | `VillageEvents`, `ClearedSpawners`, `WebMaps`, `Welcome`; each exits early on an empty collection | code |
| `HeightCache` locks | 64 bands; the critical section is one hashmap operation and the height computation runs **outside** the lock | code |
| `UnwrittenRegions` lock | set operations only; its one `Files.isRegularFile` per region runs outside the lock | code |
| the builds' blocking `level.getChunk` (town, grounds, roads, arena) | all capped at one step or one chunk per tick; measured in brand-new worlds: slowest step 71-75 ms (town), 17-21 ms (roads), 6-10 ms (grounds) | measured, three new worlds |

File I/O that *can* land on the server thread, all of it operator-triggered and none of it per-tick:
`HeraldiaConfig.save` from the config panel, and the plan and report writes of the `/heraldia update` command.

## `/locate`: one frozen tick, not a slow stretch

From (8000, −8000) in a brand-new world, with a player connected, a window of per-tick durations open around
the command:

| case | the game reports | **worst tick** | 2nd worst | waits logged on `[Server thread]` |
| --- | --- | --- | --- | --- |
| mines, new world, first time | 1,243 ms | **1,258.7 ms** | 32.9 ms | ~70, of 3 to 44 ms |
| mines, repeated in the same session | 8 ms | 17.8 ms | 16.6 ms | 0 |
| mines, after a restart | 342 ms | **355.9 ms** | 17.5 ms | 3: 10, **124**, **133** ms |
| villages, first time | 524 ms | **533.1 ms** | 20.7 ms | 0 |
| mediums, first time | 40 ms | 48.8 ms | 28.2 ms | 0 |

What makes it a freeze rather than a slowdown is the second worst tick: **32.9 ms**. The server does not run
badly for a second; a single tick eats 1,258.7 ms and the rest are fine. That is 25 ticks' worth of server
time gone in one block, for everyone connected, because one player typed a command.

**The clock-versus-CPU signature appears here and nowhere else**: 6,479 ms of tick clock against 5,639 ms of
the thread's own CPU in that window, so roughly 840 ms of that tick the thread was not executing anything.
It was waiting, cell by cell, in `ParallelLocate.await` — which the probe logs by name:

```
Heraldia: PROBE locate await 124 ms on thread [Server thread]
Heraldia: PROBE locate await 133 ms on thread [Server thread]
```

The work itself does parallelise: the profile shows `ladera_anticipada` at 1,724 ms of CPU across the pool for
a command that lasted 1.2 s of clock. What does not parallelise is the waiting, because vanilla's
`getStructureGeneratingAt` asks for each cell from the server thread. The parallelism cut the clock from about
5 s to 1.2 s without moving the wait out of the tick.

### Why it cannot simply be made asynchronous

Two obstacles, both already recorded in `LESSONS.md`:

1. **`StructureCheck` is not thread-safe** (it uses a `HashMap`). Moving the ring walk to another thread would
   have it touching the same object the server thread uses to generate: that is corruption, not slowness.
2. **The search may need to load chunks.** When `checkStart` returns `CHUNK_LOAD_NEEDED` — a positive
   prediction in an ungenerated chunk — vanilla calls `level.getChunk(..., STRUCTURE_STARTS)` to confirm it,
   and loading or generating a chunk has to happen on the server thread.

### What would work, and what it costs

Slicing the ring walk across ticks. Each cell is cheap (3-44 ms); the damage is that ~70 of them run
back-to-back inside one tick. N cells per tick turns 1,243 ms into about 25 ticks of 50 ms, all of it still on
the server thread, so neither obstacle above appears. It is the "one step per tick" shape that
`herald/Building` and `herald/Outskirts` already use, and the player would get the answer a second later
without noticing — which changes *who* pays: today the ten people playing, instead of the one who typed it.

Not implemented, because the price is real and is the owner's to weigh:

- It breaks the command's synchronous contract. `/locate` returns an int to Brigadier, so answering later means
  returning something before knowing it: `/execute if ... run locate ...` and datapack functions break.
- It is a mixin on vanilla's `getNearestGeneratedStructure`, the most invasive kind this project allows.
- `ParallelLocate` keeps the ring in a `ThreadLocal` that assumes one synchronous walk; that piece would be
  rebuilt.
- The world changes between ticks, so a sliced search could answer slightly differently from the synchronous
  one. Probably irrelevant, but not identical by construction.

The zero-code alternative: `/heraldia info nearby` already answers the same question off the thread. What the
mod lacks is not the machinery but players typing it instead of `/locate`.

## Exploring: measured for the first time

No test in the project measured this before (see `LESSONS.md`): every scenario in
`tools/smoke/runtime_cost.py` pre-generates with Chunky, places its players and lets the server settle before
sampling. Measured here off to the side, a spectator moved in a straight line over terrain nobody had touched,
with and without the mod, same seed, same route:

| | no mod | with mod | difference |
| --- | --- | --- | --- |
| **5.6 blocks/s (a sprinting player), 792 blocks** | | | |
| median / p95 / p99 | 3.61 / 8.86 / 12.86 ms | 3.78 / 10.08 / 16.00 ms | +0.17 / **+1.22** / **+3.14** |
| worst tick | 66.9 ms | 55.2 ms | — |
| **ticks over 100 ms** | **0** | **0** | — |
| tick clock over the window | 10,930 ms | 11,853 ms | **+8.4 %** |
| **22 blocks/s (creative flight), 3,113 blocks** | | | |
| median / p95 / p99 | 4.98 / 11.47 / 20.2 ms | 5.38 / 13.04 / 23.91 ms | +0.40 / **+1.57** / **+3.71** |
| worst tick | **507.7 ms** | **483.0 ms** | — |
| **ticks over 100 ms** | **2** | **4** | +2 |
| tick clock over the window | 15,124 ms | 16,678 ms | **+10.3 %** |

At a sprinting player's speed nothing breaks, with or without the mod, and the mod's cost is small and bounded.
At flying speed **ticks of half a second appear in both passes**: that is the game's own chunk delivery falling
behind a player who claims terrain faster than it generates, not the mod. The mod adds two more, in the
120-130 ms band.

GC does not explain them, and this was checked before the claim was made: in the no-mod pass the largest GC
pause of the whole window was **90 ms** against a worst tick of **507 ms**.

Standing in the finished town, for comparison (default config, a funeral event running, ~30 villagers):
median 10.57 ms, p95 15.6, p99 21.1, worst 61.2, **zero ticks over 100 ms**, and **CPU over tick clock of
0.985** — 98.5 % of the time inside ticks the thread was executing, not waiting.

## Method, and what it does not cover

- Per-tick durations read from the server's own JMX bean **from outside the game**, so the figures mean the
  same with and without the mod. The server thread's own CPU time and the cumulative GC time come from the
  same connection, 4 times a second.
- Thread names come from a temporary probe that was reverted in the same script; nothing of it is committed.
- **One pass per case**, on a **4-core** container where the mod itself logs that it would prefer its light
  profile. The worst single ticks are therefore noise; the medians, the p95s and the clock totals hold. Fixing
  a threshold on the worst ticks would need three passes per case.
- The exploring player is a **moved spectator, not a walking player**. That understates entity and collision
  cost; it does not understate generation cost, which was the thing nobody had measured. The route was
  verified against the entity's own final position (792 and 3,113 blocks), not assumed — an earlier attempt
  with a Carpet player walking moved it 16 blocks in 140 s and would otherwise have been reported as
  exploration.
- `/heraldia info nearby`'s on-thread cost is **not measured here**.

## A correctness reservation about the Atlantis anchor

`data/heraldia/atlantida.json` is a **cache, not the source of truth**: deleted from an existing world and
searched again, it returned the same chunk (block −2496, −192). Losing it does not move the city, and
restarting without it costs nothing on the server thread.

**That is not a licence to delete it.** `AtlantisAnchor.search` penalises candidate basins whose footprint is
already **explored** (it checks whether the region files exist). The test world had only its spawn generated,
2,500 blocks from the chosen basin, so exploration changed nothing. **In a long-played world, deleting the
file could legitimately move Atlantis** — which is exactly what the file's own javadoc says it exists to
prevent: "so it does not change even if the biomes or the explored area change". It is harmless today in a
young world and it is not harmless in general, and the explored-world case was **not** measured.

## The lessons

These outlive the figures and are kept in `LESSONS.md`:

- **A criterion about the maximum cannot be watched with a percentile.** The p99 of the flying pass was 23.9 ms,
  spotless, while four ticks of up to 483 ms happened: with 2,400 ticks, p99 discards the worst 24 by
  construction.
- **The instrument is not missing; the wiring is.** `runtime_cost.py` computes the worst tick and the count of
  slow ticks, combines them correctly across passes, prints them in three places — and `compare()` never reads
  them. The four limits in `runtime_reference.json` are two percentiles and two ratios.
- **A probe that does not fire is not a probe that found nothing.** The `Structures.occupied` probe came back
  empty because the measurement's own config had switched off the only things that call it.
- **Clock far above CPU is the signature of a wait**; clock equal to CPU means the thread is working, however
  slow it looks. Without both numbers, a busy tick and a blocked tick are indistinguishable.
- **An acceptance pattern must not contain the words of the failure.**
