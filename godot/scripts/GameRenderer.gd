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
const COLOR_HOLE         := Color8(60, 40, 20)
const COLOR_NO_CARRY     := Color8(255, 100, 100)
const COLOR_BRANCH       := Color8(50, 150, 50)
const COLOR_BRANCH_HIGHLIGHT_BG := Color8(150, 255, 150)
const COLOR_GRID         := Color8(200, 200, 200)
const COLOR_PLAYER       := Color8(0, 100, 200)
const COLOR_PLAYER_INACTIVE := Color8(200, 200, 200)
const COLOR_PLAYER_RING  := Color8(120, 145, 170)
const COLOR_TEXT         := Color8(0, 0, 0)
const COLOR_FLASH        := Color8(255, 80, 80)
const COLOR_TITLE        := Color8(220, 220, 220)
const COLOR_INTERACT_GRAY := Color8(100, 100, 100)
const COLOR_HINT_DARK    := Color8(60, 60, 60)
const COLOR_HINT_GRAY_B  := Color8(120, 120, 120)
const COLOR_HINT_TEXT_G  := Color8(180, 180, 180)
const COLOR_HINT_GREEN   := Color8(50, 150, 50)
const COLOR_HINT_GREEN_B := Color8(100, 255, 100)
const COLOR_HINT_M_BG    := Color8(110, 50, 110)
const COLOR_HINT_M_BD    := Color8(110, 50, 200)
const COLOR_HINT_V_BG    := Color8(40, 80, 120)
const COLOR_HINT_V_BD    := Color8(75, 150, 200)
const COLOR_HINT_F_BD    := Color8(100, 100, 100)
const COLOR_HINT_F_ON_BG := Color8(255, 140, 0)
const COLOR_HINT_F_ON_BD := Color8(255, 180, 0)
const TITLE_MARGIN_BASE  := 22.0

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
var _hint_space_label: Label = null
var _hint_action_label: Label = null
var _peek_floor_mode: bool = false


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


func set_peek_floor_mode(enabled: bool) -> void:
	if _peek_floor_mode == enabled:
		return
	_peek_floor_mode = enabled
	queue_redraw()


func _ready() -> void:
	_ensure_hint_labels()
	_set_hint_labels_visible(false)


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

	# Entities
	_draw_entities(eff, a)

	# Interaction hint highlight (draw over entities)
	if _peek_floor_mode:
		_set_hint_labels_visible(false)
	elif _spec.interaction_hint != null:
		var ih: PresentationModel.InteractionHint = _spec.interaction_hint as PresentationModel.InteractionHint
		if ih != null and ih.target_pos != Vector2i(-1, -1):
			_draw_hint_highlight(ih.target_pos, ih.text, ih.color, ih.is_inset, eff, a)
		else:
			_set_hint_labels_visible(false)
	else:
		_set_hint_labels_visible(false)

	# Flash overlay
	if _spec.flash_intensity > 0.0 and _spec.flash_pos != Vector2i(-1, -1):
		_draw_flash(eff, a)

	# Panel border
	_draw_border(gpx, a)

	# Title above panel
	_draw_title(gpx, a)

	# Adaptive hint boxes (draw once by focused branch).
	if _spec.is_focused:
		_draw_adaptive_hints(a)


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
			_draw_text_in_rect("Goal", rect, int(14.0 * cell_scale), _col(COLOR_TEXT, a))

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
			var is_highlighted_branch := _spec.highlight_branch_point and pos == _spec.state.get_player().pos
			draw_rect(rect, _col(COLOR_BRANCH_HIGHLIGHT_BG if is_highlighted_branch else COLOR_FLOOR, a))
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
				var bc := COLOR_SWITCH_ON_B if active else COLOR_SWITCH_INNER
				draw_rect(ir, _col(bc, a), false, maxf(1.0, 3.0 * cell_scale))
			else:
				draw_rect(rect, _col(COLOR_GRID, a), false, thick)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

