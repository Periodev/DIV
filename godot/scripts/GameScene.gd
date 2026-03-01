# GameScene.gd - Main game scene controller
# Wires input → GameController → PresentationModel → GameRenderer
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
@onready var instr_toast: PanelContainer = $UI/InstructionToast
@onready var instr_title: Label = $UI/InstructionToast/InstrVBox/InstrTitle
@onready var instr_body: RichTextLabel = $UI/InstructionToast/InstrVBox/InstrBody
@onready var win_toast: PanelContainer = $UI/WinToast
@onready var toast_sub: Label = $UI/WinToast/ToastVBox/ToastSub
@onready var toast_dot: ColorRect = $UI/WinToast/ToastVBox/ToastHeader/ToastDot
var hint_overlay: HintOverlay = null
var _desc_overlay: LevelDescOverlay = null

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
var merge_preview_progress: float = 0.0
const MERGE_PREVIEW_DURATION := 0.20
var peek_floor_active: bool = false

# Falling box Tween animations
var _fall_progress: Dictionary = {}  # {[branch_id, uid, pos]: float 0-1} driven by Tweens
var _fall_tweens:   Dictionary = {}  # {str_key: Tween}
const FALL_HOLD_DURATION := 0.10
const FALL_ANIM_DURATION := 0.25

# Held-key movement (mirrors Python game_window.py on_update + move_cooldown)
const MOVE_REPEAT_DELAY := 0.250  # seconds between repeats (~400ms per step)
var _move_cooldown: float = 0.0
var _last_held_dir: Vector2i = Vector2i(0, 0)
var _win_tween: Tween = null
var _instr_tween: Tween = null
var tutorial: TutorialController = TutorialController.new()
const DEBUG_VICTORY := true


func _vlog(msg: String) -> void:
	if DEBUG_VICTORY:
		print("[VictoryDebug] %s" % msg)


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------

