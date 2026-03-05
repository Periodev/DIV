extends Control
class_name SystemCalloutUI

const COL_LINE_DIM   := Color(1.0, 1.0, 1.0, 0.25)
const COL_LINE_LIT   := Color(1.0, 1.0, 1.0, 0.95)
const COL_TEXT_DIM   := Color(0.6, 0.6, 0.6, 1.0)
const COL_TEXT_LIT   := Color(0.95, 0.95, 0.95, 1.0)
const COL_STATUS     := Color(0.4, 0.8, 0.9, 0.8)
const COL_DIV_DOT    := Color(0.36, 0.92, 0.48, 0.95)
const COL_DIVERGE_DEEP := Color(0.16, 0.52, 0.24, 0.98)
const COL_READY_DIVERGE := Color(0.36, 0.92, 0.48, 0.98)
const COL_READY_MERGE   := Color(0.30, 0.62, 1.00, 0.98)
const COL_READY_FETCH   := Color(1.00, 0.62, 0.18, 0.98)

var is_diverged: bool = false
var active_branch: int = 0
var div_points: int = 0
var can_v_merge: bool = false
var can_f_fetch: bool = false
var unlock_diverge: bool = true
var unlock_merge: bool = true
var unlock_fetch: bool = true
var preview_active: bool = false
var highlight_node: String = ""        # "diverge", "merge", "tab", "preview", ""
var highlight_annotations: Array = []  # ["藍色 = 可合併", ...]
var _pulse_time: float = 0.0
var _tab_text_rect: Rect2 = Rect2()
var merge_anim_t: float = 0.0


func set_merge_anim_t(t: float) -> void:
	merge_anim_t = t
	queue_redraw()


func set_highlight(node_name: String, annotations: Array = []) -> void:
	highlight_node = node_name
	highlight_annotations = annotations
	queue_redraw()


func _process(delta: float) -> void:
	if highlight_node != "":
		_pulse_time += delta
		queue_redraw()
	else:
		_pulse_time = 0.0


func update_state(
		diverged: bool,
		focus: int,
		pts: int,
		v_merge: bool,
		f_fetch: bool,
		can_diverge_ui: bool = true,
		can_fetch_ui: bool = true,
		preview_active_ui: bool = false) -> void:
	is_diverged = diverged
	active_branch = focus
	div_points = pts
	can_v_merge = v_merge
	can_f_fetch = f_fetch
	unlock_diverge = can_diverge_ui
	# Merge unlock follows diverge unlock by design.
	unlock_merge = can_diverge_ui
	unlock_fetch = can_fetch_ui
	preview_active = preview_active_ui
	queue_redraw()