func _draw_entities(eff: float, a: float) -> void:
	var player: Entity = _spec.state.get_player()
	var overlap_labels: Dictionary = _build_overlap_labels()
	var front_pos: Vector2i = player.pos + player.direction

	# Boxes first (sorted by z), player on top.
	var boxes: Array[Entity] = []
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent == null:
			continue
		if ent.uid != 0 and ent.type == Enums.EntityType.BOX:
			boxes.append(ent)
	boxes.sort_custom(func(left: Entity, right: Entity) -> bool: return left.z < right.z)

	for ent in boxes:
		var fade_front := (
			_peek_floor_mode
			and _spec.is_focused
			and _spec.scale >= 1.0
			and ent.z == 0
			and ent.pos == front_pos
		)
		_draw_box(ent, eff, a, overlap_labels, fade_front)

	# Shadow connections (focused full-size branch, before drawing player).
	if _spec.is_focused and _spec.scale >= 1.0:
		_draw_shadow_connections(eff, a)

	_draw_player(player, eff, a)


func _draw_box(
		ent: Entity,
		eff: float,
		a: float,
		overlap_labels: Dictionary,
		fade_front: bool = false) -> void:
	var cell_scale := eff / 80.0
	var is_held    := ent.z == 1
	var is_shadow  := _spec.state.is_shadow(ent.uid)
	var is_transparent_branch: bool = _spec.alpha < 0.9
	var effective_alpha: float = a * (0.18 if fade_front else 1.0)

	# Padding: normal box=9px, underground box=15px.
	var pad_base: float = 15.0 if ent.z == -1 else 9.0
	var pad: float = float(int(round(pad_base * cell_scale)))

	# Falling animation: shift downward
	var fall_key: Array = [ent.uid, ent.pos]
	var fall_prog: float = _spec.falling_progress.get(fall_key, -1.0)
	var fall_off: float = 0.0
	if fall_prog >= 0.0:
		fall_off  = fall_prog * eff
		var animated_pad: float = (9.0 + (15.0 - 9.0) * fall_prog) * cell_scale
		pad = animated_pad

	var rect: Rect2 = Rect2(
		ent.pos.x * eff + pad,
		ent.pos.y * eff + pad + fall_off,
		eff - pad * 2, eff - pad * 2)
	var snapped_rect: Rect2 = _pixel_snap_rect(rect)

	# Box colour
	var base_col: Color = BOX_COLORS[(ent.uid - 1) % BOX_COLORS.size()]
	var fill_col: Color
	if is_transparent_branch:
		fill_col = _desaturate(base_col, 0.3)
		fill_col.a = effective_alpha
	elif is_shadow and not _spec.is_focused:
		fill_col = _desaturate(base_col, 0.5)
		fill_col.a = effective_alpha
	else:
		fill_col = base_col
		fill_col.a = effective_alpha
	if is_held:
		fill_col = fill_col.lightened(0.1)
		fill_col.a = effective_alpha

	draw_rect(snapped_rect, fill_col)

	# Border: none for transparent branch, dashed for shadow, solid otherwise.
	var border_color: Color = _col(COLOR_TEXT, effective_alpha)
	var border_thick: float = float(maxi(1, int(round(2.0 * cell_scale))))
	if not is_transparent_branch:
		if is_shadow:
			_draw_dashed_rect(snapped_rect, border_color, border_thick)
		else:
			draw_rect(snapped_rect, border_color, false, border_thick)

	# Label: fusion label > overlap label > uid
	var label: String = _entity_label(ent, overlap_labels)
	var text_alpha: float = maxf(0.0, effective_alpha - 0.16) if fade_front else effective_alpha
	var text_col := COLOR_TEXT
	text_col.a = text_alpha
	_draw_text_in_rect(label, snapped_rect, int(14.0 * cell_scale), text_col)


