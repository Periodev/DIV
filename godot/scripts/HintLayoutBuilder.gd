extends RefCounted
class_name HintLayoutBuilder


class HintBoxSpec:
	extends RefCounted
	var id: String = ""
	var visible: bool = true
	var text: String = ""
	var rect: Rect2 = Rect2()
	var text_center: Vector2 = Vector2.ZERO
	var bg_color: Color = Color.WHITE
	var border_color: Color = Color.WHITE
	var text_color: Color = Color.WHITE
	var font_size: int = 14
	var has_arrow: bool = false
	var arrow_dx: int = 0
	var arrow_dy: int = 0
	var arrow_pos: Vector2 = Vector2.ZERO
	var arrow_size: int = 11


const COLOR_HINT_DARK := Color8(60, 60, 60)
const COLOR_HINT_GRAY_B := Color8(120, 120, 120)
const COLOR_HINT_TEXT_G := Color8(180, 180, 180)
const COLOR_HINT_GREEN := Color8(50, 150, 50)
const COLOR_HINT_GREEN_B := Color8(100, 255, 100)
const COLOR_HINT_M_BG := Color8(110, 50, 110)
const COLOR_HINT_M_BD := Color8(110, 50, 200)
const COLOR_HINT_V_BG := Color8(40, 80, 120)
const COLOR_HINT_V_BD := Color8(75, 150, 200)
const COLOR_HINT_F_BD := Color8(100, 100, 100)
const COLOR_HINT_F_ON_BG := Color8(255, 140, 0)
const COLOR_HINT_F_ON_BD := Color8(255, 180, 0)

const TAB_ACTIVE_BG := Color8(20, 20, 200)
const TAB_ACTIVE_BD := Color8(0, 0, 255)
const TAB_ACTIVE_TX := Color8(255, 255, 255)
const TAB_INACTIVE_BG := Color8(80, 80, 80)
const TAB_INACTIVE_BD := Color8(120, 120, 120)
const TAB_INACTIVE_TX := Color8(160, 160, 160)


static func build(
		spec: PresentationModel.BranchViewSpec,
		viewport_size: Vector2) -> Array[HintBoxSpec]:
	var boxes: Array[HintBoxSpec] = []
	if spec == null:
		return boxes

	if not spec.has_branched:
		if spec.timeline_hint != "":
			boxes.append(_build_timeline_box(spec.branch_hint_active, viewport_size))
		return boxes

	boxes.append_array(_build_tab_boxes(spec))
	if spec.show_merge_preview_hint:
		boxes.append(_build_merge_preview_box(spec.is_merge_preview, viewport_size))
	if spec.show_merge_hint:
		boxes.append(_build_merge_box(spec.merge_hint_enabled, viewport_size))
	if spec.show_fetch_indicator:
		boxes.append(_build_fetch_box(spec.fetch_mode_enabled, viewport_size))
	return boxes


static func _build_tab_boxes(spec: PresentationModel.BranchViewSpec) -> Array[HintBoxSpec]:
	var out: Array[HintBoxSpec] = []
	var box_w: float = 75.0
	var box_h: float = 40.0
	var y: float = PresentationModel.CENTER_Y + PresentationModel.TARGET_PANEL - box_h
	var left_x: float = PresentationModel.CENTER_X - box_w - 10.0
	var right_x: float = PresentationModel.CENTER_X + PresentationModel.TARGET_PANEL + 10.0

	var left_rect := Rect2(left_x, y, box_w, box_h)
	var right_rect := Rect2(right_x, y, box_w, box_h)

	var focus_is_div0: bool = spec.title != "DIV 1"
	var left_active: bool = not focus_is_div0
	var right_active: bool = focus_is_div0

	out.append(_build_tab_box(left_rect, left_active, true))
	out.append(_build_tab_box(right_rect, right_active, false))
	return out


