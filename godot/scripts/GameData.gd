# GameData.gd - Global autoload: passes data between scenes
extends Node

var selected_level_idx: int = 0
var all_levels: Array = []   # loaded once, shared between scenes