func _ready() -> void:
	_ensure_hint_overlay()
	_ensure_desc_overlay()
	var gd = _get_game_data()
	if gd == null:
		push_error("GameScene: missing /root/GameData autoload")
		return

	if gd.all_levels.is_empty():
		var dir := DirAccess.open("res://Level")
		if dir:
			var zone_files: Array[String] = []
			dir.list_dir_begin()
			var fname := dir.get_next()
			while fname != "":
				if fname.match("Level[0-9]*.txt"):
					zone_files.append("res://Level/" + fname)
				fname = dir.get_next()
			zone_files.sort()
			for p in zone_files:
				gd.all_levels.append_array(MapParser.parse_level_resource(p))

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

	_clear_fall_tweens()
	controller = GameController.new(source)
	controller.state_changed.connect(_on_state_changed)
	controller.victory_achieved.connect(_on_victory)
	controller.collapse_occurred.connect(_on_collapse)
	_sync_interaction_hint_gates()

	overlay_backdrop.visible = false
	overlay_label.visible = false
	win_toast.visible = false
	hide_instruction()

	var tutorial_id: String = level_dict.get("tutorial", "")
	var tutorial_steps: Array = level_dict.get("tutorial_steps", [])
	tutorial.start_level(tutorial_id, tutorial_steps, self)
	hint_overlay.clear_overlay()
	if _desc_overlay != null:
		_desc_overlay.hide_desc()
		var objective: String = level_dict.get("objective", "")
		if objective != "":
			var level_name: String = str(level_dict.get("name", ""))
			_desc_overlay.show_desc(level_name, objective)
	merge_preview_active  = false
	merge_preview_progress = 0.0
	_set_peek_floor_mode(false)
	slide_progress        = 0.0
	slide_active          = false
	_move_cooldown        = 0.0
	_last_held_dir        = Vector2i(0, 0)

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

	# Falling boxes: create Tweens for newly detected falls, force redraw while active.
	if controller != null and not controller.falling_boxes.is_empty():
		for raw_key in controller.falling_boxes.keys():
			var k: Array  = raw_key as Array
			var uid: int = k[0] as int
			var pos: Vector2i = k[1] as Vector2i
			var branch_id: int = controller.current_focus if controller.has_branched else 0
			var anim_key: Array = [branch_id, uid, pos]
			var str_key   := "%d:%d:%d:%d" % [branch_id, uid, pos.x, pos.y]
			if not _fall_tweens.has(str_key):
				var captured_anim_key: Array = anim_key.duplicate(true)
				var captured_src_key: Array = raw_key as Array
				var captured_str := str_key
				_fall_progress[captured_anim_key] = 0.0  # register immediately for hold phase
				var tw := create_tween()
				_fall_tweens[str_key] = tw
				if FALL_HOLD_DURATION > 0.0:
					tw.tween_interval(FALL_HOLD_DURATION)
				tw.tween_method(
					func(v: float) -> void: _fall_progress[captured_anim_key] = v,
					0.0, 1.0, FALL_ANIM_DURATION).set_ease(Tween.EASE_IN).set_trans(Tween.TRANS_SINE)
				tw.tween_callback(func() -> void:
					_fall_progress.erase(captured_anim_key)
					_fall_tweens.erase(captured_str)
					controller.falling_boxes.erase(captured_src_key))
		needs_redraw = true
	if not _fall_progress.is_empty():
		needs_redraw = true

	# Flash needs per-frame update.
	if controller != null and controller.failed_action_pos != Vector2i(-1, -1):
		needs_redraw = true

	# Merge preview animation (M): side branch slides/scales into overlap.
	if controller != null:
		if not controller.has_branched:
			merge_preview_active = false
		var preview_target: float = 1.0 if (controller.has_branched and merge_preview_active) else 0.0
		if not is_equal_approx(merge_preview_progress, preview_target):
			merge_preview_progress = move_toward(
				merge_preview_progress,
				preview_target,
				delta / MERGE_PREVIEW_DURATION)
			needs_redraw = true

	# Keep animation effects smooth: merge-preview lines and shadow links.
	if controller != null and not controller.collapsed and not controller.victory:
		var preview_on := merge_preview_progress > 0.0
		var needs_effect := _branch_has_shadow_front(controller.get_active_branch())
		if controller.has_branched and preview_on:
			needs_effect = true
		if needs_effect:
			needs_redraw = true

	# Held-key movement — mirrors Python game_window.py on_update + move_cooldown.
	# Movement keys are NOT handled in _input(); they are polled here every frame
	# so that holding a direction gives smooth continuous movement.
	if controller != null and not controller.collapsed and not controller.victory:
		var dir := _get_held_direction()
		_move_cooldown = maxf(_move_cooldown - delta, 0.0)
		if dir == Vector2i(0, 0):
			_last_held_dir = Vector2i(0, 0)
			_move_cooldown = 0.0
		else:
			var dir_changed: bool = dir != _last_held_dir
			if dir_changed or _move_cooldown <= 0.0:
				controller.handle_move(dir)
				_move_cooldown = MOVE_REPEAT_DELAY
			_last_held_dir = dir

	# Physics runs every frame — mirrors Python game_window.py on_update (line 117).
	# update_physics() is called unconditionally each frame (not only on input),
	# so future time-driven or multi-step physics settle correctly.
	if controller != null and not controller.collapsed and not controller.victory:
		controller.update_physics()
		needs_redraw = true

	# Victory check every frame — mirrors Python game_window.py on_update (line 120).
	if controller != null and not controller.victory:
		controller.check_victory()

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
			# Guard against key-repeat from the same key that caused win/lose.
			if not end_key.pressed or end_key.echo:
				return
			# End-screen hotkeys are only valid when the overlay is actually shown.
			if not overlay_label.visible and not win_toast.visible:
				return
			match end_key.keycode:
				KEY_R:
					controller.reset()
					_full_refresh()
				KEY_Z:
					controller.undo()
					_full_refresh()
				KEY_SPACE, KEY_ENTER, KEY_KP_ENTER:
					if controller.victory:
						_start_level(current_level_idx + 1)
						return
				KEY_ESCAPE:
					var gd = _get_game_data()
					if gd != null:
						gd.selected_level_idx = current_level_idx
					get_tree().change_scene_to_file("res://scenes/level_select.tscn")
		return

	if not (event is InputEventKey):
		return

	var key_event := event as InputEventKey
	var key: int = key_event.keycode

	# F1: toggle level description overlay (intercepts all other input while open).
	if _desc_overlay != null and _desc_overlay.visible:
		if key_event.pressed:
			_desc_overlay.hide_desc()
		return
	if key == KEY_F1:
		if key_event.pressed and not key_event.echo:
			_show_level_desc()
		return

	# Hold C to peek the floor under the front box.
	if key == KEY_C:
		if key_event.echo:
			return
		_set_peek_floor_mode(key_event.pressed)
		return

	if not key_event.pressed:
		return

	match key:
		# Movement keys are polled in _process() for held-key repeat — not here.

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
			if controller.has_branched:
				merge_preview_active = not merge_preview_active
			_apply_frame_spec()
			_update_ui()

		KEY_ESCAPE:
			_save_selected_level_idx()
			get_tree().change_scene_to_file("res://scenes/level_select.tscn")

		KEY_BRACKETRIGHT:  # ] → next level
			_start_level(current_level_idx + 1)
			_save_selected_level_idx()
		KEY_BRACKETLEFT:   # [ → previous level
			_start_level(current_level_idx - 1)
			_save_selected_level_idx()

	tutorial.on_input(key)


