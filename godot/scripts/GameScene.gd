# GameScene.gd - Main game scene controller
# Wires input → GameController → GameRenderer
# Mirrors the game loop in Python's game_window.py / render_arc.py
extends Node2D
class_name GameScene

# ---------------------------------------------------------------------------
# Scene references (set in editor or via @onready)
# ---------------------------------------------------------------------------
@onready var renderer0: GameRenderer = $Renderer0  # DIV 0 / MAIN
@onready var renderer1: GameRenderer = $Renderer1  # DIV 1
@onready var hint_label: Label        = $UI/HintLabel
@onready var overlay_label: Label     = $UI/OverlayLabel

# ---------------------------------------------------------------------------
# Layout constants (matching presentation_model.py)
# ---------------------------------------------------------------------------
const WINDOW_W     := 1280
const WINDOW_H     := 720
const TARGET_PANEL := 480   # focused panel always renders to this pixel size
const GAP          := 30

const FOCUS_SCALE := 1.0
const SIDE_SCALE  := 0.7

# Derived layout constants (based on TARGET_PANEL, fixed regardless of grid_size)
const GRID_PX    := TARGET_PANEL
const SIDE_GRID  := int(TARGET_PANEL * SIDE_SCALE)         # 336
const CENTER_X   := (WINDOW_W - TARGET_PANEL) / 2          # 400
const CENTER_Y   := (WINDOW_H - TARGET_PANEL) / 2          # 120
const RIGHT_X    := CENTER_X + TARGET_PANEL + GAP           # 910
const LEFT_X     := CENTER_X - GAP - SIDE_GRID             # 54
const SIDE_Y     := (WINDOW_H - SIDE_GRID) / 2             # 192

# ---------------------------------------------------------------------------
# State
# ---------------------------------------------------------------------------
var controller: GameController = null
var all_levels:  Array         = []   # Array of level dicts from MapParser
var current_level_idx: int     = 0

# Animation
var animation_timer:    float = 0.0
var animation_frame:    int   = 0
var flash_update_timer: float = 0.0

# Slide animation (Tab focus switch)
var slide_progress:  float = 0.0
var slide_direction: int   = 0
var slide_active:    bool  = false
const SLIDE_DURATION := 0.25  # seconds

# Merge preview toggle
var merge_preview_active: bool = false
var fetch_mode_enabled:   bool = false

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

func _ready() -> void:
	# Use levels cached by LevelSelect (or load if entering scene directly)
	if GameData.all_levels.is_empty():
		var zone_files := ["res://Level/Level0.txt", "res://Level/Level1.txt",
						   "res://Level/Level2.txt", "res://Level/Level3.txt",
						   "res://Level/Level4.txt"]
		for path in zone_files:
			GameData.all_levels.append_array(MapParser.parse_level_resource(path))

	all_levels = GameData.all_levels
	_start_level(GameData.selected_level_idx)


func _start_level(idx: int) -> void:
	if all_levels.is_empty():
		return
	current_level_idx = clampi(idx, 0, all_levels.size() - 1)
	var level_dict: Dictionary = all_levels[current_level_idx]
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

	merge_preview_active = false
	fetch_mode_enabled   = false
	slide_progress       = 0.0
	slide_active         = false

	_update_renderer_layout()
	_update_renderer_data()
	_update_ui()


# ---------------------------------------------------------------------------
# Process (animation + flash update)
# ---------------------------------------------------------------------------

func _process(delta: float) -> void:
	# Animate blink (every 0.5 s)
	animation_timer += delta
	if animation_timer >= 0.5:
		animation_timer = 0.0
		animation_frame += 1
		renderer0.animation_frame = animation_frame
		renderer1.animation_frame = animation_frame
		_request_redraw()

	# Flash fade-out
	if controller != null and controller.failed_action_pos != Vector2i(-1, -1):
		flash_update_timer += delta
		if flash_update_timer >= 0.016:
			flash_update_timer = 0.0
			_update_flash()

	# Slide animation
	if slide_active:
		slide_progress = minf(slide_progress + delta / SLIDE_DURATION, 1.0)
		_update_renderer_layout()
		if slide_progress >= 1.0:
			slide_active = false

	_request_redraw()


# ---------------------------------------------------------------------------
# Input
# ---------------------------------------------------------------------------

