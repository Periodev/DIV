# GameRenderer.gd - Game panel renderer (Node Network visual style)
# Draws one BranchViewSpec via Godot's _draw() API.
# Interface unchanged: draw_frame(spec) / _draw()
extends Node2D
class_name GameRenderer

# ---------------------------------------------------------------------------
# Visual constants - Node Network style
# ---------------------------------------------------------------------------

const COLOR_BG      := Color(0.0, 0.0, 0.0)          # pure black

@export_group("Connection Colors")
@export var line_normal: Color = Color(1, 1, 1, 0.42)  # normal connection
@export var line_drop_zone: Color = Color(1, 1, 1, 0.42)  # kept for inspector compatibility
@export var line_dashed: Color = Color(1, 1, 1, 0.20)  # filled-hole connection
@export var line_broken: Color = Color(1, 1, 1, 0.18)  # hole broken segment
@export var line_cross: Color = Color(0.78, 0.24, 0.24, 0.70) # hole X mark
@export var line_stable: Color = Color(1, 1, 1, 0.24)  # fused-hole stable connection

@export_group("Entity Sizing")
@export var nr_factor: float = 0.173
@export var entity_scale: float = 1.50
@export var node_scale: float = 1.18

# Box colours - uid-1 mod 5
@export var box_colors: Array[Color] = [
	Color(0.478, 0.800, 0.400),  # #7ACC66 mint green
	Color(0.298, 0.710, 0.961),  # #4CB5F5 sky blue
	Color(0.910, 0.300, 0.780),  # #E84CC7 magenta (distinct from goal yellow and hole red)
	Color(0.616, 0.455, 0.827),  # #9D74D3 lilac purple
	Color(0.957, 0.545, 0.376),  # #F48B60 coral orange
]

# ---------------------------------------------------------------------------
# Preserved HUD / utility constants
# ---------------------------------------------------------------------------

const COLOR_FLASH        := Color8(255, 80,  80)
const COLOR_TITLE        := Color8(220, 220, 220)
const COLOR_INTERACT_GRAY := Color8(100, 100, 100)
const COLOR_HINT_DARK    := Color8( 60,  60,  60)
const COLOR_HINT_GRAY_B  := Color8(120, 120, 120)
const COLOR_HINT_TEXT_G  := Color8(180, 180, 180)
const COLOR_HINT_GREEN   := Color8( 50, 150,  50)
const COLOR_HINT_GREEN_B := Color8(100, 255, 100)
const COLOR_HINT_M_BG    := Color8(110,  50, 110)
const COLOR_HINT_M_BD    := Color8(110,  50, 200)
const COLOR_HINT_V_BG    := Color8( 40,  80, 120)
const COLOR_HINT_V_BD    := Color8( 75, 150, 200)
const COLOR_HINT_F_BD    := Color8(100, 100, 100)
const COLOR_HINT_F_ON_BG := Color8(255, 140,   0)
const COLOR_HINT_F_ON_BD := Color8(255, 180,   0)
@export_group("Border & Animation")
@export var title_margin_base: float = 22.0
@export var border_w: float = 1.5
@export var dash_scroll_speed: float = 28.0
const DROP_ZONE_HOLE_RATIO := 0.80
@export_group("Hole Animation")
@export_enum("ExpandToHex:1", "FlashToHex:2") var hole_fill_anim_mode: int = 2
@export_group("Hole Style")
@export_enum("SplitEdges:0", "VertexDots:1", "VertexStubs:2") var empty_hole_outline_mode: int = 1
@export var empty_hole_vertex_dot_radius: float = 1.4
@export var empty_hole_vertex_stub_ratio: float = 0.16
@export var hole_core_size_ratio: float = 1.08
const HOLE_SPLIT_GAP_RATIO := 0.22

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------

var _spec: PresentationModel.BranchViewSpec = null
var _hint_space_label: Label  = null
var _hint_action_label: Label = null
var _peek_floor_mode: bool    = false
var _time: float              = 0.0
var _eff: float               = 0.0
var _cell_scale: float        = 0.0
var _nr: float                = 0.0
var _gpx: float               = 0.0
var _alpha: float             = 1.0

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

## Called by GameScene every time the visual state changes.
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


func _process(delta: float) -> void:
	_time += delta
	if _spec != null:
		queue_redraw()


# ---------------------------------------------------------------------------
# Draw entry point
# ---------------------------------------------------------------------------

func _draw() -> void:
	if _spec == null or _spec.state == null:
		return

	var gs:  int   = _spec.state.grid_size
	_eff = _spec.cell_size * _spec.scale
	_gpx = _eff * gs
	_alpha = _spec.alpha
	_cell_scale = _eff / 80.0
	_nr = _eff * nr_factor * entity_scale * _spec.overlay_entity_scale

	var eff: float = _eff
	var gpx: float = _gpx
	var a:   float = _alpha

	# Merge-preview overlay panel: no background, no terrain - entities only.
	var is_overlay: bool = _spec.is_merge_preview and not _spec.is_focused
	if is_overlay:
		# Keep activated switches visible in overlay so branch activation state remains readable.
		_draw_overlay_activated_switch_nodes(gs, eff, a)
		# Show filled-hole state in overlay (semi-transparent, terrain-sized).
		_draw_overlay_filled_hole_nodes(gs, eff, a)
		_draw_entities(eff, a)
		return

	# Background
	draw_rect(Rect2(0, 0, gpx, gpx), _col(COLOR_BG, a))

	# Terrain: drop-field underlay -> connection lines -> node markers
	_draw_no_carry_underlay(gs, eff, a)
	_draw_connections(gs, eff, a)
	_draw_nodes(gs, eff, a)

	# Entities
	_draw_entities(eff, a)

	# Interaction hint - float above target entity
	_set_hint_labels_visible(false)
	_draw_interaction_hint(eff, a)

	# Flash overlay
	if _spec.flash_intensity > 0.0 and _spec.flash_pos != Vector2i(-1, -1):
		_draw_flash(eff, a)

	# Panel border (thin)
	_draw_border(gpx, a)

	# Title above panel
	_draw_title(gpx, a)

# ---------------------------------------------------------------------------
# Terrain - connection lines
# ---------------------------------------------------------------------------

func _draw_no_carry_underlay(gs: int, eff: float, a: float) -> void:
	for y in gs:
		for x in gs:
			var pos := Vector2i(x, y)
			var tt: int = _spec.state.terrain.get(pos, Enums.TerrainType.FLOOR)
			if tt != Enums.TerrainType.NO_CARRY:
				continue
			var center: Vector2 = _grid_to_local_center(pos, eff)
			_draw_drop_zone_frame(center, eff, a)


func _draw_drop_zone_fill(center: Vector2, eff: float, a: float) -> void:
	var half: float = eff * 0.5
	var r := Rect2(center.x - half, center.y - half, half * 2.0, half * 2.0)
	draw_rect(r, _col(Color(0.22, 0.22, 0.22, 0.82), a), true)


func _draw_drop_zone_frame(center: Vector2, eff: float, a: float) -> void:
	_draw_drop_zone_fill(center, eff, a)

func _draw_connections(gs: int, eff: float, a: float) -> void:
	for y in gs:
		for x in gs:
			var pos_a := Vector2i(x, y)
			var tt_a: int = _spec.state.terrain.get(pos_a, Enums.TerrainType.FLOOR)
			if tt_a == Enums.TerrainType.WALL:
				continue
			var c_a: Vector2 = _grid_to_local_center(pos_a, eff)

			# Right neighbour
			if x + 1 < gs:
				var pos_b := Vector2i(x + 1, y)
				var tt_b: int = _spec.state.terrain.get(pos_b, Enums.TerrainType.FLOOR)
				if tt_b != Enums.TerrainType.WALL:
					_draw_connection_pair(
						pos_a, tt_a, c_a,
						pos_b, tt_b, _grid_to_local_center(pos_b, eff),
						eff, a)

			# Down neighbour
			if y + 1 < gs:
				var pos_b := Vector2i(x, y + 1)
				var tt_b: int = _spec.state.terrain.get(pos_b, Enums.TerrainType.FLOOR)
				if tt_b != Enums.TerrainType.WALL:
					_draw_connection_pair(
						pos_a, tt_a, c_a,
						pos_b, tt_b, _grid_to_local_center(pos_b, eff),
						eff, a)


