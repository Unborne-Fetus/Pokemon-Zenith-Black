#!/usr/bin/env python3
"""Translate staged White2Upgrade Kalos records into Zenith Black native JSON previews.

The previews deliberately live under imports/, not res/: the runtime still
needs expanded species IDs, abilities, types, moves, graphics, and save data.
No third-party assets or ROM data are distributed by this tool.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from tools.data.datajson import constants, load_schema, name, validate  # noqa: E402
from tools.data.species_data import tutor_moves  # noqa: E402

STAGED = ROOT / "imports/white2upgrade/gen6"
PREVIEW = ROOT / "imports/white2upgrade/native-preview"
SOURCE = "https://github.com/ds-pokemon-hacking/White2Upgrade"
EVOLUTION_METHODS = {
    "METHOD_LEVELUP": "EVO_METHOD_LEVEL",
    "METHOD_TRADE": "EVO_METHOD_TRADE",
    "METHOD_TRADE_ITEM": "EVO_METHOD_TRADE_WITH_ITEM",
    "METHOD_ITEM_USE": "EVO_METHOD_ITEM",
}
STAT_KEYS = ("hp", "attack", "defense", "speed", "special_attack", "special_defense")
NAMES = {
    "SPECIES_FLABEBE": "Flabébé",
    "SPECIES_FARFETCHD": "Farfetch'd",
}
# The importer cannot invent Dex text, drawings or sounds missing from its inputs.


def without_constant_checks(node):
    """Validate the target schema's structure independently of unresolved IDs."""
    if isinstance(node, dict):
        return {k: without_constant_checks(v) for k, v in node.items() if k != "x-constant"}
    if isinstance(node, list):
        return [without_constant_checks(v) for v in node]
    return node


def naming_aliases():
    moves = [key for key in constants() if key.startswith("MOVE_")]
    simplified = {}
    for item in moves:
        simplified.setdefault(item.replace("_", ""), []).append(item)
    return {key: items[0] for key, items in simplified.items() if len(items) == 1}


def move_name(source: str, aliases: dict[str, str]) -> str:
    if source in constants():
        return source
    return aliases.get(source.replace("_", ""), source)


def named(prefix: str, value: int, missing: Counter) -> str:
    result = name(prefix, value)
    if isinstance(result, str):
        return result
    code = f"{prefix}W2U_{value}"
    missing[code] += 1
    return code


def name_of_species(identifier: str) -> str:
    if identifier in NAMES:
        return NAMES[identifier]
    return identifier.removeprefix("SPECIES_").replace("_", " ").title()


def extract_machines(p: dict, missing: Counter) -> list[str]:
    names = []
    for word_id in range(1, 5):
        word = int(p[f"TM HM {word_id}"]) & 0xFFFFFFFF
        for bit in range(32):
            if not word & (1 << bit):
                continue
            number = (word_id - 1) * 32 + bit
            if number < 95:
                names.append(f"TM{number + 1:02d}")
            elif number < 101:
                names.append(f"HM{number - 94:02d}")
            else:
                missing[f"TM/HM bit {number}"] += 1
    return names


def extract_tutors(p: dict, aliases: dict[str, str], missing: Counter) -> list[str]:
    layout = tutor_moves()
    words = [int(p["Type Tutors"])] + [int(v) for v in p["Special Tutors"]]
    if len(words) != len(layout):
        raise ValueError(f"Expected {len(layout)} tutor bitsets, got {len(words)}")
    moves = []
    for word, candidates in zip(words, layout):
        if word < 0:
            word &= 0xFFFFFFFF
        for index in range(32):
            if word & (1 << index):
                if index >= len(candidates):
                    missing[f"tutor bit {index}, group with {len(candidates)} entries"] += 1
                else:
                    moves.append(move_name(candidates[index], aliases))
    return list(dict.fromkeys(moves))


def baby_species(identifier: str, parent_by_child: dict[str, str], missing: Counter) -> str:
    species = identifier
    history = set()
    while species in parent_by_child:
        if species in history:
            missing["evolution cycle"] += 1
            return identifier
        history.add(species)
        species = parent_by_child[species]
    if identifier == "SPECIES_SYLVEON":
        return "SPECIES_EEVEE"
    return species


