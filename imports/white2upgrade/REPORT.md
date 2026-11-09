# White2Upgrade Gen 6 staging report

- Species staged: **72** (#650–721).
- These are **not playable** until engine data, save blocks, graphics, and Dex handling are expanded.
- Artwork, cries, alternate forms, Pokédex descriptions, egg moves, and engine code were **not** imported.
- Original ROM verification is unaffected because staging lives outside `res/`.
- Source: https://github.com/ds-pokemon-hacking/White2Upgrade

## Integration blockers

- Missing target type constants: TYPE_FAIRY
- Missing target move constants: MOVE_ANCIENTPOWER, MOVE_AROMATIC_MIST, MOVE_BABYDOLL_EYES, MOVE_BOOMBURST, MOVE_BUBBLEBEAM, MOVE_CRAFTY_SHIELD, MOVE_DIAMOND_STORM, MOVE_DISARMING_VOICE, MOVE_DOUBLEEDGE, MOVE_DOUBLESLAP, MOVE_DRAGONBREATH, MOVE_DRAINING_KISS, MOVE_EERIE_IMPULSE, MOVE_ELECTRIFY, MOVE_EXTREMESPEED, MOVE_FAIRY_LOCK, MOVE_FAIRY_WIND, MOVE_FEATHERDANCE, MOVE_FLOWER_SHIELD, MOVE_FLYING_PRESS, MOVE_FORESTS_CURSE, MOVE_FREEZEDRY, MOVE_GEOMANCY, MOVE_GRASSY_TERRAIN, MOVE_HYPERSPACE_HOLE, MOVE_KINGS_SHIELD, MOVE_LANDS_WRATH, MOVE_MAT_BLOCK, MOVE_MISTY_TERRAIN, MOVE_MOONBLAST, MOVE_MUDSLAP, MOVE_MYSTICAL_FIRE, MOVE_NOBLE_ROAR, MOVE_NUZZLE, MOVE_OBLIVION_WING, MOVE_PARABOLIC_CHARGE, MOVE_PARTING_SHOT, MOVE_PETAL_BLIZZARD, MOVE_PHANTOM_FORCE, MOVE_PLAY_NICE, MOVE_PLAY_ROUGH, MOVE_POISONPOWDER, MOVE_POWDER, MOVE_ROTOTILLER, MOVE_SANDATTACK, MOVE_SMOKESCREEN, MOVE_SOLARBEAM, MOVE_SPIKY_SHIELD, MOVE_STEAM_ERUPTION, MOVE_THUNDERSHOCK, MOVE_TOPSYTURVY, MOVE_TRICKORTREAT, MOVE_VICEGRIP, MOVE_WATER_SHURIKEN, MOVE_WILLOWISP
- Additional ability IDs that need mapping/engine implementation: 165, 166, 167, 168, 169, 170, 171, 173, 174, 175, 176, 177, 178, 179, 180, 181, 182, 183, 186, 187, 188
- Evolution methods requiring cross-project mapping: METHOD_ITEM_USE, METHOD_LEVELUP, METHOD_TRADE, METHOD_TRADE_ITEM
- Implement and test Pokédex/save expansion before changing the species list.
- Inspect White2Upgrade's license and asset provenance before redistributing donor graphics.