func _draw_connection_pair(
		pos_a: Vector2i, tt_a: int, c_a: Vector2,
		pos_b: Vector2i, tt_b: int, c_b: Vector2,
		eff: float, a: float) -> void:
	var a_empty_hole: bool = (tt_a == Enums.TerrainType.HOLE) and not _is_hole_filled(pos_a)
	var b_empty_hole: bool = (tt_b == Enums.TerrainType.HOLE) and not _is_hole_filled(pos_b)
	var a_filled_hole: bool = (tt_a == Enums.TerrainType.HOLE) and _is_hole_filled(pos_a)
	var b_filled_hole: bool = (tt_b == Enums.TerrainType.HOLE) and _is_hole_filled(pos_b)

	if a_empty_hole or b_empty_hole:
		_draw_broken_segment(c_a, c_b, tt_a, tt_b, a_empty_hole, b_empty_hole, eff, a)
		return

	var conn_col: Color = _connection_line_color(tt_a, tt_b, a)
	var clip_a: float = _connection_clip_radius(tt_a, eff)
	var clip_b: float = _connection_clip_radius(tt_b, eff)
	# Pass-through policy: filled holes, normal floor, and NO_CARRY center stay connected.
	if a_filled_hole or tt_a == Enums.TerrainType.FLOOR or tt_a == Enums.TerrainType.NO_CARRY:
		clip_a = 0.0
	if b_filled_hole or tt_b == Enums.TerrainType.FLOOR or tt_b == Enums.TerrainType.NO_CARRY:
		clip_b = 0.0

	_draw_clipped_connection_line(c_a, c_b, clip_a, clip_b, conn_col, 1.5)


func _connection_line_color(tt_a: int, tt_b: int, a: float) -> Color:
	# Unified route color for all segments (including DZ-related links).
	return _col(line_normal, a)


func _connection_clip_radius(tt: int, eff: float) -> float:
	match tt:
		Enums.TerrainType.GOAL:
			# Keep route touching GOAL inner contour without crossing the fill.
			return maxf(0.0, _goal_marker_radius(eff) * 1.35 - 1.2)
		Enums.TerrainType.SWITCH:
			# Clip to the hollow switch diamond contour (same geometry as _draw_switch_node).
			return maxf(0.0, _eff * nr_factor * node_scale * 1.5)
		Enums.TerrainType.NO_CARRY:
			return 0.0
		Enums.TerrainType.BRANCH1, Enums.TerrainType.BRANCH2, \
		Enums.TerrainType.BRANCH3, Enums.TerrainType.BRANCH4:
			return maxf(0.0, 3.0 * _cell_scale * node_scale)
		Enums.TerrainType.FLOOR:
			return maxf(0.0, 3.8 * node_scale)
		Enums.TerrainType.HOLE:
			# Empty holes are handled by the broken-segment path above.
			return _hole_core_radius(eff) + maxf(2.0, _cell_scale * 3.0) + 2.0
		_:
			return 0.0


func _draw_clipped_connection_line(
		from_pos: Vector2, to_pos: Vector2,
		clip_from: float, clip_to: float,
		col: Color, width: float) -> void:
	var dist: float = from_pos.distance_to(to_pos)
	if dist <= 0.001:
		return

	var dir: Vector2 = (to_pos - from_pos) / dist
	var max_clip_each: float = maxf(0.0, dist * 0.5 - 0.001)
	var start_clip: float = clampf(clip_from, 0.0, max_clip_each)
	var end_clip: float = clampf(clip_to, 0.0, max_clip_each)
	var clip_sum: float = start_clip + end_clip
	var max_total: float = dist - 0.001
	if clip_sum > max_total and clip_sum > 0.0:
		var scale: float = max_total / clip_sum
		start_clip *= scale
		end_clip *= scale

	var start: Vector2 = from_pos + dir * start_clip
	var end: Vector2 = to_pos - dir * end_clip
	if start.distance_to(end) <= 0.001:
		return
	draw_line(start, end, col, width)


func _draw_broken_segment(
		c_a: Vector2, c_b: Vector2,
		tt_a: int, tt_b: int,
		a_empty_hole: bool, b_empty_hole: bool, eff: float, a: float) -> void:
	var col_white: Color = _connection_line_color(tt_a, tt_b, a)
	var col_red: Color   = _col(line_cross, a)
	if a_empty_hole and not b_empty_hole:
		_draw_break_wire(c_b, c_a, tt_b, col_white, col_red, eff)
	elif b_empty_hole and not a_empty_hole:
		_draw_break_wire(c_a, c_b, tt_a, col_white, col_red, eff)
	else:
		# Both holes: red stub from each end, gap in middle.
		var dist: float = c_a.distance_to(c_b)
		if dist <= 0.001:
			return
		var hole_r: float = _hole_core_radius(eff) + maxf(2.0, _cell_scale * 3.0) + 2.0
		var stub: float     = minf(dist * 0.20, dist * 0.5 - hole_r)
		var dir_ab: Vector2 = (c_b - c_a) / dist
		_draw_dashed_line(c_a + dir_ab * hole_r, c_a + dir_ab * (hole_r + stub), col_red, 1.6, 5.0, 0.0)
		_draw_dashed_line(c_b - dir_ab * hole_r, c_b - dir_ab * (hole_r + stub), col_red, 1.6, 5.0, 0.0)


# Solid white line from walkable node, stops before hole visual; red dashed stub in the gap.
func _draw_break_wire(
		c_walk: Vector2, c_hole: Vector2, tt_walk: int,
		col_white: Color, col_red: Color, eff: float) -> void:
	var dist: float = c_walk.distance_to(c_hole)
	if dist <= 0.001:
		return
	var dir: Vector2  = (c_hole - c_walk) / dist
	var walk_clip: float = _connection_clip_radius(tt_walk, eff)
	# Safe boundary: leave clearance for the hole node's visual (ring + margin).
	var hole_r: float = _hole_core_radius(eff) + maxf(2.0, _cell_scale * 3.0) + 3.0
	var safe: float   = dist - hole_r - walk_clip   # px from walkable visual edge to hole visual edge
	if safe <= 0.0:
		return
	var start: Vector2 = c_walk + dir * walk_clip
	# White line: 0 to 72% of safe zone.
	draw_line(start, start + dir * safe * 0.72, col_white, 2.0)
	# Red stub: 84% to 100% of safe zone (just outside hole node visual).
	_draw_dashed_line(
		start + dir * safe * 0.84,
		start + dir * safe,
		col_red, 1.6, 5.0, 0.0)


# ---------------------------------------------------------------------------
# Terrain - node markers
# ---------------------------------------------------------------------------

func _draw_nodes(gs: int, eff: float, a: float) -> void:
	for y in gs:
		for x in gs:
			var pos := Vector2i(x, y)
			var tt: int = _spec.state.terrain.get(pos, Enums.TerrainType.FLOOR)
			if tt == Enums.TerrainType.WALL:
				continue
			_draw_node_at(pos, tt, _grid_to_local_center(pos, eff), eff, a)


func _draw_overlay_activated_switch_nodes(gs: int, eff: float, a: float) -> void:
	var NR: float = _eff * nr_factor * node_scale
	var dot_r: float = 2.0 * node_scale
	for y in gs:
		for x in gs:
			var pos := Vector2i(x, y)
			var tt: int = _spec.state.terrain.get(pos, Enums.TerrainType.FLOOR)
			if tt != Enums.TerrainType.SWITCH:
				continue
			if not _spec.state.switch_activated(pos):
				continue
			_draw_switch_node(pos, _grid_to_local_center(pos, eff), NR, dot_r, a)


func _draw_overlay_filled_hole_nodes(gs: int, eff: float, a: float) -> void:
	var overlay_a: float = a * 0.55
	var hole_scale: float = 0.72
	for y in gs:
		for x in gs:
			var pos := Vector2i(x, y)
			var tt: int = _spec.state.terrain.get(pos, Enums.TerrainType.FLOOR)
			if tt != Enums.TerrainType.HOLE:
				continue
			if not _is_hole_filled(pos):
				continue
			var center := _grid_to_local_center(pos, eff)
			draw_set_transform(center, 0.0, Vector2(hole_scale, hole_scale))
			_draw_hole_node(pos, Vector2.ZERO, eff, overlay_a)
			draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func _draw_node_at(pos: Vector2i, tt: int, center: Vector2, eff: float, a: float) -> void:
	var NR:         float = _eff * nr_factor * node_scale
	var cell_scale: float = _cell_scale

	match tt:
		Enums.TerrainType.FLOOR:
			draw_circle(center, 3.8 * node_scale, _col(Color(1, 1, 1, 1.0), a))

		Enums.TerrainType.HOLE:
			_draw_hole_node(pos, center, eff, a)

		Enums.TerrainType.SWITCH:
			_draw_switch_node(pos, center, NR, 2.0 * node_scale, a)

		Enums.TerrainType.NO_CARRY:
			draw_circle(center, 3.8 * node_scale, _col(Color(1, 1, 1, 1.0), a))

		Enums.TerrainType.BRANCH1, Enums.TerrainType.BRANCH2, \
		Enums.TerrainType.BRANCH3, Enums.TerrainType.BRANCH4:
			_draw_branch_node(pos, center, tt, eff, a)

		Enums.TerrainType.GOAL:
			_draw_goal_node(center, eff, a)

		_:
			draw_circle(center, 3.8 * node_scale, _col(Color(1, 1, 1, 1.0), a))


