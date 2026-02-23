# LevelSource.gd - Static level configuration (immutable after parse)
# Mirrors Python's LevelSource dataclass in timeline_system.py
class_name LevelSource

var grid_size: int           = 0
var terrain: Dictionary      = {}  # Vector2i -> Enums.TerrainType (int)
var entity_definitions: Dictionary = {}
	# int uid -> Array [Enums.EntityType, Vector2i pos]
var next_uid: int            = 0


## Create a fresh BranchState from this source (called at level start / reset).
## Mirrors Python's init_branch_from_source().
func init_branch() -> BranchState:
	var state := BranchState.new()
	state.terrain   = terrain.duplicate()
	state.grid_size = grid_size
	state.next_uid  = next_uid

	# Instantiate entities sorted by uid (player uid=0 first)
	var uids: Array = entity_definitions.keys()
	uids.sort()
	for p_uid in uids:
		var def: Array  = entity_definitions[p_uid]
		var etype: int  = def[0]
		var epos: Vector2i = def[1]
		var e := Entity.new(p_uid, etype, epos)
		state.entities.append(e)

	return state
