# Entity.gd - Runtime game entity (player or box)
# Mirrors Python's Entity dataclass in timeline_system.py
class_name Entity

var uid: int       = 0
var type: int      = Enums.EntityType.PLAYER  # Enums.EntityType
var pos: Vector2i  = Vector2i.ZERO
var collision: int = 1
var weight: int    = 1
var z: int         = 0       # -1=underground, 0=ground, 1=held
var holder: int    = -1      # -1=not held, 0=held by player
var direction: Vector2i = Vector2i(0, 1)  # downward default
var fused_from: Array[int] = []           # uids of absorbed entities


func _init(
	p_uid: int  = 0,
	p_type: int = Enums.EntityType.PLAYER,
	p_pos: Vector2i = Vector2i.ZERO
) -> void:
	uid  = p_uid
	type = p_type
	pos  = p_pos


## Returns true if entity is on the ground layer (not held, not underground).
func is_grounded() -> bool:
	return z == 0


## Deep copy this entity.
func copy() -> Entity:
	var e := Entity.new(uid, type, pos)
	e.collision   = collision
	e.weight      = weight
	e.z           = z
	e.holder      = holder
	e.direction   = direction
	e.fused_from  = fused_from.duplicate()
	return e
