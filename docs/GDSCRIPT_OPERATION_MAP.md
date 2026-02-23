# GDScript 4 操作映射參考 — div 核心遷移用

> 針對 `timeline_system.py`、`game_logic.py`、`game_controller.py`、`map_parser.py` 四個核心檔案，
> 逐項標記 Python 操作在 Godot 4 的可用性。

---

## 一、Godot 4 內建可直接對應（✅ 免重寫）

以下 Python 慣用法在 Godot 4 Array 有原生等價方法，遷移時只需語法轉換。

### 1.1 filter — 列表推導篩選

**Python**
```python
[e for e in self.entities if e.uid == uid]
```

**GDScript 4**
```gdscript
entities.filter(func(e): return e.uid == uid)
```

**出現位置（共 ~12 處）**

| 檔案 | 行號 | 用途 |
|---|---|---|
| timeline_system.py | 86 | `get_entities_by_uid` |
| timeline_system.py | 94 | `get_non_held_instances` |
| timeline_system.py | 108 | `get_held_items` |
| timeline_system.py | 123 | `get_blocking_entities_at` |
| timeline_system.py | 196-197 | `converge` 收集非玩家實體 |
| timeline_system.py | 250 | `converge_one` 篩選目標 uid |
| timeline_system.py | 266 | `converge_one` 移除舊實例 |
| game_logic.py | 107 | `try_drop` 找持有物 |

### 1.2 any / all — 存在/全稱檢查

**Python**
```python
any(e.pos == pos and e.z == -1 for e in self.entities)
all(self.switch_activated(pos) for pos, t in self.terrain.items() if t == TerrainType.SWITCH)
```

**GDScript 4**
```gdscript
entities.any(func(e): return e.pos == pos and e.z == -1)

# all 需要先 filter terrain 再 all（因為 dict 沒有 all，要轉 Array）
var switches = terrain.keys().filter(func(p): return terrain[p] == TerrainType.SWITCH)
switches.all(func(p): return switch_activated(p))
```

**出現位置（共 ~6 處）**

| 檔案 | 行號 | 用途 |
|---|---|---|
| timeline_system.py | 112 | `is_hole_filled` — any |
| timeline_system.py | 130 | `has_box_at` — any |
| timeline_system.py | 137 | `switch_activated` — any |
| timeline_system.py | 144 | `all_switches_activated` — all |

⚠️ **注意**：`all_switches_activated` 原本在 `dict.items()` 上做 all + filter，GDScript 需要拆成兩步。

### 1.3 reduce / sum — 累加

**Python**
```python
sum(e.collision for e in self.entities if e.pos == pos and e.z >= 0)
```

**GDScript 4**
```gdscript
entities.filter(func(e): return e.pos == pos and e.z >= 0) \
        .reduce(func(acc, e): return acc + e.collision, 0)
```

**出現位置（共 ~4 處）**

| 檔案 | 行號 | 用途 |
|---|---|---|
| timeline_system.py | 150 | `sum_ground_collision_at` |
| timeline_system.py | 155 | `sum_weight_at` |
| timeline_system.py | 302 | `collision_at` 內 entity_sum |

### 1.4 map — 映射轉換

**Python**
```python
[e.uid for e in self.entities if e.holder == 0]
```

**GDScript 4**
```gdscript
entities.filter(func(e): return e.holder == 0).map(func(e): return e.uid)
```

**出現位置**：`get_held_items`（timeline_system.py:108）

### 1.5 sort_custom — 自訂排序

**Python**
```python
for uid in sorted(source.entity_definitions.keys()):
```

**GDScript 4**
```gdscript
var keys = entity_definitions.keys()
keys.sort()
for uid in keys:
```

**出現位置**：`init_branch_from_source`（timeline_system.py:391）

### 1.6 Dictionary.duplicate() — 淺拷貝

**Python**
```python
self.terrain.copy()
```

**GDScript 4**
```gdscript
terrain.duplicate()
```

**出現位置（共 ~4 處）**：BranchState.copy()、converge()、init_branch_from_source

✅ terrain 的值是 Enum（整數），不可變，淺拷貝安全。

### 1.7 lambda + sort_custom

**Python**
```python
max(instances, key=Timeline._entity_priority)
```

**GDScript 4** — 用 reduce 模擬（見下方「需重寫」章節）

---

## 二、需手寫 Utility（⚠️ 約 40 行）

以下操作 Godot 4 無內建，但可用簡短 helper 覆蓋。

### 2.1 find_first — 找第一個符合條件的元素

**Python**
```python
next((e for e in self.entities if e.pos == pos and ...), None)
```

**GDScript 4 無等價**。建議封裝：

```gdscript
# ArrayUtil.gd
static func find_first(arr: Array, predicate: Callable) -> Variant:
    for e in arr:
        if predicate.call(e):
            return e
    return null
```

