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
import subprocess

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUTPUT_TTF = os.path.join(REPO_ROOT, "godot", "fonts", "NotoSansTC_subset.ttf")
DEFAULT_SRC = r"C:\Windows\Fonts\NotoSansTC-VF.ttf"

SCAN_DIRS = [
    os.path.join(REPO_ROOT, "levels"),
    os.path.join(REPO_ROOT, "godot", "scripts"),
]
SCAN_EXTS = {".txt", ".gd"}

# Always include: ASCII printable + common punctuation + bracket variants
BASE_RANGES = "U+0020-007E,U+2018-201F,U+2026,U+300C-300F,U+3001-3002,U+FF01-FF5E"


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


def build_unicode_arg(chars: set) -> str:
    codepoints = sorted(ord(c) for c in chars)
    hex_list = ",".join(f"U+{cp:04X}" for cp in codepoints)
    return BASE_RANGES + "," + hex_list


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

    unicodes_arg = build_unicode_arg(chars)

    if args.dry_run:
        print("Unicodes:", unicodes_arg[:200], "...")
        return

    # Try fonttools as a module first, then as an installed script
    import shutil
    fonttools_exe = shutil.which("fonttools") or shutil.which("fonttools.exe")
    if fonttools_exe:
        cmd = [fonttools_exe, "subset", args.src]
    else:
        cmd = [sys.executable, "-m", "fonttools", "subset", args.src]
    cmd += [
        f"--unicodes={unicodes_arg}",
        f"--output-file={OUTPUT_TTF}",
        "--no-hinting",
        "--desubroutinize",
    ]

    print(f"Running pyftsubset...")
    print(f"  src:  {args.src}")
    print(f"  dest: {OUTPUT_TTF}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("FAILED:", result.stderr, file=sys.stderr)
        sys.exit(1)

    size_kb = os.path.getsize(OUTPUT_TTF) // 1024
    print(f"Done. Output: {OUTPUT_TTF} ({size_kb} KB)")
    print("Restart Godot editor to reimport the font.")


if __name__ == "__main__":
    main()
