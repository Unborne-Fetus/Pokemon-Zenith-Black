#!/usr/bin/env python3
"""Stage White2Upgrade's 18x18 type chart for a future Fairy-type runtime port.

This extracts only numeric matchup data. It does not change TYPE_NULL,
the battle engine, type icons, or UI. A runnable Fairy type requires those.
"""
from __future__ import annotations
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUTPUT = ROOT / "imports/white2upgrade/fairy-type-chart.json"
TYPES = [
    "NORMAL", "FIGHTING", "FLYING", "POISON", "GROUND", "ROCK", "BUG",
    "GHOST", "STEEL", "FIRE", "WATER", "GRASS", "ELECTRIC", "PSYCHIC",
    "ICE", "DRAGON", "DARK", "FAIRY"
]


def generate(donor: Path):
    source = donor / "data/type_chart.bin"
    raw = source.read_bytes()
    if len(raw) != 18 * 18:
        raise ValueError(f"Expected exactly 324 bytes in donor type chart; got {len(raw)}")
    values = sorted(set(raw))
    if any(value not in (0, 2, 4, 8) for value in values):
        raise ValueError(f"Unexpected effectiveness encoding: {values}")
    return {
        "source": "https://github.com/ds-pokemon-hacking/White2Upgrade",
        "status": "staged_not_playable",
        "type_index": {t: n for n, t in enumerate(TYPES)},
        "entry_values": values,
        "note": "Raw donor order (18 rows by 18 columns). Battle table orientation must be verified before use.",
        "rows": [list(raw[i:i + 18]) for i in range(0, len(raw), 18)],
        "blockers": [
            "TYPE_FAIRY currently conflicts with TYPE_NULL=17 in Zenith Black",
            "type comparison and damage calculation must use 18 types",
            "battle, summary and Pokedex UI need Fairy icons and palettes",
            "runtime matchup orientation and special-type interactions require tests"
        ],
    }


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--donor", type=Path, required=True)
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    data = json.dumps(generate(args.donor), indent=2) + "\n"
    if args.check:
        if not OUTPUT.exists() or OUTPUT.read_text(encoding="utf-8") != data:
            raise SystemExit("Fairy type chart staging is missing or out of date")
    else:
        OUTPUT.parent.mkdir(parents=True, exist_ok=True)
        OUTPUT.write_text(data, encoding="utf-8")
    print("Verified White2Upgrade's 18x18 type chart (not yet connected to the battle engine).")


if __name__ == "__main__":
    main()
