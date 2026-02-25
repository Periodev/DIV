# Godot ↔ Python 主迴圈對齊紀錄

## 問題（修正前）

Godot 的 `update_physics()` + `check_victory()` 原本只在 `_on_state_changed()` 裡呼叫，
也就是「**輸入驅動**」——沒有玩家動作就不跑物理。

Python 版（`game_window.py`）是在 `on_update()` 裡**每幀無條件執行**（時間驅動）。

這個差異目前不會造成 bug，但是一個隱性的架構分歧：
- 若未來有「非輸入觸發的狀態改變」（定時事件、動畫回呼、多步物理 settle），
  Python 版會在下一幀自動處理，Godot 版的物理不會被呼叫，兩版行為會分裂。

## 改動（commit: godot: move update_physics/check_victory to _process() each frame）

檔案：`godot/scripts/GameScene.gd`

- 從 `_on_state_changed()` 移除 `update_physics()` + `check_victory()`
- 搬到 `_process()` 末端，每幀執行，加上與 Python 相同的守衛條件：
  - 物理：`not collapsed and not victory`
  - 勝利：`not victory`（避免重複 emit signal）
- `_on_state_changed()` 簡化為純 immediate redraw（視覺即時響應輸入用）

## 引擎層面等價關係

```
Python on_update()          Godot _process()
─────────────────────────   ─────────────────────────
held_keys → handle_move()   held_keys → handle_move()   ✅
update_physics()            update_physics()             ✅ 已修正
check_victory()             check_victory()              ✅ 已修正
```

引擎架構等價：
- Arcade：events → `on_update()` → `on_draw()`
- Godot：`_input()` → `_process()` → GPU flush

## 已知殘留差異（未處理）

### 1. Tab `switch_focus()` 提交時機（影響最大）

```
Python:  Tab 按下 → 開始 slide 動畫 → 動畫結束時才呼叫 switch_focus()
Godot:   Tab 按下 → 立刻 switch_focus() → 開始 slide 動畫
```

動畫期間 `current_focus` 在兩版是相反值。
目前無害（動畫期間沒有邏輯讀取 focus）。
一旦加入這類功能就必須同步兩版。

### 2. MOVE_DELAY 單位不同（低風險）

```
Python:  MOVE_DELAY = 10 幀  →  10/60 ≈ 167 ms（隨 FPS 浮動）
Godot:   MOVE_REPEAT_DELAY = 0.20 s  →  200 ms（固定）
```

### 3. `_set_initial_facing()` 缺失（Godot 未實作）

Python 在 `__init__` 和 R 重置時讓玩家朝向最近的 grounded box。
Godot `_start_level()` 沒有等效邏輯。
新增依賴初始朝向的設計時須補上。

### 4. merge_preview 的 Tab 交換動畫（Godot 未實作）

Python 在 M 模式下按 Tab 有獨立的 `merge_preview_swap` 動畫，
`switch_focus()` 也是動畫結束後才提交。
Godot 目前直接呼叫 `switch_focus()`，沒有 swap 動畫。

## `_process()` 作為 `on_update()` 替代品的結論

對物理迴圈而言：**成立**。

唯一需要小心的是第 1 點：Tab 的 `switch_focus()` 語意不同，
雙版並進時若碰到「slide 動畫期間的邏輯」，必須同步處理兩版。
