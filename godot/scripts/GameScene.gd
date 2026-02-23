# GameScene.gd - Main game scene controller
# Wires input ??GameController ??PresentationModel ??GameRenderer
extends Node2D
class_name GameScene

# ---------------------------------------------------------------------------
# Scene references
# ---------------------------------------------------------------------------
@onready var renderer0: GameRenderer = $Renderer0  # DIV 0 / MAIN
@onready var renderer1: GameRenderer = $Renderer1  # DIV 1
@onready var hint_label: Label        = $UI/HintLabel
@onready var overlay_backdrop: ColorRect = $UI/OverlayBackdrop
@onready var overlay_label: Label     = $UI/OverlayLabel
var hint_overlay: HintOverlay = null

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
var controller: GameController = null
var all_levels:  Array         = []
var current_level_idx: int     = 0
var _current_hints: Dictionary = {"diverge": true, "pickup": false, "converge": false, "fetch": false}

# Animation
var animation_timer: float = 0.0
var animation_frame: int   = 0

# Slide animation (Tab focus switch)
var slide_progress:  float = 0.0
var slide_direction: int   = 0
var slide_active:    bool  = false
const SLIDE_DURATION := 0.25  # seconds

# Merge preview toggle
var merge_preview_active: bool = false
var peek_floor_active: bool = false


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

func _ready() -> void:
	_ensure_hint_overlay()
	var gd = _get_game_data()
	if gd == null:
		push_error("GameScene: missing /root/GameData autoload")
		return

	if gd.all_levels.is_empty():
		var zone_files := ["res://Level/Level0.txt", "res://Level/Level1.txt",
						   "res://Level/Level2.txt", "res://Level/Level3.txt",
						   "res://Level/Level4.txt"]
		for path in zone_files:
			gd.all_levels.append_array(MapParser.parse_level_resource(path))

	all_levels = gd.all_levels
	_start_level(gd.selected_level_idx)


func _start_level(idx: int) -> void:
	if all_levels.is_empty():
		return
	current_level_idx = clampi(idx, 0, all_levels.size() - 1)
	var level_dict: Dictionary = all_levels[current_level_idx]
	var raw_hints = level_dict.get("hints")
	_current_hints = raw_hints if raw_hints is Dictionary \
		else {"diverge": true, "pickup": false, "converge": false, "fetch": false}
	var source := MapParser.parse_dual_layer(
		level_dict.get("floor_map", ""),
		level_dict.get("object_map", "")
	)
	if source == null:
		push_error("GameScene: failed to parse level %d" % current_level_idx)
		return

	controller = GameController.new(source)
	controller.state_changed.connect(_on_state_changed)
	controller.victory_achieved.connect(_on_victory)
	controller.collapse_occurred.connect(_on_collapse)

	overlay_backdrop.visible = false
	overlay_label.visible = false
	hint_overlay.clear_overlay()
	merge_preview_active  = false
	_set_peek_floor_mode(false)
	slide_progress        = 0.0
	slide_active          = false

	_apply_frame_spec()
	_update_ui()


# ---------------------------------------------------------------------------
# Process (slide animation, blink, falling boxes)
# ---------------------------------------------------------------------------

func _process(delta: float) -> void:
	var needs_redraw := false

	# Blink timer (every 0.5 s)
	animation_timer += delta
	if animation_timer >= 0.5:
		animation_timer = 0.0
		animation_frame += 1
		needs_redraw = true

	# Slide animation
	if slide_active:
		slide_progress = minf(slide_progress + delta / SLIDE_DURATION, 1.0)
		if slide_progress >= 1.0:
			slide_active = false
		needs_redraw = true

	# Falling boxes or flash need per-frame update
	if controller != null and (
			not controller.falling_boxes.is_empty() or
			controller.failed_action_pos != Vector2i(-1, -1)):
		needs_redraw = true

	if needs_redraw:
		_apply_frame_spec()


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