func _input(event: InputEvent) -> void:
	if controller == null or controller.collapsed or controller.victory:
		if event is InputEventKey:
			var end_key := event as InputEventKey
			if end_key.pressed:
				match end_key.keycode:
					KEY_R:
						controller.reset()
						_full_refresh()
					KEY_BRACKETRIGHT:
						_start_level(current_level_idx + 1)
						GameData.selected_level_idx = current_level_idx
					KEY_ESCAPE:
						get_tree().change_scene_to_file("res://scenes/level_select.tscn")
		return

	if not (event is InputEventKey) or not event.pressed:
		return

	var key_event := event as InputEventKey
	var key: int   = key_event.keycode
	var shift: bool = key_event.shift_pressed

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
			if controller.try_branch():
				_full_refresh()

		KEY_C:
			if shift:
				if controller.try_fetch_merge():
					_full_refresh()
			else:
				if controller.try_merge():
					_full_refresh()

		KEY_F:
			if controller.try_fetch_merge():
				_full_refresh()

		KEY_X, KEY_SPACE:
			controller.handle_adaptive_action()

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
			_request_redraw()

		KEY_ESCAPE:
			GameData.selected_level_idx = current_level_idx
			get_tree().change_scene_to_file("res://scenes/level_select.tscn")

		KEY_BRACKETRIGHT:  # ] → next level
			_start_level(current_level_idx + 1)
			GameData.selected_level_idx = current_level_idx
		KEY_BRACKETLEFT:   # [ → previous level
			_start_level(current_level_idx - 1)
			GameData.selected_level_idx = current_level_idx


# ---------------------------------------------------------------------------
# Slide animation
# ---------------------------------------------------------------------------

func _start_slide() -> void:
	# direction: 1 = switching 0→1 (focus became 1), -1 = switching 1→0
	slide_direction = 1 if controller.current_focus == 1 else -1
	slide_progress  = 0.0
	slide_active    = true


# ---------------------------------------------------------------------------
# Render update helpers
# ---------------------------------------------------------------------------

func _on_state_changed() -> void:
	controller.update_physics()
	controller.check_victory()
	_update_renderer_layout()
	_update_renderer_data()
	_update_ui()


func _on_victory() -> void:
	overlay_label.text    = "✓ 過關！\n\nR：重置　]：下一關"
	overlay_label.visible = true


func _on_collapse() -> void:
	overlay_label.text    = "✗ 墜落！\n\nR：重置　Z：上一步"
	overlay_label.visible = true


func _full_refresh() -> void:
	overlay_label.visible = false
	_update_renderer_layout()
	_update_renderer_data()
	_update_ui()


func _request_redraw() -> void:
	renderer0.queue_redraw()
	if controller != null and controller.has_branched:
		renderer1.queue_redraw()


# ---------------------------------------------------------------------------
# Layout: position and scale the two renderer nodes
# ---------------------------------------------------------------------------

func _update_renderer_layout() -> void:
	if controller == null:
		return

	# Cell size scales so the focused panel always fills TARGET_PANEL pixels
	var gs: int      = controller.main_branch.grid_size
	var cell_sz: int = TARGET_PANEL / gs
	renderer0.cell_size = cell_sz
	renderer1.cell_size = cell_sz

	var focus    := controller.current_focus
	var branched := controller.has_branched

	if not branched:
		# Single branch centred at full scale
		renderer0.position   = Vector2(CENTER_X, CENTER_Y)
		renderer0.panel_scale = FOCUS_SCALE
		renderer1.visible    = false
	else:
		renderer1.visible = true
		if slide_active:
			_apply_slide_layout(focus)
		else:
			_apply_static_layout(focus)

	renderer0.queue_redraw()
	renderer1.queue_redraw()


func _apply_static_layout(focus: int) -> void:
	if focus == 0:
		renderer0.position    = Vector2(CENTER_X, CENTER_Y)
		renderer0.panel_scale = FOCUS_SCALE
		renderer1.position    = Vector2(RIGHT_X, SIDE_Y)
		renderer1.panel_scale = SIDE_SCALE
	else:
		renderer0.position    = Vector2(LEFT_X, SIDE_Y)
		renderer0.panel_scale = SIDE_SCALE
		renderer1.position    = Vector2(CENTER_X, CENTER_Y)
		renderer1.panel_scale = FOCUS_SCALE