func _draw() -> void:
	var font: Font = ThemeDB.fallback_font
	if font == null:
		return

	var font_size: int = 14
	var center_x: float = size.x * 0.5
	var baseline_y: float = size.y - 70.0

	# Track node positions for highlight
	var node_positions: Dictionary = {}  # name → Vector2

	if not is_diverged:
		var line_w: float = 200.0
		var left_end: float = center_x - line_w
		var right_end: float = center_x + line_w

		draw_line(Vector2(left_end, baseline_y), Vector2(right_end, baseline_y), COL_LINE_DIM, 1.0)
		var diverge_pos := Vector2(center_x, baseline_y)
		node_positions["diverge"] = diverge_pos
		_draw_gated_callout_node(
			diverge_pos,
			"[V] 分裂",
			unlock_diverge,
			unlock_diverge and div_points > 0,
			COL_DIVERGE_DEEP,
			true,
			font,
			font_size
		)
		if unlock_diverge and div_points > 0:
			draw_circle(diverge_pos, 5.0, COL_READY_DIVERGE)
		_draw_div_dots(diverge_pos, div_points)
	else:
		var line_w: float = size.x * 0.12
		var left_end: float = center_x - 200.0
		var right_end: float = center_x + 200.0

		var f_x: float = center_x - line_w
		var v_x: float = center_x
		var m_x: float = center_x + line_w

		draw_line(Vector2(left_end, baseline_y), Vector2(right_end, baseline_y), COL_LINE_DIM, 1.0)
		node_positions["fetch"] = Vector2(f_x, baseline_y)
		_draw_gated_callout_node(
			Vector2(f_x, baseline_y),
			"[F] FETCH MERGE",
			unlock_fetch,
			unlock_fetch and can_f_fetch,
			COL_READY_FETCH,
			false,
			font,
			font_size
		)
		node_positions["merge"] = Vector2(v_x, baseline_y)
		_draw_gated_callout_node(
			Vector2(v_x, baseline_y),
			"[V] 合併",
			unlock_merge,
			unlock_merge and can_v_merge,
			COL_READY_MERGE,
			false,
			font,
			font_size
		)
		node_positions["preview"] = Vector2(m_x, baseline_y)
		_draw_preview_toggle_node(Vector2(m_x, baseline_y), preview_active, font, font_size, merge_anim_t)
		_draw_div_dots(Vector2(v_x, baseline_y), div_points)
		var tab_pos := _draw_tab_indicator(size.x, baseline_y, font, font_size, merge_anim_t)
		node_positions["tab"] = tab_pos

	_draw_persistent_footer(font, 11)

	# Draw highlight pulse + annotation
	if highlight_node != "" and node_positions.has(highlight_node):
		_draw_highlight(node_positions[highlight_node], font, 12)


func _draw_gated_callout_node(
		pos: Vector2,
		text: String,
		is_unlocked: bool,
		is_ready: bool,
		ready_col: Color,
		ready_as_ring: bool,
		font: Font,
		font_size: int) -> void:
	if not is_unlocked:
		draw_arc(pos, 2.5, 0.0, TAU, 12, COL_LINE_DIM, 1.0, true)
		return

	var col_line: Color = COL_LINE_LIT if is_ready else COL_LINE_DIM
	var col_text: Color = COL_TEXT_LIT if is_ready else COL_TEXT_DIM
	var line_len: float = 18.0
	var node_r: float = 10.0 if is_ready else 8.0

	if is_ready:
		if ready_as_ring:
			draw_arc(pos, node_r, 0.0, TAU, 24, ready_col, 1.8, true)
		else:
			draw_circle(pos, node_r, ready_col)
	else:
		draw_arc(pos, node_r, 0.0, TAU, 16, col_line, 1.5, true)
	draw_line(pos + Vector2(0.0, node_r), pos + Vector2(0.0, line_len), col_line, 1.0)
	_draw_callout_label(pos, text, col_text, font, font_size, line_len)


func _draw_preview_toggle_node(pos: Vector2, is_active: bool, font: Font, font_size: int, anim_t: float = 0.0) -> void:
	var line_len: float = 18.0
	var col_line: Color = COL_LINE_LIT
	var col_text: Color = COL_TEXT_LIT
	var node_r: float = 5.0 if not is_active else 4.0
	var label_text: String = "[M] 取消預覽" if is_active else "[M] 預覽"

	if is_active:
		draw_arc(pos, node_r, 0.0, TAU, 16, col_line, 1.5, true)
	else:
		draw_circle(pos, node_r, col_line)
	draw_line(pos + Vector2(0.0, node_r), pos + Vector2(0.0, line_len), col_line, 1.0)
	var text_alpha := clampf(1.0 - anim_t / 0.30, 0.0, 1.0)
	if text_alpha > 0.01:
		col_text.a *= text_alpha
		_draw_callout_label(pos, label_text, col_text, font, font_size, line_len)


func _draw_callout_node(pos: Vector2, text: String, is_lit: bool, font: Font, font_size: int) -> void:
	var col_line: Color = COL_LINE_LIT if is_lit else COL_LINE_DIM
	var col_text: Color = COL_TEXT_LIT if is_lit else COL_TEXT_DIM
	var line_len: float = 18.0

	draw_arc(pos, 4.0, 0.0, TAU, 16, col_line, 1.5, true)
	draw_line(pos + Vector2(0.0, 4.0), pos + Vector2(0.0, line_len), col_line, 1.0)
	_draw_callout_label(pos, text, col_text, font, font_size, line_len)


