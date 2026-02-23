# LevelPreview.gd - Static level preview used by level select
extends Node2D
class_name LevelPreview

var branch_state: BranchState = null
var map_pixel_size: int = 480

const BASE_CELL_SIZE := 80.0

const COLOR_FLOOR       := Color8(255, 255, 255)
const COLOR_WALL        := Color8(0, 0, 0)
const COLOR_GOAL        := Color8(255, 200, 0)
const COLOR_SWITCH_OFF  := Color8(200, 200, 200)
const COLOR_SWITCH_ON   := Color8(255, 200, 0)
const COLOR_SWITCH_INNER:= Color8(90, 90, 90)
const COLOR_SWITCH_ON_B := Color8(160, 120, 0)
const COLOR_HOLE        := Color8(60, 40, 20)
const COLOR_NO_CARRY    := Color8(255, 100, 100)
const COLOR_GRID        := Color8(200, 200, 200)
const COLOR_BRANCH      := Color8(50, 150, 50)
const COLOR_PLAYER      := Color8(0, 100, 200)
const COLOR_TEXT        := Color8(0, 0, 0)

const BOX_COLORS: Array[Color] = [
	Color8(220, 50, 50),
	Color8(50, 130, 220),
	Color8(50, 200, 80),
	Color8(255, 180, 0),
	Color8(180, 80, 220),
	Color8(0, 210, 210),
	Color8(240, 100, 160),
	Color8(255, 220, 50),
	Color8(255, 130, 40),
	Color8(100, 220, 180),
]


func set_state(state: BranchState) -> void:
	branch_state = state
	queue_redraw()


func get_grid_px() -> int:
	if branch_state == null or branch_state.grid_size <= 0:
		return 0
	var s: int = _cell_size()
	return s * branch_state.grid_size


func _draw() -> void:
	if branch_state == null or branch_state.grid_size <= 0:
		return

	var gs: int = branch_state.grid_size
	var s: int = _cell_size()
	var cell_scale: float = float(s) / BASE_CELL_SIZE

	for y in gs:
		for x in gs:
			var pos: Vector2i = Vector2i(x, y)
			var tt: int = branch_state.terrain.get(pos, Enums.TerrainType.FLOOR)
			var rect: Rect2 = Rect2(float(x * s), float(y * s), float(s), float(s))
			_draw_terrain_cell(rect, tt, pos, cell_scale)

	_draw_boxes(s, cell_scale)
	_draw_player(s)
	_draw_grid(s, cell_scale)


func _draw_terrain_cell(rect: Rect2, terrain_type: int, pos: Vector2i, cell_scale: float) -> void:
	match terrain_type:
		Enums.TerrainType.WALL:
			draw_rect(rect, COLOR_WALL)
		Enums.TerrainType.GOAL:
			draw_rect(rect, COLOR_GOAL)
			_draw_text_in_rect("Goal", rect, int(14 * cell_scale), COLOR_TEXT)
		Enums.TerrainType.SWITCH:
			var active: bool = branch_state.switch_activated(pos)
			draw_rect(rect, COLOR_SWITCH_ON if active else COLOR_SWITCH_OFF)
			if not active:
				var inner: int = maxi(4, int(rect.size.x * 0.28))
				var inner_rect: Rect2 = Rect2(
					rect.position.x + (rect.size.x - inner) * 0.5,
					rect.position.y + (rect.size.y - inner) * 0.5,
					float(inner),
					float(inner)
				)
				draw_rect(inner_rect, COLOR_SWITCH_INNER)
		Enums.TerrainType.HOLE:
			draw_rect(rect, COLOR_HOLE)
		Enums.TerrainType.NO_CARRY:
			draw_rect(rect, COLOR_NO_CARRY)
		Enums.TerrainType.BRANCH1, Enums.TerrainType.BRANCH2, Enums.TerrainType.BRANCH3, Enums.TerrainType.BRANCH4:
			draw_rect(rect, COLOR_FLOOR)
			_draw_branch_marker(rect.get_center(), terrain_type, cell_scale)
		_:
			draw_rect(rect, COLOR_FLOOR)


