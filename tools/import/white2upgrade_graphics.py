#!/usr/bin/env python3
"""Import Kalos Pokémon graphics from a local White2Upgrade checkout.

Three target NARCs contain base species (#650-721) AND the 107 new form
groups. Existing Black 2 entries, including Egg, Pokéstar, old forms, the
Substitute and Arceus palettes, are preserved and shifted deterministically.

Only the modified --zenith-721 build uses these generated NARCs. Do not
commit donor game assets or original ROM archives to the repository.
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

FIRST_SPECIES = 650
KALOS_SPECIES = 72
EXTRA_FORM_START = 66
EXTRA_FORM_GROUPS = 107
BATTLE_GROUP_SIZE = 20
ICON_GROUP_SIZE = 2

# (location in *original* Black 2 NARC, donor member start, number of entries).
# In the donor, species #650 begins at 13000/1308; its extra form sprites
# begin at 15800/1588. Existing Black 2 has 66 form groups; preserve them.
TARGETS = {
    "a/0/0/4": ("battle_sprites", [
        (650 * 20, 650 * 20, KALOS_SPECIES * BATTLE_GROUP_SIZE),
        (15020, 14480 + EXTRA_FORM_START * BATTLE_GROUP_SIZE,
         EXTRA_FORM_GROUPS * BATTLE_GROUP_SIZE),
    ]),
    "a/0/0/7": ("icons", [
        (8 + 650 * 2, 8 + 650 * 2, KALOS_SPECIES * ICON_GROUP_SIZE),
        (1510, 1456 + EXTRA_FORM_START * ICON_GROUP_SIZE,
         EXTRA_FORM_GROUPS * ICON_GROUP_SIZE),
    ]),
    "a/1/6/5": ("footprints", [
        (5 + 650, 5 + 650, KALOS_SPECIES),
    ]),
}
KINDS = {"battle": "a/0/0/4", "icons": "a/0/0/7",
         "footprints": "a/1/6/5"}


def donor_files(folder: Path) -> dict[int, Path]:
    if not folder.is_dir():
        raise ValueError(f"Missing White2Upgrade graphics directory: {folder}")
    files = {}
    for path in folder.iterdir():
        match = re.fullmatch(r"\d+_(\d{8})\.bin", path.name)
        if match:
            number = int(match.group(1))
            if number in files:
                raise ValueError(f"Duplicate donor asset index {number}: {path}")
            files[number] = path
    return files


def additions(donor: Path, archive: str) -> tuple[list[tuple[int, list[bytes]]], dict]:
    if archive not in TARGETS:
        raise ValueError(f"Unsupported Kalos graphics archive: {archive}")
    folder_name, ranges = TARGETS[archive]
    found = donor_files(donor / "data/graphics/pokegra" / folder_name)
    sections = []
    info = {"archive": archive, "folder": folder_name, "sections": [],
            "base_species": KALOS_SPECIES, "extra_form_groups":
                EXTRA_FORM_GROUPS if len(ranges) > 1 else 0}
    for at, start, count in ranges:
        missing = [n for n in range(start, start + count) if n not in found]
        if missing:
            raise ValueError(
                f"{archive}: {len(missing)} missing donor files, first: {missing[:8]}"
            )
        blobs = [found[n].read_bytes() for n in range(start, start + count)]
        sections.append((at, blobs))
        info["sections"].append({
            "insert_at_original_index": at, "donor_first": start,
            "donor_last": start + count - 1, "entries": count,
            "empty_entries": sum(not data for data in blobs),
            "total_bytes": sum(len(data) for data in blobs),
        })
    return sections, info


def splice_members(original: list[bytes], sections: list[tuple[int, list[bytes]]]) -> list[bytes]:
    output: list[bytes] = []
    previous = 0
    for at, records in sections:
        if at < previous or at > len(original):
            raise ValueError(
                f"Invalid original NARC insertion at {at}; "
                f"previous={previous}, base_entries={len(original)}"
            )
        output.extend(original[previous:at])
        output.extend(records)
        previous = at
    output.extend(original[previous:])
    return output


def merge_archive(donor: Path, archive: str, base: Path, output: Path) -> dict:
    if base.resolve() == output.resolve():
        raise ValueError("The original NARC cannot be overwritten")
    sections, info = additions(donor, archive)
    original = read_narc(base.read_bytes())
    merged = splice_members(original, sections)
    added_count = sum(len(records) for _, records in sections)
    if len(merged) != len(original) + added_count:
        raise AssertionError("Member count mismatch after splicing")
    # Verify both donor inserts AND untouched old sprite/egg/form bytes.
    offset = 0
    previous = 0
    for at, data in sections:
        if merged[previous + offset:at + offset] != original[previous:at]:
            raise AssertionError("Vanilla graphics changed before an insertion")
        if merged[at + offset:at + offset + len(data)] != data:
            raise AssertionError("Donor assets differ after an insertion")
        previous = at
        offset += len(data)
    if merged[previous + offset:] != original[previous:]:
        raise AssertionError("Vanilla graphics changed after the last insertion")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(write_narc(merged))
    if read_narc(output.read_bytes()) != merged:
        raise AssertionError(f"{archive} failed NARC readback verification")
    info["base_entries"] = len(original)
    info["output_entries"] = len(merged)
    return info


def palette_header(donor: Path, original_source: Path) -> str:
    """Build the icon palette-bank table without disturbing original icons.

    Black 2's sPokeIconPalettes includes 650 original species, 33 special
    IDs, two reserved indices, the Egg/Manaphy icons and 66 old form
    entries. Donor appends 72 Kalos species and 107 form indices.
    """
    code = original_source.read_text(encoding="utf-8")
    marker = "static const u8 sPokeIconPalettes[] = {"
    if marker not in code:
        raise ValueError("Cannot locate the original icon palette table")
    original = [int(token, 16) for token in
                re.findall(r"0x[0-9a-fA-F]+",
                           code.split(marker, 1)[1].split("};", 1)[0])]
    donor_map = (donor / "data/pokeicon_palette_map.bin").read_bytes()
    if len(original) < 753 or len(donor_map) < 897:
        raise ValueError(
            f"Icon palette tables are too short: original={len(original)}, "
            f"donor={len(donor_map)}"
        )
    # Original entries 650..752 (special IDs + Egg/Manaphy + 66 forms)
    # must remain unchanged after shifting their species positions.
    combined = (original[:650] + list(donor_map[650:722]) +
                original[650:753] + list(donor_map[790:897]))
    if len(combined) != 932:
        raise AssertionError("Expected 932 palette entries for all form groups")
    if any(byte & 0x0F > 15 or byte >> 4 > 15 for byte in combined):
        raise AssertionError("Invalid icon palette bank nibble")
    rows = [
        "    " + ", ".join(f"0x{byte:02x}" for byte in combined[n:n + 16]) + ","
        for n in range(0, len(combined), 16)
    ]
    return ("// Generated from local White2Upgrade palette indexes and the "
            "original Black 2 palette table.\n"
            "// Do not commit generated ROM-derived data.\n"
            "static const u8 sPokeIconPalettes[] = {\n" +
            "\n".join(rows) + "\n};\n")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--donor", type=Path, required=True,
                        help="Local clone of ds-pokemon-hacking/White2Upgrade")
    parser.add_argument("--archive", choices=sorted(TARGETS),
                        help="NARC to import in single-archive mode")
    parser.add_argument("--base-archive", type=Path)
    parser.add_argument("--output-archive", type=Path)
    parser.add_argument("--base-root", type=Path)
    parser.add_argument("--output-root", type=Path)
    parser.add_argument("--palette-header", type=Path,
                        help="Generate a C header defining all 932 icon palette indexes")
    parser.add_argument("--report", type=Path)
    args = parser.parse_args()
    has_single = any(x is not None for x in
                     (args.archive, args.base_archive, args.output_archive))
    has_roots = args.base_root is not None or args.output_root is not None
    if has_single and (not args.archive or not args.base_archive or not args.output_archive):
        parser.error("Provide --archive, --base-archive and --output-archive together")
    if has_roots and (not args.base_root or not args.output_root):
        parser.error("Provide --base-root and --output-root together")
    if has_roots and has_single:
        parser.error("Choose single-archive OR root mode, not both")

    if args.palette_header:
        header = palette_header(args.donor, ROOT / "src/system/poke_icon.c")
        args.palette_header.parent.mkdir(parents=True, exist_ok=True)
        args.palette_header.write_text(header, encoding="utf-8")
        print(f"Generated {args.palette_header} with 932 icon palette entries")
        if not (has_roots or has_single or args.report):
            return

    archives = [args.archive] if has_single else list(TARGETS)
    report = {}
    for archive in archives:
        if has_single:
            report[archive] = merge_archive(
                args.donor, archive, args.base_archive, args.output_archive
            )
        elif has_roots:
            base = args.base_root / archive
            output = args.output_root / archive
            if not base.is_file():
                raise ValueError(f"Missing extracted base NARC: {base}")
            report[archive] = merge_archive(args.donor, archive, base, output)
        else:
            _, report[archive] = additions(args.donor, archive)
    if args.report:
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if not (has_roots or has_single):
        print("Validated donor graphics; no original ROM files changed.")


if __name__ == "__main__":
    main()
