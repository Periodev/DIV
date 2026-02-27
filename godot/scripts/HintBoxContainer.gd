extends Control
class_name HintBoxContainer

const HintLayoutBuilder := preload("res://scripts/HintLayoutBuilder.gd")

const BOX_IDS: Array[String] = [
	"tab_left",
	"tab_right",
	"diverge",
	"preview",
	"merge",
	"fetch",
]

var _items: Dictionary = {}


func _ready() -> void:
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	visible = false
	for id in BOX_IDS:
		_items[id] = _create_box_item(id)


func update_hints(spec: PresentationModel.BranchViewSpec, panel_pos: Vector2) -> void:
	visible = spec != null and spec.is_focused
	if not visible:
		return

	modulate = Color(1, 1, 1, spec.alpha)
	_reset_all_hidden()

	var boxes = HintLayoutBuilder.build(spec, get_viewport_rect().size)
	for raw_box in boxes:
		var box = raw_box as HintLayoutBuilder.HintBoxSpec
		if box == null or not box.visible:
			continue
		if not _items.has(box.id):
			continue
		var item: Dictionary = _items[box.id]
		var panel: PanelContainer = item.panel as PanelContainer
		var label: Label = item.label as Label
		var arrow: Label = item.arrow as Label
		if panel == null or label == null or arrow == null:
			continue

		panel.visible = true
		panel.position = box.rect.position - panel_pos
		panel.size = box.rect.size
		_apply_panel_style(panel, box.bg_color, box.border_color)

		var local_text_center: Vector2 = box.text_center - box.rect.position
		label.text = box.text
		label.position = Vector2(
			round(local_text_center.x - box.rect.size.x * 0.5),
			round(local_text_center.y - box.rect.size.y * 0.5)
		)
		label.size = box.rect.size
		label.add_theme_font_size_override("font_size", box.font_size)
		label.add_theme_color_override("font_color", box.text_color)

		if box.has_arrow:
			var local_arrow: Vector2 = box.arrow_pos - box.rect.position
			arrow.visible = true
			arrow.text = "<" if box.arrow_dx < 0 else ">"
			arrow.position = Vector2(round(local_arrow.x - 10.0), round(local_arrow.y - 10.0))
			arrow.size = Vector2(20, 20)
			arrow.add_theme_font_size_override("font_size", box.font_size)
			arrow.add_theme_color_override("font_color", box.text_color)
		else:
			arrow.visible = false


func _create_box_item(id: String) -> Dictionary:
	var panel := PanelContainer.new()
	panel.name = id
	panel.visible = false
	panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	panel.clip_contents = true

	var label := Label.new()
	label.name = "Text"
	label.mouse_filter = Control.MOUSE_FILTER_IGNORE
	label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	label.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	panel.add_child(label)

	var arrow := Label.new()
	arrow.name = "Arrow"
	arrow.visible = false
	arrow.mouse_filter = Control.MOUSE_FILTER_IGNORE
	arrow.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	arrow.vertical_alignment = VERTICAL_ALIGNMENT_CENTER
	panel.add_child(arrow)

	add_child(panel)
	return {"panel": panel, "label": label, "arrow": arrow}


func _apply_panel_style(panel: PanelContainer, bg: Color, border: Color) -> void:
	var style := StyleBoxFlat.new()
	style.bg_color = Color(bg.r, bg.g, bg.b, 0.8)
	style.border_color = Color(border.r, border.g, border.b, 1.0)
	style.set_border_width_all(2)
	panel.add_theme_stylebox_override("panel", style)


func _reset_all_hidden() -> void:
	for raw in _items.values():
		var item: Dictionary = raw as Dictionary
		var panel: PanelContainer = item.panel as PanelContainer
		if panel != null:
			panel.visible = false
