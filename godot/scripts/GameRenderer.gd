# GameRenderer.gd - Game panel renderer
# Draws one BranchViewSpec via Godot's _draw() API.
# Colours and structure match LevelPreview + Python render_arc.py.
extends Node2D
class_name GameRenderer

# ---------------------------------------------------------------------------
# Colours — identical to LevelPreview.gd / Python render_arc.py
# ---------------------------------------------------------------------------

const COLOR_BG           := Color8(20, 20, 25)       # DARK_BG
const COLOR_FLOOR        := Color8(255, 255, 255)     # white
const COLOR_WALL         := Color8(0, 0, 0)           # black
const COLOR_GOAL_OFF     := Color8(255, 200, 0)       # amber
const COLOR_GOAL_ON_A    := Color8(255, 255, 100)     # blink frame 0: bright yellow
const COLOR_GOAL_ON_B    := Color8(255, 200, 0)       # blink frame 1: amber
const COLOR_GOAL_BORDER  := Color8(50, 150, 50)       # green border when active
const COLOR_SWITCH_OFF   := Color8(200, 200, 200)
const COLOR_SWITCH_ON    := Color8(255, 200, 0)
const COLOR_SWITCH_INNER := Color8(90, 90, 90)
const COLOR_SWITCH_ON_B  := Color8(160, 120, 0)       # dark amber border (on)
const COLOR_SWITCH_OFF_B := Color8(160, 160, 160)     # border (off)
const COLOR_HOLE         := Color8(60, 40, 20)
const COLOR_NO_CARRY     := Color8(255, 100, 100)
const COLOR_BRANCH       := Color8(50, 150, 50)
const COLOR_GRID         := Color8(200, 200, 200)
const COLOR_PLAYER       := Color8(0, 100, 200)
const COLOR_TEXT         := Color8(0, 0, 0)
const COLOR_FLASH        := Color8(255, 80, 80)
const COLOR_TITLE        := Color8(220, 220, 220)

# Per-UID box colour palette (matches Python BOX_COLORS, uid-1 mod 10)
const BOX_COLORS: Array[Color] = [
	Color8(220,  50,  50),   # Red
	Color8( 50, 130, 220),   # Blue
	Color8( 50, 200,  80),   # Green
	Color8(255, 180,   0),   # Orange
	Color8(180,  80, 220),   # Purple
	Color8(  0, 210, 210),   # Cyan
	Color8(240, 100, 160),   # Pink
	Color8(255, 220,  50),   # Yellow
	Color8(255, 130,  40),   # Deep Orange
	Color8(100, 220, 180),   # Teal
]

const BORDER_W := 3.0


# ---------------------------------------------------------------------------
# Current spec (set by draw_frame)
# ---------------------------------------------------------------------------

var _spec: PresentationModel.BranchViewSpec = null


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

## Called by GameScene every time the visual state changes.
## Sets this node's position from the spec and triggers a redraw.
func draw_frame(spec: PresentationModel.BranchViewSpec) -> void:
	_spec = spec
	if spec != null:
		position = Vector2(spec.pos_x, spec.pos_y)
	queue_redraw()


# ---------------------------------------------------------------------------
# Draw entry point
# ---------------------------------------------------------------------------

func _draw() -> void:
	if _spec == null or _spec.state == null:
		return

	var gs:  int   = _spec.state.grid_size
	var eff: float = _spec.cell_size * _spec.scale   # effective pixel size per cell
	var gpx: float = eff * gs                         # total panel size in pixels
	var a:   float = _spec.alpha

	# Background
	draw_rect(Rect2(0, 0, gpx, gpx), _col(COLOR_BG, a))

	# Terrain fills
	_draw_terrain(gs, eff, a)

	# Grid lines (over terrain, under entities)
	_draw_grid(gs, eff, a)

	# Interaction hint highlight
	if _spec.interaction_hint != null:
		var ih = _spec.interaction_hint
		if ih.target_pos != Vector2i(-1, -1):
			_draw_hint_highlight(ih.target_pos, ih.color, eff, a)

	# Entities
	_draw_entities(gs, eff, a)

	# Flash overlay
	if _spec.flash_intensity > 0.0 and _spec.flash_pos != Vector2i(-1, -1):
		_draw_flash(eff, a)

	# Panel border
	_draw_border(gpx, a)

	# Title above panel
	_draw_title(gpx, a)


# ---------------------------------------------------------------------------
# Terrain
# ---------------------------------------------------------------------------

func _draw_terrain(gs: int, eff: float, a: float) -> void:
	var blink_on: bool = (_spec.animation_frame % 2) == 0

	for y in gs:
		for x in gs:
			var pos  := Vector2i(x, y)
			var tt: int = _spec.state.terrain.get(pos, Enums.TerrainType.FLOOR)
			var rect := Rect2(x * eff, y * eff, eff, eff)
			_draw_terrain_cell(rect, tt, pos, eff, a, blink_on)