func _input(event: InputEvent) -> void:
	if controller == null:
		return

	if controller.collapsed or controller.victory:
		if event is InputEventKey:
			var end_key := event as InputEventKey
			if end_key.pressed:
				match end_key.keycode:
					KEY_R:
						controller.reset()
						_full_refresh()
					KEY_Z:
						controller.undo()
						_full_refresh()
					KEY_SPACE, KEY_ESCAPE:
						var gd = _get_game_data()
						if gd != null:
							gd.selected_level_idx = current_level_idx
						get_tree().change_scene_to_file("res://scenes/level_select.tscn")
		return

	if not (event is InputEventKey):
		return

	var key_event := event as InputEventKey
	var key: int = key_event.keycode

	# Hold C to peek the floor under the front box.
	if key == KEY_C:
		if key_event.echo:
			return
		_set_peek_floor_mode(key_event.pressed)
		return

	if not key_event.pressed:
		return

	match key:
		KEY_W, KEY_UP:
			controller.handle_move(Vector2i(0, -1))
		KEY_S, KEY_DOWN:
			controller.handle_move(Vector2i(0, 1))
		KEY_A, KEY_LEFT:
			controller.handle_move(Vector2i(-1, 0))
		KEY_D, KEY_RIGHT:
			controller.handle_move(Vector2i(1, 0))

		KEY_V:
			if controller.has_branched:
				if controller.try_merge():
					_full_refresh()
			elif _current_hints.get("diverge", true):
				if controller.try_branch():
					_full_refresh()

		KEY_F:
			if _current_hints.get("fetch", false):
				if controller.try_fetch_merge():
					_full_refresh()

		KEY_X, KEY_SPACE:
			controller.handle_adaptive_action(
				_current_hints.get("converge", false) as bool,
				_current_hints.get("pickup",   false) as bool)

		KEY_TAB:
			if controller.switch_focus():
				_start_slide()

		KEY_Z:
			controller.undo()
			_full_refresh()

		KEY_R:
			controller.reset()
			_full_refresh()

		KEY_M:
			merge_preview_active = not merge_preview_active
			_apply_frame_spec()

		KEY_ESCAPE:
			_save_selected_level_idx()
			get_tree().change_scene_to_file("res://scenes/level_select.tscn")

		KEY_BRACKETRIGHT:  # ] ??next level
			_start_level(current_level_idx + 1)
			_save_selected_level_idx()
		KEY_BRACKETLEFT:   # [ ??previous level
			_start_level(current_level_idx - 1)
			_save_selected_level_idx()


# ---------------------------------------------------------------------------
# Slide animation
# ---------------------------------------------------------------------------

func _start_slide() -> void:
	slide_direction = 1 if controller.current_focus == 1 else -1
	slide_progress  = 0.0
	slide_active    = true


# ---------------------------------------------------------------------------
# Signal handlers
# ---------------------------------------------------------------------------

func _on_state_changed() -> void:
	controller.update_physics()
	controller.check_victory()
	_apply_frame_spec()
	_update_ui()


func _on_victory() -> void:
	var level_dict: Dictionary = all_levels[current_level_idx] \
		if current_level_idx >= 0 and current_level_idx < all_levels.size() else {}
	var level_id: String = str(level_dict.get("id", ""))
	var gd = _get_game_data()
	if gd != null:
		gd.mark_level_played(level_id)
	overlay_backdrop.visible = true
	overlay_label.text    = "LEVEL COMPLETE!\nR: restart   Z: undo   SPACE/ESC: level select"
	overlay_label.visible = true


func _on_collapse() -> void:
	overlay_backdrop.visible = true
	overlay_label.text    = "FALL DOWN!\nR: restart   Z: undo   ESC: level select"
	overlay_label.visible = true


func _full_refresh() -> void:
	overlay_backdrop.visible = false
	overlay_label.visible = false
	_apply_frame_spec()
	_update_ui()


# ---------------------------------------------------------------------------
# Spec pipeline (replaces _update_renderer_layout + _update_renderer_data)
# ---------------------------------------------------------------------------

func _apply_frame_spec() -> void:
	if controller == null:
		if hint_overlay != null:
			hint_overlay.clear_overlay()
		return

	var spec := PresentationModel.build(
		controller,
		animation_frame,
		slide_progress if slide_active else 0.0,
		slide_direction,
		merge_preview_active)

	renderer0.draw_frame(spec.main_branch)

	if spec.sub_branch != null:
		renderer1.visible = true
		renderer1.draw_frame(spec.sub_branch)
	else:
		renderer1.visible = false

	if hint_overlay != null:
		hint_overlay.update_overlay(spec, controller, merge_preview_active, animation_frame)


# ---------------------------------------------------------------------------
# UI label
# ---------------------------------------------------------------------------

func _update_ui() -> void:
	if controller == null:
		return
	hint_label.text = ""


func _ensure_hint_overlay() -> void:
	if hint_overlay != null:
		return
	hint_overlay = HintOverlay.new()
	hint_overlay.name = "HintOverlay"
	hint_overlay.z_as_relative = false
	hint_overlay.z_index = 100
	add_child(hint_overlay)


func _set_peek_floor_mode(enabled: bool) -> void:
	if peek_floor_active == enabled:
		return
	peek_floor_active = enabled
	renderer0.set_peek_floor_mode(enabled)
	renderer1.set_peek_floor_mode(enabled)


func _save_selected_level_idx() -> void:
	var gd = _get_game_data()
	if gd != null:
		gd.selected_level_idx = current_level_idx


func _get_game_data():
	return get_node_or_null("/root/GameData")
