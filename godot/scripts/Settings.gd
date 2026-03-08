# Settings.gd - Language toggle + key bindings reference
extends Control

const BG_C     := Color8(20, 20, 25)
const TEXT_C   := Color8(220, 220, 220)
const MUTED_C  := Color8(120, 120, 130)
const TITLE_C  := Color8(96, 165, 250)
const SEL_BG_C := Color8(40, 80, 120)
const SEL_C    := Color8(96, 165, 250)
const DIV_C    := Color8(50, 55, 65)

const LABELS := {
	"zh": {
		"language": "語言",
		"controls": "按鍵說明",
		"back": "← 返回",
		"hint": "←/→ 切換語言　Enter/Esc 返回",
		"keys": [
			["移動", "←↑↓→ / WASD"],
			["互動", "X / Space"],
			["分裂", "V"],
			["合併", "V（已分裂時）"],
			["切換視角", "Tab"],
			["預覽", "M"],
			["說明", "F1"],
			["重置", "R"],
			["復原", "Z"],
			["選單", "Esc"],
		],
	},
	"en": {
		"language": "Language",
		"controls": "Controls",
		"back": "← Back",
		"hint": "←/→ language   Enter/Esc back",
		"keys": [
			["Move", "←↑↓→ / WASD"],
			["Interact", "X / Space"],
			["Diverge", "V"],
			["Merge", "V (when diverged)"],
			["Switch View", "Tab"],
			["Preview", "M"],
			["Info", "F1"],
			["Restart", "R"],
			["Undo", "Z"],
			["Menu", "Esc"],
		],
	},
}

var selected_lang: String = "en"


func _ready() -> void:
	set_process_unhandled_key_input(true)
	var gd = _get_game_data()
	if gd != null:
		selected_lang = gd.language
	queue_redraw()


func _unhandled_key_input(event: InputEvent) -> void:
	if not (event is InputEventKey):
		return
	var ke: InputEventKey = event as InputEventKey
	if not ke.pressed or ke.echo:
		return
	match ke.keycode:
		KEY_LEFT, KEY_A:
			selected_lang = "zh"
			queue_redraw()
		KEY_RIGHT, KEY_D:
			selected_lang = "en"
			queue_redraw()
		KEY_ENTER, KEY_KP_ENTER, KEY_ESCAPE:
			_confirm_and_back()


func _confirm_and_back() -> void:
	var gd = _get_game_data()
	if gd != null:
		gd.language = selected_lang
		gd.save_settings()
	get_tree().change_scene_to_file("res://scenes/level_select.tscn")


func _draw() -> void:
	var w: float = size.x
	var h: float = size.y
	draw_rect(Rect2(0, 0, w, h), BG_C)

	var lang := LABELS.get(selected_lang, LABELS["en"]) as Dictionary
	var cx := w * 0.5

	# Title
	_draw_td("DIV", cx, 30.0, TITLE_C, 27, HORIZONTAL_ALIGNMENT_CENTER, true)

	var cy := 75.0

	# ── Language ──
	var lang_hdr := str(lang.get("language", "Language"))
	_draw_td(lang_hdr, cx, cy, MUTED_C, 15, HORIZONTAL_ALIGNMENT_CENTER, true)
	cy += 34.0

	var btn_w := 64.0
	var btn_h := 28.0
	var gap   := 14.0
	var zh_x  := cx - gap * 0.5 - btn_w
	var en_x  := cx + gap * 0.5
	var btn_y := cy - btn_h * 0.5

	_draw_lang_btn("ZH", zh_x, btn_y, btn_w, btn_h, selected_lang == "zh")
	_draw_lang_btn("EN", en_x, btn_y, btn_w, btn_h, selected_lang == "en")
	cy += 30.0

	# Divider
	draw_line(Vector2(cx - 220, cy), Vector2(cx + 220, cy), DIV_C, 1.0)
	cy += 22.0

	# ── Controls ──
	var ctrl_hdr := str(lang.get("controls", "Controls"))
	_draw_td(ctrl_hdr, cx, cy, MUTED_C, 15, HORIZONTAL_ALIGNMENT_CENTER, true)
	cy += 28.0

	var label_rx := cx - 14.0
	var key_lx   := cx + 14.0
	var row_h    := 27.0
	var keys: Array = lang.get("keys", []) as Array
	for pair in keys:
		var arr := pair as Array
		if arr.size() < 2:
			continue
		_draw_td(str(arr[0]), label_rx, cy, TEXT_C, 16, HORIZONTAL_ALIGNMENT_RIGHT, true)
		_draw_td(str(arr[1]), key_lx,   cy, MUTED_C, 16, HORIZONTAL_ALIGNMENT_LEFT,  true)
		cy += row_h

	cy += 6.0
	draw_line(Vector2(cx - 220, cy), Vector2(cx + 220, cy), DIV_C, 1.0)
	cy += 26.0

	# Back / hint
	_draw_td(str(lang.get("back", "← Back")), cx, cy, MUTED_C, 16, HORIZONTAL_ALIGNMENT_CENTER, true)
	cy += 26.0
	_draw_td(str(lang.get("hint", "")), cx, h - 22.0, MUTED_C, 14, HORIZONTAL_ALIGNMENT_CENTER, true)


func _draw_lang_btn(label: String, bx: float, by: float, bw: float, bh: float, active: bool) -> void:
	if active:
		draw_rect(Rect2(bx, by, bw, bh), SEL_BG_C)
	draw_rect(Rect2(bx, by, bw, bh), SEL_C if active else MUTED_C, false, 1.0)
	_draw_td(label, bx + bw * 0.5, by + bh * 0.5, SEL_C if active else MUTED_C, 15, HORIZONTAL_ALIGNMENT_CENTER, true)


func _draw_td(
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


func _get_game_data():
	return get_node_or_null("/root/GameData")
