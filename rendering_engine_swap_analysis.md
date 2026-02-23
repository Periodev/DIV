# 渲染模組與主程式耦合度分析

## 目前架構（3 層）

- Layer 1: `game_controller.py` + `timeline_system.py` 負責規則與狀態演進。
- Layer 2: `presentation_model.py`（`ViewModelBuilder`）把控制器狀態轉成 `FrameViewSpec` / `BranchViewSpec`。
- Layer 3: `renderer.py` 只吃 `FrameViewSpec` 並繪製。

## 渲染模組「需要知道多少主程式資訊」

### 理想狀態

渲染器只需要知道「視覺規格（ViewSpec）」，不需要直接依賴 `GameController`、`GameLogic`。

### 此專案目前狀態

- 優點：`game_main.py` 先呼叫 `ViewModelBuilder.build(...)`，再 `renderer.draw_frame(frame_spec)`，主流程已採用資料驅動渲染。
- 仍有耦合：`BranchViewSpec.state` 仍直接攜帶 `BranchState`；`renderer.py` 也直接 import `timeline_system` 的 `TerrainType`、`EntityType`、`BranchState`。

=> 結論：目前是「中度解耦」，不是完全解耦。

## 對抽換渲染引擎的差別

### A. 高耦合（渲染器直接讀 Controller / Domain）

- 影響：更換 Pygame -> Godot/Unity/WebGL 時，要重寫大量與規則結構綁死的程式。
- 成本：高。
- 風險：測試難、回歸風險大。

### B. 中耦合（目前做法：有 ViewModel 但仍帶 Domain 狀態）

- 影響：可替換，但新引擎仍要理解 `BranchState` / `TerrainType`。
- 成本：中。
- 風險：視覺層被 Domain 型別變動牽動。

### C. 低耦合（純 ViewSpec DTO，不暴露 Domain）

- 影響：更換引擎時，只要重寫「渲染適配器」，遊戲規則層幾乎不動。
- 成本：低到中。
- 風險：主要在初期建立完整 ViewSpec 的工作量。

## 若要移植到 Godot，需要改哪些模組

### 必改（直接與 Pygame 綁定）

1. `renderer.py`
   - 全部重寫成 Godot 視覺節點/腳本（例如 `Node2D`、`TileMap`、`Label`、`CanvasLayer`）。
   - `draw_*` 系列函式改成「更新節點狀態」而非逐幀 `pygame.draw`。

2. `game_main.py`
   - 拆掉 Pygame event loop（`pygame.event`, `clock.tick`, `display.flip`）。
   - 改由 Godot `_process/_physics_process` + `_input` 驅動。
   - `run_game(...)` 的啟動責任改交給 Godot 場景生命週期。

3. 輸入與時間來源
   - 目前直接使用 `pygame.KEYDOWN/KEYUP`、`pygame.time.get_ticks()`。
   - Godot 需改為 `Input.is_action_pressed()`、`InputEvent`、`Time.get_ticks_msec()`（或等價 API）。

### 建議改（降低未來維護成本）

4. `presentation_model.py`
   - 把 `BranchViewSpec.state` 由 `BranchState` 改為純渲染 DTO（tile/entity/player 陣列）。
   - 讓 Godot 與 Pygame（或其他引擎）都吃同一份視覺契約。

5. `game_controller.py`（小幅）
   - 保持邏輯不變，但可把「提示文字/顏色」與輸入語意抽象化，減少 UI/引擎字串耦合。

### 可沿用（理論上不需改邏輯）

6. `timeline_system.py`, `game_logic.py`, `map_parser.py`
   - 這些是規則、物理、資料解析層，與渲染後端無關。
   - 只要介面不改，應可直接重用。

## Godot 遷移路徑（建議順序）

1. 先凍結 `FrameViewSpec` 契約（先做資料契約，再做畫面）。
2. 建立 `godot_renderer`（先只畫地板/牆/玩家/箱子，不做特效）。
3. 接上輸入與主循環（移動、互動、分裂/合併）。
4. 補齊 UI（tutorial、hint、merge progress、overlay）。
5. 最後補動畫與視覺效果（閃爍、虛線、ghost、outline）。

## 轉換效益

- 引擎抽換：從「重寫+重構」降低為「重寫 renderer adapter」。
- 維護性：規則改動不易波及渲染。
- 測試：可做 ViewSpec snapshot 測試，減少依賴實際圖形後端。
