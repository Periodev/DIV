# LevelSelect.gd - Left panel level list + right map preview
extends Control

@onready var preview: LevelPreview = $Preview

const LEFT_W := 300.0
const LPAD := 12.0

const TITLE_CY := 30.0
const ZONE_HDR_CY := 56.0
const HDIVIDE_Y := 72.0
const LIST_TOP := 80.0
const ITEM_H := 42.0
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
	var gd = _get_game_data()
	if gd == null:
		push_error("LevelSelect: missing /root/GameData autoload")
		return

	_load_levels_if_needed()
	_build_zone_groups()
	gd.load_progress()

	if levels.is_empty():
		queue_redraw()
		return

	current_index = clampi(gd.selected_level_idx, 0, levels.size() - 1)
	_sync_zone_from_index()
	_refresh_preview()
	queue_redraw()


func _unhandled_key_input(event: InputEvent) -> void:
	if not (event is InputEventKey):
		return
	var ke: InputEventKey = event as InputEventKey
	if not ke.pressed or ke.echo:
		return

	match ke.keycode:
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
		KEY_ESCAPE:
			get_tree().change_scene_to_file("res://scenes/settings.tscn")


func _draw() -> void:
	var w: float = size.x
	var h: float = size.y

	draw_rect(Rect2(0, 0, w, h), BG_C)
	draw_line(Vector2(LEFT_W, 0), Vector2(LEFT_W, h), DIV_C, 1.0)

	_draw_text_td("DIV", w * 0.5, TITLE_CY, TITLE_C, 27, HORIZONTAL_ALIGNMENT_CENTER, true)
	_draw_panel()

	_draw_footer(w * 0.5, FOOTER_CY)
	_draw_preview_label()


func _draw_panel() -> void:
	if levels.is_empty() or sorted_worlds.is_empty():
		_draw_text_td(Loc.t("ls_no_levels"), LEFT_W * 0.5, LIST_TOP, Color8(255, 120, 120), 21, HORIZONTAL_ALIGNMENT_CENTER)
		return
	var gd = _get_game_data()

	var world: int = sorted_worlds[current_zone]
	var world_text: String = Loc.t("ls_zone") % world
	var prefix: String = "< " if current_zone > 0 else "  "
	var suffix: String = " >" if current_zone < sorted_worlds.size() - 1 else "  "
	_draw_text_td(prefix + world_text + suffix, LEFT_W * 0.5, ZONE_HDR_CY, ZONE_C, 20, HORIZONTAL_ALIGNMENT_CENTER, true)

	draw_line(Vector2(0, HDIVIDE_Y), Vector2(LEFT_W, HDIVIDE_Y), DIV_C, 1.0)

	var indices: Array = world_indices.get(world, [])
	for slot in indices.size():
		var idx: int = indices[slot]
		var item_top: float = LIST_TOP + slot * ITEM_H
		var item_cy: float = item_top + ITEM_H * 0.5
		var selected: bool = idx == current_index

		if selected:
			draw_rect(Rect2(0, item_top, LEFT_W, ITEM_H), SEL_BG_C)

		var level: Dictionary = levels[idx] as Dictionary
		var level_id: String = str(level.get("id", ""))
		var x: float = LPAD
		if gd != null and gd.is_level_played(level_id):
			_draw_text_td(Loc.t("ls_done"), x, item_cy, DONE_C, 15, HORIZONTAL_ALIGNMENT_LEFT, true)
			x += 57.0

		var name_text: String = gd.level_text(level, "name") if gd != null else str(level.get("name", "Level %d" % idx))
		var name_color: Color = SEL_TEXT_C if selected else TEXT_C
		var name_size: int = 20 if selected else 18
		_draw_text_td(name_text, x, item_cy, name_color, name_size, HORIZONTAL_ALIGNMENT_LEFT, true)


func _draw_preview_label() -> void:
	if levels.is_empty() or current_index < 0 or current_index >= levels.size():
		return

	var level: Dictionary = levels[current_index] as Dictionary
	var level_id: String = str(level.get("id", ""))
	var gd_preview = _get_game_data()
	var name_text: String = gd_preview.level_text(level, "name") if gd_preview != null else str(level.get("name", ""))
	var grid_px: int = preview.get_grid_px()
	if grid_px <= 0:
		grid_px = PREVIEW_GRID_PX

	var label_y: float = (PREVIEW_Y + grid_px + FOOTER_CY) * 0.5
	_draw_text_td(
		"%s  %s" % [level_id, name_text],
		PREVIEW_X + grid_px * 0.5,
		label_y,
		TEXT_C,
		21,
		HORIZONTAL_ALIGNMENT_CENTER,
		true
	)


