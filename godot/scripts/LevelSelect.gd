# LevelSelect.gd - Left panel level list + right map preview
extends Control

@onready var preview: LevelPreview = $Preview

const LEFT_W := 300.0
const LPAD := 12.0

const TITLE_CY := 30.0
const ZONE_HDR_CY := 56.0
const HDIVIDE_Y := 72.0
const LIST_TOP := 80.0
const ITEM_H := 28.0
const FOOTER_CY := 706.0

const PREVIEW_X := 400.0
const PREVIEW_Y := 120.0
const PREVIEW_GRID_PX := 480

const BG_C := Color8(20, 20, 25)
const TEXT_C := Color8(220, 220, 220)
const MUTED_C := Color8(120, 120, 130)
const TITLE_C := Color8(96, 165, 250)
const SEL_BG_C := Color8(40, 80, 120)
const SEL_TEXT_C := Color8(96, 165, 250)
const DONE_C := Color8(80, 200, 120)
const DIV_C := Color8(50, 55, 65)
const ZONE_C := Color8(150, 200, 255)

var levels: Array = []
var preview_states: Dictionary = {}  # level_id -> BranchState

var sorted_worlds: Array[int] = []
var world_indices: Dictionary = {}   # world(int) -> Array[int]

var current_zone: int = 0
var current_index: int = 0


func _ready() -> void:
    set_process_unhandled_key_input(true)

    _load_levels_if_needed()
    _build_zone_groups()
    GameData.load_progress()

    if levels.is_empty():
        queue_redraw()
        return

    current_index = clampi(GameData.selected_level_idx, 0, levels.size() - 1)
    _sync_zone_from_index()
    _refresh_preview()
    queue_redraw()


func _unhandled_key_input(event: InputEvent) -> void:
    if not (event is InputEventKey):
        return
    var ke := event as InputEventKey
    if not ke.pressed or ke.echo:
        return

    match ke.keycode:
        KEY_ESCAPE:
            get_tree().quit()
        KEY_TAB:
            _switch_zone(-1 if ke.shift_pressed else 1)
        KEY_LEFT, KEY_A:
            _switch_zone(-1)
        KEY_RIGHT, KEY_D:
            _switch_zone(1)
        KEY_UP, KEY_W:
            _move_cursor(-1)
        KEY_DOWN, KEY_S:
            _move_cursor(1)
        KEY_ENTER, KEY_KP_ENTER, KEY_SPACE:
            _start_level()


func _draw() -> void:
    var w := size.x
    var h := size.y

    draw_rect(Rect2(0, 0, w, h), BG_C)
    draw_line(Vector2(LEFT_W, 0), Vector2(LEFT_W, h), DIV_C, 1.0)

    _draw_text_td("DIV", w * 0.5, TITLE_CY, TITLE_C, 18, HORIZONTAL_ALIGNMENT_CENTER, true)
    _draw_panel()

    var footer := "Arrows/WASD: select   Tab: zone   Enter/Space: start   Esc: exit"
    _draw_text_td(footer, w * 0.5, FOOTER_CY, MUTED_C, 11, HORIZONTAL_ALIGNMENT_CENTER, true)
    _draw_preview_label()


func _draw_panel() -> void:
    if levels.is_empty() or sorted_worlds.is_empty():
        _draw_text_td("No levels found", LEFT_W * 0.5, LIST_TOP, Color8(255, 120, 120), 14, HORIZONTAL_ALIGNMENT_CENTER)
        return

    var world: int = sorted_worlds[current_zone]
    var world_text := "Zone %d" % world
    var prefix := "< " if current_zone > 0 else "  "
    var suffix := " >" if current_zone < sorted_worlds.size() - 1 else "  "
    _draw_text_td(prefix + world_text + suffix, LEFT_W * 0.5, ZONE_HDR_CY, ZONE_C, 13, HORIZONTAL_ALIGNMENT_CENTER, true)

    draw_line(Vector2(0, HDIVIDE_Y), Vector2(LEFT_W, HDIVIDE_Y), DIV_C, 1.0)

    var indices: Array = world_indices.get(world, [])
    for slot in indices.size():
        var idx: int = indices[slot]
        var item_top := LIST_TOP + slot * ITEM_H
        var item_cy := item_top + ITEM_H * 0.5
        var selected := idx == current_index

        if selected:
            draw_rect(Rect2(0, item_top, LEFT_W, ITEM_H), SEL_BG_C)

        var level := levels[idx] as Dictionary
        var level_id := str(level.get("id", ""))
        var x := LPAD
        if GameData.is_level_played(level_id):
            _draw_text_td("Done", x, item_cy, DONE_C, 10, HORIZONTAL_ALIGNMENT_LEFT, true)
            x += 38.0

        var name_text := str(level.get("name", "Level %d" % idx))
        var name_color := SEL_TEXT_C if selected else TEXT_C
        var name_size := 13 if selected else 12
        _draw_text_td(name_text, x, item_cy, name_color, name_size, HORIZONTAL_ALIGNMENT_LEFT, true)


