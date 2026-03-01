# SymbolSpotlightUI.gd - Blocking spotlight that locks onto a game-world symbol.
# Draws a diamond lock frame at the symbol's screen position.
# Description text appears in a box outside the map, connected by a line.
class_name SymbolSpotlightUI
extends Control

signal finished

const COL_FRAME  := Color(1.00, 1.00, 0.55, 0.95)
const COL_DIM    := Color(1.00, 1.00, 0.55, 0.28)
const COL_LINE   := Color(1.00, 1.00, 0.55, 0.50)
const COL_PANEL  := Color(0.05, 0.05, 0.07, 0.93)
const COL_BORDER := Color(1.00, 1.00, 0.55, 0.30)
const COL_TITLE  := Color(0.95, 0.95, 0.95, 1.00)
const COL_TEXT   := Color(0.72, 0.72, 0.72, 1.00)
const COL_PROMPT := Color(0.50, 0.50, 0.50, 1.00)

# Each item: { "screen_center": Vector2, "cell_size": float, "title": String, "lines": Array }
var _items: Array = []
var _index: int   = 0
var _time:  float = 0.0


func show_sequence(items: Array) -> void:
	_items = items
	_index = 0
	visible = true
	set_process(true)
	queue_redraw()


func _process(delta: float) -> void:
	if visible:
		_time += delta
		queue_redraw()


func _input(event: InputEvent) -> void:
	if not visible:
		return
	if event is InputEventKey and event.pressed and not event.echo:
		accept_event()
		_index += 1
		if _index >= _items.size():
			visible = false
			set_process(false)
			finished.emit()
		else:
			queue_redraw()


func _draw() -> void:
	if _index >= _items.size():
		return
	var item: Dictionary = _items[_index]
	var center: Vector2 = item.get("screen_center", Vector2.ZERO)
	var cell_size: float = item.get("cell_size", 60.0)
	var title: String   = item.get("title", "")
	var lines: Array    = item.get("lines", [])
	var is_last: bool   = _index >= _items.size() - 1

	var font: Font = ThemeDB.fallback_font
	if font == null:
		return

	var pulse := 0.5 + 0.5 * sin(_time * 3.0)
	var sw    := size.x

	# Lock frame
	var r := cell_size * 0.60
	_draw_lock_frame(center, r, pulse)

	# Text box layout
	var title_fs: int  = 16
	var text_fs:  int  = 13
	var line_h:   float = text_fs + 6.0
	var pad:      float = 14.0

	var max_w: float = font.get_string_size(title, HORIZONTAL_ALIGNMENT_LEFT, -1.0, title_fs).x
	for line in lines:
		var lw := font.get_string_size(str(line), HORIZONTAL_ALIGNMENT_LEFT, -1.0, text_fs).x
		if lw > max_w:
			max_w = lw

	var box_w  := max_w + pad * 2.0
	var box_h  := pad + title_fs + pad * 0.5 + lines.size() * line_h + pad
	var gap    := r + 28.0
	var go_right := center.x + gap + box_w <= sw - 20.0
	var box_x  := center.x + gap if go_right else center.x - gap - box_w
	var box_y  := clampf(center.y - box_h * 0.5, 10.0, size.y - box_h - 10.0)

	# Connection line
	var h_sign := 1.0 if go_right else -1.0
	var frame_pt := center + Vector2(h_sign * (r + 4.0), 0.0)
	var box_pt   := Vector2(box_x if go_right else box_x + box_w, box_y + box_h * 0.5)
	draw_line(frame_pt, box_pt, Color(COL_LINE.r, COL_LINE.g, COL_LINE.b, 0.4 + 0.25 * pulse), 1.0)

	# Text box
	draw_rect(Rect2(box_x, box_y, box_w, box_h), COL_PANEL)
	draw_rect(Rect2(box_x, box_y, box_w, box_h),
		Color(COL_BORDER.r, COL_BORDER.g, COL_BORDER.b, 0.22 + 0.20 * pulse), false, 1.0)

	# Title
	var title_y := box_y + pad + title_fs * 0.85
	draw_string(font, Vector2(box_x + pad, title_y),
		title, HORIZONTAL_ALIGNMENT_LEFT, -1.0, title_fs, COL_TITLE)

	# Separator
	var sep_y := title_y + 7.0
	draw_line(Vector2(box_x + pad * 0.5, sep_y), Vector2(box_x + box_w - pad * 0.5, sep_y),
		Color(0.4, 0.4, 0.4, 0.55), 1.0)

	# Description lines
	for i in lines.size():
		draw_string(font, Vector2(box_x + pad, sep_y + 5.0 + (i + 1) * line_h),
			str(lines[i]), HORIZONTAL_ALIGNMENT_LEFT, -1.0, text_fs, COL_TEXT)

	# Prompt below box
	var prompt    := "按任意鍵開始" if is_last else "按任意鍵繼續"
	var prompt_fs := 11
	var blink     := 0.38 + 0.50 * sin(_time * 3.5)
	var prompt_w  := font.get_string_size(prompt, HORIZONTAL_ALIGNMENT_LEFT, -1.0, prompt_fs).x
	draw_string(font,
		Vector2(box_x + (box_w - prompt_w) * 0.5, box_y + box_h + 16.0 + prompt_fs),
		prompt, HORIZONTAL_ALIGNMENT_LEFT, -1.0, prompt_fs,
		Color(COL_PROMPT.r, COL_PROMPT.g, COL_PROMPT.b, blink))


func _draw_lock_frame(center: Vector2, r: float, pulse: float) -> void:
	var top    := Vector2(center.x,     center.y - r)
	var right  := Vector2(center.x + r, center.y    )
	var bottom := Vector2(center.x,     center.y + r)
	var left   := Vector2(center.x - r, center.y    )

	# Dim full diamond outline
	draw_polyline(PackedVector2Array([top, right, bottom, left, top]),
		Color(COL_DIM.r, COL_DIM.g, COL_DIM.b, 0.20 + 0.12 * pulse), 1.0)

	# Bright corner ticks
	var tick := r * 0.28
	var col  := Color(COL_FRAME.r, COL_FRAME.g, COL_FRAME.b, 0.72 + 0.22 * pulse)
	var w    := 2.0

	draw_line(top,    top    + (right  - top   ).normalized() * tick, col, w)
	draw_line(top,    top    + (left   - top   ).normalized() * tick, col, w)
	draw_line(right,  right  + (top    - right ).normalized() * tick, col, w)
	draw_line(right,  right  + (bottom - right ).normalized() * tick, col, w)
	draw_line(bottom, bottom + (right  - bottom).normalized() * tick, col, w)
	draw_line(bottom, bottom + (left   - bottom).normalized() * tick, col, w)
	draw_line(left,   left   + (top    - left  ).normalized() * tick, col, w)
	draw_line(left,   left   + (bottom - left  ).normalized() * tick, col, w)

