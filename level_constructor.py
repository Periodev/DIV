"""Build main level list from the game's active level source.

Prefer ``godot/scripts/Levels.gd`` because the running game reads that file.
Fall back to legacy ``godot/Level/Level*.txt`` only when needed.
"""

import os
import re
import ast


BASE_HINTS = {
    "diverge": True,
    "pickup": False,
    "converge": False,
    "fetch": False,
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
            parsed_hints = {"diverge": False, "pickup": False, "converge": False, "fetch": False}
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
        hints["fetch"] = True

    return hints


def _unescape_gd_string(raw: str) -> str:
    """Decode a quoted GDScript string literal into a Python string."""
    try:
        return ast.literal_eval(raw)
    except Exception:
        inner = raw[1:-1]
        return bytes(inner, "utf-8").decode("unicode_escape")


def _extract_bracket_block(text: str, start_index: int, open_ch: str, close_ch: str) -> str:
    depth = 0
    in_string = False
    escape = False
    begin = -1

    for i in range(start_index, len(text)):
        ch = text[i]
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue

        if ch == '"':
            in_string = True
            continue
        if ch == open_ch:
            if depth == 0:
                begin = i
            depth += 1
        elif ch == close_ch:
            depth -= 1
            if depth == 0 and begin >= 0:
                return text[begin:i + 1]

    raise ValueError(f"Unclosed block starting at index {start_index}")


def _iter_top_level_dict_blocks(array_block: str):
    i = 0
    while i < len(array_block):
        if array_block[i] == "{":
            block = _extract_bracket_block(array_block, i, "{", "}")
            yield block
            i += len(block)
        else:
            i += 1


def _parse_gd_hints(block: str) -> dict:
    hints_match = re.search(r'"hints"\s*:\s*\{([^}]*)\}', block, flags=re.S)
    hints = {"diverge": False, "pickup": False, "converge": False, "fetch": False}
    if not hints_match:
        return hints

    for key, value in re.findall(r'"([^"]+)"\s*:\s*(true|false)', hints_match.group(1)):
        hints[key] = (value == "true")
    return hints


def _parse_levels_gd(levels_gd_path: str):
    with open(levels_gd_path, "r", encoding="utf-8") as f:
        text = f.read()

    all_match = re.search(r'const\s+ALL\s*:\s*Array\s*=\s*\[', text)
    if not all_match:
        return []

    array_block = _extract_bracket_block(text, all_match.end() - 1, "[", "]")
    levels = []

    for block in _iter_top_level_dict_blocks(array_block):
        id_match = re.search(r'"id"\s*:\s*("([^"\\]|\\.)*")', block)
        if not id_match:
            continue

        zone_match = re.search(r'"zone"\s*:\s*(\d+)', block)
        name_match = re.search(r'"name"\s*:\s*("([^"\\]|\\.)*")', block)
        floor_match = re.search(r'"floor_map"\s*:\s*("([^"\\]|\\.)*")', block)
        object_match = re.search(r'"object_map"\s*:\s*("([^"\\]|\\.)*")', block)
        objective_match = re.search(r'"objective"\s*:\s*("([^"\\]|\\.)*")', block)

        if not (name_match and floor_match and object_match):
            continue

        objective_text = _unescape_gd_string(objective_match.group(1)) if objective_match else ""
        objective_lines = [line.rstrip() for line in objective_text.splitlines()]

        levels.append(
            {
                "id": _unescape_gd_string(id_match.group(1)),
                "zone": int(zone_match.group(1)) if zone_match else None,
                "name": _unescape_gd_string(name_match.group(1)),
                "floor_map": _unescape_gd_string(floor_match.group(1)).strip("\n"),
                "object_map": _unescape_gd_string(object_match.group(1)).strip("\n"),
                "hints": _parse_gd_hints(block),
                "objective": {
                    "title": _unescape_gd_string(name_match.group(1)),
                    "items": objective_lines,
                },
            }
        )

    return levels


def load_main_levels(level_dir: str | None = None):
    base_dir = os.path.dirname(__file__)
    levels_gd_path = os.path.join(base_dir, "godot", "scripts", "Levels.gd")
    if os.path.isfile(levels_gd_path):
        gd_levels = _parse_levels_gd(levels_gd_path)
        if gd_levels:
            return gd_levels

    folder = level_dir or os.path.join(base_dir, "godot", "Level")

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

