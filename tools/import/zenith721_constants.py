#!/usr/bin/env python3
"""Prepare opt-in Pokémon Zenith Black 721-species constant lists.

The generated files are *not* a playable patch. They stage deterministic
species, moves, ability and Fairy-type IDs for the experimental --zenith-721
build. Normal generated/ lists and matching decomp builds are not modified.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
IMPORTED = ROOT / "imports/white2upgrade"
OUT = IMPORTED / "zenith721-lists"
ABILITY_NAMES = [
    "AROMA_VEIL", "FLOWER_VEIL", "CHEEK_POUCH", "PROTEAN",
    "FUR_COAT", "MAGICIAN", "BULLETPROOF", "COMPETITIVE",
    "STRONG_JAW", "REFRIGERATE", "SWEET_VEIL", "STANCE_CHANGE",
    "GALE_WINGS", "MEGA_LAUNCHER", "GRASS_PELT", "SYMBIOSIS",
    "TOUGH_CLAWS", "PIXILATE", "GOOEY", "AERILATE",
    "PARENTAL_BOND", "DARK_AURA", "FAIRY_AURA", "AURA_BREAK",
]


def read_records(folder, first, last, field):
    records = [json.loads(p.read_text(encoding="utf-8")) for p in folder.glob("*.json")
               if p.name != "REPORT.json"]
    records.sort(key=lambda item: item[field])
    expected = list(range(first, last + 1))
    got = [item[field] for item in records]
    if got != expected:
        raise ValueError(f"{folder}: expected {first}–{last} exactly, got {got}")
    return records


def insert_after(text: str, marker: str, entries: list[str], next_marker: str | None = None) -> str:
    lines = text.splitlines()
    if lines.count(marker) != 1:
        raise ValueError(f"Expected one {marker} in source constants")
    i = lines.index(marker) + 1
    if next_marker is not None and lines[i] != next_marker:
        raise ValueError(f"{marker} must be immediately followed by {next_marker}, got {lines[i]}")
    if any(value in lines for value in entries):
        raise ValueError("One or more expansion constants already exist")
    return "\n".join(lines[:i] + entries + lines[i:]) + "\n"


def constant_names(text: str) -> set[str]:
    return {line.partition("=")[0].strip() for line in text.splitlines()
            if line.strip() and not line.startswith("#")}


def ensure_unique(text: str) -> None:
    lines = [line.partition("=")[0].strip() for line in text.splitlines()
             if line.strip() and not line.startswith("#")]
    if len(lines) != len(set(lines)):
        raise ValueError("Duplicate constant in generated list")


def generate() -> dict[str, str]:
    mons = read_records(IMPORTED / "gen6", 650, 721, "national_dex")
    moves = read_records(IMPORTED / "moves", 560, 621, "move_id")
    species = [row["species"] for row in mons]
    move_names = [row["identifier"] for row in moves]
    abilities = [f"ABILITY_{name}" for name in ABILITY_NAMES]
    originals = {name: (ROOT / "generated" / f"{name}.txt").read_text(encoding="utf-8")
                 for name in ("species", "moves", "abilities", "types")}
    assert len(species) == 72 and len(move_names) == 62 and len(abilities) == 24
    files = {
        "species": insert_after(originals["species"], "SPECIES_GENESECT", species, "SPECIES_EGG"),
        "moves": insert_after(originals["moves"], "MOVE_FUSION_BOLT", move_names),
        "abilities": insert_after(originals["abilities"], "ABILITY_TERAVOLT", abilities),
    }
    types = originals["types"]
    if "TYPE_NULL = 17" not in types or "TYPE_FAIRY" in types:
        raise ValueError("Expected original TYPE_NULL = 17 and no Fairy type")
    files["types"] = types.replace("TYPE_NULL = 17", "TYPE_FAIRY = 17\nTYPE_NULL = 18")
    for value in files.values():
        ensure_unique(value)

    # Simulate gen_constants.parse's value assignment without loading source tree.
    def indexed(text: str) -> dict[str, int]:
        mapping = {}
        n = -1
        for line in text.splitlines():
            line = line.split("#", 1)[0].strip()
            if not line:
                continue
            name, eq, assigned = line.partition("=")
            n = int(assigned.strip(), 0) if eq else n + 1
            mapping[name.strip()] = n
        return mapping

    s, m, a, t = (indexed(files[k]) for k in ("species", "moves", "abilities", "types"))
    expected = {
        "species": {"SPECIES_CHESPIN": 650, "SPECIES_VOLCANION": 721,
                    "SPECIES_EGG": 722, "SPECIES_BAD_EGG": 723},
        "moves": {"MOVE_FLYING_PRESS": 560, "MOVE_HYPERSPACE_FURY": 621},
        "abilities": {"ABILITY_AROMA_VEIL": 165, "ABILITY_AURA_BREAK": 188},
        "types": {"TYPE_FAIRY": 17, "TYPE_NULL": 18},
    }
    for category, actual in zip(expected, (s, m, a, t)):
        for key, value in expected[category].items():
            if actual.get(key) != value:
                raise ValueError(f"{category}: {key} was {actual.get(key)}, expected {value}")
    return {f"{name}.txt": value for name, value in files.items()}


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="Check committed generated lists against their deterministic sources")
    parser.add_argument("--out", type=Path, default=OUT)
    args = parser.parse_args()
    content = generate()
    if args.check:
        bad = [name for name, value in content.items()
               if not (args.out / name).exists() or
               (args.out / name).read_text(encoding="utf-8") != value]
        if bad:
            raise SystemExit("721-species constant lists are missing or stale: " + ", ".join(bad))
    else:
        args.out.mkdir(parents=True, exist_ok=True)
        for name, value in content.items():
            (args.out / name).write_text(value, encoding="utf-8")
    print("Validated species #650–721, moves #560–621, abilities #165–188, Fairy type #17.")
    print("Experimental constants staged only; original generated/ lists were not modified.")


if __name__ == "__main__":
    main()
