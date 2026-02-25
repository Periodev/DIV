# Enums.gd - Game-wide enum definitions and terrain utilities
class_name Enums

enum EntityType {
	PLAYER = 0,
	BOX    = 1,
}

enum TerrainType {
	FLOOR    = 0,
	WALL     = 1,
	SWITCH   = 2,
	NO_CARRY = 3,
	BRANCH1  = 4,  # v  1 use remaining
	BRANCH2  = 5,  # V  2 uses remaining
	BRANCH3  = 6,  # x  3 uses remaining
	BRANCH4  = 7,  # X  4 uses remaining
	GOAL     = 8,
	HOLE     = 9,
}

enum PhysicsResult {
	OK   = 0,
	FALL = 1,
}

# ASCII character -> TerrainType (for map parsing)
const CHAR_TO_TERRAIN: Dictionary = {
	"#": TerrainType.WALL,
	" ": TerrainType.WALL,
	"v": TerrainType.BRANCH1,
	"V": TerrainType.BRANCH2,
	"x": TerrainType.BRANCH3,
	"X": TerrainType.BRANCH4,
	"G": TerrainType.GOAL,
	"H": TerrainType.HOLE,
	"S": TerrainType.SWITCH,
	"c": TerrainType.NO_CARRY,
}

# Branch point decrement when used (BRANCH4->3->2->1->FLOOR)
const BRANCH_DECREMENT: Dictionary = {
	TerrainType.BRANCH4: TerrainType.BRANCH3,
	TerrainType.BRANCH3: TerrainType.BRANCH2,
	TerrainType.BRANCH2: TerrainType.BRANCH1,
	TerrainType.BRANCH1: TerrainType.FLOOR,
}

const BRANCH_TERRAINS: Array = [
	TerrainType.BRANCH1,
	TerrainType.BRANCH2,
	TerrainType.BRANCH3,
	TerrainType.BRANCH4,
]

# Charges awarded when stepping onto a branch tile (collected all at once)
const BRANCH_CHARGE: Dictionary = {
	TerrainType.BRANCH1: 1,
	TerrainType.BRANCH2: 2,
	TerrainType.BRANCH3: 3,
	TerrainType.BRANCH4: 4,
}