func _draw_hole_node(pos: Vector2i, center: Vector2, eff: float, a: float) -> void:
	var core_r: float = _hole_core_radius(eff)

	# Exclude entities still in fall animation (including hold phase t=0) - hole stays empty.
	var uids: Array[int] = []
	for uid in _get_uids_in_hole(pos):
		if _get_fall_progress(uid, pos) < 0.0:
			uids.append(uid)

	if uids.is_empty():
		# Empty hole: dashed regular hexagon + dark hex fill.
		var ring_w: float = maxf(2.0, _cell_scale * 3.0)
		var outer_r: float = core_r + ring_w
		var border_col: Color = _col(Color(0.86, 0.21, 0.24, 0.95), a)
		var fill_col: Color = _col(Color(0.0, 0.0, 0.0, 0.98), a)
		var hex_inner: PackedVector2Array = _regular_ngon_points(center, core_r, 6, -PI * 0.5)
		var hex_outer: PackedVector2Array = _regular_ngon_points(center, outer_r, 6, -PI * 0.5)
		if hex_inner.size() >= 3:
			draw_colored_polygon(hex_inner, fill_col)
		_draw_empty_hole_outline(hex_outer, border_col)
		return

	uids.sort()
	if uids.size() == 1:
		_draw_hole_fill_half(center, uids[0], core_r, eff, a, 0.0, TAU)
	else:
		# Two entities: left half (lower uid) / right half (higher uid).
		_draw_hole_fill_half(center, uids[0], core_r, eff, a, PI * 0.5, PI * 1.5)
		_draw_hole_fill_half(center, uids[1], core_r, eff, a, -PI * 0.5, PI * 0.5)
	# Filled hole keeps the normal floor center marker to indicate full pass-through.
	draw_circle(center, 3.8 * node_scale, _col(Color(1, 1, 1, 1.0), a))


func _draw_hole_fill_half(
		center: Vector2, uid: int, core_r: float, eff: float, a: float,
		angle_from: float, angle_to: float) -> void:
	var col: Color = box_colors[(uid - 1) % 5]
	var is_shadow: bool = _spec.state.is_shadow(uid)
	var frac: float = (angle_to - angle_from) / TAU
	var ring_w: float = maxf(2.0, _cell_scale * 3.0)
	var hex_r: float = core_r + ring_w
	var hex := _regular_ngon_points(center, hex_r, 6, -PI * 0.5)
	if frac >= 0.999:
		if is_shadow:
			_draw_split_polygon_outline(
				hex,
				Color(col.r, col.g, col.b, 0.95 * a),
				_hole_split_line_width(),
				HOLE_SPLIT_GAP_RATIO
			)
		else:
			var rim_w: float = maxf(3.0, _cell_scale * 4.5)
			_draw_polygon_outline(hex, Color(col.r, col.g, col.b, 0.92 * a), rim_w)
		return
	var mid_angle: float = 0.5 * (angle_from + angle_to)
	var side: int = 1 if cos(mid_angle) >= 0.0 else -1
	var path: PackedVector2Array = _hole_half_outer_path(hex, side)
	if is_shadow:
		_draw_hole_path_outline(
			path,
			Color(col.r, col.g, col.b, 0.95 * a),
			_hole_split_line_width(),
			true,
			maxf(4.0, _cell_scale * 6.0)
		)
	else:
		_draw_hole_path_outline(
			path,
			Color(col.r, col.g, col.b, 0.92 * a),
			maxf(3.0, _cell_scale * 4.5),
			false
		)


func _regular_ngon_points(
		center: Vector2, radius: float, sides: int,
		rotation: float = -PI * 0.5) -> PackedVector2Array:
	var pts := PackedVector2Array()
	if sides < 3 or radius <= 0.001:
		return pts
	for i in sides:
		var theta: float = rotation + TAU * float(i) / float(sides)
		pts.append(center + Vector2(cos(theta) * radius, sin(theta) * radius))
	return pts


func _regular_ngon_radius_at(theta: float, sides: int, radius: float, rotation: float = -PI * 0.5) -> float:
	if sides < 3 or radius <= 0.001:
		return 0.0
	var sector: float = TAU / float(sides)
	var local: float = fposmod(theta - rotation, TAU)
	var in_sector: float = fposmod(local, sector)
	var rel: float = in_sector - sector * 0.5
	var denom: float = maxf(cos(rel), 0.0001)
	var apothem: float = radius * cos(PI / float(sides))
	return apothem / denom


func _morph_diamond_hex_pts(
		center: Vector2, radius: float,
		t: float, rotation: float = -PI * 0.5, N: int = 30) -> PackedVector2Array:
	var pts := PackedVector2Array()
	var mt: float = clampf(t, 0.0, 1.0)
	for i in N:
		var theta: float = float(i) * TAU / float(N)
		var r_diamond: float = radius / maxf(abs(cos(theta)) + abs(sin(theta)), 0.0001)
		var r_hex: float = _regular_ngon_radius_at(theta, 6, radius, rotation)
		var r: float = lerpf(r_diamond, r_hex, mt)
		pts.append(center + Vector2(cos(theta) * r, sin(theta) * r))
	return pts


func _draw_polygon_outline(pts: PackedVector2Array, col: Color, width: float) -> void:
	if pts.size() < 2:
		return
	var closed := PackedVector2Array(pts)
	closed.append(pts[0])
	draw_polyline(closed, col, width, true)


func _draw_dashed_polygon_outline(
		pts: PackedVector2Array, col: Color,
		width: float, dash_len: float, offset: float = 0.0) -> void:
	var n: int = pts.size()
	if n < 2:
		return
	for i in n:
		var a_pos: Vector2 = pts[i]
		var b_pos: Vector2 = pts[(i + 1) % n]
		_draw_dashed_line(a_pos, b_pos, col, width, dash_len, offset)


func _draw_split_polygon_outline(
		pts: PackedVector2Array, col: Color,
		width: float, center_gap_ratio: float = 0.22) -> void:
	var n: int = pts.size()
	if n < 2:
		return
	var half_gap: float = clampf(center_gap_ratio, 0.02, 0.90) * 0.5
	var left_end_t: float = 0.5 - half_gap
	var right_start_t: float = 0.5 + half_gap
	for i in n:
		var a_pos: Vector2 = pts[i]
		var b_pos: Vector2 = pts[(i + 1) % n]
		var ab: Vector2 = b_pos - a_pos
		if ab.length_squared() <= 0.000001:
			continue
		draw_line(a_pos, a_pos + ab * left_end_t, col, width, true)
		draw_line(a_pos + ab * right_start_t, b_pos, col, width, true)


func _draw_empty_hole_outline(pts: PackedVector2Array, col: Color) -> void:
	var width: float = _hole_split_line_width()
	match empty_hole_outline_mode:
		1:
			_draw_vertex_dots_outline(pts, col, width)
		2:
			_draw_vertex_stubs_outline(pts, col, width, empty_hole_vertex_stub_ratio)
		_:
			_draw_split_polygon_outline(pts, col, width, HOLE_SPLIT_GAP_RATIO)


func _draw_vertex_dots_outline(pts: PackedVector2Array, col: Color, width: float) -> void:
	var n: int = pts.size()
	if n < 2:
		return
	var dot_r: float = maxf(width * 0.52, _cell_scale * empty_hole_vertex_dot_radius)
	var mid_r: float = dot_r * 0.9
	for i in n:
		var p: Vector2 = pts[i]
		var q: Vector2 = pts[(i + 1) % n]
		var m: Vector2 = (p + q) * 0.5
		draw_circle(p, dot_r, col)
		draw_circle(m, mid_r, col)


func _draw_vertex_stubs_outline(
		pts: PackedVector2Array, col: Color,
		width: float, stub_ratio: float) -> void:
	var n: int = pts.size()
	if n < 2:
		return
	var t: float = clampf(stub_ratio, 0.05, 0.40)
	for i in n:
		var v: Vector2 = pts[i]
		var prev_v: Vector2 = pts[(i - 1 + n) % n]
		var next_v: Vector2 = pts[(i + 1) % n]
		draw_line(v, v + (prev_v - v) * t, col, width, true)
		draw_line(v, v + (next_v - v) * t, col, width, true)


func _hole_half_outer_path(hex: PackedVector2Array, side: int) -> PackedVector2Array:
	var path := PackedVector2Array()
	if hex.size() < 6:
		return path
	if side >= 0:
		path.append(hex[0])  # top
		path.append(hex[1])  # upper-right
		path.append(hex[2])  # lower-right
		path.append(hex[3])  # bottom
	else:
		path.append(hex[0])  # top
		path.append(hex[5])  # upper-left
		path.append(hex[4])  # lower-left
		path.append(hex[3])  # bottom
	return path


func _draw_hole_path_outline(
		path: PackedVector2Array, col: Color,
		width: float, dashed: bool, dash_len: float = 5.0) -> void:
	var n: int = path.size()
	if n < 2:
		return
	for i in range(n - 1):
		_draw_styled_line(path[i], path[i + 1], col, dashed, width, dash_len, 0.0)


func _hole_split_line_width() -> float:
	var ring_w: float = maxf(2.0, _cell_scale * 3.0)
	return maxf(1.6, ring_w * 0.8)


