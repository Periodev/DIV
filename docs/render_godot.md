根據先前對 GameRenderer.gd 的 review，以下是 Godot 化渲染的待辦清單：

  ---
  渲染 Godot 化待辦事項

  🔴 高優先（架構問題）

  1. 動畫狀態移出 GameController
    - 目前：falling_boxes、failed_action_pos 存在 GameController 裡
    - 目標：改用 Tween 節點在 renderer 層處理，控制器只管邏輯狀態
  2. 文字改用 Label 節點
    - 目前：draw_string() 手動計算字體 ascent、座標偏移
    - 目標：用 Label / RichTextLabel 節點，讓 Godot UI 系統管理排版

  ---
  🟡 中優先（效能 / 可維護性）

  3. 地形改用 TileMapLayer
    - 目前：每幀重繪所有格子（7×7 = 49 次 draw_rect）
    - 目標：用 TileMapLayer，只在地形實際變更時更新（dirty flag）
  4. 實體改用 Sprite2D 節點
    - 目前：draw_rect 畫方塊
    - 目標：用 Sprite2D 節點，支援動畫、旋轉、縮放，方便之後加素材
  5. 提示 UI 改用 Control 節點
    - 目前：HintOverlay 在 _draw() 裡做全域座標換算
    - 目標：改成 CanvasLayer + Control 節點，座標系統清楚不混亂

  ---
  🟢 低優先（視覺細節）

  6. 方向箭頭改用 Sprite2D + 旋轉
    - 目前：多邊形手算頂點畫箭頭
    - 目標：一張箭頭圖片 + rotation 屬性，更容易換美術素材

  ---
  🔴 動畫專項（下一批實作）

  7. 收束線（Converge / Shadow Connection）
    - 目前：虛線偏移靠 animation_frame，更新頻率低，視覺偏跳格
    - 目標：改成連續時間驅動（每幀捲動），並保留跨空間禁畫規則
  8. 抓取線（Fetch Line）
    - 目前：僅 merge preview 下畫線，動態感不足
    - 目標：加連續流動效果，並和收束線節奏一致
  9. 物件掉落坑（Fall Into Hole）
    - 目前：只有位移 + padding 變化
    - 目標：補透明度/尺寸過渡，讓「落入」感更明顯
  10. 疊圖（同格多箱顯示）
    - 目前：僅文字合併標籤，方塊本體完全重疊
    - 目標：同格實體加偏移與縮放分層，避免資訊被遮住

  ---
  以上項目可依優先順序逐步重構，不需一次全部完成。