**出現位置（共 5 處）**

| 檔案 | 行號 | 用途 |
|---|---|---|
| timeline_system.py | 116 | `find_box_at` |
| timeline_system.py | 255 | `converge_one` 找 held |
| timeline_system.py | 260 | `converge_one` 找 at_pos |

### 2.2 Set 建構與操作

**Python**
```python
positions = {e.pos for e in instances}          # set comprehension
sub_held_uids = set(sub.get_held_items())       # list → set
focused_held | other_held                        # union
after_underground - before_underground           # difference
focused_held != other_held                       # inequality
```

**GDScript 4 無原生 Set**。建議封裝：

```gdscript
# SetUtil.gd — 用 Dictionary 模擬 Set
static func from_array(arr: Array) -> Dictionary:
    var s = {}
    for v in arr:
        s[v] = true
    return s

static func union(a: Dictionary, b: Dictionary) -> Dictionary:
    var result = a.duplicate()
    for k in b:
        result[k] = true
    return result

static func difference(a: Dictionary, b: Dictionary) -> Dictionary:
    var result = {}
    for k in a:
        if not b.has(k):
            result[k] = true
    return result

static func equals(a: Dictionary, b: Dictionary) -> bool:
    if a.size() != b.size():
        return false
    for k in a:
        if not b.has(k):
            return false
    return true
```

**出現位置（共 ~10 處）**

| 檔案 | 行號 | 操作 |
|---|---|---|
| timeline_system.py | 102 | `is_shadow` — set comprehension 去重 |
| timeline_system.py | 193 | `converge` — list → set |
| timeline_system.py | 273 | `settle_carried` — list → set |
| game_controller.py | 153 | `update_physics` — set comprehension |
| game_controller.py | 161 | `update_physics` — set difference |
| game_controller.py | 244-245 | `can_show_inherit_hint` — list → set |
| game_controller.py | 251 | — set union |
| game_controller.py | 264-266 | `_merge_branches` — set + union |
| game_controller.py | 270 | — set union 取繼承清單 |
| game_controller.py | 477-481 | `get_timeline_hint` — set 比較 |

### 2.3 group_by — 按 key 分組

**Python**
```python
by_uid_pos: Dict[Tuple[int, Position], List[Entity]] = {}
for e in all_entities:
    key = (e.uid, e.pos)
    by_uid_pos.setdefault(key, []).append(e)
```

**GDScript 4 無 setdefault**。建議封裝：

```gdscript
# ArrayUtil.gd
static func group_by(arr: Array, key_fn: Callable) -> Dictionary:
    var groups = {}
    for item in arr:
        var k = key_fn.call(item)
        if not groups.has(k):
            groups[k] = []
        groups[k].append(item)
    return groups
```

**出現位置**：`Timeline.converge`（timeline_system.py:200-203）— 合併核心邏輯

### 2.4 max with key — 帶優先級的最大值

**Python**
```python
best = max(instances, key=Timeline._entity_priority)
```

其中 `_entity_priority` 回傳 tuple `(bool, int)` 利用 Python 的 tuple lexicographic 比較。

**GDScript 4 無 max(key=)**。建議封裝：

```gdscript
# ArrayUtil.gd
static func max_by(arr: Array, key_fn: Callable) -> Variant:
    var best = arr[0]
    var best_key = key_fn.call(best)
    for i in range(1, arr.size()):
        var k = key_fn.call(arr[i])
        if k > best_key:
            best = arr[i]
            best_key = k
    return best
```

⚠️ **關鍵陷阱**：Python 的 `(True, 0) > (False, 1)` 是合法的 tuple 比較。
GDScript 的 Array 比較行為不同（`[true, 0] > [false, 1]` 不保證相同語意）。
建議改為回傳 int 優先級值：`held*10 + z` 避免歧義。

**出現位置**：`Timeline.converge`（timeline_system.py:207）

---

## 三、資料模型映射

### 3.1 Position 型別

| Python | GDScript 4 |
|---|---|
| `Tuple[int, int]` | `Vector2i` |
| `(px + dx, py + dy)` | `pos + dir` (Vector2i 支援加法) |
| `(0, -1)` 方向常量 | `Vector2i.UP` 等 |

✅ 遷移後大量簡化——所有 `(x, y)` 元組運算改為向量運算。

### 3.2 Entity

| Python | GDScript 4 |
|---|---|
| `@dataclass class Entity` | `class Entity extends RefCounted` 或 `Resource` |
| `Optional[int] = None` | `holder: int = -1`（用 -1 哨兵值）|
| 欄位預設值 | `_init()` 建構子 |

