# BranchState.gd - Runtime state of one timeline branch
# Mirrors Python's BranchState class in timeline_system.py
class_name BranchState

var entities: Array  = []   # Array[Entity], entities[0] is always player
var terrain: Dictionary = {}  # Vector2i -> Enums.TerrainType (int)
var grid_size: int   = 0
var next_uid: int    = 0


## Computed: the player entity is always entities[0].
func get_player() -> Entity:
	return entities[0]


## Deep copy this branch state.
func copy() -> BranchState:
	var s := BranchState.new()
	s.terrain   = terrain.duplicate()
	s.grid_size = grid_size
	s.next_uid  = next_uid
	s.entities  = []
	for e in entities:
		s.entities.append((e as Entity).copy())
	return s


## Get all entity instances with a given uid.
func get_entities_by_uid(p_uid: int) -> Array:
	var result: Array = []
	for e in entities:
		if (e as Entity).uid == p_uid:
			result.append(e)
	return result


## Get non-held instances of uid (grounded or underground).
func get_non_held_instances(p_uid: int) -> Array:
	var result: Array = []
	for e in entities:
		var ent := e as Entity
		if ent.uid == p_uid and ent.z <= 0 and ent.holder == -1:
			result.append(e)
	return result


## Check if uid is in a "shadow" state (multiple positions, or fusion paradox).
func is_shadow(p_uid: int) -> bool:
	var instances := get_entities_by_uid(p_uid)
	if instances.is_empty():
		return false

	# Standard shadow: same uid at multiple (pos, z) locations
	var positions: Dictionary = {}
	for e in instances:
		var ent := e as Entity
		var key := Vector3i(ent.pos.x, ent.pos.y, ent.z)
		positions[key] = true
	if positions.size() > 1:
		return true

	# Fusion paradox ①: this entity is a fusion AND at least one source still exists
	var entity := instances[0] as Entity
	if entity.fused_from.size() > 0:
		for e in entities:
			if entity.fused_from.has((e as Entity).uid):
				return true

	# Fusion paradox ②: another entity has absorbed this uid into a fusion
	for e in entities:
		var ent := e as Entity
		if ent.uid != p_uid and ent.fused_from.has(p_uid):
			return true

	return false


## Return uids of all items currently held by the player (holder == 0).
func get_held_items() -> Array[int]:
	var result: Array[int] = []
	for e in entities:
		if (e as Entity).holder == 0:
			result.append((e as Entity).uid)
	return result


## True if a hole at pos is filled (has an underground entity there).
func is_hole_filled(pos: Vector2i) -> bool:
	for e in entities:
		var ent := e as Entity
		if ent.pos == pos and ent.z == -1:
			return true
	return false


## Find the first grounded box at pos (pickup target).
func find_box_at(pos: Vector2i) -> Entity:
	for e in entities:
		var ent := e as Entity
		if ent.pos == pos and ent.type == Enums.EntityType.BOX and ent.is_grounded():
			return ent
	return null


## Get all grounded entities with collision at pos (pushable objects).
func get_blocking_entities_at(pos: Vector2i) -> Array:
	var result: Array = []
	for e in entities:
		var ent := e as Entity
		if ent.pos == pos and ent.collision > 0 and ent.is_grounded():
			result.append(e)
	return result


## True if a grounded box exists at pos.
func has_box_at(pos: Vector2i) -> bool:
	for e in entities:
		var ent := e as Entity
		if ent.type == Enums.EntityType.BOX and ent.pos == pos and ent.is_grounded():
			return true
	return false


## True if a grounded box is on the switch at pos.
func switch_activated(pos: Vector2i) -> bool:
	for e in entities:
		var ent := e as Entity
		if ent.type == Enums.EntityType.BOX and ent.pos == pos and ent.is_grounded():
			return true
	return false


## True if every switch tile has an activating box.
func all_switches_activated() -> bool:
	for pos in terrain:
		if terrain[pos] == Enums.TerrainType.SWITCH:
			if not switch_activated(pos):
				return false
	return true


## Sum of collision volumes of ground-level entities at pos.
func sum_ground_collision_at(pos: Vector2i) -> int:
	var total := 0
	for e in entities:
		var ent := e as Entity
		if ent.pos == pos and ent.z >= 0:
			total += ent.collision
	return total


## Total weight of all entities at pos.
func sum_weight_at(pos: Vector2i) -> int:
	var total := 0
	for e in entities:
		var ent := e as Entity
		if ent.pos == pos:
			total += ent.weight
	return total
