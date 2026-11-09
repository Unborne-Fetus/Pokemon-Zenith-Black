#!/usr/bin/env python3
"""Stage White2Upgrade's Gen 6 Pokémon data for Zenith Black.

This is a data import, NOT an engine patch. It intentionally does not modify
res/pokemon or generated/species.txt until species/save/graphics limits are fixed.
Source: https://github.com/ds-pokemon-hacking/White2Upgrade
"""
from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FIRST, LAST = 650, 721
SOURCE_URL = "https://github.com/ds-pokemon-hacking/White2Upgrade"
NUMBER = re.compile(r"^-?(?:0x[0-9a-fA-F]+|[0-9]+)$")


def scalar(raw: str):
    value = raw.strip()
    return int(value, 0) if NUMBER.fullmatch(value) and value.lower().startswith("0x") else (
        int(value) if re.fullmatch(r"-?[0-9]+", value) else value
    )


def header(text: str) -> tuple[str, list[str]]:
    lines = text.replace("\r", "").splitlines()
    raw = lines[0].strip() if lines else ""
    normalized = unicodedata.normalize("NFKD", raw)
    normalized = "".join(ch for ch in normalized if not unicodedata.combining(ch)).upper()
    if not re.fullmatch(r"SPECIES_[A-Z0-9_]+:", normalized):
        raise ValueError(f"Unrecognized White2Upgrade species file header: {raw!r}")
    return normalized[:-1], lines[1:]


def personal(text: str) -> tuple[str, dict]:
    species, lines = header(text)
    fields: dict = {}
    current_list = None
    for line in lines:
        match = re.fullmatch(r"- ([^:]+):\s*(.*)", line)
        if match:
            key, raw = match.group(1).strip(), match.group(2).strip()
            fields[key] = [] if not raw else scalar(raw)
            current_list = key if not raw else None
            continue
        item = re.fullmatch(r"\s+-\s+(-?(?:0x[0-9a-fA-F]+|[0-9]+))\s*", line)
        if item and current_list:
            fields[current_list].append(scalar(item.group(1)))
        elif line.strip():
            raise ValueError(f"Unexpected personal-data line: {line!r}")
    for required in ("Base HP", "Base Attack", "Base Defense", "Base Speed",
                     "Base Special Attack", "Base Special Defense", "Primary Type",
                     "Secondary Type", "Primary Ability", "Hidden Ability"):
        # Source actually has an extra space before the colon on 'Primary Ability'.
        if required not in fields:
            raise ValueError(f"Missing personal-data field: {required}")
    return species, fields


def table(text: str, prefix: str) -> tuple[str, list[dict]]:
    species, lines = header(text)
    entries, current = [], None
    for line in lines:
        match = re.fullmatch(r"\s*- (" + re.escape(prefix) + r"_[0-9]+|LEARNSET_END):\s*", line)
        if match:
            if current is not None:
                entries.append(current)
            current = {}
            continue
        value = re.fullmatch(r"\s+- ([^:]+):\s*(.*?)\s*", line)
        if value and current is not None:
            current[value.group(1).strip()] = scalar(value.group(2))
        elif line.strip():
            raise ValueError(f"Unexpected {prefix} line: {line!r}")
    if current is not None:
        entries.append(current)
    return species, entries


def species_constants(donor: Path) -> dict[int, str]:
    source = (donor / "include/Species.h").read_text(encoding="utf-8")
    found = {
        int(index): name
        for name, index in re.findall(r"^#define (SPECIES_[A-Z0-9_]+) (\d+)\s*$", source, re.M)
        if FIRST <= int(index) <= LAST
    }
    if len(found) != LAST - FIRST + 1:
        raise ValueError("Donor species constants do not cover #650–721")
    return found