func _draw_callout_label(
		pos: Vector2,
		text: String,
		col_text: Color,
		font: Font,
		font_size: int,
		line_len: float) -> void:
	var label_y: float = line_len + 16.0
	var parts: PackedStringArray = text.split(" ", false, 1)
	if parts.size() >= 2:
		var key_text: String = parts[0]
		var desc_text: String = parts[1]
		var key_w: float = font.get_string_size(key_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
		var key_pos: Vector2 = pos + Vector2(-key_w * 0.5, label_y)
		draw_string(font, key_pos, key_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, col_text)
		var gap: float = font.get_string_size(" ", HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
		var desc_pos: Vector2 = Vector2(key_pos.x + key_w + gap, key_pos.y)
		draw_string(font, desc_pos, desc_text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, col_text)
	else:
		var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
		var text_pos: Vector2 = pos + Vector2(-text_w * 0.5, label_y)
		draw_string(font, text_pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, col_text)


func _draw_div_dots(anchor_pos: Vector2, points: int) -> void:
	# Reserve the first point for the main diverge node itself.
	var count: int = maxi(0, mini(points - 1, 6))
	if count <= 0:
		return
	var start: Vector2 = anchor_pos + Vector2(18.0, 0.0)
	var gap: float = 12.0
	for i in count:
		draw_circle(start + Vector2(gap * float(i), 0.0), 5.0, COL_DIV_DOT)


func _draw_persistent_footer(font: Font, font_size: int) -> void:
	var entries: Array[String] = ["[ESC] 選擇關卡", "[F1] 說明", "[R] 重置", "[Z] 退回"]
	var x_fracs: Array[float] = [0.15, 0.38, 0.62, 0.85]
	var r := 2.5
	var y_node := 12.0
	draw_line(
		Vector2(60.0, y_node + 12.0),
		Vector2(size.x - 60.0, y_node + 12.0),
		Color(1.0, 1.0, 1.0, 0.06), 1.0)
	for i in entries.size():
		var text: String = entries[i]
		var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
		var total_w: float = r * 2.0 + 6.0 + text_w
		var gx: float = size.x * x_fracs[i] - total_w * 0.5
		draw_arc(Vector2(gx + r, y_node), r, 0.0, TAU, 12, COL_LINE_DIM, 1.0, true)
		draw_string(font, Vector2(gx + r * 2.0 + 6.0, y_node + float(font_size) * 0.38),
			text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, COL_TEXT_DIM)


func _draw_tab_indicator(screen_w: float, y_pos: float, font: Font, font_size: int, anim_t: float = 0.0) -> Vector2:
	# Direction cue: left only when DIV1 is centered, otherwise right.
	var show_left: bool = active_branch == 1
	var tab_x: float = screen_w * 0.22 if show_left else screen_w * 0.78
	var text: String = "< [TAB]" if show_left else "[TAB] >"
	var pos: Vector2 = Vector2(tab_x, y_pos)
	var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
	var text_pos: Vector2 = pos + Vector2(12.0, 34.0) if show_left else pos + Vector2(-text_w - 12.0, 34.0)
	var line_col: Color = COL_LINE_DIM
	var text_col: Color = COL_TEXT_LIT

	# Keep one node at mini-panel center; track animated panel position during merge.
	var elbow_base: float = float(PresentationModel.RIGHT_X + PresentationModel.SIDE_GRID / 2)
	if show_left:
		elbow_base = float(PresentationModel.LEFT_X + PresentationModel.SIDE_GRID / 2)
	var elbow_target: float = float(PresentationModel.CENTER_X + PresentationModel.SIDE_GRID / 2)
	var elbow_x: float = lerpf(elbow_base, elbow_target, anim_t)
	var center_target_x: float = screen_w * 0.5 - 200.0 if show_left else screen_w * 0.5 + 200.0

	# Merge animation:
	#   Phase 1 (0→0.45): text fades + elbow shortens (synchronized)
	#   Phase 2 (0.45→1.0): panel (elbow_x) moves; horizontal collapses from elbow_base → center_target_x
	var phase1_frac := clampf(1.0 - anim_t / 0.45, 0.0, 1.0)
	var text_alpha  := phase1_frac
	var elbow_h     := 24.0 * phase1_frac
	var phase2_t    := clampf((anim_t - 0.45) / 0.55, 0.0, 1.0)
	elbow_x = lerpf(elbow_base, elbow_target, phase2_t)
	var h_moving    := lerpf(elbow_base, center_target_x, phase2_t)

	var node_pos: Vector2 = Vector2(elbow_x, y_pos - elbow_h)
	draw_line(Vector2(minf(center_target_x, h_moving), y_pos), Vector2(maxf(center_target_x, h_moving), y_pos), line_col, 1.0)
	if elbow_h > 0.5:
		draw_line(Vector2(elbow_x, y_pos), node_pos, line_col, 1.0)
		draw_arc(node_pos, 3.0, 0.0, TAU, 12, line_col, 1.0, true)

	if text_alpha > 0.01:
		draw_string(font, text_pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size,
			Color(text_col.r, text_col.g, text_col.b, text_col.a * text_alpha))
	_tab_text_rect = Rect2(text_pos.x - 3.0, text_pos.y - font_size - 1.0, text_w + 6.0, font_size + 4.0)
	return node_pos


func _draw_highlight(pos: Vector2, font: Font, font_size: int) -> void:
	var blink: float = 0.5 + 0.5 * sin(_pulse_time * 4.0)

	if highlight_node == "tab" and _tab_text_rect.size != Vector2.ZERO:
		# Box highlight around the "[TAB]" text label
		var rect_col := Color(1.0, 1.0, 0.6, 0.40 + 0.45 * blink)
		draw_rect(_tab_text_rect, Color(1.0, 1.0, 0.6, 0.06 + 0.06 * blink))
		draw_rect(_tab_text_rect, rect_col, false, 1.5)
		return

	# Default: ring around node
	var ring_r: float = 16.0
	var ring_col := Color(1.0, 1.0, 0.6, 0.35 + 0.45 * blink)
	draw_arc(pos, ring_r, 0.0, TAU, 32, ring_col, 2.0, true)

	# Annotation box on the LEFT side of the node.
	if highlight_annotations.is_empty():
		return
	var line_h: float = float(font_size) + 4.0
	var pad_x: float = 8.0
	var pad_y: float = 4.0
	var gap: float = 8.0  # gap between ring and box

	# Measure max text width
	var max_w: float = 0.0
	for ann in highlight_annotations:
		var w: float = font.get_string_size(str(ann), HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
		if w > max_w:
			max_w = w

	var box_w: float = max_w + pad_x * 2.0
	var box_h: float = line_h * highlight_annotations.size() + pad_y * 2.0
	var box_x: float = pos.x - ring_r - gap - box_w
	var box_y: float = pos.y - box_h * 0.5

	# Background
	var bg_col := Color(0.08, 0.08, 0.08, 0.9)
	draw_rect(Rect2(box_x, box_y, box_w, box_h), bg_col)
	# Border
	var border_col := Color(1.0, 1.0, 0.6, 0.45 + 0.35 * blink)
	draw_rect(Rect2(box_x, box_y, box_w, box_h), border_col, false, 1.0)

	# Text lines
	for i in highlight_annotations.size():
		var text: String = str(highlight_annotations[i])
		var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
		var tx: float = box_x + (box_w - text_w) * 0.5
		var ty: float = box_y + pad_y + line_h * (i + 1) - 2.0
		draw_string(font, Vector2(tx, ty), text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, Color(1.0, 1.0, 0.85, 0.95))
