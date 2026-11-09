#!/usr/bin/env python3
"""Stage White2Upgrade's Gen 6 move records (#560–621) as parsed metadata.

The source move-effect IDs and flags are NOT automatically compatible with
the Zenith Black battle engine. These records are intentionally not applied to
res/moves until their effects and descriptions are implemented.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
START, END = 560, 621
OUT = ROOT / "imports/white2upgrade/moves"


def scalar(text):
    text = text.strip()
    if re.fullmatch(r"-?\d+", text):
        return int(text)
    if re.fullmatch(r"0[xX][0-9a-fA-F]+", text):
        return int(text, 16)
    return text


def parse_record(text):
    lines = text.replace("\r", "").splitlines()
    head = lines[0].strip()
    if not re.fullmatch(r"MOVE_[A-Z0-9_]+:", head):
        raise ValueError(f"Invalid donor move header {head!r}")
    result = {}
    last = None
    for line in lines[1:]:
        match = re.fullmatch(r"- ([^:]+):\s*(.*)", line)
        if match:
            key, value = match.groups()
            last = key.strip()
            result[last] = scalar(value) if value else []
            continue
        item = re.fullmatch(r"\s+-\s+(.*?)\s*", line)
        if item and last is not None and isinstance(result[last], list):
            result[last].append(scalar(item.group(1)))
        elif line.strip():
            raise ValueError(f"Unexpected donor move line {line!r}")
    return head[:-1], result


def generate(donor):
    records = []
    for index in range(START, END + 1):
        source = donor / f"data/pml/moves/{index:03}.yml"
        species, data = parse_record(source.read_text(encoding="utf-8"))
        for required in ("Type", "Quality", "Category", "Power", "Accuracy", "Base PP",
                         "Priority", "Move Animation ID", "Flags"):
            if required not in data:
                raise ValueError(f"{source}: required field {required} missing")
        records.append((index, species, data))
    if len({x[1] for x in records}) != len(records):
        raise ValueError("Duplicate move identifier")

    output = {}
    for number, identifier, data in records:
        name = f"{number:03}-{identifier.removeprefix('MOVE_').lower()}.json"
        record = {
            "source": "https://github.com/ds-pokemon-hacking/White2Upgrade",
            "move_id": number,
            "identifier": identifier,
            "donor_move_data": data,
            "status": "staged_not_playable",
        }
        output[OUT / name] = json.dumps(record, ensure_ascii=False, indent=2) + "\n"
    stats = {
        "count": len(records),
        "range": [START, END],
        "fairy_moves": [ident for _, ident, data in records if data["Type"] == "TYPE_FAIRY"],
        "requires_move_effect_porting": True,
        "includes_playable_battle_implementations": False,
    }
    output[OUT / "REPORT.json"] = json.dumps(stats, indent=2) + "\n"
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--donor", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    result = generate(args.donor)
    if args.check:
        missing = [str(p) for p, value in result.items()
                   if not p.exists() or p.read_text(encoding="utf-8") != value]
        if missing:
            raise SystemExit("Missing/outdated move files:\n" + "\n".join(missing))
    else:
        for path, content in result.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8")
    print(f"Parsed {END - START + 1} White2Upgrade move records; effects remain unimplemented.")


if __name__ == "__main__":
    main()