func _draw_player(player: Entity, eff: float, a: float) -> void:
	if player == null:
		return
	var cell_scale := eff / 80.0
	var center: Vector2 = Vector2(
		player.pos.x * eff + eff * 0.5,
		player.pos.y * eff + eff * 0.5)
	var held_items: Array[int] = _spec.state.get_held_items()
	var held_uid: int = held_items[0] if not held_items.is_empty() else -1

	var dx: int = player.direction.x
	var dy: int = player.direction.y
	var arrow_offset: float = 8.0 * cell_scale
	var arrow_center: Vector2 = Vector2(
		center.x + dx * arrow_offset,
		center.y + dy * arrow_offset)

	if held_uid != -1:
		# Holding item: player becomes box-shaped with held UID color.
		var color_index: int = (held_uid - 1) % BOX_COLORS.size()
		var player_color: Color = _col(BOX_COLORS[color_index], a)

		var pad: float = 5.0 * cell_scale
		var rect: Rect2 = Rect2(
			player.pos.x * eff + pad,
			player.pos.y * eff + pad,
			eff - pad * 2.0,
			eff - pad * 2.0)
		draw_rect(rect, player_color)
		draw_rect(rect, _col(COLOR_TEXT, a), false, maxf(1.0, 3.0 * cell_scale))

		var held_label: String = str(held_uid)
		var held_entity: Entity = _find_first_entity_by_uid(held_uid)
		if held_entity != null and held_entity.fused_from.size() > 0:
			var pieces: Array[String] = []
			for raw_uid in held_entity.fused_from:
				pieces.append(str(raw_uid))
			held_label = "+".join(pieces)
		_draw_text_in_rect(held_label, rect, int(14.0 * cell_scale), _col(COLOR_TEXT, a))
		_draw_arrow(arrow_center, dx, dy, int(21.0 * cell_scale), _col(COLOR_TEXT, a))
	else:
		# Normal player: focused blue fill, non-focused gray ring.
		var radius: float = eff * 0.20
		if _spec.is_focused:
			draw_circle(center, radius, _col(COLOR_PLAYER, a))
		else:
			draw_arc(center, radius, 0.0, TAU, 28, _col(COLOR_PLAYER_RING, a), maxf(2.0, 3.0 * cell_scale), true)
		_draw_arrow(arrow_center, dx, dy, int(21.0 * cell_scale), _col(COLOR_TEXT, a))


func _draw_shadow_connections(eff: float, a: float) -> void:
	if not _spec.state.get_held_items().is_empty():
		return

	var player: Entity = _spec.state.get_player()
	if player == null:
		return

	var front_pos: Vector2i = player.pos + player.direction
	var entities_at_front: Array[Entity] = []
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent == null:
			continue
		if ent.pos == front_pos and ent.is_grounded():
			entities_at_front.append(ent)
	if entities_at_front.is_empty():
		return

	var front_uids: Dictionary = {}
	for ent in entities_at_front:
		front_uids[ent.uid] = true

	var front_center: Vector2 = _grid_to_local_center(front_pos, eff)
	var line_color: Color = Color8(50, 220, 50)
	line_color.a *= a
	var offset: float = float(_spec.animation_frame) * 0.25

	for raw_uid in front_uids.keys():
		var uid: int = int(raw_uid)
		if not _spec.state.is_shadow(uid):
			continue

		var instances: Array = _spec.state.get_entities_by_uid(uid)
		var positions: Dictionary = {}
		for raw in instances:
			var inst: Entity = raw as Entity
			if inst == null:
				continue
			positions[inst.pos] = true

		if positions.size() <= 1:
			continue

		for raw_pos in positions.keys():
			var pos: Vector2i = raw_pos as Vector2i
			if pos == front_pos:
				continue
			var other_center: Vector2 = _grid_to_local_center(pos, eff)
			_draw_dashed_line(other_center, front_center, line_color, 3.0, 12.0, offset)