func _draw_switch_node(
		pos: Vector2i, center: Vector2, NR: float,
		node_dot_r: float, a: float) -> void:
	var active: bool = _spec.state.switch_activated(pos)
	var active_col: Color = Color(1.0, 0.78, 0.0, 1.0)  # Amber (uniform, source-independent)
	var inactive_gray: Color = Color8(128, 128, 128, 255)  # Pure gray, opaque

	if active:
		_draw_diamond(center, NR * 1.5 + 6.0,
				_col(active_col, a), false, 2.0)
		_draw_diamond(center, NR * 1.5,
				_col(Color(0.71, 0.73, 0.76, 0.55), a), false, 2.0)
		draw_circle(center, node_dot_r, _col(Color(0.55, 0.57, 0.60, 0.95), a))
	else:
		_draw_diamond(center, NR * 1.5, _col(inactive_gray, a), false, 2.0)
		draw_circle(center, node_dot_r, _col(inactive_gray, a))


func _draw_branch_node(pos: Vector2i, center: Vector2, tt: int, eff: float, a: float) -> void:
	var uses_map: Dictionary = {
		Enums.TerrainType.BRANCH1: 1,
		Enums.TerrainType.BRANCH2: 2,
		Enums.TerrainType.BRANCH3: 3,
		Enums.TerrainType.BRANCH4: 4,
	}
	# Rings represent extra uses beyond the base one.
	var rings: int = maxi(0, int(uses_map.get(tt, 1)) - 1)

	var base_color: Color = \
		Color(0.31, 0.86, 0.39) if not _spec.has_branched else Color(0.47, 0.47, 0.47)

	# Highlight when player is standing on this point
	var player: Entity = _spec.state.get_player()
	if _spec.highlight_branch_point and player != null and player.pos == pos:
		base_color = Color(0.31, 0.95, 0.40)

	var ring_size_scale: float = 1.2
	var ring_line_width: float = 1.6
	var center_dot_scale: float = 2.3

	for i in rings:
		var r: float = (6.0 + float(i + 1) * 8.0) * _cell_scale * node_scale * ring_size_scale
		draw_arc(center, r, 0, TAU, 32, _col(base_color, a), ring_line_width)

	draw_circle(center, 3.0 * _cell_scale * node_scale * center_dot_scale, _col(base_color, a))


func _draw_goal_node(center: Vector2, eff: float, a: float) -> void:
	var goal_radius: float = _goal_marker_radius(eff) * 1.35
	var pulse: float = 0.6 + 0.4 * sin(_time * 2.0)
	var amber := Color(1.0, 0.78, 0.0)
	var green := Color(0.31, 0.86, 0.39)

	# Preserve goal-state visualization, but remove "G" text.
	if _spec.goal_glow == 0:
		draw_arc(center, goal_radius, 0, TAU, 32,
				_col(Color(0.55, 0.55, 0.55, 0.60), a), 2.0)
		draw_circle(center, goal_radius,
				_col(Color(0.55, 0.55, 0.55, 0.08), a))
	else:
		if _spec.goal_glow == 2:
			draw_arc(center, goal_radius + 8.0, 0, TAU, 32,
					_col(Color(green.r, green.g, green.b, 0.70 * pulse), a), 2.0)
		else:
			draw_arc(center, goal_radius + 8.0, 0, TAU, 32,
					_col(Color(amber.r, amber.g, amber.b, 0.32 * pulse), a), 1.5)
		draw_arc(center, goal_radius, 0, TAU, 32,
				_col(Color(amber.r, amber.g, amber.b, 0.5 + pulse * 0.4), a), 2.0)
		draw_circle(center, goal_radius,
				_col(Color(amber.r, amber.g, amber.b, 0.12 + pulse * 0.12), a))

	# Always draw a centered solid yellow dot (inactive to active).
	var dot_r: float = maxf(6.0 * _cell_scale * node_scale, _goal_marker_radius(eff) * 0.42)
	draw_circle(center, dot_r, _col(Color(1.0, 0.78, 0.0, 1.0), a))


# ---------------------------------------------------------------------------
# Hole helpers
# ---------------------------------------------------------------------------

func _is_hole_filled(pos: Vector2i) -> bool:
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent != null and ent.pos == pos and ent.z == -1:
			return true
	return false


func _goal_marker_radius(eff: float) -> float:
	var player_radius: float = eff * nr_factor * entity_scale * 0.68
	return player_radius * 1.5


func _hole_core_radius(eff: float) -> float:
	return _goal_marker_radius(eff) * hole_core_size_ratio


func _get_uids_in_hole(pos: Vector2i) -> Array[int]:
	var uids: Array[int] = []
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent != null and ent.pos == pos and ent.z == -1:
			uids.append(ent.uid)
	return uids


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

func _draw_entities(eff: float, a: float) -> void:
	var player: Entity   = _spec.state.get_player()
	var overlap_map: Dictionary = _build_overlap_map()
	var rendered_overlap: Dictionary = {}
	var front_pos: Vector2i = \
		player.pos + player.direction if player != null else Vector2i(-1, -1)

	# Sort boxes by z (underground first)
	var boxes: Array[Entity] = []
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent == null or ent.uid == 0 or ent.type != Enums.EntityType.BOX:
			continue
		# Underground boxes are represented by the fused hole node style.
		if ent.z == -1:
			continue
		boxes.append(ent)
	boxes.sort_custom(func(l: Entity, r: Entity) -> bool: return l.z < r.z)

	var is_overlay: bool = _spec.is_merge_preview and not _spec.is_focused

	for ent in boxes:
		# Skip overlay entities at positions already occupied in the focused branch.
		if is_overlay and _spec.overlay_skip_positions.has(ent.pos):
			continue
		var fade_front: bool = (
			_peek_floor_mode
			and _spec.is_focused
			and _spec.scale >= 1.0
			and ent.z == 0
			and ent.pos == front_pos
		)
		var draw_alpha: float = a * (0.18 if fade_front else 1.0)
		var key: String = _entity_stack_key(ent.pos, ent.z)
		var stacked: Array = overlap_map.get(key, [])
		if stacked.size() >= 2:
			if rendered_overlap.has(key):
				continue
			rendered_overlap[key] = true
			_draw_overlap_box_diamond(stacked, ent.pos, eff, draw_alpha)
		else:
			_draw_box_diamond(ent, eff, draw_alpha)

	# Falling box morph animations (z == -1, just dropped into hole).
	_draw_falling_boxes(eff, a)

	# Shadow connections (focused full-size only)
	if _spec.is_focused and _spec.scale >= 1.0:
		_draw_shadow_connections(eff, a)

	_draw_player(player, eff, a)


func _draw_box_diamond(ent: Entity, eff: float, a: float) -> void:
	var cell_scale: float = _cell_scale
	var NR: float         = _nr
	var uid_color: Color  = box_colors[(ent.uid - 1) % 5]
	var is_shadow: bool   = _spec.state.is_shadow(ent.uid)

	var center: Vector2 = _grid_to_local_center(ent.pos, eff)
	var font_size: int = int(14.0 * cell_scale * entity_scale * _spec.overlay_entity_scale)

	if is_shadow:
		# Shadow entity: bg-color fill (clears overlap) + original-color dashed border + colored text.
		_draw_diamond(center, NR, _col(COLOR_BG, a), true)
		var sc_border: Color = uid_color
		sc_border.a = 0.88 * a
		_draw_dashed_diamond(center, NR, sc_border, 1.8, 3.2, 0.0)
		# White outline when this is the facing-box target.
		if _spec.facing_box_hint_pos != Vector2i(-1, -1) and ent.pos == _spec.facing_box_hint_pos:
			_draw_diamond(center, NR, Color(1, 1, 1, 0.90 * a), false, 2.2)
		var sc_text: Color = uid_color
		sc_text.a = 0.92 * a
		_draw_center_text(str(ent.uid), center, font_size, sc_text)
	else:
		# Solid entity: original color fill + black outline + black text.
		var uc: Color = uid_color
		uc.a = a
		_draw_diamond(center, NR, uc, true)
		_draw_diamond(center, NR, Color(0, 0, 0, 0.88 * a), false, 2.2)
		# Facing-box highlight uses the same-size outer frame.
		if _spec.facing_box_hint_pos != Vector2i(-1, -1) and ent.pos == _spec.facing_box_hint_pos:
			_draw_diamond(center, NR, Color(1, 1, 1, 0.95 * a), false, 2.2)
		_draw_center_text(str(ent.uid), center, font_size,
				Color(0.07, 0.07, 0.07, a))


