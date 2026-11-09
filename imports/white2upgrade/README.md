# White2Upgrade → Pokémon Zenith Black (Gen 6 integration)

**Status: source-data and asset import tooling is working; playable Gen 6 is not yet implemented.**

This fork contains a reproducible, opt-in import pipeline that references
[White2Upgrade](https://github.com/ds-pokemon-hacking/White2Upgrade).
It does not copy the donor's copyrighted artwork or patch the game in place.
All imports go under `imports/white2upgrade/` and leave the matching
Black 2/White 2 build sources unchanged.

## What is now on this development branch

| Deliverable | Output | State |
| --- | --- | --- |
| 72 Kalos Pokémon (#650–721) | `gen6/*.json` | complete staged metadata |
| 72 target-schema Pokémon records | `native-preview/*/data.json` | structural validation passed |
| Gen 6 moves #560–621 | `moves/*.json` | 62 source records staged |
| 18×18 Fairy matchup data | `fairy-type-chart.json` | extracted and validated, not active |
| 72 battle sprites | `graphics-inventory.json` | 1,440 donor entries indexed |
| 72 Pokémon icons | `graphics-inventory.json` | 144 donor entries indexed |
| 72 footprints | `graphics-inventory.json` | 72 donor entries indexed |
| Archive-building tool | `tools/import/white2upgrade_graphics.py` | local-only, needs extracted base archives |

The [native conversion report](native-preview/REPORT.md) records missing
ability constants, unsupported TM/tutor bits, new forms, type IDs and moves.
This report should be checked before attempting a modified build.

## Local reproducible import

Use your own copy of the public donor repository:

```sh
git clone --depth=1 https://github.com/ds-pokemon-hacking/White2Upgrade.git ../White2Upgrade
python3 tools/import/white2upgrade_gen6.py --donor ../White2Upgrade
python3 tools/import/white2upgrade_gen6.py --donor ../White2Upgrade --check
python3 tools/import/white2upgrade_native.py
python3 tools/import/white2upgrade_native.py --check
python3 tools/import/white2upgrade_moves.py --donor ../White2Upgrade
python3 tools/import/white2upgrade_moves.py --donor ../White2Upgrade --check
python3 tools/import/white2upgrade_type_chart.py --donor ../White2Upgrade
python3 tools/import/white2upgrade_type_chart.py --donor ../White2Upgrade --check
python3 tools/import/white2upgrade_graphics.py --donor ../White2Upgrade
```

To generate *local* graphics archives using NARCs extracted from your own
game dump, run the graphics importer with both roots:

```sh
python3 tools/import/white2upgrade_graphics.py \
    --donor ../White2Upgrade \
    --base-root extract/b2_us/files \
    --output-root build/gen6-graphics
```

The three resulting `a/.../` archives are **intermediate assets**, not a
playable patched ROM. They are not incorporated into the game until the
runtime code and file indexes are expanded to match them.

## Work still required before Gen 6 is playable

1. **Species identifiers**: insert #650–721, audit every numeric species
   reference, and relocate Egg/Bad Egg/Pokéstar IDs in engine data and code.
2. **Pokédex and save**: extend caught/seen bitfields (current 84-byte
   capacity is only 672 species); update counters, form tracking, completion,
   list/search/UI and save migration without losing existing Pokémon.
3. **Graphics integration**: wire the expanded battle, icon and footprint
   archives into the modded ROM; update group/form indices, icon palettes,
   graphics loaders and animations.
4. **Fairy type**: introduce type 17, relocate the existing typeless marker
   `TYPE_NULL=17`, port the damage chart and UI graphics, and test all
   effectiveness interactions. The staged chart is not a runtime patch.
5. **Moves and abilities**: add all new move records, exact effects, battle
   animations, strings and ability handlers; map the donor's numeric IDs to
   Zenith's C constants. Gen 6 IDs fit an 8-bit ability field, but the
   ultimate 1,025-species target needs a wider future-ability design.
6. **Evolution items and new methods**: Sachet, Whipped Dream, Eevee →
   Sylveon and all Gen 6 special evolution conditions, plus existing
   Pokémon gaining newer evolutions.
7. **Forms and visual/audio data**: validate extra forms of Vivillon,
   Flabébé, Floette, Florges, Furfrou, Aegislash, etc.; obtain allowed Dex
   descriptions, cries, footprints, icons and idle/cell animations.
8. **Testing**: modified Black 2 ROM build, Chespin encounter/capture/
   battle/evolve/PC/save/reload, then full roster stress tests.

**No actual ROM build or emulator verification has been completed.** The
GitHub Actions job verifies the *import scripts*, not the Black 2 game.
The repository does not distribute ROMs, and a local modified build needs a
legally obtained compatible copy of the game.

## Safety and provenance

White2Upgrade code injections use a different build system and are not
directly compatible with the decompilation. The new Python tools are original
conversion code. Do not redistribute artwork, sound, or ROM data copied from
other projects without checking their terms and provenance.

## Broader target

The current donor reaches #721. Pokémon #722–1025 (304 species) require
additional sourced data and art, plus separate engine expansion work.