func _draw_arrow(center: Vector2, dx: int, dy: int, size: int, col: Color) -> void:
	var half: float = float(size) * 0.5
	var points: PackedVector2Array
	if dy < 0:  # up
		points = PackedVector2Array([
			Vector2(center.x, center.y - size),
			Vector2(center.x - half, center.y - half),
			Vector2(center.x + half, center.y - half),
		])
	elif dy > 0:  # down
		points = PackedVector2Array([
			Vector2(center.x, center.y + size),
			Vector2(center.x - half, center.y + half),
			Vector2(center.x + half, center.y + half),
		])
	elif dx < 0:  # left
		points = PackedVector2Array([
			Vector2(center.x - size, center.y),
			Vector2(center.x - half, center.y - half),
			Vector2(center.x - half, center.y + half),
		])
	else:  # right
		points = PackedVector2Array([
			Vector2(center.x + size, center.y),
			Vector2(center.x + half, center.y - half),
			Vector2(center.x + half, center.y + half),
		])
	draw_colored_polygon(points, col)


func _draw_dashed_rect(rect: Rect2, col: Color, width: float) -> void:
	var dash: float = 5.0
	var gap: float = 5.0
	var step: float = dash + gap

	var x0: float = rect.position.x
	var y0: float = rect.position.y
	var x1: float = rect.position.x + rect.size.x
	var y1: float = rect.position.y + rect.size.y

	var i: float = 0.0
	while i < rect.size.x:
		var seg_end_x: float = minf(i + dash, rect.size.x)
		draw_line(Vector2(x0 + i, y0), Vector2(x0 + seg_end_x, y0), col, width, true)
		draw_line(Vector2(x0 + i, y1), Vector2(x0 + seg_end_x, y1), col, width, true)
		i += step

	i = 0.0
	while i < rect.size.y:
		var seg_end_y: float = minf(i + dash, rect.size.y)
		draw_line(Vector2(x0, y0 + i), Vector2(x0, y0 + seg_end_y), col, width, true)
		draw_line(Vector2(x1, y0 + i), Vector2(x1, y0 + seg_end_y), col, width, true)
		i += step


func _draw_dashed_line(
		from_pos: Vector2,
		to_pos: Vector2,
		col: Color,
		width: float = 3.0,
		dash_len: float = 9.0,
		offset: float = 0.0) -> void:
	var dist: float = from_pos.distance_to(to_pos)
	if dist <= 0.001:
		return
	var dir: Vector2 = (to_pos - from_pos) / dist
	var period: float = dash_len * 2.0
	var pos: float = fmod(offset, period)
	while pos < dist:
		var seg_start: float = maxf(0.0, pos)
		var seg_end: float = minf(dist, pos + dash_len)
		if seg_end > seg_start:
			var p0: Vector2 = from_pos + dir * seg_start
			var p1: Vector2 = from_pos + dir * seg_end
			draw_line(p0, p1, col, width, true)
		pos += period


func _grid_to_local_center(pos: Vector2i, eff: float) -> Vector2:
	return Vector2(
		(float(pos.x) + 0.5) * eff,
		(float(pos.y) + 0.5) * eff)


func _pixel_snap_rect(rect: Rect2) -> Rect2:
	return Rect2(
		round(rect.position.x),
		round(rect.position.y),
		round(rect.size.x),
		round(rect.size.y))


func _build_overlap_labels() -> Dictionary:
	var by_pos: Dictionary = {}
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent == null:
			continue
		if ent.uid == 0 or ent.type != Enums.EntityType.BOX:
			continue
		var key: String = _entity_stack_key(ent.pos, ent.z)
		if not by_pos.has(key):
			by_pos[key] = {}
		var seen: Dictionary = by_pos[key]
		seen[ent.uid] = true
		by_pos[key] = seen

	var labels: Dictionary = {}
	for key in by_pos.keys():
		var seen: Dictionary = by_pos[key]
		if seen.size() < 2:
			continue
		var uids: Array = seen.keys()
		uids.sort()
		var parts: Array[String] = []
		for uid in uids:
			parts.append(str(uid))
		labels[key] = "|".join(parts)
	return labels