func _draw_overlap_box_diamond(stacked: Array, pos: Vector2i, eff: float, a: float) -> void:
	if stacked.size() < 2:
		return

	var left_ent: Entity = stacked[0] as Entity
	var right_ent: Entity = stacked[1] as Entity
	if left_ent == null or right_ent == null:
		return
	if right_ent.uid < left_ent.uid:
		var tmp: Entity = left_ent
		left_ent = right_ent
		right_ent = tmp

	var NR: float = _nr
	var center: Vector2 = _grid_to_local_center(pos, eff)
	var left_base: Color  = box_colors[(left_ent.uid  - 1) % 5]
	var right_base: Color = box_colors[(right_ent.uid - 1) % 5]
	var left_shadow:  bool = _spec.state.is_shadow(left_ent.uid)
	var right_shadow: bool = _spec.state.is_shadow(right_ent.uid)

	# Background mask: shadow halves need a bg-color underlay so connection lines
	# do not bleed through (rule: floor entities must not show lines behind them).
	if left_shadow:
		_draw_half_diamond(center, NR, _col(COLOR_BG, a), -1, true)
	if right_shadow:
		_draw_half_diamond(center, NR, _col(COLOR_BG, a),  1, true)

	# Fill: original color for solid, minimal tint for shadow (over bg mask).
	var left_fill: Color  = left_base
	var right_fill: Color = right_base
	left_fill.a  = (0.10 if left_shadow  else 0.92) * a
	right_fill.a = (0.10 if right_shadow else 0.92) * a
	_draw_half_diamond(center, NR, left_fill,  -1, true)
	_draw_half_diamond(center, NR, right_fill,  1, true)

	# Outline: white solid for solid entity, original-color dashed for shadow.
	var left_outline:  Color = Color(1, 1, 1, 0.88 * a) if not left_shadow \
			else Color(left_base.r,  left_base.g,  left_base.b,  0.88 * a)
	var right_outline: Color = Color(1, 1, 1, 0.88 * a) if not right_shadow \
			else Color(right_base.r, right_base.g, right_base.b, 0.88 * a)
	_draw_overlap_half_outline(center, NR, -1, left_outline,  left_shadow,  1.6, 3.2, 0.0)
	_draw_overlap_half_outline(center, NR,  1, right_outline, right_shadow, 1.6, 3.2, 0.0)

	# Center divider.
	var center_top:    Vector2 = center + Vector2(0, -NR)
	var center_bottom: Vector2 = center + Vector2(0,  NR)
	var center_col: Color = Color(1, 1, 1, 0.40 * a)
	if left_shadow == right_shadow:
		_draw_styled_line(center_top, center_bottom, center_col, left_shadow, 0.9, 3.0, 0.0)
	else:
		var split_off: float = maxf(0.8, NR * 0.03)
		_draw_styled_line(center_top + Vector2(-split_off, 0), center_bottom + Vector2(-split_off, 0),
				center_col, left_shadow,  0.85, 3.0, 0.0)
		_draw_styled_line(center_top + Vector2(split_off, 0), center_bottom + Vector2(split_off, 0),
				center_col, right_shadow, 0.85, 3.0, 0.0)

	# Labels: two separate numbers on each half.
	# Solid half - black text; shadow half - original-color text.
	var font_size: int = int(13.0 * _cell_scale * entity_scale * _spec.overlay_entity_scale)
	var half_off:  float = NR * 0.32
	var left_text_col: Color = Color(0.07, 0.07, 0.07, a) if not left_shadow \
			else Color(left_base.r,  left_base.g,  left_base.b,  0.92 * a)
	var right_text_col: Color = Color(0.07, 0.07, 0.07, a) if not right_shadow \
			else Color(right_base.r, right_base.g, right_base.b, 0.92 * a)
	_draw_center_text(str(left_ent.uid),  center + Vector2(-half_off, 0), font_size, left_text_col)
	_draw_center_text(str(right_ent.uid), center + Vector2( half_off, 0), font_size, right_text_col)


func _draw_player(player: Entity, eff: float, a: float) -> void:
	if player == null:
		return

	var is_overlay: bool = _spec.is_merge_preview and not _spec.is_focused

	# Skip overlay player if at a position shared with the focused branch.
	if is_overlay and _spec.overlay_skip_positions.has(player.pos):
		return

	var cell_scale: float = _cell_scale
	var NR: float         = _nr
	var PR: float         = NR * 0.68
	var arrow_base: float = PR
	var center: Vector2   = _grid_to_local_center(player.pos, eff)

	# Overlay mode: always draw as desaturated blue circle, no arrow.
	if is_overlay:
		var fill_col := _desat(Color(0.467, 0.600, 0.933, 1.0), 0.35)
		var rim_col  := _desat(Color(0.78, 0.86, 1.0, 0.75), 0.35)
		draw_circle(center, PR, _col(fill_col, a))
		draw_arc(center, PR, 0, TAU, 24, _col(rim_col, a), 2.0)
		return

	var held_items: Array[int] = _spec.state.get_held_items()
	var held_uid: int     = held_items[0] if not held_items.is_empty() else -1
	var font_size: int    = int(14.0 * cell_scale * entity_scale)
	# On NO_CARRY tile the player loses carry ability — render hollow to signal this.
	var on_drop_zone: bool = \
		_spec.state.terrain.get(player.pos, Enums.TerrainType.FLOOR) == Enums.TerrainType.NO_CARRY

	if on_drop_zone:
		var hole_r: float = PR * DROP_ZONE_HOLE_RATIO
		var mid_r: float = (PR + hole_r) * 0.5
		var band_w: float = maxf(1.6, PR - hole_r)
		draw_arc(center, mid_r, 0.0, TAU, 28,
				_col(Color(0.467, 0.600, 0.933, 1.0), a), band_w, true)
		draw_arc(center, PR, 0, TAU, 24,
				_col(Color(0.78, 0.86, 1.0, 0.75), a), 2.0)
	elif held_uid != -1:
		var uid_color: Color = box_colors[(held_uid - 1) % 5]
		var uc: Color = uid_color
		uc.a = a
		_draw_diamond(center, NR, uc, true)
		_draw_diamond(center, NR, Color(1, 1, 1, 0.80 * a), false, 2.2)
		_draw_center_text(str(held_uid), center, font_size,
				Color(0.07, 0.07, 0.07, a))
	else:
		draw_circle(center, PR, _col(Color(0.467, 0.600, 0.933, 1.0), a))
		draw_arc(center, PR, 0, TAU, 24,
				_col(Color(0.78, 0.86, 1.0, 0.75), a), 2.0)

	# Arrow
	if _spec.show_player_direction:
		_draw_dir_arrow(center, player.direction, arrow_base, Color(1, 1, 1, 0.92 * a))


# ---------------------------------------------------------------------------
# Visual helpers - diamonds, glow, arrows
# ---------------------------------------------------------------------------

func _draw_diamond(
		center: Vector2, size: float, color: Color,
		filled: bool, line_width: float = 2.0) -> void:
	var pts := PackedVector2Array([
		center + Vector2(0,    -size),
		center + Vector2(size,  0   ),
		center + Vector2(0,     size),
		center + Vector2(-size, 0   ),
	])
	if filled:
		draw_colored_polygon(pts, color)
	else:
		var closed := PackedVector2Array(pts)
		closed.append(pts[0])
		draw_polyline(closed, color, line_width)


func _draw_dashed_diamond(
		center: Vector2, size: float, color: Color,
		line_width: float = 1.0, dash_len: float = 5.0, offset: float = 0.0) -> void:
	var top: Vector2 = center + Vector2(0, -size)
	var right: Vector2 = center + Vector2(size, 0)
	var bottom: Vector2 = center + Vector2(0, size)
	var left: Vector2 = center + Vector2(-size, 0)
	_draw_dashed_line(top, right, color, line_width, dash_len, offset)
	_draw_dashed_line(right, bottom, color, line_width, dash_len, offset)
	_draw_dashed_line(bottom, left, color, line_width, dash_len, offset)
	_draw_dashed_line(left, top, color, line_width, dash_len, offset)


func _draw_dashed_circle(
		center: Vector2, radius: float, color: Color,
		line_width: float = 1.0, dash_count: int = 24,
		duty: float = 0.55, phase: float = 0.0) -> void:
	if radius <= 0.001 or dash_count < 2:
		return
	var seg: float = TAU / float(dash_count)
	var on: float = seg * clampf(duty, 0.05, 0.95)
	for i in dash_count:
		var start: float = phase + float(i) * seg
		var end: float = start + on
		draw_arc(center, radius, start, end, 6, color, line_width, true)


func _draw_dashed_arc(
		center: Vector2, radius: float, color: Color,
		angle_from: float, angle_to: float,
		line_width: float = 1.0, dash_count: int = 9,
		duty: float = 0.55) -> void:
	if radius <= 0.001 or dash_count < 1:
		return
	var seg: float = (angle_to - angle_from) / float(dash_count)
	var on: float  = seg * clampf(duty, 0.05, 0.95)
	for i in dash_count:
		var start: float = angle_from + float(i) * seg
		draw_arc(center, radius, start, start + on, 4, color, line_width, true)


func _draw_half_diamond(
		center: Vector2, size: float, color: Color,
		side: int, filled: bool) -> void:
	var pts: PackedVector2Array
	if side == -1:  # left half
		pts = PackedVector2Array([
			center + Vector2(0,    -size),
			center + Vector2(0,     size),
			center + Vector2(-size, 0   ),
		])
	else:           # right half
		pts = PackedVector2Array([
			center + Vector2(0,    -size),
			center + Vector2(size,  0   ),
			center + Vector2(0,     size),
		])
	if filled:
		draw_colored_polygon(pts, color)
	else:
		var closed := PackedVector2Array(pts)
		closed.append(pts[0])
		draw_polyline(closed, color, 1.5)


