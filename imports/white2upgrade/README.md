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
| 72 Kalos battle sprite groups and 107 additional forms | `tools/import/white2upgrade_graphics.py` | 3,580 donor members wired into the opt-in build |
| 72 Kalos icon groups and 107 additional forms | `tools/import/white2upgrade_graphics.py` | 358 donor members wired into the opt-in build |
| 72 footprints | `tools/import/white2upgrade_graphics.py` | 72 donor members wired into the opt-in build |
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

## Kalos graphics integration (new)

The experimental `--zenith-721` build now **automatically imports**
White2Upgrade's already-encoded Nitro sprite members into its generated
graphics NARCs. All graphics remain local to your build; the repository
does not distribute donor game artwork.

The importer preserves the original Pokémon and special IDs and places:

| Graphics | Kalos base species | New alternate forms | Generated NARC |
| --- | ---: | ---: | --- |
| Battle sprites, backs, animations and palettes | 72 × 20 = 1,440 members | 107 × 20 = 2,140 members | `a/0/0/4` |
| Party/PC icons | 72 × 2 = 144 members | 107 × 2 = 214 members | `a/0/0/7` |
| Footprints | 72 members | Uses existing form footprint handling | `a/1/6/5` |

This accounts for **3,580 battle-sprite members, 358 icon members, and
72 footprint members**. Empty female-icon/sprite slots are preserved
because the donor NARCs use numbered member positions, not a compact
sprite list.

New groups are inserted without changing the old Pokéstar/Egg/Manaphy
sprites, old form groups, Substitute graphics, or Arceus palettes.
The importer also generates a 932-entry C icon palette table using the
donor's palette banks for Kalos forms and the original banks for existing
Pokémon. In the modified runtime, `POKEGRA_FORM_PALETTES` is adjusted
for the 107 added sprite groups.

Clone the donor next to Zenith Black:

```sh
git clone --depth 1 https://github.com/ds-pokemon-hacking/White2Upgrade.git ../White2Upgrade
```

For a modified ROM build, first complete the species, moves, forms,
save-layout and battle-engine work listed below, then configure with
the opt-in graphics source:

```sh
python3 configure.py b2_us --zenith-721 --zenith-donor ../White2Upgrade
ninja
```

The `--zenith-721` preflight still refuses to proceed while the main
`generated/species.txt` lacks Kalos species; **this is deliberate**.
The graphics build integration is complete as a source path, but
a runnable 721-Pokémon ROM remains blocked on the full game-data migration.
The original matching build is unchanged.

To splice and inspect graphics archives independently of a ROM build,
use your own extracted Black 2 NARCs:

```sh
python3 tools/import/white2upgrade_graphics.py \
    --donor ../White2Upgrade \
    --base-root extract/b2_us/files \
    --output-root build/gen6-graphics
```

You can also generate the extra icon palette C header alone:

```sh
python3 tools/import/white2upgrade_graphics.py \
    --donor ../White2Upgrade \
    --palette-header build/include/generated/zenith721_icon_palettes.h
```

ROM-free unit tests check complete donor ranges, insertion positions,
preservation of the original archive members, NARC round-trips, and
palette-bank indexing:

```sh
ZENITH_GRAPHICS_TEST_DONOR=../White2Upgrade \
python3 -m unittest tools.import.test_white2upgrade_graphics -v
```

**Known remaining graphics limits:** Alternate-form battle resources
are present in the expanded NARC, but the species form records and
transitions must still be integrated to make the game select them.
New cries are audio assets, not covered by this graphics pass. The
modified archive build still requires a compatible personal ROM dump
to compile and test the complete game.

## Experimental runtime work committed

The development branch also includes these changes guarded by `ZENITH_721`.
They **do not activate in the original matching Black 2/White 2 build**:

- Enlarged Pokédex seen/caught arrays, national completion counts and Kalos form tracking.
- Updated Pokédex search count for species 650–721.
- Battle graphics and party-icon archive offset adjustments for the 72 new species.
- Temporary fallback cries and preserved original Egg/Pokéstar wave ID handling.
- `configure.py --zenith-721` for a nonmatching build, with a Gen 6 species
  constant preflight check.
- `tools/import/zenith721_constants.py` produces validated replacement
  `species.txt`, `moves.txt`, `abilities.txt`, and `types.txt` under
  `imports/white2upgrade/zenith721-lists/`. It deliberately **does not**
  overwrite the original matching-build `generated/` files.

**Critical**: These are partial runtime source changes, not a completed
modified ROM build. Replacing only constant lists is unsafe until all
dependent resources, save layout and engine tables are expanded.

## Build verification status

The importer is validated by public GitHub Actions with no ROM required.
Source formatting and ordinary compilation can be checked independently.
The repository's ROM build workflow attempts to check out private source
ROM dumps using `ROMS_DEPLOY_KEY`, which is not available here. Therefore
there is no successful 721-Pokémon ROM compile, gameplay test or patch.
Existing saves must not be used with the expanded save structure until
migration is implemented and tested.

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