func _entity_label(ent: Entity, overlap_labels: Dictionary) -> String:
	if ent.fused_from.size() > 0:
		var pieces: Array[String] = []
		for uid in ent.fused_from:
			pieces.append(str(uid))
		return "+".join(pieces)

	var key: String = _entity_stack_key(ent.pos, ent.z)
	if overlap_labels.has(key):
		return str(overlap_labels[key])
	return str(ent.uid)


func _entity_stack_key(pos: Vector2i, z: int) -> String:
	return "%d|%d|%d" % [pos.x, pos.y, z]


func _find_first_entity_by_uid(uid: int) -> Entity:
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent != null and ent.uid == uid:
			return ent
	return null


# ---------------------------------------------------------------------------
# Interaction hint highlight
# ---------------------------------------------------------------------------

func _draw_hint_highlight(
		pos: Vector2i, hint_text: String, _hint_col: Color, is_inset: bool, eff: float, a: float) -> void:
	var rect := Rect2(pos.x * eff, pos.y * eff, eff, eff)
	var cell_scale: float = eff / 80.0
	var center: Vector2 = rect.get_center()
	_update_hint_text_overlay(hint_text, center, cell_scale, a)

	# Drop hint: only show inset dashed mini-frame, no lock corners.
	if is_inset:
		var margin: float = maxf(2.0, 8.0 * cell_scale)
		var inset_rect: Rect2 = rect.grow(-margin)
		var frame_col: Color = COLOR_INTERACT_GRAY
		frame_col.a = 0.9 * a
		_draw_dashed_rect(
			_pixel_snap_rect(inset_rect),
			frame_col,
			float(maxi(1, int(round(2.0 * cell_scale)))))
		return

	var corner_color: Color = COLOR_INTERACT_GRAY
	corner_color.a = 0.95 * a
	_draw_lock_corners(
		rect,
		corner_color,
		maxf(8.0, 24.0 * cell_scale),
		maxf(1.0, 4.0 * cell_scale),
		-3.0 * cell_scale)


func _draw_lock_corners(
		rect: Rect2, col: Color, corner_size: float, thickness: float, margin: float = 0.0) -> void:
	var r: Rect2 = _pixel_snap_rect(rect.grow(margin))
	var left: float = r.position.x
	var top: float = r.position.y
	var right: float = r.position.x + r.size.x
	var bottom: float = r.position.y + r.size.y
	var size: float = minf(corner_size, minf(r.size.x * 0.5, r.size.y * 0.5))

	# Top-left
	draw_line(Vector2(left, top), Vector2(left + size, top), col, thickness, true)
	draw_line(Vector2(left, top), Vector2(left, top + size), col, thickness, true)
	# Top-right
	draw_line(Vector2(right - size, top), Vector2(right, top), col, thickness, true)
	draw_line(Vector2(right, top), Vector2(right, top + size), col, thickness, true)
	# Bottom-left
	draw_line(Vector2(left, bottom - size), Vector2(left, bottom), col, thickness, true)
	draw_line(Vector2(left, bottom), Vector2(left + size, bottom), col, thickness, true)
	# Bottom-right
	draw_line(Vector2(right - size, bottom), Vector2(right, bottom), col, thickness, true)
	draw_line(Vector2(right, bottom - size), Vector2(right, bottom), col, thickness, true)


func _ensure_hint_labels() -> void:
	if _hint_space_label == null:
		_hint_space_label = _create_hint_label()
		_hint_space_label.text = "[SPACE]"
		add_child(_hint_space_label)
	if _hint_action_label == null:
		_hint_action_label = _create_hint_label()
		add_child(_hint_action_label)