func _draw_overlap_half_outline(
		center: Vector2, size: float, side: int,
		color: Color, dashed: bool,
		line_width: float = 2.0, dash_len: float = 5.0, offset: float = 0.0) -> void:
	var top: Vector2 = center + Vector2(0, -size)
	var bottom: Vector2 = center + Vector2(0, size)
	if side == -1:
		var left: Vector2 = center + Vector2(-size, 0)
		_draw_styled_line(top, left, color, dashed, line_width, dash_len, offset)
		_draw_styled_line(left, bottom, color, dashed, line_width, dash_len, offset)
	else:
		var right: Vector2 = center + Vector2(size, 0)
		_draw_styled_line(top, right, color, dashed, line_width, dash_len, offset)
		_draw_styled_line(right, bottom, color, dashed, line_width, dash_len, offset)


func _draw_styled_line(
		from_pos: Vector2, to_pos: Vector2, col: Color, dashed: bool,
		width: float = 2.0, dash_len: float = 5.0, offset: float = 0.0) -> void:
	if dashed:
		_draw_dashed_line(from_pos, to_pos, col, width, dash_len, offset)
	else:
		draw_line(from_pos, to_pos, col, width, true)


func _draw_glow(
		center: Vector2, radius: float,
		color: Color, peak_alpha: float) -> void:
	# 3 layers outer->inner so the bright core draws on top
	for i in range(2, -1, -1):
		var r: float = radius * (0.4 + float(i) * 0.3)
		var c: Color = color
		c.a = peak_alpha * (1.0 - float(i) * 0.3)
		draw_circle(center, r, c)


## Direction arrow for entity / player (new geometry, scale-aware).
func _draw_dir_arrow(
		origin: Vector2, dir: Vector2i,
		base_size: float, color: Color) -> void:
	var fdir := Vector2(float(dir.x), float(dir.y))
	if fdir.length_squared() <= 0.0:
		return
	var perp  := Vector2(-float(dir.y), float(dir.x))
	var thickness: float = maxf(2.0, base_size * 0.24)
	var arm_len: float = base_size * 0.75
	var half_span: float = base_size * 0.62

	# Keep the marker near the player to avoid clipping outside panel bounds.
	var center := origin + fdir * base_size * 1.375
	var tip := center + fdir * arm_len
	var p0 := center - perp * half_span
	var p1 := tip
	var p2 := center + perp * half_span
	draw_polyline(PackedVector2Array([p0, p1, p2]), color, thickness, true)


# ---------------------------------------------------------------------------
# Falling animation helper
# ---------------------------------------------------------------------------

## Returns fall progress 0-1 for (uid, pos), or -1 if not falling.
func _get_fall_progress(uid: int, pos: Vector2i) -> float:
	for raw_key in _spec.falling_progress.keys():
		var k: Array = raw_key as Array
		if k[0] == uid and k[1] == pos:
			return _spec.falling_progress[raw_key] as float
	return -1.0


## Builds N polygon points interpolated between a diamond (t=0) and circle (t=1).
## Diamond boundary in polar: r = NR / (|cos(theta)| + |sin(theta)|).
func _morph_diamond_circle_pts(center: Vector2, NR: float, t: float, N: int = 32) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in N:
		var theta: float    = float(i) * TAU / float(N)
		var r_diamond: float = NR / maxf(abs(cos(theta)) + abs(sin(theta)), 0.0001)
		var r: float         = lerpf(r_diamond, NR, t)
		pts.append(center + Vector2(cos(theta) * r, sin(theta) * r))
	return pts


## Draws hole-fill animation for boxes at z==-1 with active fall progress.
## The active visual scheme is selected by `hole_fill_anim_mode`.
func _draw_falling_boxes(eff: float, a: float) -> void:
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent == null or ent.uid == 0 or ent.type != Enums.EntityType.BOX or ent.z != -1:
			continue
		var t: float = _get_fall_progress(ent.uid, ent.pos)
		if t < 0.0:
			continue

		var NR: float        = _nr
		var core_r: float    = _hole_core_radius(eff)
		var ring_w: float    = maxf(2.0, _cell_scale * 3.0)
		var outer_r: float   = core_r + ring_w
		var uid_color: Color = box_colors[(ent.uid - 1) % 5]
		var is_shadow: bool  = _spec.state.is_shadow(ent.uid)
		var center: Vector2  = _grid_to_local_center(ent.pos, eff)
		var t_anim: float = clampf(t, 0.0, 1.0)
		if t_anim <= 0.0001:
			_draw_falling_entry_overlay(center, NR, uid_color, is_shadow, ent.uid, a)
			continue

		if hole_fill_anim_mode == 2:
			_draw_falling_hex_flash_mode(center, outer_r, uid_color, is_shadow, t_anim, a)
		else:
			_draw_falling_hex_expand_mode(center, NR, outer_r, uid_color, is_shadow, t_anim, a)


func _draw_falling_hex_expand_mode(
		center: Vector2, NR: float, outer_r: float,
		uid_color: Color, is_shadow: bool,
		t: float, a: float) -> void:
	var morph_cut: float = 0.62
	if t < morph_cut:
		var p: float = clampf(t / morph_cut, 0.0, 1.0)
		var radius: float = lerpf(NR, outer_r, p)
		var pts: PackedVector2Array = _morph_diamond_hex_pts(center, radius, p, -PI * 0.5, 30)
		var hex: PackedVector2Array = _regular_ngon_points(center, radius, 6, -PI * 0.5)
		if is_shadow:
			draw_colored_polygon(pts, _col(COLOR_BG, a))
			_draw_split_polygon_outline(
				hex,
				Color(uid_color.r, uid_color.g, uid_color.b, (0.45 + 0.45 * p) * a),
				_hole_split_line_width(),
				HOLE_SPLIT_GAP_RATIO
			)
		else:
			draw_colored_polygon(pts, Color(uid_color.r, uid_color.g, uid_color.b, (0.88 + 0.08 * p) * a))
			_draw_polygon_outline(hex, Color(1, 1, 1, (0.45 + 0.35 * p) * a), maxf(1.4, _cell_scale * 2.0))
		return

	var p2: float = clampf((t - morph_cut) / maxf(0.001, 1.0 - morph_cut), 0.0, 1.0)
	var hex_outer: PackedVector2Array = _regular_ngon_points(center, outer_r, 6, -PI * 0.5)
	if is_shadow:
		_draw_split_polygon_outline(
			hex_outer,
			Color(uid_color.r, uid_color.g, uid_color.b, (0.70 + 0.25 * p2) * a),
			_hole_split_line_width(),
			HOLE_SPLIT_GAP_RATIO
		)
	else:
		var fill_alpha: float = (1.0 - p2) * 0.92 * a
		if fill_alpha > 0.001:
			draw_colored_polygon(hex_outer, Color(uid_color.r, uid_color.g, uid_color.b, fill_alpha))
		_draw_polygon_outline(
			hex_outer,
			Color(uid_color.r, uid_color.g, uid_color.b, (0.35 + 0.65 * p2) * a),
			maxf(2.4, _cell_scale * 4.0)
		)


func _draw_falling_hex_flash_mode(
		center: Vector2, outer_r: float,
		uid_color: Color, is_shadow: bool,
		t: float, a: float) -> void:
	var flash_cut: float = 0.45
	var hex_outer: PackedVector2Array = _regular_ngon_points(center, outer_r, 6, -PI * 0.5)
	if t < flash_cut:
		var p: float = clampf(t / flash_cut, 0.0, 1.0)
		# Single flash envelope (one rise), avoids repeated time-based pulsing.
		var pulse: float = sin(p * PI * 0.5)
		var white_fill_a: float = (0.18 + 0.74 * pulse) * a
		draw_colored_polygon(hex_outer, Color(1, 1, 1, white_fill_a))
		_draw_polygon_outline(hex_outer, Color(1, 1, 1, (0.35 + 0.55 * pulse) * a), maxf(2.0, _cell_scale * 3.4))
		return

	var p2: float = clampf((t - flash_cut) / maxf(0.001, 1.0 - flash_cut), 0.0, 1.0)
	var white_alpha: float = (1.0 - p2) * 0.90 * a
	if white_alpha > 0.001:
		draw_colored_polygon(hex_outer, Color(1, 1, 1, white_alpha))

	if is_shadow:
		_draw_split_polygon_outline(
			hex_outer,
			Color(uid_color.r, uid_color.g, uid_color.b, (0.55 + 0.40 * p2) * a),
			_hole_split_line_width(),
			HOLE_SPLIT_GAP_RATIO
		)
	else:
		_draw_polygon_outline(
			hex_outer,
			Color(uid_color.r, uid_color.g, uid_color.b, (0.25 + 0.70 * p2) * a),
			maxf(2.4, _cell_scale * 4.0)
		)