def convert(record: dict, parents: dict[str, str], aliases: dict[str, str], missing: Counter) -> dict:
    p = record["personal_source_fields"]
    species = record["species"]
    color_value = int(p["Color"])
    forms = int(p["Form Count"])
    if forms > 1:
        missing[f"{species} has {forms - 1} alternate forms without converted assets"] += 1
    evolutions = []
    for evo in record["evolutions"]:
        method = EVOLUTION_METHODS.get(evo["method"])
        if not method:
            missing[f"unmapped evolution method {evo['method']}"] += 1
            continue
        parameter = evo["parameter"]
        if method in ("EVO_METHOD_ITEM", "EVO_METHOD_TRADE_WITH_ITEM"):
            parameter = named("ITEM_", int(parameter), missing)
        evolutions.append({
            "method": method, "param": parameter, "species": evo["target"]
        })
    if len(evolutions) > 7:
        missing[f"{species} exceeds 7 evolution slots"] += 1

    ability_one = named("ABILITY_", int(p["Primary Ability"]), missing)
    ability_two = named("ABILITY_", int(p["Secondary Ability"]), missing)
    hidden = named("ABILITY_", int(p["Hidden Ability"]), missing)
    by_level = [[int(level), move_name(move, aliases)] for level, move in record["level_up_moves"]]
    if len(by_level) > 25:
        missing[f"{species} has {len(by_level)} level-up moves (LEARNSET_MAX=26 including terminator)"] += 1
    return {
        "$schema": "../species.schema.json",
        "name": name_of_species(species),
        "base_stats": record["base_stats"],
        "types": record["types"],
        "catch_rate": int(p["Capture Rate"]),
        "evolution_stage": int(p["Evolution Stage"]),
        "ev_yields": record["ev_yields"],
        "underground": bool(int(p["EV Yield"]) & (1 << 12)),
        "held_items": {
            key: named("ITEM_", int(p[field]), missing)
            for key, field in [
                ("common", "Wild Item (50%)"),
                ("rare", "Wild Item (5%)"),
                ("very_rare", "Wild Item (1%)")
            ]
        },
        "gender_ratio": int(p["Gender Probability"]),
        "hatch_cycles": int(p["Egg Happiness"]),
        "base_friendship": int(p["Base Happiness"]),
        "growth_rate": named("GROWTH_", int(p["Experience Group"]), missing),
        "egg_groups": [
            named("EGG_GROUP_", int(p["Egg Group 1"]), missing),
            named("EGG_GROUP_", int(p["Egg Group 2"]), missing)
        ],
        "abilities": [ability_one, ability_two],
        "hidden_ability": hidden,
        "flee_rate": int(p["Escape Rate"]),
        "forms": {
            "count": forms,
            "sprite_offset": int(p["Form Sprite Offset"])
        },
        "color": named("COLOR_", color_value & 0x3F, missing),
        "asymmetric": bool(color_value & 0x40),
        "palette_forms": bool(color_value & 0x80),
        "base_exp": int(p["Base Experience"]),
        "height": int(round(int(p["Height (cm)"]) / 10)),
        "weight": int(p["Weight (cg)"]),
        "learnset": {
            "by_level": by_level,
            "by_tm": extract_machines(p, missing),
            "by_tutor": extract_tutors(p, aliases, missing),
            "egg_moves": []
        },
        "evolutions": evolutions,
        "regional_dex_number": None,
        "baby_species": baby_species(species, parents, missing),
    }


def generate() -> dict[Path, str]:
    paths = sorted(STAGED.glob("*.json"))
    records = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    if len(records) != 72 or [r["national_dex"] for r in records] != list(range(650, 722)):
        raise ValueError("Expected a complete sequential Gen 6 staging set (#650–721)")
    parents = {}
    for record in records:
        for evo in record["evolutions"]:
            target = evo["target"]
            if target in parents and parents[target] != record["species"]:
                raise ValueError(f"{target} has multiple parents")
            parents[target] = record["species"]

    missing = Counter()
    aliases = naming_aliases()
    schema = without_constant_checks(load_schema(ROOT / "res/pokemon/species.schema.json"))
    output = {}
    for record in records:
        data = convert(record, parents, aliases, missing)
        validate(data, schema, f"#{record['national_dex']}")
        path = PREVIEW / record["species"].removeprefix("SPECIES_").lower() / "data.json"
        output[path] = json.dumps(data, ensure_ascii=False, indent=2) + "\n"

    unresolved = set()
    for path, contents in output.items():
        data = json.loads(contents)
        for code in data["types"] + data["abilities"] + [data["hidden_ability"]]:
            if code not in constants():
                unresolved.add(code)
        for _, move in data["learnset"]["by_level"]:
            if move not in constants():
                unresolved.add(move)
    lines = [
        "# Native Gen 6 data conversion audit", "",
        "- Generated **72** Zenith Black-formatted `data.json` previews (#650–721).",
        "- Structural validation against `res/pokemon/species.schema.json`: **passed**.",
        "- This is not a playable ROM integration. The generated files are **not** in `res/pokemon/`.",
        "- Missing Pokédex prose, sprites, icons, cell animations, footprints, cries and egg moves.",
        "- New form offsets, battle data, save migrations and engine limits are unresolved.",
        f"- Donor: {SOURCE}", "",
        "## Missing references and conversion warnings", "",
        *[f"- {item}: {count}" for item, count in sorted(missing.items())],
        "", "## Unresolved type/move/ability references", "",
        *[f"- `{item}`" for item in sorted(unresolved)],
        "",
    ]
    output[PREVIEW / "REPORT.md"] = "\n".join(lines)
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail if generated files differ")
    args = parser.parse_args()
    output = generate()
    if args.check:
        stale = [str(p) for p, body in output.items()
                 if not p.exists() or p.read_text(encoding="utf-8") != body]
        if stale:
            raise SystemExit("Native previews out of date:\n" + "\n".join(stale))
    else:
        for path, contents in output.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(contents, encoding="utf-8")
    print("Converted and structurally validated 72 Kalos Pokémon into native-format previews.")


if __name__ == "__main__":
    main()
