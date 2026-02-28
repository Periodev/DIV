# LevelPreview.gd - Level select preview: thin wrapper around GameRenderer.
# Keeps the same set_state(BranchState) / get_grid_px() interface so
# LevelSelect.gd and level_select.tscn need no changes.
extends GameRenderer
class_name LevelPreview

var map_pixel_size: int = 480


func set_state(state: BranchState) -> void:
	if state == null or state.grid_size <= 0:
		draw_frame(null)
		return
	var cell_size: int = max(1, int(float(map_pixel_size) / float(state.grid_size)))
	var spec := PresentationModel.BranchViewSpec.new()
	spec.state      = state
	spec.cell_size  = cell_size
	spec.scale      = 1.0
	spec.alpha      = 1.0
	spec.is_focused = true
	spec.pos_x      = int(position.x)
	spec.pos_y      = int(position.y)
	draw_frame(spec)


func get_grid_px() -> int:
	if _spec == null or _spec.state == null or _spec.state.grid_size <= 0:
		return 0
	return int(float(_spec.cell_size) * float(_spec.state.grid_size))


# Static preview — no per-frame animation needed.
func _process(_delta: float) -> void:
	pass