func _draw_falling_entry_overlay(
		center: Vector2, NR: float,
		uid_color: Color, is_shadow: bool,
		uid: int, a: float) -> void:
	var font_size: int = int(14.0 * _cell_scale * entity_scale * _spec.overlay_entity_scale)
	if is_shadow:
		_draw_diamond(center, NR, _col(COLOR_BG, a), true)
		_draw_dashed_diamond(center, NR, Color(uid_color.r, uid_color.g, uid_color.b, 0.88 * a), 1.8, 3.2, 0.0)
		_draw_center_text(str(uid), center, font_size, Color(uid_color.r, uid_color.g, uid_color.b, 0.92 * a))
	else:
		_draw_diamond(center, NR, Color(uid_color.r, uid_color.g, uid_color.b, a), true)
		_draw_diamond(center, NR, Color(0, 0, 0, 0.88 * a), false, 2.2)
		_draw_center_text(str(uid), center, font_size, Color(0.07, 0.07, 0.07, a))


# ---------------------------------------------------------------------------
# Overlap utilities
# ---------------------------------------------------------------------------

## Returns a dict: entity_stack_key -> Array[uid] (only keys with >=2 entries matter).
func _build_overlap_map() -> Dictionary:
	var by_key: Dictionary = {}
	for e in _spec.state.entities:
		var ent: Entity = e as Entity
		if ent == null or ent.uid == 0 or ent.type != Enums.EntityType.BOX:
			continue
		if ent.z == -1:
			continue
		var key: String = _entity_stack_key(ent.pos, ent.z)
		if not by_key.has(key):
			by_key[key] = []
		var stack: Array = by_key[key]
		stack.append(ent)
		by_key[key] = stack

	# Stable left/right assignment for split overlap diamonds.
	for key in by_key.keys():
		var stack: Array = by_key[key]
		stack.sort_custom(func(l_raw, r_raw) -> bool:
			var l: Entity = l_raw as Entity
			var r: Entity = r_raw as Entity
			if l == null or r == null:
				return false
			if l.uid == r.uid:
				return l.z < r.z
			return l.uid < r.uid
		)
		by_key[key] = stack
	return by_key


func _entity_stack_key(pos: Vector2i, z: int) -> String:
	return "%d|%d|%d" % [pos.x, pos.y, z]


# ---------------------------------------------------------------------------
# Static helpers - used by LevelPreview.gd
# ---------------------------------------------------------------------------

static func branch_marker_dot_radius(cell_scale: float) -> float:
	return maxf(4.0, 8.0 * cell_scale)


static func branch_marker_dot_positions(
		center: Vector2, tt: int, cell_scale: float) -> PackedVector2Array:
	var uses_map := {
		Enums.TerrainType.BRANCH1: 1, Enums.TerrainType.BRANCH2: 2,
		Enums.TerrainType.BRANCH3: 3, Enums.TerrainType.BRANCH4: 4,
	}
	var uses: int = uses_map.get(tt, 1)
	var br: float = branch_marker_dot_radius(cell_scale)
	var sp: float = br * 2.8

	var dots := PackedVector2Array()
	match uses:
		1:
			dots.append(center)
		2:
			var h := sp * 0.5
			dots.append(center + Vector2(-h, 0.0))
			dots.append(center + Vector2( h, 0.0))
		3:
			var R := sp / sqrt(3.0)
			dots.append(center + Vector2( 0.0,      -R))
			dots.append(center + Vector2(-sp * 0.5,  R * 0.5))
			dots.append(center + Vector2( sp * 0.5,  R * 0.5))
		4:
			var h := sp * 0.5
			dots.append(center + Vector2(-h, -h))
			dots.append(center + Vector2( h, -h))
			dots.append(center + Vector2(-h,  h))
			dots.append(center + Vector2( h,  h))
	return dots


# ---------------------------------------------------------------------------
# Shadow connections - preserved unchanged
# ---------------------------------------------------------------------------

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
	var offset: float = _dash_offset()

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

		var base_color: Color = box_colors[(uid - 1) % 5]
		var line_color: Color = Color(base_color.r, base_color.g, base_color.b, 0.72 * a)

		for raw_pos in positions.keys():
			var pos: Vector2i = raw_pos as Vector2i
			if pos == front_pos:
				continue
			var other_center: Vector2 = _grid_to_local_center(pos, eff)
			var seg: Vector2 = front_center - other_center
			var seg_len: float = seg.length()
			var clip: float = _nr
			if seg_len <= clip * 2.0:
				continue
			var seg_dir: Vector2 = seg / seg_len
			_draw_dashed_line(
				other_center + seg_dir * clip,
				front_center - seg_dir * clip,
				line_color, 2.8, 12.0, offset)


# ---------------------------------------------------------------------------
# Flash, border, title - preserved
# ---------------------------------------------------------------------------

func _draw_flash(eff: float, a: float) -> void:
	var center: Vector2 = _grid_to_local_center(_spec.flash_pos, eff)
	var alpha_k: float = _spec.flash_intensity * a
	var col := COLOR_FLASH
	col.a = alpha_k
	match _spec.flash_style:
		"player_circle":
			var pr: float = _nr * 0.68
			draw_circle(center, pr, Color(col.r, col.g, col.b, 0.30 * alpha_k))
			draw_arc(center, pr, 0.0, TAU, 24, Color(col.r, col.g, col.b, 0.95 * alpha_k), 2.4, true)
		"player_square":
			var nr: float = _nr
			_draw_diamond(center, nr, Color(col.r, col.g, col.b, 0.32 * alpha_k), true)
			_draw_diamond(center, nr, Color(col.r, col.g, col.b, 0.95 * alpha_k), false, 2.4)
		"diamond":
			var nr: float = _nr
			_draw_diamond(center, nr, Color(col.r, col.g, col.b, 0.40 * alpha_k), true)
			_draw_diamond(center, nr, Color(col.r, col.g, col.b, 0.95 * alpha_k), false, 3.0)
		_:
			var rect := Rect2(
				_spec.flash_pos.x * eff,
				_spec.flash_pos.y * eff,
				eff, eff)
			draw_rect(rect, col)


func _draw_border(gpx: float, a: float) -> void:
	var col := _spec.border_color
	col.a   *= a
	draw_rect(Rect2(0, 0, gpx, gpx), col, false, border_w)


func _draw_title(gpx: float, a: float) -> void:
	var col   := _col(COLOR_TITLE, a)
	var size  := int(16.0 * _cell_scale)
	var title_y: float = -maxf(14.0, title_margin_base * _cell_scale)
	_draw_center_text(_spec.title, Vector2(gpx * 0.5, title_y), size, col)


# ---------------------------------------------------------------------------
# Interaction hint - floating text above target entity/position
# ---------------------------------------------------------------------------