func _draw_terrain_cell(
		rect: Rect2, tt: int, pos: Vector2i,
		eff: float, a: float, blink_on: bool) -> void:

	var cell_scale := eff / 80.0

	match tt:
		Enums.TerrainType.WALL:
			draw_rect(rect, _col(COLOR_WALL, a))

		Enums.TerrainType.GOAL:
			if _spec.goal_active:
				var gc := COLOR_GOAL_ON_A if blink_on else COLOR_GOAL_ON_B
				draw_rect(rect, _col(gc, a))
				var inset := maxf(1.0, 3.0 * cell_scale)
				var br    := rect.grow(-inset)
				draw_rect(br, _col(COLOR_GOAL_BORDER, a), false, maxf(1.0, 4.0 * cell_scale))
			else:
				draw_rect(rect, _col(COLOR_GOAL_OFF, a))
			_draw_center_text("Goal", rect.get_center(), int(14.0 * cell_scale), _col(COLOR_TEXT, a))

		Enums.TerrainType.SWITCH:
			var active := _spec.state.switch_activated(pos)
			draw_rect(rect, _col(COLOR_SWITCH_ON if active else COLOR_SWITCH_OFF, a))
			if not active:
				var inner := maxi(4, int(eff * 0.28))
				var ir    := Rect2(
					rect.position.x + (eff - inner) * 0.5,
					rect.position.y + (eff - inner) * 0.5,
					float(inner), float(inner))
				draw_rect(ir, _col(COLOR_SWITCH_INNER, a))

		Enums.TerrainType.HOLE:
			draw_rect(rect, _col(COLOR_HOLE, a))

		Enums.TerrainType.NO_CARRY:
			draw_rect(rect, _col(COLOR_NO_CARRY, a))

		Enums.TerrainType.BRANCH1, Enums.TerrainType.BRANCH2, \
		Enums.TerrainType.BRANCH3, Enums.TerrainType.BRANCH4:
			draw_rect(rect, _col(COLOR_FLOOR, a))
			_draw_branch_marker(rect.get_center(), tt, eff, a)

		_:  # FLOOR and anything else
			draw_rect(rect, _col(COLOR_FLOOR, a))


func _draw_branch_marker(center: Vector2, tt: int, eff: float, a: float) -> void:
	var uses_map := {
		Enums.TerrainType.BRANCH1: 1, Enums.TerrainType.BRANCH2: 2,
		Enums.TerrainType.BRANCH3: 3, Enums.TerrainType.BRANCH4: 4,
	}
	var uses: int = uses_map.get(tt, 1)
	var cell_scale := eff / 80.0
	var br    := maxf(2.0, 4.0 * cell_scale)
	var lw    := maxf(1.0, 2.0 * cell_scale)
	# Highlight if player is standing on this tile and not yet branched
	var mc := COLOR_BRANCH if not _spec.has_branched else Color8(120, 120, 120)
	if _spec.highlight_branch_point:
		mc = Color8(50, 220, 50)  # brighter green when ready to branch
	var col := _col(mc, a)
	for i in range(uses - 1, 0, -1):
		draw_arc(center, br * (i + 1), 0.0, TAU, 20, col, lw, true)
	draw_circle(center, br, col)


# ---------------------------------------------------------------------------
# Grid lines
# ---------------------------------------------------------------------------

func _draw_grid(gs: int, eff: float, a: float) -> void:
	var cell_scale := eff / 80.0
	var thick      := maxf(1.0, 1.0 * cell_scale)

	for y in gs:
		for x in gs:
			var pos := Vector2i(x, y)
			var tt: int = _spec.state.terrain.get(pos, Enums.TerrainType.FLOOR)
			var rect := Rect2(x * eff, y * eff, eff, eff)

			if tt == Enums.TerrainType.WALL:
				continue
			elif tt == Enums.TerrainType.SWITCH:
				var active := _spec.state.switch_activated(pos)
				var inset  := maxi(1, int(3.0 * cell_scale))
				var ir     := Rect2(
					rect.position.x + inset, rect.position.y + inset,
					eff - inset * 2, eff - inset * 2)
				var bc := COLOR_SWITCH_ON_B if active else COLOR_SWITCH_OFF_B
				draw_rect(ir, _col(bc, a), false, maxf(1.0, 3.0 * cell_scale))
			else:
				draw_rect(rect, _col(COLOR_GRID, a), false, thick)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

func _draw_entities(gs: int, eff: float, a: float) -> void:
	var player := _spec.state.get_player()

	# Boxes first, player on top
	for e in _spec.state.entities:
		var ent := e as Entity
		if ent.uid == 0:
			continue
		_draw_box(ent, eff, a)

	_draw_player(player, eff, a)


