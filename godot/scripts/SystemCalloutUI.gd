extends Control
class_name SystemCalloutUI

const COL_LINE_DIM   := Color(1.0, 1.0, 1.0, 0.25)
const COL_LINE_LIT   := Color(1.0, 1.0, 1.0, 0.95)
const COL_TEXT_DIM   := Color(0.6, 0.6, 0.6, 1.0)
const COL_TEXT_LIT   := Color(0.95, 0.95, 0.95, 1.0)
const COL_TAB_ACCENT := Color(0.3, 0.6, 1.0, 1.0)
const COL_STATUS     := Color(0.4, 0.8, 0.9, 0.8)
const COL_DIV_DOT    := Color(0.36, 0.92, 0.48, 0.95)

var is_diverged: bool = false
var active_branch: int = 0
var div_points: int = 0
var can_v_merge: bool = false
var can_f_fetch: bool = false


func update_state(diverged: bool, focus: int, pts: int, v_merge: bool, f_fetch: bool) -> void:
	is_diverged = diverged
	active_branch = focus
	div_points = pts
	can_v_merge = v_merge
	can_f_fetch = f_fetch
	queue_redraw()


func _draw() -> void:
	var font: Font = ThemeDB.fallback_font
	if font == null:
		return

	var font_size: int = 14
	var center_x: float = size.x * 0.5
	var baseline_y: float = size.y - 70.0

	if not is_diverged:
		var line_w: float = 200.0
		var left_end: float = center_x - line_w
		var right_end: float = center_x + line_w

		draw_line(Vector2(left_end, baseline_y), Vector2(right_end, baseline_y), COL_LINE_DIM, 1.0)
		_draw_callout_node(Vector2(center_x, baseline_y), "[V] DIVERGE", div_points > 0, font, font_size)
		_draw_div_dots(Vector2(center_x, baseline_y), div_points)
	else:
		var line_w: float = size.x * 0.12
		var left_end: float = center_x - line_w - 40.0
		var right_end: float = center_x + line_w + 40.0

		var f_x: float = center_x - line_w
		var v_x: float = center_x
		var m_x: float = center_x + line_w

		draw_line(Vector2(left_end, baseline_y), Vector2(right_end, baseline_y), COL_LINE_DIM, 1.0)
		_draw_callout_node(Vector2(f_x, baseline_y), "[F] FETCH MERGE", can_f_fetch, font, font_size)
		_draw_callout_node(Vector2(v_x, baseline_y), "[V] MERGE", can_v_merge, font, font_size)
		_draw_callout_node(Vector2(m_x, baseline_y), "[M] PREVIEW", true, font, font_size)
		_draw_div_dots(Vector2(v_x, baseline_y), div_points)
		_draw_tab_indicator(size.x, baseline_y - 65.0, font, font_size)


func _draw_callout_node(pos: Vector2, text: String, is_lit: bool, font: Font, font_size: int) -> void:
	var col_line: Color = COL_LINE_LIT if is_lit else COL_LINE_DIM
	var col_text: Color = COL_TEXT_LIT if is_lit else COL_TEXT_DIM
	var line_len: float = 18.0

	draw_arc(pos, 4.0, 0.0, TAU, 16, col_line, 1.5, true)
	draw_line(pos + Vector2(0.0, 4.0), pos + Vector2(0.0, line_len), col_line, 1.0)

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
	var count: int = maxi(0, mini(points, 6))
	if count <= 0:
		return
	var start: Vector2 = anchor_pos + Vector2(18.0, 0.0)
	var gap: float = 12.0
	for i in count:
		_draw_diamond(start + Vector2(gap * float(i), 0.0), 7.0, COL_DIV_DOT)


func _draw_diamond(center: Vector2, size: float, col: Color) -> void:
	var h: float = size * 0.5
	var pts := PackedVector2Array([
		center + Vector2(0.0, -h),
		center + Vector2(h, 0.0),
		center + Vector2(0.0, h),
		center + Vector2(-h, 0.0),
	])
	draw_colored_polygon(pts, col)


func _draw_tab_indicator(screen_w: float, y_pos: float, font: Font, font_size: int) -> void:
	# Direction cue: left only when DIV1 is centered, otherwise right.
	var show_left: bool = active_branch == 1
	var tab_x: float = screen_w * 0.22 if show_left else screen_w * 0.78
	var text: String = "< [TAB]" if show_left else "[TAB] >"
	var pos: Vector2 = Vector2(tab_x, y_pos)

	var elbow_x: float = tab_x - 24.0 if show_left else tab_x + 24.0
	var node_pos: Vector2 = Vector2(elbow_x, y_pos - 24.0)

	draw_line(pos, Vector2(elbow_x, y_pos), COL_TAB_ACCENT, 1.0)
	draw_line(Vector2(elbow_x, y_pos), node_pos, COL_TAB_ACCENT, 1.0)
	draw_arc(node_pos, 3.0, 0.0, TAU, 12, COL_TAB_ACCENT, 1.0, true)

	var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
	var text_pos: Vector2 = pos + Vector2(12.0, 4.0) if show_left else pos + Vector2(-text_w - 12.0, 4.0)
	draw_string(font, text_pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, COL_TAB_ACCENT)
