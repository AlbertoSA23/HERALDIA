# Pyramid temple (`heraldia:unicas/piramide`)

A great stepped pyramid in Mesoamerican style in the jungle, with a central staircase, a temple at the top,
two side platforms and an attached ball court. Inside it spirals down through rooms to an inner cenote
and, at the deepest point, the tomb of the Jaguar King and the treasure chamber.

- Biomes: `minecraft:jungle` and `minecraft:sparse_jungle` (the bamboo jungle is left out: the bamboo would cover it).
- Rarity: the contract's (`spacing` 250 / `separation` 190 chunks, one every ~3,000-5,000 blocks).
- Size: a footprint of 79 × 70 blocks; 36 high above the ground and 27 of basement. Two jigsaw pieces (radius 80).

## How it differs from the vanilla ones

| | Jungle temple | Desert pyramid | Pyramid temple |
|---|---|---|---|
| Shape | a 3-story stone box | a smooth pyramid with 2 towers | 6 talud-tablero tiers with a projecting staircase, a temple with a roof comb, a ball court |
| Material | cobblestone and mossy cobblestone | sandstone | tuff (bricks, polished, chiseled), red terracotta stucco; a basement of stone brick, natural rock and deepslate |
| Inside | one corridor, 2 chests | one chamber with TNT | 6 levels, 13 chests, 4 spawners, a guardian, 3 hidden rooms |

## Pieces and terrain

- `superficie` (rigid, `beard_thin`): everything from y = 0 upwards. The square's paving is at
  y = 0, so the terrain is filled up to it. The whole volume of the footprint up to y = 20 (and up to the top
  above the pyramid) is explicitly air: a hill cannot go through the pyramid.