func _draw_box(ent: Entity, eff: float, a: float) -> void:
	if ent.z == -1:
		return  # underground / inside hole

	var cell_scale := eff / 80.0
	var is_held    := ent.z == 1
	var is_shadow  := _spec.state.is_shadow(ent.uid)

	# Padding: 9px base, increase when falling for visual shrink
	var pad_base := 9.0
	var pad      := pad_base * cell_scale

	# Falling animation: shift downward
	var fall_key := [ent.uid, ent.pos]
	var fall_prog: float = _spec.falling_progress.get(fall_key, -1.0)
	var fall_off := 0.0
	if fall_prog >= 0.0:
		fall_off  = fall_prog * eff
		pad      += 6.0 * cell_scale * fall_prog  # shrink while falling

	var rect := Rect2(
		ent.pos.x * eff + pad,
		ent.pos.y * eff + pad + fall_off,
		eff - pad * 2, eff - pad * 2)

	# Box colour
	var base_col := BOX_COLORS[(ent.uid - 1) % BOX_COLORS.size()]
	var fill_col: Color
	if is_shadow:
		fill_col = _desaturate(base_col, 0.5)
		fill_col.a = 0.65 * a
	elif is_held:
		fill_col = base_col.lightened(0.25)
		fill_col.a = a
	else:
		fill_col = base_col
		fill_col.a = a

	draw_rect(rect, fill_col)

	# Shadow gets a dashed outline
	if is_shadow:
		draw_rect(rect, _col(Color8(255, 255, 255, 100), a), false, maxf(1.0, 2.0 * cell_scale))

	# UID label
	_draw_center_text(
		str(ent.uid), rect.get_center(),
		int(14.0 * cell_scale), _col(COLOR_TEXT, a))


func _draw_player(player: Entity, eff: float, a: float) -> void:
	if player == null:
		return
	var cell_scale := eff / 80.0
	var center := Vector2(
		player.pos.x * eff + eff * 0.5,
		player.pos.y * eff + eff * 0.5)
	var radius := eff * 0.20

	var col := _col(COLOR_PLAYER, a)
	if _spec.is_focused:
		col = _col(Color8(50, 140, 240), a)  # slightly brighter when focused
	draw_circle(center, radius, col)

	# Direction arrow
	var dx := float(player.direction.x)
	var dy := float(player.direction.y)
	var tip := center + Vector2(dx, dy) * radius
	draw_line(center, tip, _col(Color8(255, 255, 255, 200), a),
		maxf(2.0, 3.0 * cell_scale), true)


# ---------------------------------------------------------------------------
# Interaction hint highlight
# ---------------------------------------------------------------------------

func _draw_hint_highlight(pos: Vector2i, col: Color, eff: float, a: float) -> void:
	var rect := Rect2(pos.x * eff, pos.y * eff, eff, eff)
	var fill := col
	fill.a    = 0.25 * a
	draw_rect(rect, fill)
	var border := col
	border.a   = 0.85 * a
	draw_rect(rect, border, false, maxf(2.0, 2.0 * (eff / 80.0)))


# ---------------------------------------------------------------------------
# Flash effect
# ---------------------------------------------------------------------------

func _draw_flash(eff: float, a: float) -> void:
	var rect := Rect2(
		_spec.flash_pos.x * eff,
		_spec.flash_pos.y * eff,
		eff, eff)
	var col  := COLOR_FLASH
	col.a     = _spec.flash_intensity * a
	draw_rect(rect, col)


# ---------------------------------------------------------------------------
# Panel border
# ---------------------------------------------------------------------------

func _draw_border(gpx: float, a: float) -> void:
	var col := _spec.border_color
	col.a   *= a
	draw_rect(Rect2(0, 0, gpx, gpx), col, false, BORDER_W)


# ---------------------------------------------------------------------------
# Title
# ---------------------------------------------------------------------------

func _draw_title(gpx: float, a: float) -> void:
	var col  := _col(COLOR_TITLE, a)
	var eff: float = _spec.cell_size * _spec.scale
	var size := int(16.0 * (eff / 80.0))
	_draw_center_text(_spec.title, Vector2(gpx * 0.5, -8.0), size, col)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

func _col(c: Color, a: float) -> Color:
	var out := c
	out.a   *= a
	return out


func _desaturate(c: Color, amount: float) -> Color:
	var avg := (c.r + c.g + c.b) / 3.0
	return Color(
		c.r + (avg - c.r) * amount,
		c.g + (avg - c.g) * amount,
		c.b + (avg - c.b) * amount,
		c.a)


func _draw_center_text(text: String, center: Vector2, font_size: int, col: Color) -> void:
	if text == "":
		return
	var font := ThemeDB.fallback_font
	if font == null:
		return
	var ascent := font.get_ascent(font_size)
	draw_string(
		font,
		Vector2(center.x, center.y + ascent * 0.35),
		text,
		HORIZONTAL_ALIGNMENT_CENTER,
		-1.0,
		font_size,
		col)