func _draw_interaction_hint(eff: float, a: float) -> void:
	var ih = _spec.interaction_hint
	if ih == null or ih.text == "":
		return
	if ih.target_pos == Vector2i(-1, -1):
		return
	var player: Entity = _spec.state.get_player()
	if player == null:
		return
	var font: Font = ThemeDB.fallback_font
	if font == null:
		return
	var NR: float       = _nr
	var cell_scale: float = _cell_scale
	var font_size: int  = maxi(10, int(round(11.0 * cell_scale)))
	if ih.text == "放下":
		var drop_center: Vector2 = _grid_to_local_center(ih.target_pos, eff)
		var drop_size: float = NR * 0.90
		var frame_col: Color = COLOR_INTERACT_GRAY
		frame_col.a = 0.9 * a
		_draw_dashed_diamond(
				drop_center,
				drop_size,
				frame_col,
				maxf(1.2, 1.8 * cell_scale),
				maxf(3.0, 4.0 * cell_scale),
				0.0)
	var anchor: Vector2 = _grid_to_local_center(ih.target_pos, eff)
	var clearance: float = NR + 9.0 * cell_scale + 2.0
	var text_center: Vector2 = anchor - Vector2(0.0, clearance)
	var hint_text: String = ih.text
	var text_w: float  = font.get_string_size(hint_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
	var ascent: float  = font.get_ascent(font_size)
	var descent: float = font.get_descent(font_size)
	var baseline_y: float = text_center.y + (ascent - descent) * 0.5
	var draw_pos: Vector2 = Vector2(text_center.x - text_w * 0.5, baseline_y)
	# Black outline: 4 offset draws.
	var shadow: Color = Color(0, 0, 0, 0.85 * a)
	for dx in [-1, 0, 1]:
		for dy in [-1, 0, 1]:
			if dx == 0 and dy == 0:
				continue
			draw_string(font, draw_pos + Vector2(dx, dy), hint_text,
					HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, shadow)
	# Fixed white foreground for interaction hint readability.
	var col: Color = Color(1.0, 1.0, 1.0, a)
	draw_string(font, draw_pos, hint_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, col)


# Interaction hint highlight - preserved
# ---------------------------------------------------------------------------

func _draw_hint_highlight(
		pos: Vector2i, hint_text: String, _hint_col: Color,
		is_inset: bool, eff: float, a: float) -> void:
	var rect := Rect2(pos.x * eff, pos.y * eff, eff, eff)
	var cell_scale: float = _cell_scale
	var center: Vector2 = rect.get_center()
	_update_hint_text_overlay(hint_text, center, cell_scale, a)

	if is_inset:
		var margin: float    = maxf(2.0, 8.0 * cell_scale)
		var inset_rect: Rect2 = rect.grow(-margin)
		var frame_col: Color  = COLOR_INTERACT_GRAY
		frame_col.a           = 0.9 * a
		_draw_dashed_rect(
			_pixel_snap_rect(inset_rect),
			frame_col,
			float(maxi(1, int(round(2.0 * cell_scale)))))
		return

	var corner_color: Color = COLOR_INTERACT_GRAY
	corner_color.a = 0.95 * a
	_draw_lock_corners(
		rect, corner_color,
		maxf(8.0, 24.0 * cell_scale),
		maxf(1.0,  4.0 * cell_scale),
		-3.0 * cell_scale)


func _draw_lock_corners(
		rect: Rect2, col: Color,
		corner_size: float, thickness: float, margin: float = 0.0) -> void:
	var r: Rect2    = _pixel_snap_rect(rect.grow(margin))
	var left: float = r.position.x
	var top: float  = r.position.y
	var right: float  = r.position.x + r.size.x
	var bottom: float = r.position.y + r.size.y
	var size: float = minf(corner_size, minf(r.size.x * 0.5, r.size.y * 0.5))

	draw_line(Vector2(left,         top),          Vector2(left + size, top),          col, thickness, true)
	draw_line(Vector2(left,         top),          Vector2(left,        top + size),   col, thickness, true)
	draw_line(Vector2(right - size, top),          Vector2(right,       top),          col, thickness, true)
	draw_line(Vector2(right,        top),          Vector2(right,       top + size),   col, thickness, true)
	draw_line(Vector2(left,         bottom - size),Vector2(left,        bottom),       col, thickness, true)
	draw_line(Vector2(left,         bottom),       Vector2(left + size, bottom),       col, thickness, true)
	draw_line(Vector2(right - size, bottom),       Vector2(right,       bottom),       col, thickness, true)
	draw_line(Vector2(right,        bottom - size),Vector2(right,       bottom),       col, thickness, true)


# ---------------------------------------------------------------------------
# Hint label system - preserved
# ---------------------------------------------------------------------------

func _ensure_hint_labels() -> void:
	if _hint_space_label == null:
		_hint_space_label       = _create_hint_label()
		_hint_space_label.text  = "[SPACE]"
		add_child(_hint_space_label)
	if _hint_action_label == null:
		_hint_action_label = _create_hint_label()
		add_child(_hint_action_label)


func _create_hint_label() -> Label:
	var label: Label = Label.new()
	label.visible               = false
	label.mouse_filter          = Control.MOUSE_FILTER_IGNORE
	label.horizontal_alignment  = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment    = VERTICAL_ALIGNMENT_CENTER
	return label


func _set_hint_labels_visible(v: bool) -> void:
	if _hint_space_label  != null: _hint_space_label.visible  = v
	if _hint_action_label != null: _hint_action_label.visible = v


func _update_hint_text_overlay(
		hint_text: String, center: Vector2,
		cell_scale: float, a: float) -> void:
	_ensure_hint_labels()

	var font_size:    int   = maxi(10, int(round(12.0 * cell_scale)))
	var outline_size: int   = maxi(2,  int(round( 2.4 * cell_scale)))
	var label_w:      float = round(maxf( 90.0, 130.0 * cell_scale))
	var label_h:      float = round(maxf( 16.0,  22.0 * cell_scale))
	var top_center:    Vector2 = Vector2(center.x, center.y +  8.0 * cell_scale)
	var bottom_center: Vector2 = Vector2(center.x, center.y - 12.0 * cell_scale)

	_apply_hint_label_style(_hint_space_label,  font_size, outline_size, a)
	_apply_hint_label_style(_hint_action_label, font_size, outline_size, a)

	_hint_action_label.text = hint_text
	_layout_hint_label(_hint_space_label,  top_center,    label_w, label_h)
	_layout_hint_label(_hint_action_label, bottom_center, label_w, label_h)
	_set_hint_labels_visible(true)


func _apply_hint_label_style(
		label: Label, font_size: int,
		outline_size: int, a: float) -> void:
	label.add_theme_font_size_override("font_size",         font_size)
	label.add_theme_constant_override("outline_size",       outline_size)
	label.add_theme_color_override("font_color",            Color(1.0, 1.0, 1.0, a))
	label.add_theme_color_override("font_outline_color",    Color(0.0, 0.0, 0.0, a))
	label.add_theme_constant_override("shadow_outline_size",outline_size)
	label.add_theme_color_override("font_shadow_color",     Color(0.0, 0.0, 0.0, a))
	label.add_theme_constant_override("shadow_offset_x",    0)
	label.add_theme_constant_override("shadow_offset_y",    0)


func _layout_hint_label(ctrl: Control, center: Vector2, w: float, h: float) -> void:
	ctrl.position = Vector2(round(center.x - w * 0.5), round(center.y - h * 0.5))
	ctrl.size     = Vector2(w, h)


# ---------------------------------------------------------------------------
# Dashed drawing utilities - preserved
# ---------------------------------------------------------------------------

func _draw_dashed_rect(rect: Rect2, col: Color, width: float) -> void:
	var dash: float = 5.0
	var gap:  float = 5.0
	var step: float = dash + gap
	var x0: float = rect.position.x
	var y0: float = rect.position.y
	var x1: float = rect.position.x + rect.size.x
	var y1: float = rect.position.y + rect.size.y

	var i: float = 0.0
	while i < rect.size.x:
		var seg_x: float = minf(i + dash, rect.size.x)
		draw_line(Vector2(x0 + i, y0), Vector2(x0 + seg_x, y0), col, width, true)
		draw_line(Vector2(x0 + i, y1), Vector2(x0 + seg_x, y1), col, width, true)
		i += step

	i = 0.0
	while i < rect.size.y:
		var seg_y: float = minf(i + dash, rect.size.y)
		draw_line(Vector2(x0, y0 + i), Vector2(x0, y0 + seg_y), col, width, true)
		draw_line(Vector2(x1, y0 + i), Vector2(x1, y0 + seg_y), col, width, true)
		i += step


func _draw_dashed_line(
		from_pos: Vector2, to_pos: Vector2,
		col: Color, width: float = 3.0,
		dash_len: float = 9.0, offset: float = 0.0) -> void:
	var dist: float = from_pos.distance_to(to_pos)
	if dist <= 0.001:
		return
	var dir: Vector2 = (to_pos - from_pos) / dist
	var period: float = dash_len * 2.0
	var pos: float = fmod(offset, period)
	while pos < dist:
		var seg_start: float = maxf(0.0, pos)
		var seg_end:   float = minf(dist, pos + dash_len)
		if seg_end > seg_start:
			draw_line(from_pos + dir * seg_start, from_pos + dir * seg_end, col, width, true)
		pos += period


func _draw_dashed_gradient_line(
		from_pos: Vector2, to_pos: Vector2,
		col_start: Color, col_end: Color,
		width: float = 3.0, dash_len: float = 9.0, offset: float = 0.0) -> void:
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
			var t: float = ((seg_start + seg_end) * 0.5) / dist
			var seg_col: Color = col_start.lerp(col_end, clampf(t, 0.0, 1.0))
			draw_line(from_pos + dir * seg_start, from_pos + dir * seg_end, seg_col, width, true)
		pos += period


func _dash_offset(speed: float = -1.0) -> float:
	if speed < 0.0:
		speed = dash_scroll_speed
	return (Time.get_ticks_msec() / 1000.0) * speed


# ---------------------------------------------------------------------------
# General utilities - preserved
# ---------------------------------------------------------------------------

func _grid_to_local_center(pos: Vector2i, eff: float) -> Vector2:
	return Vector2((float(pos.x) + 0.5) * eff, (float(pos.y) + 0.5) * eff)


func _pixel_snap_rect(rect: Rect2) -> Rect2:
	return Rect2(
		round(rect.position.x), round(rect.position.y),
		round(rect.size.x),     round(rect.size.y))


func _col(c: Color, a: float) -> Color:
	var out := c
	out.a   *= a
	return out


## Reduce saturation: factor 1.0 = original, 0.0 = fully gray.
func _desat(c: Color, factor: float) -> Color:
	var gray: float = c.r * 0.299 + c.g * 0.587 + c.b * 0.114
	return Color(
		lerpf(gray, c.r, factor),
		lerpf(gray, c.g, factor),
		lerpf(gray, c.b, factor),
		c.a)


func _draw_center_text(text: String, center: Vector2, font_size: int, col: Color) -> void:
	if text == "":
		return
	var font: Font = ThemeDB.fallback_font
	if font == null:
		return
	var text_w:     float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
	var ascent:     float = font.get_ascent(font_size)
	var descent:    float = font.get_descent(font_size)
	var baseline_y: float = center.y + (ascent - descent) * 0.5
	draw_string(font,
		Vector2(center.x - text_w * 0.5, baseline_y),
		text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, col)
