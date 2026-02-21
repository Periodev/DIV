"""Build main level list from ASCII map files under /Level."""

import os
import re


BASE_HINTS = {
    "diverge": True,
    "pickup": False,
    "converge": False,
    "inherit": False,
}


def _clean_map_block(block: str) -> str:
    lines = [line.rstrip() for line in block.strip().splitlines()]
    return "\n".join(lines)


def _parse_sections(text: str):
    sections = re.split(r"^\s*-{4,}\s*$", text.replace("\r", ""), flags=re.MULTILINE)
    for section in sections:
        content = section.strip()
        if not content:
            continue

        floor_match = re.search(r"floor_map\s*=\s*'''([\s\S]*?)'''", content, flags=re.MULTILINE)
        object_match = re.search(r"object_map\s*=\s*'''([\s\S]*?)'''", content, flags=re.MULTILINE)
        if not floor_match or not object_match:
            continue

        name_match = re.search(r"^\s*#\s*(.+?)\s*$", content, flags=re.MULTILINE)
        name = name_match.group(1).strip() if name_match else ""

        obj_match = re.search(r"objective\s*=\s*'''([\s\S]*?)'''", content, flags=re.MULTILINE)
        objective_items = [line.rstrip() for line in obj_match.group(1).splitlines()] if obj_match else None

        hints_match = re.search(r"^\s*hints\s*=\s*(.+?)\s*$", content, flags=re.MULTILINE)
        if hints_match:
            tokens = hints_match.group(1).strip().split()
            parsed_hints = {"diverge": False, "pickup": False, "converge": False, "inherit": False}
            if tokens != ["none"]:
                for token in tokens:
                    if token in parsed_hints:
                        parsed_hints[token] = True
        else:
            parsed_hints = None

        yield {
            "name": name,
            "floor_map": _clean_map_block(floor_match.group(1)),
            "object_map": _clean_map_block(object_match.group(1)),
            "objective_items": objective_items,
            "parsed_hints": parsed_hints,
        }


def _hints_for_level(world_num: int, level_num: int):
    """
    Progressive unlocks (union):
    - Zone 0: base controls available (movement always on)
    - Zone 1: from 1-3 onward, unlock converge
    - Zone 3: unlock pickup
    """
    hints = BASE_HINTS.copy()

    # Zone 1 special unlock point
    if world_num >= 1:
        hints["converge"] = True

    # Zone 3 unlock
    if world_num >= 3:
        hints["pickup"] = True

    # Zone 4 unlock
    if world_num >= 4:
        hints["inherit"] = True

    return hints


def load_main_levels(level_dir: str | None = None):
    base_dir = os.path.dirname(__file__)
    folder = level_dir or os.path.join(base_dir, "Level")

    if not os.path.isdir(folder):
        return []

    level_files = []
    for filename in os.listdir(folder):
        match = re.fullmatch(r"Level(\d+)\.txt", filename)
        if match:
            level_files.append((int(match.group(1)), filename))
    level_files.sort(key=lambda item: item[0])

    levels = []
    for world_num, filename in level_files:
        path = os.path.join(folder, filename)
        with open(path, "r", encoding="utf-8") as f:
            raw_text = f.read()

        parsed = list(_parse_sections(raw_text))
        for idx, item in enumerate(parsed, start=1):
            level_id = f"{world_num}-{idx}"
            level_name = item["name"] or f"Level {level_id}"
            objective_items = item["objective_items"]
            objective = {"title": level_name, "items": objective_items} if objective_items is not None else None
            hints = item["parsed_hints"] if item["parsed_hints"] is not None else _hints_for_level(world_num, idx)
            levels.append(
                {
                    "id": level_id,
                    "name": level_name,
                    "floor_map": item["floor_map"],
                    "object_map": item["object_map"],
                    "hints": hints,
                    "objective": objective,
                }
            )

    return levels


MAIN_LEVELS = load_main_levels()
