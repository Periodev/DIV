extends Control
class_name LevelDescOverlay

signal dismissed

# Colors matching the game's visual palette.
const COLOR_BACKDROP   := Color(0.0,  0.0,  0.0,  0.78)
const COLOR_PANEL_BG   := Color(0.08, 0.09, 0.12, 0.97)
const COLOR_PANEL_BD   := Color(0.50, 0.55, 0.65, 1.0)
const COLOR_TITLE      := Color8(255, 200,  60)   # amber — same family as goal glow
const COLOR_BODY       := Color8(210, 210, 210)
const COLOR_FOOTER     := Color8( 90, 130, 160)
const COLOR_SEP        := Color(0.35, 0.38, 0.45, 1.0)

const PANEL_W          := 520
const TITLE_SIZE       := 22
const BODY_SIZE        := 16
const FOOTER_SIZE      := 13


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	_build_ui()
	visible = false


func show_desc(level_name: String, objective: String) -> void:
	($Backdrop as ColorRect).color = COLOR_BACKDROP
	($Center/Panel/VBox/Title as Label).text = level_name
	var body_text := objective.strip_edges()
	($Center/Panel/VBox/Body as Label).text = body_text
	($Center/Panel/VBox/Footer as Label).text = Localization.t("desc_close")
	visible = true


func hide_desc() -> void:
	visible = false
	dismissed.emit()


# ---------------------------------------------------------------------------
# Private
# ---------------------------------------------------------------------------

func _build_ui() -> void:
	# Full-screen backdrop
	var backdrop := ColorRect.new()
	backdrop.name = "Backdrop"
	backdrop.mouse_filter = Control.MOUSE_FILTER_IGNORE
	backdrop.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(backdrop)

	# CenterContainer so the panel is always screen-centered
	var center := CenterContainer.new()
	center.name = "Center"
	center.mouse_filter = Control.MOUSE_FILTER_IGNORE
	center.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	add_child(center)

	# Panel
	var panel := PanelContainer.new()
	panel.name = "Panel"
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.custom_minimum_size = Vector2(PANEL_W, 0)
	var style := StyleBoxFlat.new()
	style.bg_color = COLOR_PANEL_BG
	style.border_color = COLOR_PANEL_BD
	style.set_border_width_all(2)
	style.corner_radius_top_left    = 6
	style.corner_radius_top_right   = 6
	style.corner_radius_bottom_left = 6
	style.corner_radius_bottom_right = 6
	style.content_margin_left   = 36
	style.content_margin_right  = 36
	style.content_margin_top    = 28
	style.content_margin_bottom = 28
	panel.add_theme_stylebox_override("panel", style)
	center.add_child(panel)

	# VBox inside panel
	var vbox := VBoxContainer.new()
	vbox.name = "VBox"
	vbox.add_theme_constant_override("separation", 14)
	panel.add_child(vbox)

	# Title
	var title := Label.new()
	title.name = "Title"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", TITLE_SIZE)
	title.add_theme_color_override("font_color", COLOR_TITLE)
	vbox.add_child(title)

	# Separator
	var sep := ColorRect.new()
	sep.name = "Sep"
	sep.color = COLOR_SEP
	sep.custom_minimum_size = Vector2(0, 1)
	vbox.add_child(sep)

	# Body
	var body := Label.new()
	body.name = "Body"
	body.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	body.add_theme_font_size_override("font_size", BODY_SIZE)
	body.add_theme_color_override("font_color", COLOR_BODY)
	vbox.add_child(body)

	# Footer
	var footer := Label.new()
	footer.name = "Footer"
	footer.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	footer.add_theme_font_size_override("font_size", FOOTER_SIZE)
	footer.add_theme_color_override("font_color", COLOR_FOOTER)
	footer.text = Localization.t("desc_close")
	vbox.add_child(footer)
