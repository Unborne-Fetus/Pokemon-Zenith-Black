#!/usr/bin/env python3
"""Audit or locally splice White2Upgrade's Kalos graphics into Gen 5 NARCs.

This tool does NOT modify game code, fix Pokémon indices, or make Pokémon
playable on its own. It requires the donor assets and, for splice mode,
locally extracted base archives. Do not commit the produced binary archives.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from tools.data.narc import read_narc, write_narc  # noqa: E402

FIRST_SPECIES, LAST_SPECIES = 650, 721
TARGETS = {
    # name: (donor folder, donor first index, count, base NARC archive,
    #        zero-based insertion index in the original Zenith Black archive)
    "battle": ("battle_sprites", FIRST_SPECIES * 20, 72 * 20, "a/0/0/4", FIRST_SPECIES * 20),
    "icons": ("icons", 8 + FIRST_SPECIES * 2, 72 * 2, "a/0/0/7", 8 + FIRST_SPECIES * 2),
    "footprints": ("footprints", 5 + FIRST_SPECIES, 72, "a/1/6/5", 5 + FIRST_SPECIES),
}


def donor_files(folder: Path) -> dict[int, Path]:
    found = {}
    for path in folder.iterdir():
        match = re.search(r"_(\d{8})\.bin$", path.name)
        if match:
            number = int(match.group(1))
            if number in found:
                raise ValueError(f"Duplicate donor graphic index {number}: {path}")
            found[number] = path
    return found


def get_additions(donor: Path) -> tuple[dict[str, list[bytes]], dict]:
    assets = donor / "data/graphics/pokegra"
    output = {}
    report = {}
    for kind, (subdir, first, count, archive, insert) in TARGETS.items():
        folder = assets / subdir
        if not folder.is_dir():
            raise ValueError(f"Donor graphics folder not found: {folder}")
        found = donor_files(folder)
        missing = [number for number in range(first, first + count) if number not in found]
        if missing:
            raise ValueError(f"{kind}: {len(missing)} missing files (first ten: {missing[:10]})")
        entries = [found[number].read_bytes() for number in range(first, first + count)]
        output[kind] = entries
        report[kind] = {
            "source_archive": archive,
            "source_index_first": first,
            "source_index_last": first + count - 1,
            "target_insert_at": insert,
            "entries": len(entries),
            "empty_entries": sum(not v for v in entries),
            "source_bytes": sum(len(v) for v in entries)
        }
    return output, report


def insert_members(original: list[bytes], added: list[bytes], at: int) -> list[bytes]:
    if at > len(original):
        raise ValueError(f"Base NARC has {len(original)} members but insertion index is {at}")
    return original[:at] + added + original[at:]


def splice(donor: Path, base: Path, output: Path, report: dict, additions: dict) -> None:
    if base.resolve() == output.resolve():
        raise ValueError("Base and output roots must differ; refusing in-place changes")
    for kind, (_, _, count, archive_name, insert) in TARGETS.items():
        source = base / archive_name
        if not source.is_file():
            raise ValueError(f"Expected extracted base NARC archive {source}")
        orig = read_narc(source.read_bytes())
        merged = insert_members(orig, additions[kind], insert)
        if len(merged) != len(orig) + count or merged[insert:insert + count] != additions[kind]:
            raise AssertionError(f"{kind} splice did not preserve all generated members")
        destination = output / archive_name
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(write_narc(merged))
        if read_narc(destination.read_bytes()) != merged:
            raise AssertionError(f"{kind} NARC failed round-trip validation")
        report[kind]["base_entries"] = len(orig)
        report[kind]["expanded_entries"] = len(merged)
        report[kind]["output"] = str(destination)
    print(f"Saved expanded graphics NARCs under {output}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--donor", type=Path, required=True,
                        help="Local White2Upgrade checkout; not stored in the Zenith repository")
    parser.add_argument("--base-root", type=Path,
                        help="Root containing your own extracted NARC archives (a/0/0/4 etc.)")
    parser.add_argument("--output-root", type=Path,
                        help="Output root for expanded NARC archives")
    parser.add_argument("--report", type=Path,
                        help="Optional JSON inventory report")
    args = parser.parse_args()
    additions, report = get_additions(args.donor)
    if args.base_root is not None or args.output_root is not None:
        if args.base_root is None or args.output_root is None:
            parser.error("--base-root and --output-root must be supplied together")
        splice(args.donor, args.base_root, args.output_root, report, additions)
    else:
        print("Donor archive inventory complete; no base ROM files touched.")
    report_path = args.report
    if report_path:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    print("IMPORTANT: Engine species indices, form graphics, palette maps, cries and saves still require changes.")


if __name__ == "__main__":
    main()
