# Castle (`heraldia:unicas/castillo`)

A 100 x 100 block medieval fortress in plains, sunflower plains and meadows, one every 3,000-5,000 blocks
(configurable grid, `spacing` 250 / `separation` 190 chunks). A single variant, designed by hand.
Code: `tools/gen/uniques/castle/` (uses the shared pieces in `tools/gen/uniques/_common/`) · Plans by level: [`castillo/planos.md`](castillo/planos.md) · Renders: `castillo/*.png`.

## Terrain adaptation
- Two rigid templates: the castle (x, z 0..99, y 0..27; terrain at y=5, feet at y=6) and the dungeon (48 x 56 x 16)
  under the keep, joined by a vertical jigsaw in the spiral staircase's pier (`down_south` / `up_south`, aligned).
- `start_height` -6 with projection to `WORLD_SURFACE_WG`: the template's y=5 layer matches the surface, and the moat and
  foundations (y 0..4) are buried. `beard_thin` centers its core on the base of each piece: at the surface the castle
  only sinks the edge by 1 block at most, and the dungeon (ceiling 6 blocks below the courtyard, 13 high) does not reach the surface.
- The whole footprint of the castle below the surface and the whole box of the dungeon have explicit blocks: whatever the
  adapter digs out inside the box is refilled by the template. The courtyard and the banks have explicit air up to 3-4 blocks.
- Not verified in real generation: the cavities the adapter may open around the dungeon (outside its box).

## Floor plans
**Exterior and curtain wall.** A grass bank (ring 0-3) with stone riprap, a water moat 6 wide and 3 deep,
a curtain wall 3 thick with a wall-walk at y=17 and battlements. Four round towers at the corners (ground floor with a door to the courtyard,
wall-walk floor with doors to both stretches of wall, a crenellated terrace, ladders) and two bastions halfway along the wall
east and west, which the wall-walk passes through. Stone stairs from the courtyard to the wall-walk along the west and east walls.
**Barbican (south).** A drawbridge lowered over the moat (one plank missing), an arch with a raised portcullis hanging from chains
of the windlass in the upper room, a guardroom and a storeroom on either side of the passage, the windlass room with beds and a roof terrace; two
drum towers flank the entrance.
**Parade ground.** A path from the gate to the keep, a covered well in the center, stables with five stalls
(west), a smithy with a forge, anvil and trough (east), a chapel with pews, altar and stained glass (northeast), a garden with a ditch next
to the kitchen (northwest), a tiltyard with targets and quintains (southwest), street lamps.
**Keep** (40 x 32, walls 3 thick, four turrets): ground floor with a double-height great hall (long table,
high table under the gallery, fireplace, main staircase to the gallery), kitchen, pantry and cellar to the west, armory and barracks
to the east. Upper floor: study, library and antechamber to the west; the lord's bedchamber and solar to the east, joined by the gallery.
A slab spiral staircase (3 x 3) in an enclosed shaft from the dungeon (y=-13) to the roof terrace (y=22), with exits to the hall,
the antechamber and the roof terrace.
**Dungeon** (feet at y=-13): a guardroom at the foot of the spiral; to the east, a corridor with eight cells (iron doors
open); to the west, the crypt; to the north, the cistern with pools, a bridge and an island; to the northeast, the false treasury; to the south,
the arrow-slit corridor and the guardian's hall (vault 7 high, pillars, throne); behind it, the treasure chamber.

## Player route
Bridge → barbican (guardroom, storeroom, windlass room, roof terrace) → courtyard (stables, smithy, chapel, well, garden, tiltyard,
towers and the complete wall-walk) → keep (hall, kitchen, pantry, cellar, armory, barracks; stairs to the gallery and to
the upper floor) → spiral → dungeon: guardroom → cells → passage to the false treasury → cistern → crypt → guardroom
(closed circuit) → arrow-slit corridor → guardian's hall → riddle → treasure chamber.
The audit checks it all with the secret rooms open: every reached cell has a way back, and every chest, barrel,
workstation, lever, spawner, door (from both sides) and ladder is next to a reachable cell.
With the mechanisms closed, the secret cabinet, the treasure chamber and the niche cannot be reached.

## Puzzles, traps, spawners and guardian
- **Secret door of the study** (upper floor): in the northwest corner, a lever on the floor; when flipped, two bookshelves of the
  west wall retract into the corner (extended sticky pistons powered by a torch; the lever turns it off). Behind, a
  passage inside the thickness of the west wall (arrow slits and torches) leads to the **secret cabinet** in the southwest turret.
