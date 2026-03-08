# Timeline.gd - Pure timeline operations: diverge, merge, fuse, converge
# Mirrors Python's Timeline class in timeline_system.py
class_name Timeline


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

static func _copy_entity(e: Entity) -> Entity:
	return e.copy()


## Priority tuple for dedup: held > grounded > underground.
static func _entity_priority(e: Entity) -> Array:
	return [1 if e.holder != -1 else 0, e.z]


## Pick entity with highest priority from a list.
static func _get_best_entity(instances: Array) -> Entity:
	var best := instances[0] as Entity
	for i in range(1, instances.size()):
		var ent := instances[i] as Entity
		var pb := _entity_priority(best)
		var pe := _entity_priority(ent)
		if pe[0] > pb[0] or (pe[0] == pb[0] and pe[1] > pb[1]):
			best = ent
	return best


## Collect all uids absorbed by any fusion entity (transitively).
static func _absorbed_uid_closure(entities: Array) -> Array:
	var fused_map: Dictionary = {}  # uid -> Array[int]
	var seeds: Array[int] = []

	for e in entities:
		var ent := e as Entity
		if ent.fused_from.size() > 0:
			fused_map[ent.uid] = ent.fused_from.duplicate()
			for f_uid in ent.fused_from:
				seeds.append(f_uid)

	var absorbed: Array[int] = []
	var stack: Array[int] = seeds.duplicate()
	while stack.size() > 0:
		var uid: int = stack.pop_back()
		if absorbed.has(uid):
			continue
		absorbed.append(uid)
		if fused_map.has(uid):
			for child_uid in fused_map[uid]:
				if not absorbed.has(child_uid):
					stack.append(child_uid)
	return absorbed


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

## Diverge: return [main_copy, sub_copy] from a single branch.
static func diverge(branch: BranchState) -> Array:
	return [branch.copy(), branch.copy()]


## Low-level merge: combine entities from focused (main) and non-focused (sub).
## Does NOT settle carried items — call merge_normal() or merge_fetch() instead.
static func merge(main: BranchState, sub: BranchState) -> BranchState:
	var result := BranchState.new()
	result.terrain   = main.terrain.duplicate()
	result.grid_size = main.grid_size
	result.next_uid  = max(main.next_uid, sub.next_uid)

	# Identify held sets
	var main_held: Array[int] = main.get_held_items()
	var sub_held:  Array[int] = sub.get_held_items()

	var both_held: Array[int] = []
	for uid in main_held:
		if sub_held.has(uid):
			both_held.append(uid)

	var sub_only_held: Array[int] = []
	for uid in sub_held:
		if not both_held.has(uid):
			sub_only_held.append(uid)

	# Collect all non-player entities
	var all_entities: Array = []
	for e in main.entities:
		if (e as Entity).uid != 0:
			all_entities.append(e)
	for e in sub.entities:
		var ent := e as Entity
		if ent.uid != 0 and not (both_held.has(ent.uid) and ent.holder == 0):
			all_entities.append(e)

	# Group by (uid, pos, z) — use string key
	var by_group: Dictionary = {}
	for e in all_entities:
		var ent := e as Entity
		var key := "%d|%d|%d|%d" % [ent.uid, ent.pos.x, ent.pos.y, ent.z]
		if not by_group.has(key):
			by_group[key] = []
		by_group[key].append(e)

	# Pick best instance per group
	for group in by_group.values():
		var best  := _get_best_entity(group)
		var copied := _copy_entity(best)

		# Drop sub-exclusive held items at sub player's position
		if sub_only_held.has(copied.uid) and copied.holder == 0 \
		   and copied.pos == sub.get_player().pos:
			copied.holder    = -1
			copied.z         = 0
			copied.collision = 1
			# Skip if main already has this uid grounded at same pos
			var has_dup := false
			for re in result.entities:
				var re_ent := re as Entity
				if re_ent.uid == copied.uid and re_ent.pos == copied.pos and re_ent.z == 0:
					has_dup = true
					break
			if has_dup:
				continue

		result.entities.append(copied)

	# Remove source instances co-located with their fusion entity
	var fusions: Array = []
	for e in result.entities:
		if (e as Entity).fused_from.size() > 0:
			fusions.append(e)

	if fusions.size() > 0:
		var co_located: Dictionary = {}
		for fusion in fusions:
			var f := fusion as Entity
			for fuid in f.fused_from:
				# Include z so only same-layer source instances are removed.
				# A z=0 surface entity must not be swept away by a z=-1 fusion repair trace.
				var key := "%d|%d|%d|%d" % [fuid, f.pos.x, f.pos.y, f.z]
				co_located[key] = true

		var filtered: Array = []
		for e in result.entities:
			var ent := e as Entity
			var key := "%d|%d|%d|%d" % [ent.uid, ent.pos.x, ent.pos.y, ent.z]
			if not co_located.has(key):
				filtered.append(e)
		result.entities = filtered

	# Insert player from focused (main) branch at front
	result.entities.insert(0, _copy_entity(main.get_player()))
	return result


