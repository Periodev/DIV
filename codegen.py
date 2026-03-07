#!/usr/bin/env python3
"""
codegen.py — Reads levels/Level*.txt, outputs godot/scripts/Levels.gd
Usage: python codegen.py
"""

import re
import sys
from pathlib import Path

ROOT       = Path(__file__).parent
LEVELS_DIR = ROOT / "levels"
OUTPUT     = ROOT / "godot" / "scripts" / "Levels.gd"


# ---------------------------------------------------------------------------
# Hints defaults — mirrors MapParser.gd _hints_for_level exactly
# ---------------------------------------------------------------------------

def _hints_for_level(world_num: int) -> dict:
    h = {"diverge": True, "pickup": False, "converge": False, "fetch": False}
    if world_num >= 1:
        h["pickup"] = True
    if world_num >= 3:
        h["converge"] = True
    if world_num >= 4:
        h["fetch"] = True
    return h


# ---------------------------------------------------------------------------
# Parse one .txt file → list of level dicts
# ---------------------------------------------------------------------------

def parse_txt(path: Path) -> list:
    text = path.read_text(encoding="utf-8")

    m = re.match(r"Level(\d+)\.txt$", path.name, re.IGNORECASE)
    world_num = int(m.group(1)) if m else -1

    sections = re.split(r"\n-{10,}\n", text)
    levels = []
    for idx, section in enumerate(sections):
        level = _parse_section(section.strip(), world_num, idx)
        if level is None:
            continue
        if level["hints"] is None:
            level["hints"] = _hints_for_level(world_num)
        levels.append(level)
    return levels


def _parse_section(text: str, world_num: int, section_idx: int) -> dict | None:
    if not text.strip():
        return None

    # Must have both maps
    floor_m = re.search(r"floor_map\s*=\s*'''([\s\S]*?)'''", text)
    obj_m   = re.search(r"object_map\s*=\s*'''([\s\S]*?)'''", text)
    if not floor_m or not obj_m:
        return None

    name_m = re.search(r"^#\s*(.+)", text, re.MULTILINE)
    name   = name_m.group(1).strip() if name_m else ""

    # name_en: extract English prefix before first CJK character
    name_en = ""
    if name_m:
        raw_name = name
        cjk_idx = next(
            (i for i, ch in enumerate(raw_name)
             if '\u4e00' <= ch <= '\u9fff' or '\u3400' <= ch <= '\u4dbf'),
            None
        )
        if cjk_idx is not None:
            name_en = raw_name[:cjk_idx].strip()

    # hints
    hints_m      = re.search(r"(?m)^\s*hints\s*=\s*(.+?)\s*$", text)
    parsed_hints = None
    if hints_m:
        parsed_hints = {"diverge": False, "pickup": False, "converge": False, "fetch": False}
        for token in hints_m.group(1).strip().split():
            if token in parsed_hints:
                parsed_hints[token] = True

    # objective
    obj_text_m = re.search(r"objective\s*=\s*'''([\s\S]*?)'''", text)
    objective  = obj_text_m.group(1) if obj_text_m else ""

    # objective_en
    obj_en_m   = re.search(r"objective_en\s*=\s*'''([\s\S]*?)'''", text)
    objective_en = obj_en_m.group(1) if obj_en_m else ""

    # tutorial
    tut_m      = re.search(r"(?m)^\s*tutorial\s*=\s*(\S+)\s*$", text)
    tutorial   = tut_m.group(1).strip() if tut_m else ""

    # tutorial_steps
    steps_m       = re.search(r"tutorial_steps\s*=\s*'''([\s\S]*?)'''", text)
    tutorial_steps = []
    if steps_m:
        for line in steps_m.group(1).splitlines():
            s = line.strip()
            if s:
                tutorial_steps.append(s)

    # tutorial_steps_en
    steps_en_m        = re.search(r"tutorial_steps_en\s*=\s*'''([\s\S]*?)'''", text)
    tutorial_steps_en = []
    if steps_en_m:
        for line in steps_en_m.group(1).splitlines():
            s = line.strip()
            if s:
                tutorial_steps_en.append(s)

    # tutorial_display
    td_m             = re.search(r"(?m)^\s*tutorial_display\s*=\s*(\S+)\s*$", text)
    tutorial_display = td_m.group(1).strip() if td_m else ""

    # auto_desc
    ad_m      = re.search(r"(?m)^\s*auto_desc\s*=\s*(\S+)\s*$", text)
    auto_desc = True
    if ad_m:
        auto_desc = ad_m.group(1).strip() != "false"

    level_id = f"{world_num}-{section_idx}" if world_num >= 0 else f"x-{section_idx}"

    result = {
        "id":               level_id,
        "zone":             world_num,
        "name":             name,
        "floor_map":        floor_m.group(1),
        "object_map":       obj_m.group(1),
        "hints":            parsed_hints,
        "objective":        objective,
        "tutorial":         tutorial,
        "tutorial_steps":   tutorial_steps,
        "tutorial_display": tutorial_display,
        "auto_desc":        auto_desc,
    }
    if name_en:
        result["name_en"] = name_en
    if objective_en.strip():
        result["objective_en"] = objective_en
    if tutorial_steps_en:
        result["tutorial_steps_en"] = tutorial_steps_en
    return result


# ---------------------------------------------------------------------------
# GDScript serialisation
# ---------------------------------------------------------------------------

def _gd_str(s: str) -> str:
    return '"' + s.replace("\\", "\\\\").replace('"', '\\"').replace("\n", "\\n").replace("\r", "") + '"'


def _gd_value(v) -> str:
    if isinstance(v, bool):
        return "true" if v else "false"
    if isinstance(v, str):
        return _gd_str(v)
    if isinstance(v, list):
        items = ", ".join(_gd_str(x) if isinstance(x, str) else _gd_value(x) for x in v)
        return f"[{items}]"
    if isinstance(v, dict):
        pairs = ", ".join(f'"{k}": {_gd_value(val)}' for k, val in v.items())
        return "{" + pairs + "}"
    if v is None:
        return "null"
    return str(v)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

KEYS = ["id", "zone", "name", "name_en", "floor_map", "object_map", "hints",
        "objective", "objective_en", "tutorial", "tutorial_steps", "tutorial_steps_en",
        "tutorial_display", "auto_desc"]


def main() -> None:
    level_files = sorted(LEVELS_DIR.glob("Level*.txt"))
    if not level_files:
        print(f"ERROR: No Level*.txt found in {LEVELS_DIR}", file=sys.stderr)
        sys.exit(1)

    all_levels = []
    for f in level_files:
        levels = parse_txt(f)
        print(f"  {f.name}: {len(levels)} levels")
        all_levels.extend(levels)

    lines = [
        "# AUTO-GENERATED by codegen.py — do not edit manually.",
        "# Source: levels/Level*.txt  |  Regenerate: python codegen.py",
        "class_name Levels",
        "",
        "const ALL: Array = [",
    ]
    last = len(all_levels) - 1
    for i, level in enumerate(all_levels):
        lines.append("\t{")
        level_keys = [k for k in KEYS if k in level]
        for ki, key in enumerate(level_keys):
            comma = "," if ki < len(level_keys) - 1 else ""
            lines.append(f'\t\t"{key}": {_gd_value(level[key])}{comma}')
        lines.append("\t}," if i < last else "\t}")
    lines.append("]")
    lines.append("")

    OUTPUT.write_text("\n".join(lines), encoding="utf-8")
    print(f"Written: {OUTPUT}  ({len(all_levels)} levels total)")


if __name__ == "__main__":
    main()
