# White2Upgrade → Pokémon Zenith Black (Generation 6)

This integration stages the **72 Kalos species, #650–721**, using the public
[White2Upgrade](https://github.com/ds-pokemon-hacking/White2Upgrade) data
as a source. It does **not** yet add playable Pokémon to Black 2.

## Data imported

The script `tools/import/white2upgrade_gen6.py` reads the donor's numbered
personal, evolution and level-up learnset YAML files. It checks that the
species names match `include/Species.h`, preserves all numeric personal
fields, and writes one JSON per species to
`imports/white2upgrade/gen6/`. It also writes `REPORT.md` with references
to moves, Fairy type, ability IDs and evolution methods requiring engine work.

These staged JSON files are deliberately outside `res/` so that the original
Black 2 / White 2 byte-for-byte matching builds remain unchanged.

## Recreate the import

From the Zenith Black repository root:

```sh
git clone --depth=1 https://github.com/ds-pokemon-hacking/White2Upgrade.git ../White2Upgrade
python3 tools/import/white2upgrade_gen6.py --donor ../White2Upgrade
python3 tools/import/white2upgrade_gen6.py --donor ../White2Upgrade --check
```

The importer uses only Python 3.11+ standard-library modules. The
`--dry-run` option validates without writing files.

## Not yet integrated

- Gen 6 species constants and revised Egg/Pokéstar species indices
- Pokédex 1,025-species arrays, indexing, UI and save migration
- A properly expanded battle engine, including Fairy type and new abilities
- New moves/effects and remapped evolution methods
- Sprites/icons/animations/cries and graphics archive indexing
- Egg moves, form data, Dex text, evolution changes to pre-existing Pokémon
- Catching, battles, breeding, PC storage, and save/reload tests

**Do not put these files directly into `res/pokemon/` without the engine
changes.** The existing `res/pokemon/<species>/data.json` schema has a
different representation, and incomplete assets can break the game.

White2Upgrade's build system and ROM code-injection patches cannot be copied
directly into this decompilation's source tree. Keep credit for the original
donor project; check the provenance and redistribution permissions of graphics
and other assets before adding them to a distributable game.

## Next implementation milestone

Integrate **Chespin (#650)** as a complete playable Pokémon first, including
battle graphics and save/reload, then batch-apply the validated pattern to
the remaining 71 Kalos species. Only after that should the team expand to
the additional 304 species from Generations 7–9.
