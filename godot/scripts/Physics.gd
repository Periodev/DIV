# Physics.gd - Static physics helpers
# Mirrors Python's Physics class in timeline_system.py
class_name Physics


## True if entity is on the ground layer (z == 0).
static func grounded(entity: Entity) -> bool:
	return entity.z == 0


## True if pos is within the grid bounds.
static func in_bound(pos: Vector2i, state: BranchState) -> bool:
	return pos.x >= 0 and pos.x < state.grid_size \
	   and pos.y >= 0 and pos.y < state.grid_size


## Total collision volume at pos (terrain + entities).
## Returns 255 for wall/out-of-bounds, -1 for unfilled hole, 0+ for walkable.
static func collision_at(pos: Vector2i, state: BranchState) -> int:
	var terrain_type: int = state.terrain.get(pos, Enums.TerrainType.FLOOR)

	if terrain_type == Enums.TerrainType.HOLE:
		var terrain_base: int = 0 if state.is_hole_filled(pos) else -1
		return terrain_base + state.sum_ground_collision_at(pos)

	elif terrain_type == Enums.TerrainType.WALL:
		return 255

	elif not in_bound(pos, state):
		return 255

	else:
		var total := 0
		for e in state.entities:
			if (e as Entity).pos == pos:
				total += (e as Entity).collision
		return total


## True if the player's tile has net collision below player's own contribution
## (i.e. the player is falling into a hole).
static func check_fall(state: BranchState) -> bool:
	var player := state.get_player()
	return collision_at(player.pos, state) < player.collision


## Effective carry capacity at pos (0 = NO_CARRY, 1 = normal).
static func effective_capacity(state: BranchState, at_pos: Vector2i = Vector2i(-1, -1)) -> int:
	var pos := at_pos if at_pos != Vector2i(-1, -1) else state.get_player().pos
	var terrain_type: int = state.terrain.get(pos, Enums.TerrainType.FLOOR)
	return 0 if terrain_type == Enums.TerrainType.NO_CARRY else 1


## Run physics step: settle boxes into holes, then check for player fall.
## Returns Enums.PhysicsResult.
static func step(state: BranchState) -> int:
	# 1. Settle holes (loop until stable for chain reactions)
	while true:
		var changed := false
		for e in state.entities:
			var ent := e as Entity
			if ent.type == Enums.EntityType.BOX and ent.z == 0:
				if state.terrain.get(ent.pos, Enums.TerrainType.FLOOR) == Enums.TerrainType.HOLE:
					if not state.is_hole_filled(ent.pos):
						ent.z = -1
						changed = true
		if not changed:
			break

	# 2. Check player fall
	if check_fall(state):
		return Enums.PhysicsResult.FALL

	return Enums.PhysicsResult.OK