## Normal merge: merge + settle all carried items.
static func merge_normal(main: BranchState, sub: BranchState) -> BranchState:
	var merged := merge(main, sub)
	settle_carried(merged)
	return merged


## Fetch merge: merge + re-assign fetch_uids to player + settle.
static func merge_fetch(main: BranchState, sub: BranchState, fetch_uids: Array) -> BranchState:
	var merged := merge(main, sub)
	for uid in fetch_uids:
		for e in merged.entities:
			if (e as Entity).uid == uid:
				(e as Entity).holder = 0
	settle_carried(merged)
	return merged


## Collapse all instances of target_uid into one (priority: held > target_pos > first).
## Returns the surviving entity.
static func converge(state: BranchState, target_uid: int, target_pos: Vector2i = Vector2i(-1, -1)) -> Entity:
	var instances := state.get_entities_by_uid(target_uid)
	if instances.is_empty():
		return null

	var target: Entity
	# Priority 1: held instance
	var held: Entity = null
	for e in instances:
		if (e as Entity).holder == 0:
			held = e as Entity
			break
	if held != null:
		target = held
	# Priority 2: best instance at target_pos
	elif target_pos != Vector2i(-1, -1):
		var at_pos: Array = []
		for e in instances:
			if (e as Entity).pos == target_pos:
				at_pos.append(e)
		target = _get_best_entity(at_pos) if not at_pos.is_empty() else instances[0] as Entity
	# Priority 3: first instance
	else:
		target = instances[0] as Entity

	# Remove all other instances of this uid
	var kept: Array = []
	for e in state.entities:
		if (e as Entity).uid != target_uid:
			kept.append(e)
	kept.append(target)
	state.entities = kept
	return target


## Check if multiple distinct shadow boxes overlap at pos; if so, fuse them.
## Returns true if fusion occurred.
static func try_fuse(state: BranchState, pos: Vector2i) -> bool:
	# Collect distinct uids at pos (grounded boxes only)
	var seen_uids: Dictionary = {}
	var ordered_uids: Array[int] = []
	for e in state.entities:
		var ent := e as Entity
		if ent.uid != 0 and ent.type == Enums.EntityType.BOX \
		   and ent.pos == pos and ent.is_grounded():
			if not seen_uids.has(ent.uid):
				seen_uids[ent.uid] = true
				ordered_uids.append(ent.uid)

	if ordered_uids.size() < 2:
		return false

	# Don't fuse if entities are already in a fusion-paradox relationship
	var entities_at_pos: Array = []
	for e in state.entities:
		if seen_uids.has((e as Entity).uid):
			entities_at_pos.append(e)
	var already_absorbed := _absorbed_uid_closure(entities_at_pos)
	for uid in already_absorbed:
		if seen_uids.has(uid):
			return false

	# Remove all instances of each fusing uid
	var fused_from: Array[int] = ordered_uids.duplicate()
	var remaining: Array = []
	for e in state.entities:
		if not seen_uids.has((e as Entity).uid):
			remaining.append(e)
	state.entities = remaining

	# Create fusion entity
	var new_uid := state.next_uid
	state.next_uid += 1
	var fusion := Entity.new(new_uid, Enums.EntityType.BOX, pos)
	fusion.collision  = 1
	fusion.weight     = fused_from.size()
	fusion.z          = 0
	fusion.fused_from = fused_from.duplicate()
	state.entities.append(fusion)
	return true


## Resolve fusion paradox: keep the fusion entity, remove its source entities.
static func resolve_fusion_toward_fusion(state: BranchState, _fusion_uid: int) -> void:
	var absorbed := _absorbed_uid_closure(state.entities)
	var kept: Array = []
	for e in state.entities:
		if not absorbed.has((e as Entity).uid):
			kept.append(e)
	state.entities = kept


## Resolve fusion paradox: keep source entities, remove the fusion entity.
static func resolve_fusion_toward_sources(state: BranchState, source_uid: int) -> void:
	var fusion: Entity = null
	for e in state.entities:
		var ent := e as Entity
		if ent.fused_from.size() > 0 and ent.fused_from.has(source_uid):
			fusion = ent
			break
	if fusion == null:
		return
	var kept: Array = []
	for e in state.entities:
		if (e as Entity).uid != fusion.uid:
			kept.append(e)
	state.entities = kept


## After merge, converge all shadow copies of held items to player position.
static func settle_carried(state: BranchState) -> void:
	var held_uids := state.get_held_items()
	if held_uids.is_empty():
		return
	for uid in held_uids:
		var target := converge(state, uid)
		if target == null:
			continue
		target.z         = 1
		target.holder    = 0
		target.collision = 0
		target.pos       = state.get_player().pos