def build(donor: Path, number: int, species: str) -> dict:
    source = donor / "data/pml"
    a, p = personal((source / f"personal/{number:03}.yml").read_text(encoding="utf-8"))
    b, evos = table((source / f"evolutions/{number:03}.yml").read_text(encoding="utf-8"), "EVOLUTION")
    c, moves = table((source / f"learnsets/{number:03}.yml").read_text(encoding="utf-8"), "LEARNSET_ENTRY")
    if {a, b, c} != {species}:
        raise ValueError(f"Species identifier mismatch in donor files for #{number}: {a}, {b}, {c}")
    evolutions = [
        {"method": e["Method"], "parameter": e["Parameter"], "target": e["Target Species"]}
        for e in evos if e.get("Method") not in ("METHOD_NONE", None)
    ]
    learnset = [
        [e["LEVEL"], e["MOVE"]] for e in moves
        if e.get("MOVE") not in ("0xFFFF", 65535, None)
    ]
    stats = {
        name: p[label] for name, label in (
            ("hp", "Base HP"), ("attack", "Base Attack"),
            ("defense", "Base Defense"), ("speed", "Base Speed"),
            ("special_attack", "Base Special Attack"),
            ("special_defense", "Base Special Defense"))
    }
    ev = int(p["EV Yield"])
    ev_names = list(stats)
    return {
        "source": {
            "project": "White2Upgrade", "repository": SOURCE_URL,
            "personal": f"data/pml/personal/{number:03}.yml",
            "evolutions": f"data/pml/evolutions/{number:03}.yml",
            "learnsets": f"data/pml/learnsets/{number:03}.yml"
        },
        "national_dex": number,
        "species": species,
        "base_stats": stats,
        "types": [p["Primary Type"], p["Secondary Type"]],
        "ev_yields": {name: (ev >> (i * 2)) & 3 for i, name in enumerate(ev_names)},
        "level_up_moves": learnset,
        "evolutions": evolutions,
        "personal_source_fields": p,
        "status": "staged_not_playable"
    }


def constants(path: Path, prefix: str) -> set[str]:
    return set(re.findall(r"^(" + prefix + r"_[A-Z0-9_]+)", path.read_text(encoding="utf-8"), re.M))


def report(records: list[dict]) -> str:
    abilities = constants(ROOT / "generated/abilities.txt", "ABILITY")
    moves = constants(ROOT / "generated/moves.txt", "MOVE")
    types = constants(ROOT / "generated/types.txt", "TYPE")
    unknown_moves = sorted({
        move for r in records for _, move in r["level_up_moves"] if move not in moves
    })
    unknown_types = sorted({
        value for r in records for value in r["types"] if value not in types
    })
    ability_ids = sorted({
        int(r["personal_source_fields"][key])
        for r in records for key in ("Primary Ability", "Secondary Ability", "Hidden Ability")
    })
    # Generated ability constants are consecutive, starting at ABILITY_NONE = 0.
    additional_ability_ids = [n for n in ability_ids if n >= len(abilities)]
    unknown_methods = sorted({
        e["method"] for r in records for e in r["evolutions"]
    })
    return "\n".join([
        "# White2Upgrade Gen 6 staging report", "",
        f"- Species staged: **{len(records)}** (#650–721).",
        "- These are **not playable** until engine data, save blocks, graphics, and Dex handling are expanded.",
        "- Artwork, cries, alternate forms, Pokédex descriptions, egg moves, and engine code were **not** imported.",
        "- Original ROM verification is unaffected because staging lives outside `res/`.",
        f"- Source: {SOURCE_URL}", "",
        "## Integration blockers", "",
        f"- Missing target type constants: {', '.join(unknown_types) or 'none'}",
        f"- Missing target move constants: {', '.join(unknown_moves) or 'none'}",
        f"- Additional ability IDs that need mapping/engine implementation: {', '.join(map(str, additional_ability_ids)) or 'none'}",
        f"- Evolution methods requiring cross-project mapping: {', '.join(unknown_methods) or 'none'}",
        "- Implement and test Pokédex/save expansion before changing the species list.",
        "- Inspect White2Upgrade's license and asset provenance before redistributing donor graphics.",
        "",
    ]) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--donor", type=Path, required=True, help="Local clone of White2Upgrade")
    parser.add_argument("--out", type=Path, default=ROOT / "imports/white2upgrade/gen6")
    parser.add_argument("--check", action="store_true", help="Compare generated data against staged files")
    parser.add_argument("--dry-run", action="store_true", help="Validate sources without writing anything")
    args = parser.parse_args()
    ids = species_constants(args.donor)
    records = [build(args.donor, number, ids[number]) for number in range(FIRST, LAST + 1)]
    generated = {
        args.out / f"{r['national_dex']:03}-{r['species'][8:].lower()}.json":
            json.dumps(r, ensure_ascii=False, indent=2) + "\n"
        for r in records
    }
    generated[args.out.parent / "REPORT.md"] = report(records)
    if args.check:
        stale = [str(p) for p, body in generated.items() if not p.exists() or p.read_text(encoding="utf-8") != body]
        if stale:
            raise SystemExit("Generated files missing or out of date:\n" + "\n".join(stale))
    elif not args.dry_run:
        for path, body in generated.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(body, encoding="utf-8")
    print(f"Validated {len(records)} White2Upgrade species (#650–721).")
    if args.dry_run:
        print("Dry run: no files written.")


if __name__ == "__main__":
    main()
