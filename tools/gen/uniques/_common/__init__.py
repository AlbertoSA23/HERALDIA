"""Common, parameterized pieces of the unique structures (not a structure itself: the _ prefix excludes it).

  chest_loot.py   chest tables with an extra solo_sin_lootr group, items with translatable names, books, potions.
  redstone.py static redstone simulator (wire shape and game rules) to audit puzzles.
  pieces.py  generators, guardians, signs, chests, secret piston doors, string and TNT traps,
             spiral staircases (in runs of 6, continuous steps or half-height slabs), circles,
             paintings and fence/glass/wall connections.
  walkthrough.py views for lint.walk (with mechanisms closed or open), reach, strict walkthrough (walking, with
             agua=True for swimming), dead-end-free roads and floating blocks.
The pieces receive `put(x, y, z, state, nbt=None)`, so they work for any coordinate system.
"""