func _create_hint_label() -> Label:
	var label: Label = Label.new()
	label.visible = false
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	return label


func _set_hint_labels_visible(v: bool) -> void:
	if _hint_space_label != null:
		_hint_space_label.visible = v
	if _hint_action_label != null:
		_hint_action_label.visible = v


func _update_hint_text_overlay(hint_text: String, center: Vector2, cell_scale: float, a: float) -> void:
	_ensure_hint_labels()

	var font_size: int = maxi(10, int(round(12.0 * cell_scale)))
	var outline_size: int = maxi(2, int(round(2.4 * cell_scale)))
	var label_w: float = round(maxf(90.0, 130.0 * cell_scale))
	var label_h: float = round(maxf(16.0, 22.0 * cell_scale))
	var top_center: Vector2 = Vector2(center.x, center.y + 8.0 * cell_scale)
	var bottom_center: Vector2 = Vector2(center.x, center.y - 12.0 * cell_scale)

	_apply_hint_label_style(_hint_space_label, font_size, outline_size, a)
	_apply_hint_label_style(_hint_action_label, font_size, outline_size, a)

	_hint_action_label.text = hint_text
	_layout_hint_label(_hint_space_label, top_center, label_w, label_h)
	_layout_hint_label(_hint_action_label, bottom_center, label_w, label_h)
	_set_hint_labels_visible(true)


func _apply_hint_label_style(label: Label, font_size: int, outline_size: int, a: float) -> void:
	label.add_theme_font_size_override("font_size", font_size)
	label.add_theme_constant_override("outline_size", outline_size)
	label.add_theme_color_override("font_color", Color(1.0, 1.0, 1.0, a))
	label.add_theme_color_override("font_outline_color", Color(0.0, 0.0, 0.0, a))
	label.add_theme_constant_override("shadow_outline_size", outline_size)
	label.add_theme_color_override("font_shadow_color", Color(0.0, 0.0, 0.0, a))
	label.add_theme_constant_override("shadow_offset_x", 0)
	label.add_theme_constant_override("shadow_offset_y", 0)


func _layout_hint_label(ctrl: Control, center: Vector2, w: float, h: float) -> void:
	ctrl.position = Vector2(round(center.x - w * 0.5), round(center.y - h * 0.5))
	ctrl.size = Vector2(w, h)


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
	var title_y: float = -maxf(14.0, TITLE_MARGIN_BASE * (eff / 80.0))
	_draw_center_text(_spec.title, Vector2(gpx * 0.5, title_y), size, col)


func _draw_adaptive_hints(a: float) -> void:
	if not _spec.has_branched:
		if _spec.timeline_hint != "":
			_draw_timeline_hint_box(_spec.branch_hint_active, a)
		return

	if _spec.show_merge_preview_hint:
		_draw_merge_preview_hint(_spec.is_merge_preview, a)
	if _spec.show_merge_hint:
		_draw_merge_hint(a)
	if _spec.show_fetch_indicator:
		_draw_fetch_mode_indicator(_spec.fetch_mode_enabled, a)


func _draw_timeline_hint_box(is_active: bool, a: float) -> void:
	var box_w: float = 150.0
	var box_h: float = 40.0
	var view_size: Vector2 = get_viewport_rect().size
	var center_x: float = (view_size.x - box_w) * 0.5
	var y: float = (view_size.y + PresentationModel.TARGET_PANEL) * 0.5 + 15.0
	var x: float = center_x
	var rect: Rect2 = _global_rect_to_local(Rect2(x, y, box_w, box_h))

	var bg: Color = _col(COLOR_HINT_GREEN if is_active else COLOR_HINT_DARK, a * 0.8)
	var border: Color = _col(COLOR_HINT_GREEN_B if is_active else COLOR_HINT_GRAY_B, a)
	var text_col: Color = _col(Color8(60, 30, 0) if is_active else COLOR_HINT_TEXT_G, a)

	draw_rect(rect, bg)
	draw_rect(rect, border, false, 2.0)
	_draw_text_in_rect("V Branch", rect, 16, text_col)


