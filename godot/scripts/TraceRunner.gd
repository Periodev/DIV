# TraceRunner.gd — headless cross-implementation trace runner
# Produces canonical JSON matching tools/trace_runner.py output.
#
# Run from Godot project root:
#   godot --headless --script res://scripts/TraceRunner.gd -- <level_idx> [moves]
#
# Example:
#   godot --headless --script res://scripts/TraceRunner.gd -- 1 "UUDRXV"
#   godot --headless --script res://scripts/TraceRunner.gd -- 0 "" > /tmp/gd.json
#
# Compare with Python output:
#   python tools/trace_runner.py 0 "" > /tmp/py.json
#   diff /tmp/py.json /tmp/gd.json
extends SceneTree


# ---------------------------------------------------------------------------
# Serialization — canonical format (must match tools/trace_runner.py exactly)
# Enums serialised as ints, matching Enums.gd values.
# ---------------------------------------------------------------------------

static func _ser_branch(branch: BranchState) -> Dictionary:
	# Terrain: keys sorted by (x, y), encoded as "x,y"
	var keys: Array = branch.terrain.keys()
	keys.sort_custom(func(a: Variant, b: Variant) -> bool:
		var va := a as Vector2i
		var vb := b as Vector2i
		if va.x != vb.x:
			return va.x < vb.x
		return va.y < vb.y)

	var terrain: Dictionary = {}
	for k in keys:
		var v := k as Vector2i
		terrain["%d,%d" % [v.x, v.y]] = branch.terrain[k] as int

	# Entities: sorted by uid
	var ents: Array = branch.entities.duplicate()
	ents.sort_custom(func(a: Variant, b: Variant) -> bool:
		return (a as Entity).uid < (b as Entity).uid)

	var ents_out: Array = []
	for raw in ents:
		var e := raw as Entity
		var fused: Array = e.fused_from.duplicate()
		fused.sort()
		ents_out.append({
			"collision":  e.collision,
			"direction":  [e.direction.x, e.direction.y],
			"fused_from": fused,
			"holder":     e.holder,
			"pos":        [e.pos.x, e.pos.y],
			"type":       e.type,
			"uid":        e.uid,
			"weight":     e.weight,
			"z":          e.z,
		})

	return {
		"entities":  ents_out,
		"grid_size": branch.grid_size,
		"next_uid":  branch.next_uid,
		"terrain":   terrain,
	}


static func _ser_ctrl(ctrl: GameController) -> Dictionary:
	return {
		"collapsed":     ctrl.collapsed,
		"current_focus": ctrl.current_focus,
		"has_branched":  ctrl.has_branched,
		"main_branch":   _ser_branch(ctrl.main_branch),
		"sub_branch":    _ser_branch(ctrl.sub_branch) if ctrl.sub_branch != null else null,
		"victory":       ctrl.victory,
	}


# ---------------------------------------------------------------------------
# Action dispatch — mirrors replay_core.py execute_action
# ---------------------------------------------------------------------------

static func _exec(ctrl: GameController, ch: String, hints: Dictionary) -> void:
	if ctrl.collapsed or ctrl.victory:
		return
	match ch:
		"U": ctrl.handle_move(Vector2i(0, -1))
		"D": ctrl.handle_move(Vector2i(0,  1))
		"L": ctrl.handle_move(Vector2i(-1, 0))
		"R": ctrl.handle_move(Vector2i( 1, 0))
		"V": ctrl.try_branch()
		"C": ctrl.try_merge()
		"F": ctrl.try_fetch_merge()
		"T": ctrl.switch_focus()
		"X": ctrl.handle_adaptive_action(
				hints.get("converge", true) as bool,
				hints.get("pickup",   true) as bool)
		"P": ctrl.handle_pickup(hints.get("pickup", true) as bool)
		"O": ctrl.handle_drop()
		"Z": ctrl.undo()


# ---------------------------------------------------------------------------
# Trace runner
# ---------------------------------------------------------------------------

static func run_trace(level_dict: Dictionary, moves: String) -> Array:
	var source := MapParser.parse_dual_layer(
		level_dict.get("floor_map", "") as String,
		level_dict.get("object_map", "") as String)
	if source == null:
		return []

	# hints — mirrors Replayer.__init__ fallback
	var hints: Dictionary
	var raw = level_dict.get("hints")
	if raw is Dictionary:
		hints = raw as Dictionary
	else:
		hints = {"converge": true, "diverge": true, "fetch": true, "pickup": true}

	var ctrl := GameController.new(source)

	# Settle initial state — mirrors Replayer.seek(0)
	ctrl.update_physics()
	if not ctrl.victory:
		ctrl.check_victory()

	var trace: Array = [{
		"move":  "",
		"state": _ser_ctrl(ctrl),
		"step":  0,
	}]

	for i in moves.length():
		var ch: String = moves[i]
		_exec(ctrl, ch, hints)
		if not ctrl.collapsed and not ctrl.victory:
			ctrl.update_physics()
		trace.append({
			"move":  ch,
			"state": _ser_ctrl(ctrl),
			"step":  i + 1,
		})

	return trace


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

func _initialize() -> void:
	var args := OS.get_cmdline_user_args()
	if args.is_empty():
		printerr("Usage: godot --headless --script res://scripts/TraceRunner.gd -- <level_idx> [moves]")
		quit(1)
		return

	var level_idx  := int(args[0])
	var moves: String = args[1] if args.size() > 1 else ""

	var all_levels: Array = []
	for path: String in [
		"res://Level/Level0.txt", "res://Level/Level1.txt",
		"res://Level/Level2.txt", "res://Level/Level3.txt",
		"res://Level/Level4.txt",
	]:
		all_levels.append_array(MapParser.parse_level_resource(path))

	if level_idx < 0 or level_idx >= all_levels.size():
		printerr("Level index %d out of range (0-%d)" % [level_idx, all_levels.size() - 1])
		quit(1)
		return

	var trace := run_trace(all_levels[level_idx] as Dictionary, moves)
	if trace.is_empty():
		printerr("run_trace failed (parse error?)")
		quit(1)
		return

	# sort_keys=true (default) — matches Python json.dumps(sort_keys=True)
	print(JSON.stringify(trace, "  "))
	quit()
