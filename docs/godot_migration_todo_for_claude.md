# Godot 移植待改動清單（交接給 Claude）

## 目標
- 第二階段目標：讓 Godot 遊戲畫面與 Python 版 `presentation_model.py + render_arc.py` 盡量 1:1。
- 目前狀態：選關畫面已可用（左欄清單 + 右側預覽 + Done 進度）。

## 目前關鍵結論
- Domain 層相容度高（`GameController/BranchState/Timeline` 已基本可用）。
- Presentation 層相容度中低：Godot 目前沒有完整 `FrameViewSpec/BranchViewSpec`，仍是 `GameScene` 直接塞 `renderer` 欄位。
- 要達成 1:1，優先工作是補齊 Presentation Model，而不是先堆 renderer 細節。

---

## P0（先做）

### P0-1 新增 Godot 版 Presentation Model
- 新增檔案：`godot/scripts/PresentationModel.gd`
- 目標：對齊 Python `presentation_model.py` 的核心資料結構與 `build()`。
- 需包含：
1. `InteractionHint`
2. `BranchViewSpec`
3. `FrameViewSpec`
4. `ViewModelBuilder.build(...)`
5. `_calc_slide_positions()`
6. `_calc_merge_preview_positions()`
7. `_calc_merge_preview_swap()`

- 參照來源：`presentation_model.py`

- 驗收：
1. `build()` 能單次輸出完整 frame spec（main/sub 分支、focus、alpha、位置、scale、flash、falling）
2. 不依賴 renderer 內部狀態，純資料輸出

### P0-2 改 `GameScene.gd` 改走 spec 管線
- 修改檔案：`godot/scripts/GameScene.gd`
- 目前：`_update_renderer_layout()` + `_update_renderer_data()` 手動塞欄位。
- 目標：改成每幀產生 `frame_spec`，交給 renderer 一次繪製。

- 需改動：
1. 新增/改寫 `_build_frame_spec()`
2. 保留輸入與 controller 更新，但渲染資料由 spec 驅動
3. 清掉 renderer 逐欄位塞值的分散邏輯

- 驗收：
1. `GameScene` 不再知道 renderer 的細節欄位
2. `renderer.draw_frame(frame_spec)` 成唯一渲染入口

### P0-3 改 `GameRenderer.gd` 對齊 `draw_frame/_draw_branch`
- 修改檔案：`godot/scripts/GameRenderer.gd`
- 目標：先完成「基礎視覺一致」：
1. terrain 色票
2. grid lines
3. box/player 造型與 draw order
4. focused / non-focused 分支位置與比例

- 需改動：
1. 新增 `draw_frame(spec)`
2. 新增 `_draw_branch(spec, ...)`
3. `_draw()` 只吃一份當前 spec，不再直接讀外部散欄位

- 驗收：
1. 未分支 / 分支狀態下，基本布局與 Python 版一致
2. 主要元素（地板、牆、箱子、玩家、格線）視覺接近

---

## P1（第二批）

### P1-1 Merge Preview 動畫與透明層
- 修改檔案：
1. `godot/scripts/GameScene.gd`
2. `godot/scripts/PresentationModel.gd`
3. `godot/scripts/GameRenderer.gd`

- 目標：補齊 `merge_preview_progress`、`merge_preview_swap_progress`、alpha 疊圖邏輯。
- 驗收：
1. `M` 預覽進入/退出有過渡
2. `Tab` 於預覽模式下可 swap
3. 非 focused 分支有正確透明度

### P1-2 Hint 與提示條對齊
- 修改檔案：
1. `godot/scripts/GameRenderer.gd`
2. `godot/scripts/GameController.gd`（必要時）

- 目標：對齊 timeline/diverge/merge/fetch/cell hint 顯示規則。
- 驗收：
1. 單分支時顯示 diverge hint
2. 分支後顯示 merge/fetch 相關 hint
3. focused 格子互動提示位置與顏色正確

### P1-3 位置常數對齊（重要）
- Python 與 Godot 目前中心座標定義不同（會影響 1:1）。
- 修改檔案：
1. `godot/scripts/GameScene.gd`
2. `godot/scripts/PresentationModel.gd`

- 目標：以同一組常數驅動 layout（`CENTER_X/Y`, `LEFT_X`, `RIGHT_X`, `SIDE_Y`）。
- 驗收：
1. 分支前後面板位置與 Python 對齊
2. 切 focus 時滑動軌跡一致

---

## P2（第三批）

### P2-1 進階視覺特效
- 項目：
1. shadow connection 線
2. grounded lock corners
3. fetched hold hint / converge 線
4. merge/fetch indicator UI
5. overlay 文案與提示樣式對齊

- 修改檔案：`godot/scripts/GameRenderer.gd`

### P2-2 視覺回歸驗證
- 新增文件：`docs/godot_render_parity_checklist.md`
- 內容：固定 3~5 個關卡狀態的比對清單（未分支、已分支、持箱、merge preview）。

---

## 建議施工順序（給 Claude）
1. 建 `PresentationModel.gd`（先 DTO + build + slide）
2. 接 `GameScene -> renderer.draw_frame(spec)`
3. 重構 `GameRenderer` 基礎 draw path
4. 補 merge preview 與 hints
5. 補特效與回歸清單

---

## 每次改完必做
1. 編譯檢查：
```bash
D:/Godot/Godot_4.5.1/Godot_v4.5.1-stable_win64.exe --headless --quit --path D:/DIV/DIV_Godot/godot
```
2. 檢查 editor warnings（本專案為 warnings-as-errors）
3. 用同一關卡做 Python/Godot 視覺比對截圖

---

## 已完成（不用重做）
1. 選關畫面重構（左欄 + 右側預覽）
2. 關卡預覽渲染 `LevelPreview.gd`
3. `GameData` 進度儲存與 `Done` 標記
4. 通關時寫入 progress（`GameScene._on_victory`）