func _draw_merge_preview_hint(is_active: bool, a: float) -> void:
	var box_w: float = 130.0
	var box_h: float = 40.0
	var view_size: Vector2 = get_viewport_rect().size
	var center_x: float = (view_size.x - PresentationModel.TARGET_PANEL) * 0.5
	var center_y: float = (view_size.y - PresentationModel.TARGET_PANEL) * 0.5
	var x: float = center_x + PresentationModel.TARGET_PANEL - box_w
	var y: float = center_y + PresentationModel.TARGET_PANEL + 15.0
	var rect: Rect2 = _global_rect_to_local(Rect2(x, y, box_w, box_h))

	draw_rect(rect, _col(COLOR_HINT_M_BG, a * 0.8))
	draw_rect(rect, _col(COLOR_HINT_M_BD, a), false, 2.0)
	var text: String = "M Cancel Preview" if is_active else "M Preview Merge"
	_draw_text_in_rect(text, rect, 14, _col(Color.WHITE, a))


func _draw_merge_hint(a: float) -> void:
	var box_w: float = 150.0
	var box_h: float = 40.0
	var view_size: Vector2 = get_viewport_rect().size
	var x: float = (view_size.x - box_w) * 0.5
	var y: float = (view_size.y + PresentationModel.TARGET_PANEL) * 0.5 + 15.0
	var rect: Rect2 = _global_rect_to_local(Rect2(x, y, box_w, box_h))

	draw_rect(rect, _col(COLOR_HINT_V_BG, a * 0.8))
	draw_rect(rect, _col(COLOR_HINT_V_BD, a), false, 2.0)
	_draw_text_in_rect("V Merge", rect, 16, _col(Color.WHITE, a))


func _draw_fetch_mode_indicator(enabled: bool, a: float) -> void:
	var box_w: float = 120.0
	var box_h: float = 40.0
	var view_size: Vector2 = get_viewport_rect().size
	var center_x: float = (view_size.x - PresentationModel.TARGET_PANEL) * 0.5
	var y: float = (view_size.y + PresentationModel.TARGET_PANEL) * 0.5 + 15.0
	var x: float = center_x
	var rect: Rect2 = _global_rect_to_local(Rect2(x, y, box_w, box_h))

	var bg: Color = _col(COLOR_HINT_F_ON_BG if enabled else COLOR_HINT_DARK, a * 0.8)
	var bd: Color = _col(COLOR_HINT_F_ON_BD if enabled else COLOR_HINT_F_BD, a)
	var tx: Color = _col(Color8(60, 30, 0) if enabled else Color8(220, 220, 220), a)

	draw_rect(rect, bg)
	draw_rect(rect, bd, false, 2.0)
	_draw_text_in_rect("F Fetch Merge", rect, 14, tx)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

func _col(c: Color, a: float) -> Color:
	var out := c
	out.a   *= a
	return out


func _global_rect_to_local(rect: Rect2) -> Rect2:
	return Rect2(
		rect.position.x - position.x,
		rect.position.y - position.y,
		rect.size.x,
		rect.size.y)


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
	var font: Font = ThemeDB.fallback_font
	if font == null:
		return
	var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
	var ascent: float = font.get_ascent(font_size)
	var descent: float = font.get_descent(font_size)
	var baseline_y: float = center.y + (ascent - descent) * 0.5
	draw_string(
		font,
		Vector2(center.x - text_w * 0.5, baseline_y),
		text,
		HORIZONTAL_ALIGNMENT_LEFT,
		-1.0,
		font_size,
		col)


func _draw_text_in_rect(text: String, rect: Rect2, font_size: int, col: Color) -> void:
	if text == "":
		return
	var font: Font = ThemeDB.fallback_font
	if font == null:
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
		col)