static func _build_tab_box(rect: Rect2, active: bool, is_left: bool) -> HintBoxSpec:
	var box := HintBoxSpec.new()
	box.id = "tab_left" if is_left else "tab_right"
	box.text = "Tab"
	box.rect = rect
	box.font_size = 18
	box.bg_color = TAB_ACTIVE_BG if active else TAB_INACTIVE_BG
	box.border_color = TAB_ACTIVE_BD if active else TAB_INACTIVE_BD
	box.text_color = TAB_ACTIVE_TX if active else TAB_INACTIVE_TX
	box.has_arrow = true
	box.arrow_size = 11
	box.arrow_dy = 0
	box.text_center = Vector2(
		rect.position.x + (46.0 if is_left else 28.0),
		rect.get_center().y
	)
	if is_left:
		box.arrow_dx = -1
		box.arrow_pos = Vector2(rect.position.x + 20.0, rect.get_center().y)
	else:
		box.arrow_dx = 1
		box.arrow_pos = Vector2(rect.position.x + rect.size.x - 20.0, rect.get_center().y)
	return box


static func _build_timeline_box(is_active: bool, viewport_size: Vector2) -> HintBoxSpec:
	var box_w: float = 150.0
	var box_h: float = 40.0
	var center_x: float = (viewport_size.x - box_w) * 0.5
	var y: float = (viewport_size.y + PresentationModel.TARGET_PANEL) * 0.5 + 15.0
	var rect := Rect2(center_x, y, box_w, box_h)

	var box := HintBoxSpec.new()
	box.id = "diverge"
	box.text = "V Diverge"
	box.rect = rect
	box.text_center = rect.get_center()
	box.font_size = 16
	box.bg_color = COLOR_HINT_GREEN if is_active else COLOR_HINT_DARK
	box.border_color = COLOR_HINT_GREEN_B if is_active else COLOR_HINT_GRAY_B
	box.text_color = Color8(60, 30, 0) if is_active else COLOR_HINT_TEXT_G
	return box


static func _build_merge_preview_box(is_active: bool, viewport_size: Vector2) -> HintBoxSpec:
	var box_w: float = 130.0
	var box_h: float = 40.0
	var center_x: float = (viewport_size.x - PresentationModel.TARGET_PANEL) * 0.5
	var center_y: float = (viewport_size.y - PresentationModel.TARGET_PANEL) * 0.5
	var x: float = center_x + PresentationModel.TARGET_PANEL - box_w
	var y: float = center_y + PresentationModel.TARGET_PANEL + 15.0
	var rect := Rect2(x, y, box_w, box_h)

	var box := HintBoxSpec.new()
	box.id = "preview"
	box.text = "M Cancel Preview" if is_active else "M Preview Merge"
	box.rect = rect
	box.text_center = rect.get_center()
	box.font_size = 14
	box.bg_color = COLOR_HINT_M_BG
	box.border_color = COLOR_HINT_M_BD
	box.text_color = Color.WHITE
	return box


static func _build_merge_box(enabled: bool, viewport_size: Vector2) -> HintBoxSpec:
	var box_w: float = 150.0
	var box_h: float = 40.0
	var x: float = (viewport_size.x - box_w) * 0.5
	var y: float = (viewport_size.y + PresentationModel.TARGET_PANEL) * 0.5 + 15.0
	var rect := Rect2(x, y, box_w, box_h)

	var box := HintBoxSpec.new()
	box.id = "merge"
	box.text = "V Merge"
	box.rect = rect
	box.text_center = rect.get_center()
	box.font_size = 16
	box.bg_color = COLOR_HINT_V_BG if enabled else COLOR_HINT_DARK
	box.border_color = COLOR_HINT_V_BD if enabled else COLOR_HINT_GRAY_B
	box.text_color = Color.WHITE if enabled else COLOR_HINT_TEXT_G
	return box


static func _build_fetch_box(enabled: bool, viewport_size: Vector2) -> HintBoxSpec:
	var box_w: float = 120.0
	var box_h: float = 40.0
	var x: float = (viewport_size.x - PresentationModel.TARGET_PANEL) * 0.5
	var y: float = (viewport_size.y + PresentationModel.TARGET_PANEL) * 0.5 + 15.0
	var rect := Rect2(x, y, box_w, box_h)

	var box := HintBoxSpec.new()
	box.id = "fetch"
	box.text = "F Fetch Merge"
	box.rect = rect
	box.text_center = rect.get_center()
	box.font_size = 14
	box.bg_color = COLOR_HINT_F_ON_BG if enabled else COLOR_HINT_DARK
	box.border_color = COLOR_HINT_F_ON_BD if enabled else COLOR_HINT_F_BD
	box.text_color = Color8(60, 30, 0) if enabled else Color8(220, 220, 220)
	return box