# ---------------------------------------------------------------------------
# Slide animation
# ---------------------------------------------------------------------------

func _start_slide() -> void:
	slide_direction = 1 if controller.current_focus == 1 else -1
	slide_progress  = 0.0
	slide_active    = true


# Returns the movement direction currently held by the player, or (0,0) if none.
func _get_held_direction() -> Vector2i:
	if Input.is_key_pressed(KEY_W) or Input.is_key_pressed(KEY_UP):
		return Vector2i(0, -1)
	if Input.is_key_pressed(KEY_S) or Input.is_key_pressed(KEY_DOWN):
		return Vector2i(0, 1)
	if Input.is_key_pressed(KEY_A) or Input.is_key_pressed(KEY_LEFT):
		return Vector2i(-1, 0)
	if Input.is_key_pressed(KEY_D) or Input.is_key_pressed(KEY_RIGHT):
		return Vector2i(1, 0)
	return Vector2i(0, 0)


func _branch_has_shadow_front(branch: BranchState) -> bool:
	if branch == null:
		return false
	if not branch.get_held_items().is_empty():
		return false
	var player := branch.get_player()
	if player == null:
		return false
	var front_pos := player.pos + player.direction
	var front_uids: Dictionary = {}
	for e in branch.entities:
		var ent := e as Entity
		if ent == null:
			continue
		if ent.uid == 0 or ent.type != Enums.EntityType.BOX or not ent.is_grounded():
			continue
		if ent.pos == front_pos:
			front_uids[ent.uid] = true
	for raw_uid in front_uids.keys():
		var uid := int(raw_uid)
		if branch.is_shadow(uid):
			return true
	return false


# ---------------------------------------------------------------------------
# Signal handlers
# ---------------------------------------------------------------------------

func _on_state_changed() -> void:
	_vlog("state_changed: collapsed=%s victory=%s branched=%s overlay=%s" % [
		controller.collapsed, controller.victory, controller.has_branched, overlay_label.visible
	])
	# Physics and victory are now handled each frame in _process().
	# _on_state_changed() only triggers an immediate redraw so the visual
	# responds to input without waiting for the next _process() tick.
	tutorial.on_state_changed()
	_apply_frame_spec()
	_update_ui()


func _on_victory() -> void:
	_vlog("_on_victory fired")
	var solution_chars := PackedStringArray()
	for ch in controller.input_log:
		solution_chars.append(str(ch))
	var solution := "".join(solution_chars)
	print("\n=== VICTORY ===")
	print("Steps: %d" % controller.input_log.size())
	print("Solution: %s" % solution)
	print("===============\n")
	var level_dict: Dictionary = all_levels[current_level_idx] \
		if current_level_idx >= 0 and current_level_idx < all_levels.size() else {}
	var level_id: String = str(level_dict.get("id", ""))
	var gd = _get_game_data()
	if gd != null:
		gd.mark_level_played(level_id)
	# Toast instead of full-screen overlay
	toast_sub.text = "Level %s  ·  %d steps" % [level_id, controller.input_log.size()]
	toast_dot.color = Color(0.29, 0.54, 0.29)
	win_toast.modulate.a = 0.0
	win_toast.visible = true
	if _win_tween != null:
		_win_tween.kill()
	_win_tween = create_tween()
	_win_tween.tween_property(win_toast, "modulate:a", 1.0, 0.35) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)


func _on_collapse() -> void:
	overlay_backdrop.visible = true
	overlay_label.text    = "FALL DOWN!\nR: restart   Z: undo   ESC: level select"
	overlay_label.visible = true


func _clear_fall_tweens() -> void:
	for tw in _fall_tweens.values():
		if tw is Tween:
			(tw as Tween).kill()
	_fall_tweens.clear()
	_fall_progress.clear()