func _draw_preview_label() -> void:
    if levels.is_empty() or current_index < 0 or current_index >= levels.size():
        return

    var level := levels[current_index] as Dictionary
    var level_id := str(level.get("id", ""))
    var name_text := str(level.get("name", ""))
    var grid_px := preview.get_grid_px()
    if grid_px <= 0:
        grid_px = PREVIEW_GRID_PX

    var label_y := (PREVIEW_Y + grid_px + FOOTER_CY) * 0.5
    _draw_text_td(
        "%s  %s" % [level_id, name_text],
        PREVIEW_X + grid_px * 0.5,
        label_y,
        TEXT_C,
        14,
        HORIZONTAL_ALIGNMENT_CENTER,
        true
    )


func _draw_text_td(
    text: String,
    x: float,
    y_td: float,
    color: Color,
    font_size: int,
    align: int = HORIZONTAL_ALIGNMENT_LEFT,
    center_y: bool = false
) -> void:
    if text == "":
        return
    var font := ThemeDB.fallback_font
    if font == null:
        return

    var baseline_y := y_td
    if center_y:
        baseline_y += font_size * 0.35

    draw_string(font, Vector2(x, baseline_y), text, align, -1.0, font_size, color)


func _load_levels_if_needed() -> void:
    var needs_rebuild := GameData.all_levels.is_empty()
    if not needs_rebuild:
        var first_raw = GameData.all_levels[0]
        if typeof(first_raw) != TYPE_DICTIONARY:
            needs_rebuild = true
        else:
            var first := first_raw as Dictionary
            needs_rebuild = not first.has("id") or not first.has("zone")

    if needs_rebuild:
        var built_levels: Array = []
        var zone_files := [
            "res://Level/Level0.txt",
            "res://Level/Level1.txt",
            "res://Level/Level2.txt",
            "res://Level/Level3.txt",
            "res://Level/Level4.txt",
        ]

        for world in zone_files.size():
            var parsed := MapParser.parse_level_resource(zone_files[world])
            for i in parsed.size():
                var lv := (parsed[i] as Dictionary).duplicate(true)
                lv["id"] = "%d-%d" % [world, i + 1]
                lv["zone"] = world
                built_levels.append(lv)

        GameData.all_levels = built_levels

    levels = GameData.all_levels


func _build_zone_groups() -> void:
    sorted_worlds.clear()
    world_indices.clear()

    for i in levels.size():
        var level := levels[i] as Dictionary
        var world: int = int(level.get("zone", 0))
        if not world_indices.has(world):
            world_indices[world] = []
        var arr: Array = world_indices[world]
        arr.append(i)
        world_indices[world] = arr

    var worlds := world_indices.keys()
    worlds.sort()
    for w in worlds:
        sorted_worlds.append(int(w))


func _sync_zone_from_index() -> void:
    if sorted_worlds.is_empty():
        current_zone = 0
        return

    for z in sorted_worlds.size():
        var world: int = sorted_worlds[z]
        var indices: Array = world_indices.get(world, [])
        if indices.has(current_index):
            current_zone = z
            return

    current_zone = 0
    var fallback_world: int = sorted_worlds[0]
    var fallback_indices: Array = world_indices.get(fallback_world, [])
    if not fallback_indices.is_empty():
        current_index = fallback_indices[0]


func _switch_zone(delta: int) -> void:
    if sorted_worlds.is_empty():
        return

    current_zone = posmod(current_zone + delta, sorted_worlds.size())
    var world: int = sorted_worlds[current_zone]
    var indices: Array = world_indices.get(world, [])
    if not indices.is_empty():
        current_index = indices[0]

    _refresh_preview()
    queue_redraw()


func _move_cursor(delta: int) -> void:
    if sorted_worlds.is_empty():
        return

    var world: int = sorted_worlds[current_zone]
    var indices: Array = world_indices.get(world, [])
    if indices.is_empty():
        return

    var pos := indices.find(current_index)
    if pos == -1:
        current_index = indices[0]
    else:
        current_index = indices[posmod(pos + delta, indices.size())]

    _refresh_preview()
    queue_redraw()


func _refresh_preview() -> void:
    if levels.is_empty() or current_index < 0 or current_index >= levels.size():
        preview.set_state(null)
        return

    var level := levels[current_index] as Dictionary
    var level_id := str(level.get("id", ""))
    if level_id == "":
        preview.set_state(null)
        return

    if not preview_states.has(level_id):
        var source := MapParser.parse_dual_layer(
            str(level.get("floor_map", "")),
            str(level.get("object_map", ""))
        )
        preview_states[level_id] = source.init_branch() if source != null else null

    preview.position = Vector2(PREVIEW_X, PREVIEW_Y)
    preview.map_pixel_size = PREVIEW_GRID_PX
    var state_obj = preview_states[level_id]
    var state := state_obj as BranchState
    preview.set_state(state)


func _start_level() -> void:
    if levels.is_empty():
        return
    GameData.selected_level_idx = current_index
    get_tree().change_scene_to_file("res://scenes/game_scene.tscn")