func _draw_branch_marker(center: Vector2, terrain_type: int, cell_scale: float) -> void:
	var uses_map: Dictionary = {
		Enums.TerrainType.BRANCH1: 1,
		Enums.TerrainType.BRANCH2: 2,
		Enums.TerrainType.BRANCH3: 3,
		Enums.TerrainType.BRANCH4: 4,
	}
	var uses: int = uses_map.get(terrain_type, 1)
	var base_radius: float = maxf(2.0, 4.0 * cell_scale)
	var line_width: float = maxf(1.0, 2.0 * cell_scale)
	for i in range(uses - 1, 0, -1):
		draw_arc(center, base_radius * (i + 1), 0.0, TAU, 20, COLOR_BRANCH, line_width, true)
	draw_circle(center, base_radius, COLOR_BRANCH)


func _draw_boxes(cell_size: int, cell_scale: float) -> void:
	for e in branch_state.entities:
		var ent: Entity = e as Entity
		if ent == null or ent.uid == 0:
			continue
		var pad_base: int = 15 if ent.z == -1 else 9
		var pad: int = int(pad_base * cell_scale)
		var rect: Rect2 = Rect2(
			float(ent.pos.x * cell_size + pad),
			float(ent.pos.y * cell_size + pad),
			float(cell_size - pad * 2),
			float(cell_size - pad * 2)
		)
		var fill: Color = BOX_COLORS[(ent.uid - 1) % BOX_COLORS.size()]
		draw_rect(rect, fill)
		draw_rect(rect, COLOR_TEXT, false, max(1.0, 2.0 * cell_scale))
		_draw_text_in_rect(str(ent.uid), rect, int(14 * cell_scale), COLOR_TEXT)


func _draw_player(cell_size: int) -> void:
	var player: Entity = branch_state.get_player()
	if player == null:
		return
	var center: Vector2 = Vector2(
		player.pos.x * cell_size + cell_size * 0.5,
		player.pos.y * cell_size + cell_size * 0.5
	)
	draw_circle(center, cell_size * 0.2, COLOR_PLAYER)


func _draw_grid(cell_size: int, cell_scale: float) -> void:
	var gs: int = branch_state.grid_size
	var thick: float = maxf(1.0, 1.0 * cell_scale)
	for y in gs:
		for x in gs:
			var pos: Vector2i = Vector2i(x, y)
			var tt: int = branch_state.terrain.get(pos, Enums.TerrainType.FLOOR)
			var rect: Rect2 = Rect2(float(x * cell_size), float(y * cell_size), float(cell_size), float(cell_size))

			if tt == Enums.TerrainType.WALL:
				continue
			if tt == Enums.TerrainType.SWITCH:
				var active: bool = branch_state.switch_activated(pos)
				var inset: int = maxi(1, int(3 * cell_scale))
				var c: Color = COLOR_SWITCH_ON_B if active else COLOR_SWITCH_INNER
				var inner_rect: Rect2 = Rect2(
					rect.position.x + inset,
					rect.position.y + inset,
					rect.size.x - inset * 2,
					rect.size.y - inset * 2
				)
				draw_rect(inner_rect, c, false, max(1.0, 3.0 * cell_scale))
			else:
				draw_rect(rect, COLOR_GRID, false, thick)


func _draw_center_text(text: String, center: Vector2, font_size: int, color: Color) -> void:
	var font: Font = ThemeDB.fallback_font
	if font == null or text == "":
		return
	var ascent: float = font.get_ascent(font_size)
	var descent: float = font.get_descent(font_size)
	var baseline_y: float = center.y + (ascent - descent) * 0.5
	draw_string(
		font,
		Vector2(center.x, baseline_y),
		text,
		HORIZONTAL_ALIGNMENT_CENTER,
		-1.0,
		font_size,
		color
	)


func _draw_text_in_rect(text: String, rect: Rect2, font_size: int, color: Color) -> void:
	var font: Font = ThemeDB.fallback_font
	if font == null or text == "":
		return
	var ascent: float = font.get_ascent(font_size)
	var descent: float = font.get_descent(font_size)
	var baseline_y: float = rect.position.y + (rect.size.y + ascent - descent) * 0.5
	draw_string(
		font,
		Vector2(rect.position.x, baseline_y),
		text,
		HORIZONTAL_ALIGNMENT_CENTER,
		rect.size.x,
		font_size,
		color
	)


func _cell_size() -> int:
	return max(1, int(float(map_pixel_size) / branch_state.grid_size))