func _apply_slide_layout(_focus: int) -> void:
	var t: float = _ease_in_out(slide_progress)

	if slide_direction == 1:  # focus 0→1: DIV0 shrinks left, DIV1 grows to center
		renderer0.position    = Vector2(int(CENTER_X + (LEFT_X  - CENTER_X) * t), int(CENTER_Y + (SIDE_Y   - CENTER_Y) * t))
		renderer0.panel_scale = FOCUS_SCALE + (SIDE_SCALE  - FOCUS_SCALE) * t
		renderer1.position    = Vector2(int(RIGHT_X  + (CENTER_X - RIGHT_X)  * t), int(SIDE_Y   + (CENTER_Y - SIDE_Y)   * t))
		renderer1.panel_scale = SIDE_SCALE  + (FOCUS_SCALE - SIDE_SCALE)  * t
	else:  # focus 1→0: DIV0 grows to center, DIV1 shrinks right
		renderer0.position    = Vector2(int(LEFT_X   + (CENTER_X - LEFT_X)   * t), int(SIDE_Y   + (CENTER_Y - SIDE_Y)   * t))
		renderer0.panel_scale = SIDE_SCALE  + (FOCUS_SCALE - SIDE_SCALE)  * t
		renderer1.position    = Vector2(int(CENTER_X + (RIGHT_X  - CENTER_X) * t), int(CENTER_Y + (SIDE_Y   - CENTER_Y) * t))
		renderer1.panel_scale = FOCUS_SCALE + (SIDE_SCALE  - FOCUS_SCALE) * t


func _ease_in_out(t: float) -> float:
	if t < 0.5:
		return 2.0 * t * t
	return 1.0 - pow(-2.0 * t + 2.0, 2.0) / 2.0


# ---------------------------------------------------------------------------
# Renderer data sync
# ---------------------------------------------------------------------------

func _update_renderer_data() -> void:
	if controller == null:
		return

	var focus    := controller.current_focus
	var branched := controller.has_branched
	var preview  := controller.get_merge_preview()
	var goal_ok  := preview.all_switches_activated()

	# Flash
	var now          := Time.get_unix_time_from_system()
	var flash_pos    := controller.failed_action_pos
	var flash_int    := 0.0
	if flash_pos != Vector2i(-1, -1):
		var elapsed      := now - controller.failed_action_time
		var flash_dur    := 0.3
		if elapsed < flash_dur:
			flash_int = 1.0 - elapsed / flash_dur
		else:
			flash_pos = Vector2i(-1, -1)

	# Falling boxes
	var falling: Dictionary = {}
	for raw_key in controller.falling_boxes.keys():
		var fall_arr := raw_key as Array
		var prog: float = controller.get_falling_progress(fall_arr[0] as int, fall_arr[1] as Vector2i)
		if prog >= 0.0:
			falling[raw_key] = prog

	# Interaction hint
	var hint: Dictionary = controller.get_interaction_hint()
	var hint_target: Vector2i = hint.get("target_pos", Vector2i(-1, -1)) as Vector2i
	var hint_color:  Color    = hint.get("color", Color.WHITE) as Color
	var hint_text:   String   = hint.get("text", "") as String

	# Renderer 0 (main / DIV 0)
	renderer0.branch_state    = controller.main_branch
	renderer0.is_focused      = (focus == 0)
	renderer0.border_color    = Color(1.0, 0.55, 0.0) if (focus == 0) else Color(0.4, 0.4, 0.4)
	renderer0.goal_active     = goal_ok
	renderer0.animation_frame  = animation_frame
	renderer0.is_merge_preview = merge_preview_active
	renderer0.flash_pos       = flash_pos if (focus == 0) else Vector2i(-1, -1)
	renderer0.flash_intensity  = flash_int if (focus == 0) else 0.0
	renderer0.falling_progress = falling
	renderer0.hint_target_pos  = hint_target if (focus == 0) else Vector2i(-1, -1)
	renderer0.hint_color      = hint_color
	renderer0.hint_text       = hint_text
	renderer0.panel_title     = "DIV 0" if branched else "MAIN"

	# Renderer 1 (sub / DIV 1)
	if branched and controller.sub_branch != null:
		renderer1.branch_state   = controller.sub_branch
		renderer1.is_focused     = (focus == 1)
		renderer1.border_color   = Color(0.0, 0.86, 1.0) if (focus == 1) else Color(0.4, 0.4, 0.4)
		renderer1.goal_active    = goal_ok
		renderer1.animation_frame = animation_frame
		renderer1.is_merge_preview= merge_preview_active
		renderer1.flash_pos      = flash_pos if (focus == 1) else Vector2i(-1, -1)
		renderer1.flash_intensity = flash_int if (focus == 1) else 0.0
		renderer1.falling_progress = falling
		renderer1.hint_target_pos = hint_target if (focus == 1) else Vector2i(-1, -1)
		renderer1.hint_color      = hint_color
		renderer1.hint_text       = hint_text
		renderer1.panel_title    = "DIV 1"

	renderer0.queue_redraw()
	renderer1.queue_redraw()


func _update_flash() -> void:
	_update_renderer_data()


# ---------------------------------------------------------------------------
# UI label
# ---------------------------------------------------------------------------

func _update_ui() -> void:
	if controller == null:
		return
	var hint_str := controller.get_timeline_hint()
	hint_label.text = hint_str