func _full_refresh() -> void:
	var should_hide_overlay := controller == null or (not controller.victory and not controller.collapsed)
	if should_hide_overlay:
		overlay_backdrop.visible = false
		overlay_label.visible = false
		win_toast.visible = false
	else:
		_vlog("_full_refresh called in end-state; keep overlay visible")
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
	_sync_interaction_hint_gates()

	var preview_on := merge_preview_progress > 0.0
	var spec := PresentationModel.build(
		controller,
		animation_frame,
		_fall_progress,
		slide_progress if slide_active else 0.0,
		slide_direction,
		merge_preview_active,
		merge_preview_progress)

	_update_renderer_layering(preview_on)

	renderer0.draw_frame(spec.main_branch)

	if spec.sub_branch != null:
		renderer1.visible = true
		renderer1.draw_frame(spec.sub_branch)
	else:
		renderer1.visible = false

	if hint_overlay != null:
		hint_overlay.update_overlay(spec, controller, preview_on, animation_frame)


func _sync_interaction_hint_gates() -> void:
	if controller == null:
		return
	if not controller.has_method("set_interaction_hint_gates"):
		return
	controller.set_interaction_hint_gates(
		_current_hints.get("converge", false) as bool,
		_current_hints.get("pickup", false) as bool,
		_current_hints.get("face_box", true) as bool,
		_current_hints.get("fetch", false) as bool
	)


func _update_renderer_layering(preview_on: bool) -> void:
	if controller == null or not controller.has_branched:
		renderer0.z_index = 0
		renderer1.z_index = 0
		return

	var focused_is_main := controller.current_focus == 0
	# render_arc parity:
	# - normal mode: focused branch on top
	# - merge preview: non-focused branch on top
	var top_main := (focused_is_main and not preview_on) or ((not focused_is_main) and preview_on)
	if top_main:
		renderer0.z_index = 2
		renderer1.z_index = 1
	else:
		renderer0.z_index = 1
		renderer1.z_index = 2


# ---------------------------------------------------------------------------
# UI label
# ---------------------------------------------------------------------------

func _update_ui() -> void:
	if controller == null:
		return
	hint_label.text = ""
	var callout_ui = get_node_or_null("UI/SystemCalloutUI")
	if callout_ui == null:
		return
	var pts := controller.div_points
	var can_merge := controller.can_normal_merge() if controller.has_method("can_normal_merge") else false
	var can_fetch := controller.can_show_fetch_hint()
	callout_ui.update_state(
		controller.has_branched,
		controller.current_focus,
		pts,
		can_merge,
		can_fetch,
		_current_hints.get("diverge", true) as bool,
		_current_hints.get("fetch", false) as bool,
		merge_preview_active
	)


func _ensure_hint_overlay() -> void:
	if hint_overlay != null:
		return
	hint_overlay = HintOverlay.new()
	hint_overlay.name = "HintOverlay"
	hint_overlay.z_as_relative = false
	hint_overlay.z_index = 100
	add_child(hint_overlay)


func _ensure_desc_overlay() -> void:
	if _desc_overlay != null:
		return
	_desc_overlay = LevelDescOverlay.new()
	_desc_overlay.name = "LevelDescOverlay"
	$UI.add_child(_desc_overlay)


func _show_level_desc() -> void:
	if _desc_overlay == null or all_levels.is_empty():
		return
	var level_dict: Dictionary = all_levels[current_level_idx]
	_desc_overlay.show_desc(
		str(level_dict.get("name", "")),
		str(level_dict.get("objective", ""))
	)


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


func show_instruction(title: String, body_bbcode: String) -> void:
	if _instr_tween != null:
		_instr_tween.kill()
		_instr_tween = null
	instr_title.text = title
	instr_body.text = body_bbcode
	var already_visible := instr_toast.visible and instr_toast.modulate.a > 0.9
	if not already_visible:
		instr_toast.modulate.a = 0.0
		instr_toast.visible = true
		_instr_tween = create_tween()
		_instr_tween.tween_property(instr_toast, "modulate:a", 1.0, 0.3) \
			.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_OUT)


func hide_instruction() -> void:
	if not instr_toast.visible:
		return
	if _instr_tween != null:
		_instr_tween.kill()
	_instr_tween = create_tween()
	_instr_tween.tween_property(instr_toast, "modulate:a", 0.0, 0.2) \
		.set_trans(Tween.TRANS_CUBIC).set_ease(Tween.EASE_IN)
	_instr_tween.tween_callback(func(): instr_toast.visible = false)


func _get_game_data():
	return get_node_or_null("/root/GameData")