- **Riddle of the three levers** (guardian's hall): three levers under green, red and black banners; the castle's banners
  are red. The red one turns off the torch of an identical secret door in the northeast corner and opens the treasure chamber;
  the green and the black ones each fire three arrow dispensers at whoever pulls them.
- **Arrow-slit corridor**: a tripwire with six dispensers (jungle temple).
- **False treasury**: a chest on a dais and a pressure plate in front of it with five TNT under the floor (desert temple).
- **Hidden niche**: behind cracked bricks at the back of the second south cell (it has to be mined).
- **Spawners**: zombie (a cell with its bars torn out), skeleton (crypt), spider (the cistern's island).
- **Guardian**: Sir Aldric, the Cursed Castellan (a zombie with a translatable name, 60 health, 5 attack, 0.4 knockback
  resistance, iron helmet and leggings, chainmail chestplate and boots, iron sword; `PersistenceRequired`).
- Everything at rest is stable: torches lit, pistons extended with their head, levers and dust off.
- No villagers or golems: the castle is abandoned and taken over by the undead.

## Loot (`heraldia:unicas/castillo/<table>`, vanilla only; each table with an extra `solo_sin_lootr` pool)
| Table | Where | Contents |
|---|---|---|
| `menor` | gate storeroom, towers, bastions, barracks, false treasury | food and basic materials |
| `cocina` | kitchen, pantry, cellar, storeroom | cooked food and provisions |
| `armeria` | guardroom, windlass room, towers, armory, tiltyard | arrows, iron, worn weapons and armor |
| `herreria` | smithy | iron, coal, tools, a chipped anvil |
| `establo` | stables | wheat, leads, a saddle, leather or iron horse armor |
| `capilla` | chapel | candles, paper, lapis lazuli, books |
| `aposentos` | study, library, bedchamber | gold, emeralds, clock, compass, enchanted book (5-15) |
| `mazmorra` | guardroom, cells, crypt, cistern, false treasury | bones, nuggets, chains, some iron and gold |
| `oculto` | bottom of the well, secret cabinet, niche, treasure chamber | gold, emeralds, a rare diamond, book (10-20), pearls |
| `premium` | treasure chamber | see below |

**Premium**: 3-4 showy items (the Castellan's Sword, the Helm of the Guard, the Huntsman's Bow with enchantments 10-25;
the Heraldia Shield; the Chamber Key; sentry, wild, coast and host trims; discs 13, cat, mall and strad; gold,
emeralds, bottles o' enchanting, gold horse armor) and a jewel: 90 % showy (the Lord's Crown, the Tower Clock, the Lookout's
Spyglass, a name tag, the Pigstep disc, golden apples) and 10 % strong (enchanted apple, Aldric's Blade or a diamond chestplate 20-30,
3-5 diamonds, a level 30 book). No netherite or elytra.

## Ruin (83 % in good condition)
The northeast tower has lost its top (no terrace, upper floor caved in at the center, vines, rubble inside and at its foot), the
north parapet next to it has no battlements, the stables' roof has caved in with cobwebs and a fallen beam, a broken stained-glass window in the chapel,
a plank missing on the bridge, cobwebs in the cellar and the dungeon; and a processor that adds moss (15 %) and cracks (10 %) to the
stone bricks and moss (20 %) to the cobblestone. `audit.ruin_share` estimates 17 % of the visible surface in poor condition.

## Against the owner's criteria
Complete staircases without jumps (half-height slabs in the spiral, block stairs with their fill); no door without an
exit or inaccessible room (audited); furniture against the walls and tables with chairs facing outwards; lanterns hanging
from the ceiling or a chain; water always contained (moat, well, ditch, pools); symmetry in the curtain wall, barbican and
keep; every element with a function (portcullis with a windlass, forge with a chimney, trough, ditch).

## Checks
- Generation: `lint.py` (supports, jigsaws) and `audit.py` (walk, hidden rooms, redstone at rest, nothing floating).
- `smoke_redstone.py`: on a 26.3 dedicated server it places the templates with `/place template`, forces updates next to
  torches and pistons, and checks closed doors, opening and closing the study, the green lever (fires, does not open), the red one
  (opens, does not fire), tripwire, the TNT plate, the guardian (name, equipment, 60 health) and chests.
- Pending screenshots from the owner's game: look, lighting and terrain adaptation in real generation.
