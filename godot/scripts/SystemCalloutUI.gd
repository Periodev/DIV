extends Control
class_name SystemCalloutUI

const COL_LINE_DIM   := Color(1.0, 1.0, 1.0, 0.25)
const COL_LINE_LIT   := Color(1.0, 1.0, 1.0, 0.95)
const COL_TEXT_DIM   := Color(0.6, 0.6, 0.6, 1.0)
const COL_TEXT_LIT   := Color(0.95, 0.95, 0.95, 1.0)
const COL_TAB_ACCENT := Color(0.3, 0.6, 1.0, 1.0)

var is_diverged: bool = false
var active_branch: int = 0
var div_points: int = 0
var can_v_merge: bool = false
var can_f_fetch: bool = false


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE


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
	var baseline_y: float = size.y - 45.0

	if not is_diverged:
		var left_x := center_x - 140.0
		var right_x := center_x + 140.0
		draw_line(Vector2(left_x - 30.0, baseline_y), Vector2(right_x + 30.0, baseline_y), COL_LINE_DIM, 1.0)
		_draw_callout_node(Vector2(left_x, baseline_y), "[V] DIVERGE", div_points > 0, font, font_size)
		_draw_callout_node(Vector2(right_x, baseline_y), "DIV PTS: " + str(div_points), div_points > 0, font, font_size)
	else:
		var f_x := center_x - (size.x * 0.12)
		var v_x := center_x
		var m_x := center_x + (size.x * 0.12)
		draw_line(Vector2(f_x - 40.0, baseline_y), Vector2(m_x + 40.0, baseline_y), COL_LINE_DIM, 1.0)
		_draw_callout_node(Vector2(f_x, baseline_y), "[F] FETCH MERGE", can_f_fetch, font, font_size)
		_draw_callout_node(Vector2(v_x, baseline_y), "[V] MERGE", can_v_merge, font, font_size)
		_draw_callout_node(Vector2(m_x, baseline_y), "[M] PREVIEW MERGE", true, font, font_size)
		_draw_tab_indicator(size.x, baseline_y - 65.0, font, font_size)


func _draw_callout_node(pos: Vector2, text: String, is_lit: bool, font: Font, font_size: int) -> void:
	var col_line: Color = COL_LINE_LIT if is_lit else COL_LINE_DIM
	var col_text: Color = COL_TEXT_LIT if is_lit else COL_TEXT_DIM
	var line_len := 18.0
	draw_arc(pos, 4.0, 0.0, TAU, 16, col_line, 1.5, true)
	draw_line(pos + Vector2(0.0, 4.0), pos + Vector2(0.0, line_len), col_line, 1.0)
	var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
	var text_pos := pos + Vector2(-text_w * 0.5, line_len + 16.0)
	draw_string(font, text_pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, col_text)


func _draw_tab_indicator(screen_w: float, y_pos: float, font: Font, font_size: int) -> void:
	# Direction cue: show LEFT when DIV1 is centered, RIGHT when DIV0/main is centered.
	var show_left: bool = active_branch == 1
	var tab_x: float = screen_w * 0.22 if show_left else screen_w * 0.78
	var text: String = "< [TAB]" if show_left else "[TAB] >"
	var pos := Vector2(tab_x, y_pos)
	var elbow_x: float = tab_x - 24.0 if show_left else tab_x + 24.0
	var node_pos := Vector2(elbow_x, y_pos - 24.0)

	draw_line(pos, Vector2(elbow_x, y_pos), COL_TAB_ACCENT, 1.0)
	draw_line(Vector2(elbow_x, y_pos), node_pos, COL_TAB_ACCENT, 1.0)
	draw_arc(node_pos, 3.0, 0.0, TAU, 12, COL_TAB_ACCENT, 1.0, true)

	var text_w: float = font.get_string_size(text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size).x
	var text_pos := pos + Vector2(12.0, 4.0) if show_left else pos + Vector2(-text_w - 12.0, 4.0)
	draw_string(font, text_pos, text, HORIZONTAL_ALIGNMENT_LEFT, -1.0, font_size, COL_TAB_ACCENT)
