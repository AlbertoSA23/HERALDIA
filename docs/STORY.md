# The Chronicle of the Heralds

A light, optional shared story thread that links Heraldia's unique structures. It changes nothing in the game except for a
written book (a "leaf") in a chest each unique structure already had. The texts of each leaf are in the `HISTORIA` of its
module (`tools/gen/unicas/<id>`); this document is the reference for writing those of future unique structures without
contradicting what their signs, guardians, trophies and named items already tell.

## Background

The **Order of the Heralds** was born in Atlantis: its heralds were cartographers and messengers, they drew the maps of the
world and kept the coats of arms of every realm (hence the mod's name). When the sea swallowed the city, the last
herald, **Ysolda**, saved the one thing the ocean must not keep: **the way back**.

She wrote it on leaves, with an ink that water does not wash away (the archmage Malvarius gave it to her), and travelled the world
entrusting each leaf to a guardian who swore to keep it until someone worthy came. **The oaths
outlived those who swore them**: that is why the guardians of the unique structures are still at their posts, cursed, drowned,
frozen or sleepless, and why they must be defeated or outwitted. The last leaf stayed home, in the Academy of
Atlantis.

Each leaf tells what Ysolda found in that place, whom she left the leaf with and where they hid it, and ends with a
page that **points to the next unique structure** with a biome-and-feature clue (without naming it). Sometimes (10 %) it comes with the
treasure map of that structure (the same system as the epic chests and the cartographers, `tools/gen/mapas.py`).

Rules for not contradicting what exists: the guardian of each unique structure is the one who swore the oath (or inherited it); the place
where the leaf was kept is the chest that holds it; proper names are those of the structure's signs, guardians, trophies
and items.

## The chain

It is computed on its own from the registered unique structures (`_comun/botin.historia_cadena`): by id, with the final one (
Atlantis, `"final": True`) at the end. Each leaf points to the next and the Atlantis one points back to the first,
so it is a single cycle: you can start anywhere and reach all of them. A new unique structure takes its place on its own
(by its id) and the pages are renumbered ("Leaf N of M").

| Leaf | Unique structure | Chest (table) | With whom | Points to |
|---|---|---|---|---|
| 1 | Ruined aqueduct | `cisterna` | the centurion Aquilio, by earth and water | Castle |
| 2 | Castle | `capilla` | Sir Aldric, on his sword (his oath is the curse) | Gothic cathedral |
| 3 | Gothic cathedral | `biblioteca` | Friar Osmundo, who did not want to know what it held | Dwarven citadel |
| 4 | Dwarven citadel | `real` | Borin Ironbeard, who swore to be the last one out | Ruined coliseum |
| 5 | Ruined coliseum | `lanista` | the Champion of the Arena, who chose the leaf over freedom | Smugglers' lighthouse |
| 6 | Smugglers' lighthouse | `despacho` | captain Bruma, for gold and not for honor | Ice fortress |
| 7 | Ice fortress | `galeria` | the Frost King: the ice preserves it | Stranded galleon |
| 8 | Stranded galleon | `capitan` | the drowned captain, still at the helm | Corsair's Isle |
| 9 | Corsair's Isle | `cartas` | the corsair Roque Salitre, among his charts in the map room; he swore not to put to sea while he had it | Mycologist's Laboratory |
| 10 | Mycologist's Laboratory | `biblioteca` | Master Ambrosio, among the jars of his spore library (he tested his last remedy on himself) | Haunted mansion |
| 11 | Haunted mansion | `biblioteca` | count Malaquías, until the midnight at the end of the world | Lost Mine of Hondavena |
| 12 | Lost Mine of Hondavena | `despacho` | Tizón, the last foreman, behind the bookcase in his office; he stayed digging by the vein | Mountain monastery |
| 13 | Mountain monastery | `biblioteca` | Friar Tenebrio, next to the reliquary | Observatory |
| 14 | Observatory | `oculto` | the Keeper of the Stars, as long as there are stars | Eastern palace |
| 15 | Eastern palace | `biblioteca_secreta` | the emperor and the commander of the Imperial Guard | Pyramid temple |
| 16 | Pyramid temple | `tumba` | the Jaguar King, as an offering | Jarl's Hall |
| 17 | Jarl's Hall | `ofrendas` | jarl Ulfgrim, for his ancestors; not even dead does he let go of it | Druid Sanctuary |
| 18 | Druid Sanctuary | `biblioteca` | the archdruid Cadoc, by the roots of the tree (he was corrupted when the tree withered) | Wizard's tower |
| 19 | Wizard's tower | `escondite` | the archmage Malvarius (who opened it and seeks the rest) | Atlantis |
| 20 | Atlantis | `sello_academia` | Ysolda, at home: prologue and epilogue | Aqueduct (starts again) |

## How it plays

- Each leaf is a written book ("Chronicle of the Heralds: <structure>", by Ysolda, uncommon rarity) with
  `custom_data` `{heraldia_historia:"<id>"}`, in the table of the chosen chest of each unique structure (`HISTORIA["cofre"]`), which
  nests it from `heraldia:historia/<id>`. It always appears (also with Lootr: each player finds their own).
- Pages are translatable components (with a Spanish fallback), translated by each client when the book is opened.
- The **Chronicler** challenge (Heraldia tab) asks for all of them in the inventory (500 experience).
- To test: `/loot give @s loot heraldia:historia/<id>` (the leaf, sometimes with the map) or `/loot give @s loot
  heraldia:unicas/<id>/<cofre>` (the whole chest).

## New unique structure

`HISTORIA` is mandatory in the contract of `tools/gen/unicas/__init__.py` (like `TROFEO`): without it, with a chest that is not
in its templates or with pages that do not fit in a book (14 lines of 114 px, computed with the font's
widths), the build fails. It is enough to write its part and its clue:

```python
HISTORIA = {"cofre": "biblioteca",            # a smaller or hidden-room chest already in its templates
            "relato": [(es, en), (es, en)],    # 1-2 pages: what Ysolda found and whom she left the leaf with
            "pista": (es, en)}                 # "the <biome>, where <feature>": used by the previous leaf
```

The clue goes after "El siguiente pliego lo llevé hasta…" / "The next leaf I carried to…" and after "…que busque el primer
pliego en…" / "…seek the first leaf in…": it starts with an article ("el desierto, donde…", "a beach, where…").
