# GameLogic.gd - Movement, pickup, and drop rules
# Mirrors Python's GameLogic class in game_logic.py
class_name GameLogic


## Check if moving in direction is valid from current state.
static func can_move(state: BranchState, direction: Vector2i) -> bool:
	var player := state.get_player()

	# Player trapped inside a grounded box → must undo
	if state.has_box_at(player.pos):
		return false

	var new_pos := player.pos + direction

	var col := Physics.collision_at(new_pos, state)

	# Unfilled hole blocks player
	if col < 0:
		return false

	# Out-of-bounds or wall
	if col >= 255:
		return false

	# NO_CARRY tile while carrying items
	var held_count := state.get_held_items().size()
	var target_cap := Physics.effective_capacity(state, new_pos)
	if held_count > target_cap:
		return false

	if col > 0:
		# Cannot push shadows
		var blocking := state.get_blocking_entities_at(new_pos)
		for e in blocking:
			if state.is_shadow((e as Entity).uid):
				return false

		# Push requires empty cell behind blocker
		var push_pos := new_pos + direction
		if Physics.collision_at(push_pos, state) > 0:
			return false

	return true


## Execute movement (moves player and optionally pushes a box).
static func execute_move(state: BranchState, direction: Vector2i) -> void:
	var player  := state.get_player()
	var new_pos := player.pos + direction

	# Push boxes at new_pos
	var blocking := state.get_blocking_entities_at(new_pos)
	if not blocking.is_empty():
		var push_pos := new_pos + direction
		for e in blocking:
			(e as Entity).pos = push_pos

	# Move player
	player.pos       = new_pos
	player.direction = direction

	# Move carried items with player
	for e in state.entities:
		if (e as Entity).holder == 0:
			(e as Entity).pos = new_pos


## Pick up the box in front of the player. Returns true on success.
static func try_pickup(state: BranchState) -> bool:
	var player    := state.get_player()
	var player_pos := player.pos

	# Cannot pick up while on NO_CARRY tile
	if Physics.effective_capacity(state, player_pos) == 0:
		return false

	var front_pos := player_pos + player.direction

	var target := state.find_box_at(front_pos)
	if target == null:
		return false

	# Converge shadow instances before picking up
	target = Timeline.converge_one(state, target.uid)

	target.z         = 1
	target.holder    = 0
	target.collision = 0
	target.pos       = player_pos
	return true


## Drop held item in front of the player. Returns true on success.
static func try_drop(state: BranchState) -> bool:
	var player    := state.get_player()
	var front_pos := player.pos + player.direction

	var held: Array = []
	for e in state.entities:
		if (e as Entity).holder == 0:
			held.append(e)

	if held.is_empty():
		return false

	if Physics.collision_at(front_pos, state) > 0:
		return false

	for e in held:
		var ent      := e as Entity
		ent.z         = 0
		ent.holder    = -1
		ent.collision = 1
		ent.pos       = front_pos
	return true