```gdscript
class_name Entity extends RefCounted

var uid: int
var type: int  # EntityType enum
var pos: Vector2i
var collision: int = 1
var weight: int = 1
var z: int = 0
var holder: int = -1  # -1 = no holder, 0 = player
var direction: Vector2i = Vector2i.DOWN

func duplicate_entity() -> Entity:
    var e = Entity.new()
    e.uid = uid; e.type = type; e.pos = pos
    e.collision = collision; e.weight = weight
    e.z = z; e.holder = holder; e.direction = direction
    return e
```

### 3.3 Enum

| Python | GDScript 4 |
|---|---|
| `class EntityType(Enum): PLAYER = "player"` | `enum EntityType { PLAYER, BOX }` |
| `TerrainType.WALL` | `TerrainType.WALL` |
| Enum 有 string value | GDScript enum 是 int，需另建 `TERRAIN_CHARS` dict 做 char↔enum 對應 |

```gdscript
enum TerrainType { FLOOR, WALL, SWITCH, NO_CARRY, BRANCH1, BRANCH2, BRANCH3, BRANCH4, GOAL, HOLE }

const TERRAIN_CHAR_MAP: Dictionary = {
    ".": TerrainType.FLOOR,
    "#": TerrainType.WALL,
    "S": TerrainType.SWITCH,
    # ...
}
```

### 3.4 BranchState.copy()

| Python | GDScript 4 |
|---|---|
| 手動逐 entity 複製 | 同樣需手動——`Array.duplicate()` 是淺拷貝，entity 是 RefCounted 需逐個 `.duplicate_entity()` |

```gdscript
func copy() -> BranchState:
    var new_state = BranchState.new()
    new_state.terrain = terrain.duplicate()  # 淺拷貝安全（enum 值不可變）
    new_state.grid_size = grid_size
    new_state.entities = entities.map(func(e): return e.duplicate_entity())
    return new_state
```

### 3.5 @staticmethod → static func

一對一對應，無語意差異。

```gdscript
class_name Timeline

static func diverge(branch: BranchState) -> BranchState:
    return branch.copy()
```

### 3.6 @property → get

```gdscript
var player: Entity:
    get:
        return entities[0]
```

---

## 四、其他零星映射

| Python | GDScript 4 | 出處 |
|---|---|---|
| `import time; time.time()` | `Time.get_ticks_msec() / 1000.0` | game_controller.py 動畫計時 |
| `dict.get(key, default)` | `terrain.get(pos, TerrainType.FLOOR)` — ✅ GDScript Dictionary 也有 `.get(key, default)` | 多處 |
| `dict.items()` | `for key in dict: var val = dict[key]` 或 Godot 4.4+ 可能有改進 | timeline_system.py:145 |
| `str.strip().split('\n')` | `string.strip_edges().split("\n")` | map_parser.py |
| `len(line)` | `line.length()` | map_parser.py |
| `enumerate(lines)` | `for y in lines.size(): var line = lines[y]` | map_parser.py |
| `line.rstrip()` | `line.strip_edges(false, true)` | map_parser.py |
| `List[str]` 型別提示 | `Array[String]` | 各處 |
| `x in dict` | `dict.has(x)` | 各處 |

---

## 五、遷移優先級建議

### 第一步：建立 Utility（開工前完成）

建立 `utils/array_util.gd` 和 `utils/set_util.gd`，共約 40 行：

- `find_first(arr, predicate)` → 5 處依賴
- `SetUtil.from_array / union / difference / equals` → 10 處依賴
- `group_by(arr, key_fn)` → 1 處依賴（但是合併核心）
- `max_by(arr, key_fn)` → 1 處依賴（但是合併核心）

### 第二步：Entity / BranchState 資料模型

- Entity class + `duplicate_entity()`
- BranchState class + `copy()` 使用 `entities.map()`
- Enum 定義 + TERRAIN_CHAR_MAP

### 第三步：直接轉換區（佔比最大，但最機械化）

所有 `filter` / `any` / `all` / `reduce` 的使用處，語法轉換即可。

### 第四步：重點審查區

- `Timeline.converge()` — group_by + max_by + set 操作的組合
- `Timeline._entity_priority()` — tuple 比較語意轉換
- `Physics.step()` — while loop 收斂（邏輯不變，但需測試）
- `GameController.update_physics()` — set difference 偵測新落坑

---

## 六、不需遷移的部分

| 項目 | 原因 |
|---|---|
| `render_arc.py` | 整個替換為 Godot Node2D/Sprite 渲染 |
| `game_window.py` | 替換為 Godot Scene/Input 系統 |
| `presentation_model.py` | 重新設計為 Godot 的 presentation layer |
| `level_selector.py` | 替換為 Godot UI |
| solver / replay 工具 | 短期保留 Python 版，透過 JSON 互通 |
