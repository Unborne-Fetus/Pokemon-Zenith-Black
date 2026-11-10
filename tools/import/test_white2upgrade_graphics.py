#!/usr/bin/env python3
"""ROM-free regression tests for Kalos graphics archive and palette indexing.

Run with a local donor clone:
    ZENITH_GRAPHICS_TEST_DONOR=../White2Upgrade python3 -m unittest \
        tools.import.test_white2upgrade_graphics
"""
from __future__ import annotations

import os
import re
import tempfile
import unittest
from pathlib import Path

from tools.data.narc import read_narc, write_narc
from importlib import import_module

graphics = import_module("tools.import.white2upgrade_graphics")
ROOT = graphics.ROOT
TARGETS = graphics.TARGETS
additions = graphics.additions
merge_archive = graphics.merge_archive
palette_header = graphics.palette_header
splice_members = graphics.splice_members

BASE_COUNTS = {"a/0/0/4": 15065, "a/0/0/7": 1510, "a/1/6/5": 690}
INSERT_COUNTS = {"a/0/0/4": 3580, "a/0/0/7": 358, "a/1/6/5": 72}
CHECKS = {
    "a/0/0/4": {
        13000: ("donor", 13000),
        14440: ("base", 13000),
        15100: ("base", 13660),  # Original Egg battle sprite
        15140: ("base", 13700),  # First original form
        16460: ("donor", 15800),  # First new form (form offset 66)
        18600: ("base", 15020),  # Substitute
        18613: ("base", 15033),  # Arceus palette
    },
    "a/0/0/7": {
        1308: ("donor", 1308),
        1452: ("base", 1308),
        1518: ("base", 1374),  # Original Egg icon
        1522: ("base", 1378),  # Original form icon
        1654: ("donor", 1588),  # New form icon
    },
    "a/1/6/5": {
        655: ("donor", 655),
        727: ("base", 655),
    },
}


class KalosGraphicsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.donor = Path(os.environ.get(
            "ZENITH_GRAPHICS_TEST_DONOR", "../White2Upgrade")).resolve()
        if not (cls.donor / "data/graphics/pokegra/battle_sprites").is_dir():
            raise RuntimeError(
                f"Need White2Upgrade checkout for graphics tests: {cls.donor}"
            )

    def test_donor_ranges_complete(self):
        for archive in TARGETS:
            with self.subTest(archive=archive):
                sections, manifest = additions(self.donor, archive)
                self.assertEqual(
                    sum(len(data) for _, data in sections),
                    INSERT_COUNTS[archive],
                )
                self.assertEqual(
                    len(manifest["sections"]), len(TARGETS[archive][1])
                )

    def test_graphics_roundtrip_and_original_id_preservation(self):
        with tempfile.TemporaryDirectory() as directory:
            work = Path(directory)
            for archive, count in BASE_COUNTS.items():
                with self.subTest(archive=archive):
                    # Synthetic 4-byte values reveal original member IDs.
                    base = [n.to_bytes(4, "little") for n in range(count)]
                    original_path = work / "base" / archive
                    original_path.parent.mkdir(parents=True, exist_ok=True)
                    original_path.write_bytes(write_narc(base))
                    output = work / "patched" / archive
                    info = merge_archive(self.donor, archive, original_path, output)
                    merged = read_narc(output.read_bytes())
                    donor_sections, _ = additions(self.donor, archive)
                    inserted = dict(
                        (original_at, data) for original_at, data in donor_sections
                    )
                    self.assertEqual(len(merged), count + INSERT_COUNTS[archive])
                    self.assertEqual(info["base_entries"], count)
                    self.assertEqual(info["output_entries"], len(merged))
                    for result_index, (kind, source_index) in CHECKS[archive].items():
                        if kind == "base":
                            self.assertEqual(
                                merged[result_index], base[source_index]
                            )
                        else:
                            self.assertIn(
                                merged[result_index],
                                [member for values in inserted.values()
                                 for member in values],
                            )
                    self.assertEqual(merged[0], base[0])
                    # Icons append their extra forms *after* the old last
                    # icon, so the original tail is no longer the archive tail.
                    old_tail = (count - 1 + 144 if archive == "a/0/0/7"
                                else len(merged) - 1)
                    self.assertEqual(merged[old_tail], base[-1])

    def test_icon_palette_table_has_all_new_forms(self):
        header = palette_header(
            self.donor, ROOT / "src/system/poke_icon.c"
        )
        start = header.index("static const u8 sPokeIconPalettes[]")
        values = [int(s, 16) for s in
                  re.findall(r"0x[0-9a-fA-F]{2}", header[start:])]
        self.assertEqual(len(values), 932)
        donor_map = (self.donor / "data/pokeicon_palette_map.bin").read_bytes()
        self.assertEqual(values[650:722], list(donor_map[650:722]))
        self.assertEqual(values[825:932], list(donor_map[790:897]))
        self.assertEqual(values[0], 0)

    def test_reject_corrupt_insert_position(self):
        with self.assertRaises(ValueError):
            splice_members([b"x"], [(2, [b"y"])])


if __name__ == "__main__":
    unittest.main()