func _draw_footer(cx: float, cy: float) -> void:
	var fs := 17
	var font: Font = ThemeDB.fallback_font
	if font == null:
		return
	var r := 4.5
	var seg1: String = Loc.t("ls_footer1")
	var seg2: String = Loc.t("ls_footer2")
	var w1 := font.get_string_size(seg1, HORIZONTAL_ALIGNMENT_LEFT, -1.0, fs).x
	var w2 := font.get_string_size(seg2, HORIZONTAL_ALIGNMENT_LEFT, -1.0, fs).x
	var pair_vw := r * 2.8   # ↑↓ pair width
	var pair_hw := r * 5.0   # ← → pair width
	var total_w := pair_vw + w1 + pair_hw + w2
	var x := cx - total_w * 0.5
	var baseline := cy + fs * 0.35
	# ↑↓
	_draw_tri_v(x + r * 1.4, cy - r - 1.0, r, true, MUTED_C)
	_draw_tri_v(x + r * 1.4, cy + r + 1.0, r, false, MUTED_C)
	x += pair_vw
	draw_string(font, Vector2(x, baseline), seg1, HORIZONTAL_ALIGNMENT_LEFT, -1.0, fs, MUTED_C)
	x += w1
	# ← →
	_draw_tri_h(x + r * 1.4, cy, r, true, MUTED_C)
	_draw_tri_h(x + r * 1.4 + r * 3.2, cy, r, false, MUTED_C)
	x += pair_hw
	draw_string(font, Vector2(x, baseline), seg2, HORIZONTAL_ALIGNMENT_LEFT, -1.0, fs, MUTED_C)


func _draw_tri_v(px: float, py: float, r: float, up: bool, color: Color) -> void:
	var s := r * 1.2
	var pts: PackedVector2Array
	if up:
		pts = PackedVector2Array([Vector2(px, py - r), Vector2(px + s, py + r), Vector2(px - s, py + r)])
	else:
		pts = PackedVector2Array([Vector2(px, py + r), Vector2(px + s, py - r), Vector2(px - s, py - r)])
	draw_polygon(pts, PackedColorArray([color, color, color]))


func _draw_tri_h(px: float, py: float, r: float, left: bool, color: Color) -> void:
	var s := r * 1.2
	var pts: PackedVector2Array
	if left:
		pts = PackedVector2Array([Vector2(px - r, py), Vector2(px + r, py - s), Vector2(px + r, py + s)])
	else:
		pts = PackedVector2Array([Vector2(px + r, py), Vector2(px - r, py - s), Vector2(px - r, py + s)])
	draw_polygon(pts, PackedColorArray([color, color, color]))


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
	var font: Font = ThemeDB.fallback_font
	if font == null:
		return
	var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x

	var baseline_y: float = y_td + (font_size * 0.35 if center_y else 0.0)
	var draw_x: float = x
	if align == HORIZONTAL_ALIGNMENT_CENTER:
		draw_x = x - text_w * 0.5
	elif align == HORIZONTAL_ALIGNMENT_RIGHT:
		draw_x = x - text_w

	draw_string(font, Vector2(draw_x, baseline_y), text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, color)


func _load_levels_if_needed() -> void:
	var gd = _get_game_data()
	if gd == null:
		push_error("LevelSelect: missing /root/GameData autoload")
		levels = []
		return

	if gd.all_levels.is_empty():
		gd.all_levels.append_array(Levels.ALL)

	levels = gd.all_levels


func _build_zone_groups() -> void:
	sorted_worlds.clear()
	world_indices.clear()

	for i in levels.size():
		var level: Dictionary = levels[i] as Dictionary
		var world: int = int(level.get("zone", 0))
		if not world_indices.has(world):
			world_indices[world] = []
		var arr: Array = world_indices[world]
		arr.append(i)
		world_indices[world] = arr

	var worlds: Array = world_indices.keys()
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

	var pos: int = indices.find(current_index)
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

	var level: Dictionary = levels[current_index] as Dictionary
	var level_id: String = str(level.get("id", ""))
	if level_id == "":
		preview.set_state(null)
		return

	if not preview_states.has(level_id):
		var source: LevelSource = MapParser.parse_dual_layer(
			str(level.get("floor_map", "")),
			str(level.get("object_map", ""))
		)
		preview_states[level_id] = source.init_branch() if source != null else null

	preview.position = Vector2(PREVIEW_X, PREVIEW_Y)
	preview.map_pixel_size = PREVIEW_GRID_PX
	var state_obj = preview_states[level_id]
	var state: BranchState = state_obj as BranchState
	preview.set_state(state)


func _start_level() -> void:
	if levels.is_empty():
		return
	var gd = _get_game_data()
	if gd != null:
		gd.selected_level_idx = current_index
	get_tree().change_scene_to_file("res://scenes/game_scene.tscn")


func _get_game_data():
	return get_node_or_null("/root/GameData")