- `subsuelo` (rigid): from y = -1 to -27, hanging from the first with a vertical jigsaw (`down_north` → `up_north`,
  `aligned` joint, same rotation). It is a solid block of rock with the rooms carved into it: that piece's terrain
  adjustment acts 27 blocks deep (where the terrain's density is high) and does not sink the surface;
  whatever is around cannot open holes because every room is surrounded by the template's own rock.

## Floor plans by level (level = height of the feet)

**Exterior (level 1).** A tuff square with a causeway (sacbe) towards the staircase. Two 9 × 9 side platforms
(level 4) in front of the pyramid: the west one with the offering altar and a chest; the east one with a
*tzompantli* (a skull rack). Two stelae. To the east, the ball court: a 7-wide alley between two slopes
with a sloping bench, a wall and a stone ring on each side; at the top of the west slope, a small shrine with a
chest. The south end of the east slope has collapsed.

**Pyramid.** Six tiers 4 high (half-widths 24, 21, 18, 15, 12, 9) in talud-tablero: a stepped slope, a
molding, a recessed panel with reliefs and a cornice. A 9-wide staircase that projects 7 blocks, with balustrades
and serpent heads at the foot. Top at level 24.

**Temple at the top (level 24).** A portico with three openings and a sanctuary with an altar, an offering chest and the mouth of the
Staircase of the Inscriptions (an opening with a parapet). An openwork roof comb above the roof, broken at its east end.

**Staircase of the Inscriptions.** Flight A (3 wide) towards the north from level 24 to 12; a landing; central flight B
towards the south from level 12 to 1. From the landing branch off the Offering Chamber (west, chest) and the **Walled-up
Chamber** (east): its door is blocked with cobblestone and suspicious gravel; whoever opens it finds a hidden chest.

**Cenote Hall (level 1).** A 25 × 17 hall of columns in the heart of the pyramid. In the center, the mouth of the
shaft (an octagon of radius 4) with a parapet, which drops 15 blocks to the cenote's water. You can also get here through
the **West breach**: the wall at the base is burst open and a gallery leads to the hall; halfway along the gallery, a
tripwire fires two arrow dispensers. In the southeast corner the staircase goes down to the underground.

**Galleries of the underworld (level -6).** A U-shaped corridor around the shaft with three windows onto it. Exits:
- North: a corridor with a **pit trap**: three pressure plates open three iron trapdoors; the pit (3
  deep, no damage) has its own exit by a staircase to the corridor. At the back, the Chamber of Judgment (chest).
- West: a spider den (cave spider spawner, cobwebs, chest).
- East: an ossuary (skeleton spawner, bones, chest).
- Southwest: stairs to the cenote.

**Cenote (level -14).** A natural cavern of radius 9 with a vault, stalactites and roots; a pool of radius 6 and 5 deep
with sea pickles at the bottom; a walkable ledge around it. Under the water, to the east, a tunnel (the pickles
mark it) leads to the **Submerged Chamber**: a dry room with a hidden chest. North of the ledge the staircase goes down to the
tomb.

**Tomb (level -24).** The Hall of the Guardians (zombie spawner, statues, chest), a corridor of **dart plates**
(six plates over dispensers that fire upwards) and the King's Tomb: a sarcophagus, grave goods (chest) and the
**guardian "The Jaguar King"** (a zombie with a gold crown and pectoral and an iron sword; 40 health, 5 damage,
armor 4, no reinforcements and no equipment drop, `PersistenceRequired`). In the north wall, a blind niche: it is the
**secret door**. A lever hidden at floor level in a recess of the same wall turns off a redstone
torch; the two sticky pistons holding the door's blocks retract and open onto the
**Treasure Chamber** (premium chest).

## Player route

Square → platforms (2 chests) → ball court (1) → staircase → temple (1) → Staircase of the Inscriptions
→ Offering Chamber (1) and Walled-up Chamber (hidden, 1) → Cenote Hall (1). Alternative: the West breach with the
tripwire trap → Cenote Hall. Down to the galleries: the Chamber of Judgment behind the pit trap (1), spiders
(1), ossuary (1) → cenote: a dive to the Submerged Chamber (hidden, 1) → Hall of the Guardians (1) → dart plates →
Tomb (grave goods, 1; guardian) → lever → Treasure Chamber (premium). A shortcut for the brave: jump down the shaft from the
Cenote Hall (you land in 5 blocks of water).

## Redstone: why it works when generated

Every circuit is in a consistent rest state and nothing needs a block update when placed:
- Tripwire: hooks `attached=true` and string `attached=true` (like the jungle temple); the hook strongly powers
  its support block and the dispenser is stuck to that block.
- Pit: the plate strongly powers the block it rests on and that block touches the iron trapdoor; at rest nothing
  is powered.
- Darts: the plate is on top of the dispenser, which receives it directly.
- Secret door: the only circuit powered at rest. A lit torch, the block above strongly
  powered, the pistons extended with their sticky head and the door's blocks in front. The lever powers the
  torch's block → it turns off → the pistons retract pulling the door. Pulling the lever down closes it.

It is checked in the audit (states and adjacencies) and on a real server (`smoke_server.py`, which places the
templates and forces each circuit).

## Spawners and enemies

Cave spiders (den), skeletons (ossuary), zombies (Hall of the Guardians) and bogged (Chamber of Judgment),
all underground. A final guardian in the tomb. No villagers or golems: it is a sealed ruin.

## Condition (80-85 % in good condition)

The piece's processors: tuff brick and polished tuff → tuff (erosion), red terracotta → terracotta (washed stucco),
stone brick → mossy or cracked, deepslate → cracked. Hand-made gaps that make sense: the southeast corner of
tiers 4-6 slumped with rubble on the terrace below, the west base breach, the broken roof comb, the notched
east balustrade, the collapsed end of the ball court, vines and moss. The audit computes the fraction of
the outer surface that is intact (expected, with the processors' probabilities) and requires 0.80-0.85.

## Loot (vanilla only; the extra pool of each chest has `solo_sin_lootr`)

| Table | Where | Contents |
|---|---|---|
| `menor` | platforms, ball court, temple, offerings, hall | food, cocoa, arrows, candles, gold nuggets and ingots, a loose emerald |
| `galeria` | judgment, spiders, ossuary, guardians | the above plus iron, gold, lapis lazuli, bottle o' enchanting, a modest enchanted book |
| `oculto` | walled-up chamber, submerged chamber | gold, emeralds, a loose diamond, golden apple, pottery sherds, wild armor trim, enchanted book |
| `tumba` | the king's grave goods | gold, emeralds, enchanted gold gear, wild trim, disc |
| `premium` | treasure chamber | a base of gold, emeralds and experience; and a lot: 90 % showy (a named crown and scepter, moderate enchantments, armor trims, discs, sherds) or 10 % something stronger (a named diamond sword or pectoral with enchantments 20-30, an enchanted golden apple) |

No netherite gear, no elytra, no totems.

## Against the design criteria

- Complete staircases (the grand staircase, three inner flights and three basement staircases, all step by step);
  the only drop is the trap's pit, 3 blocks and with an exit.
- No door or room without an exit; the three hidden rooms have real access (breaking the wall, diving, a lever).
- Nothing floating: the audit requires every block to be joined to the ground; lanterns on chains; the water is enclosed
  on every side except from above.
- Symmetry in the pyramid, the temple, the platforms and the ball court; the collapses break the symmetry on
  purpose.

## Result and checks

- Audit (a condition for generating): 13 chests and 4 spawners reachable on foot from the square (10,854 cells),
  with the lever, the traps, the guardian and the three hidden rooms; without opening the secret door the treasure cannot be
  reached and without breaking the wall the walled-up chamber cannot either; from the bottom of the pit you can get back to the square; nothing
  floats; the water is enclosed; no block is powered except the door's torch. Outer surface
  in good condition: 0.825 (erosion of the brick and polished tuff computed for the middle of the range: 13.7 %).
- 26.3 dedicated server (`smoke_server.py`, templates unrotated): the guardian with 40 health; the door closed
  at rest, open when the torch's block is powered and closed again; the tripwire, the pit plates and the dart plates
  fire with an armor stand on top; the water does not leak; the premium chest has its table.
- Smoke test: the structure is placed with `/place structure` and all its loot tables open.
- Not checked: the look in game (missing screenshots from the owner) and the terrain adjustment in a real jungle
  with `/place structure` on different reliefs.

Floor plans by level in [`piramide/planos.txt`](piramide/planos.txt) (`.` reachable on foot) and renders in
`piramide/*.png`. They are regenerated with `python3 tools/gen/uniques/pyramid/blueprints.py`.
