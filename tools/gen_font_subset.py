#!/usr/bin/env python3
"""
gen_font_subset.py — Rebuild NotoSansTC_subset.ttf from all project text.

Usage:
    python tools/gen_font_subset.py

Requires:
    fonttools  (pip install fonttools)
    Source font: C:/Windows/Fonts/NotoSansTC-VF.ttf  (or override with --src)

Run this script whenever level text or UI strings are updated.
"""

import os
import sys
import argparse

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_TTF = os.path.join(REPO_ROOT, "godot", "fonts", "NotoSansTC_subset.ttf")
DEFAULT_SRC = r"C:\Windows\Fonts\NotoSansTC-VF.ttf"

SCAN_DIRS = [
    os.path.join(REPO_ROOT, "levels"),
    os.path.join(REPO_ROOT, "godot", "scripts"),
]
SCAN_EXTS = {".txt", ".gd"}

# Always include: ASCII printable + common punctuation + bracket variants
BASE_UNICODES = list(range(0x0020, 0x007F)) + [
    0x2018, 0x2019, 0x201C, 0x201D, 0x2026,
    0x3001, 0x3002, 0x300C, 0x300D, 0x300E, 0x300F,
    *range(0xFF01, 0xFF5F),
]


def collect_chars() -> set:
    chars = set()
    for scan_dir in SCAN_DIRS:
        if not os.path.isdir(scan_dir):
            continue
        for fname in os.listdir(scan_dir):
            if os.path.splitext(fname)[1] not in SCAN_EXTS:
                continue
            fpath = os.path.join(scan_dir, fname)
            with open(fpath, encoding="utf-8", errors="ignore") as fh:
                for ch in fh.read():
                    if ord(ch) > 127:
                        chars.add(ch)
    return chars


def main():
    parser = argparse.ArgumentParser(description="Rebuild NotoSansTC font subset")
    parser.add_argument("--src", default=DEFAULT_SRC, help="Source NotoSansTC TTF/VF path")
    parser.add_argument("--dry-run", action="store_true", help="Print chars only, don't rebuild")
    args = parser.parse_args()

    if not os.path.isfile(args.src):
        print(f"ERROR: Source font not found: {args.src}", file=sys.stderr)
        print("Provide path with --src /path/to/NotoSansTC.ttf", file=sys.stderr)
        sys.exit(1)

    chars = collect_chars()
    print(f"Collected {len(chars)} unique non-ASCII characters from project")

    if args.dry_run:
        print("Sample:", "".join(sorted(chars)[:80]))
        return

    try:
        from fontTools import subset as ft_subset
    except ImportError:
        print("ERROR: fonttools not found. Run: pip install fonttools", file=sys.stderr)
        sys.exit(1)

    codepoints = sorted(set(BASE_UNICODES) | {ord(c) for c in chars})
    unicodes_str = ",".join(f"U+{cp:04X}" for cp in codepoints)

    print(f"  src:  {args.src}")
    print(f"  dest: {OUTPUT_TTF}")

    ft_subset.main([
        args.src,
        f"--unicodes={unicodes_str}",
        f"--output-file={OUTPUT_TTF}",
        "--no-hinting",
        "--desubroutinize",
    ])

    size_kb = os.path.getsize(OUTPUT_TTF) // 1024
    print(f"Done. {OUTPUT_TTF} ({size_kb} KB)")
    print("Restart Godot editor to reimport the font.")


if __name__ == "__main__":
    main()
