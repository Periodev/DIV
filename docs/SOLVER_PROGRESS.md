# Solver 開發進度報告

## 專案背景

這是一個具有**時間線分裂/合併**機制的解謎遊戲 solver。玩家可以在特定格子分裂成兩條時間線（主/副分支），分別操控兩個版本的角色，最後合併達成目標。

## 遊戲動作集

| 字元 | 動作 |
|------|------|
| U/D/L/R | 移動（含兩步轉向機制：面對箱子或持物時，第一次轉向，第二次才移動） |
| V | 分裂（在分裂點地形上才有效） |
| C | 普通合併 |
| I | 繼承合併（箱子跟著焦點玩家） |
| T | 切換焦點（主↔副分支） |
| X | 自適應動作（持物→放下；面對影子→收束；面對實體→拾取） |
| P | 拾取 |
| O | 放下 |

## 已實作的 Solver 架構

### 核心模組
- `solver_core.py` — BFS 核心邏輯
- `solver.py` — CLI 入口（`python solver.py <level_id> [max_depth]`）
- `replay_core.py` — 共用的 `execute_action()` 函數與 `Replayer` 類別
- `replay.py` — 可視化重播工具

---

## 優化歷程

### 階段一：noop 剪枝（成功）

在狀態複製之前先預判無效動作：

| 剪枝規則 | 說明 |
|----------|------|
| `can_move` 牆壁/邊界/容量檢查 | 移動前先驗證合法性 |
| V 需站在分裂點地形 | `terrain not in BRANCH_DECREMENT` |
| T/C/I 需已分裂 | `not has_branched` |
| T→T 連續 | 兩次切換焦點等於 noop |
| V→T 連續 | 分裂後兩盤面必然相同，T 為 noop（見階段四修正） |
| V→C/I 連續 | 分裂後立刻合併（terrain 已遞減但無實質進展） |
| 反向移動（無推箱） | L 後立刻 R，若沒有箱子被推過則必定回到已 visited 狀態 |
| X/P/O 完整預檢查 | 前方無目標、持物狀態不符等情況直接略過 |
| I 等效於 C | 若 other branch 無持物，fetch merge 結果與 normal merge 相同 |

### 階段二：嘗試 A*（失敗，原因已分析）

#### 嘗試 1：GBFS
- 太貪心，解法需要先繞路設置分支，GBFS 把這些必要狀態排到最後，漏解。

#### 嘗試 2：A*（mark-when-pushed + 不一致啟發函數）
- `h = Manhattan(active_player, GOAL)`
- T 動作讓 h 劇烈跳動，違反一致性（主分支距 GOAL=5、副分支距 GOAL=1，T 後 h 從 5 降到 1，但 5 > 1+1）。不一致啟發函數導致漏解。

#### 嘗試 3：A*（mark-when-popped）
- 同樣的根本問題：狀態被長路徑版本先展開，剩餘深度不足。

#### 嘗試 4：一致啟發函數 `h = min(dist_main, dist_sub)`
- T 動作不改變 min，一致性成立。但 h 太弱，不反映 switch 狀態，退化為 BFS + heap overhead。

**結論：Manhattan 距離系列啟發函數對本遊戲無效，解法結構與「往 GOAL 前進」方向不一致。回退純 BFS。**

### 階段三：Opus 重構（大幅提速）

Opus 對 `solver_core.py` 進行深度重構，主要改進：

**1. 狀態表示優化**

- `_canonical_direction(b)`：當玩家附近無箱子且未持物時，方向歸一化為 `(0, 0)`，消除無意義的方向差異造成的狀態爆炸。
- `_state_key()` 正規化：分裂狀態下，若 `main_key > sub_key` 則交換並翻轉 focus，讓 `(A, B, focus=0)` 與 `(B, A, focus=1)` 被視為同一狀態，消除主/副分支標籤的任意性。

**2. 動作生成優化**

- `_legal_actions_for_state()`：按當前狀態動態生成合法動作集，而非靜態地生成所有可能動作再用 `_is_noop` 過濾。X/P/O 僅在前方有有效目標時才加入候選。

**3. 複製效率**

- `ctrl.clone_for_solver()` 取代 `copy.deepcopy(ctrl)`，大幅降低每個節點的複製成本。

### 階段四：V→T 剪枝的正確分析與還原

**核心命題**：V 分裂後，兩個分支是完全相同的複製（`Timeline.diverge` 做兩次 `branch.copy()`）。`is_shadow()` 在單一分支內計算，分裂後每個 uid 在各自分支只有一個實例，因此：

```
_branch_key(main) == _branch_key(sub)   ← V 後永遠相等
```

加上 `_state_key()` 正規化：當 `main_key == sub_key` 時，`focus_key` 強制為 0，所以：
- V 後 focus=0 的 state key = `(K, K, 0, True)`
- V→T 後 focus=1 的 state key = `(K, K, 0, True)`（相同）

V→T 被 visited set 正確去重，`if last_action == 'V': return True` 是**冗餘但正確**的剪枝，而非 bug。

**Opus 重構時曾錯誤移除此行**，理由是「main 持有 real、sub 持有 shadow，branch_key 不等」—— 這個分析是錯的。實際的 600x 加速來自其他重構（canonical_direction、state_key 正規化、clone_for_solver），與 V→T 行本身無關。

**最終狀態**：還原此行，並附上正確說明：
```python
if last_action == 'V':
    return True  # 分裂後兩盤面相同，T 為 noop（由 state_key 正規化保證）
```

---

## 最終測試結果

### 1-6 Triple 對比

| 版本 | 時間 | 探索狀態數 |
|------|------|-----------|
| 舊版（Opus 重構前） | **11795s（3.3小時）** | 425,000+ |
| 新版（Opus 重構） | **19.6s** | 65,000 |
| 加速倍數 | **600x** | — |

### 所有關卡結果（最新版本）

| 關卡 | 名稱 | 解 | 步數 | 時間 |
|------|------|----|------|------|
| 0-1 | Move | `UUURRRRRDDD` | 11 | <0.1s |
| 0-4 | Diverge | `RVRTURRDDC` | 10 | ~2s |
| 0-5 | Multitask | `VDTLDRRLC` | 9 | ~6s |
| 0-6 | Shadow | `VDRRTRDDRDC` | 11 | ~8s |
| 0-7 | Converge | `RVRRCLXLLRRRR` | 13 | ~6s |
| 1-3 | 2nd Diverge | `UVDLLLCDLVRURXRTRULXRRUCDXD` | 27 | ~數分鐘 |
| 1-4 | Crossroad | `DVUULLCVRXRUCDXDR` | 17 | 7.5s |
| 1-5 | 2nd Converge | `UVDLLLCVRXRTXRRUCDXD` | 20 | ~12s |
| 1-6 | Triple | `RRDDLLVDRRTUCVRRDXRDLLTDDC` | **26**（比人類解短4步） | **~12s** |

---

## 階段五：Fusion 悖論機制（遊戲端）

### 背景

原本 fusion（兩個 shadow 箱子重疊後合體）在遊戲中已存在，但屬於「操作失誤」的副產物，出現即視為失敗。設計上考慮將其改良為可玩的悖論機制。

### 新機制設計

**悖論語意**：在某一分支中造出 fusion 後合併，fusion 是來源的「合體殘影」。只要來源仍存在於其他位置，fusion 本身即符合殘影（shadow）定義，雙方都需透過 X 收束才能成為實體。

```
V 分裂 → sub 分支造出 fusion(1+2) → C 合併
→ 場上：fusion(1+2) @ posC（shadow），uid1 @ posA（shadow），uid2 @ posB（shadow）
→ 面向 fusion，X → 保留 fusion（uid1/uid2 消除）
→ 面向 uid1，X → 保留來源（fusion 消除）
```

### 實作改動

**`timeline_system.py`**
- `BranchState.is_shadow()`：新增兩個 fusion paradox 條件：
  - ① 這個 entity 是 fusion 且至少一個來源 uid 仍存在
  - ② 有 fusion 包含此 uid，且該 fusion 仍存在
- `Timeline.converge()`：移除 `_absorbed_uid_closure` 過濾，保留全部 entity（fusion + 來源共存）；新增 co-located 清理：fusion 所在格的來源 shadow 實例移除（只保留非同格的來源作為悖論殘影）
- `Timeline.try_fuse()`：新增 absorbed 關係檢查，若位置上的 uid 之間已有包含關係則不建新 fusion（防止誤建 meta-fusion）
- `Timeline.resolve_fusion_toward_fusion()`：新增，保留 fusion、移除來源
- `Timeline.resolve_fusion_toward_sources()`：新增，保留來源、移除 fusion

**`game_controller.py`**
- `handle_adaptive_action()`：X 動作新增 fusion paradox 分支判斷：面向 fusion → 保留 fusion；面向來源 → 保留來源

**`render_arc.py`**
- Fusion 顯示格式統一改為 `1+2`（原本 2-fusion 顯示 `?`，3+-fusion 才顯示 uid 組合，現一律一致）

### Bug 修正過程

**Bug 1**：`try_fuse` 誤建 meta-fusion
當 `uid5(fused_from={1,2})` 和 `uid1` 在同格時，`try_fuse` 看到兩個不同 uid 而創出 `uid6(fused_from={5,1})`，顯示成 `1+5`。
**修法**：`try_fuse` 呼叫 `_absorbed_uid_closure` 檢查，若位置上的 uid 已有包含關係則 return False。

**Bug 2**：co-located shadow 殘留
初始狀態 `uid1@pos1, uid1@pos3, uid2@pos2, uid2@pos3`（兩個 shadow），div0 在 pos3 收束成 `uid3(1+2)`，div1 不動，merge 後 pos3 出現 `uid1+uid2+uid3` 三個 entity。
**修法**：`converge()` 新增 co-located 清理，fusion 所在格的直接來源 uid 實例移除。

### Solver 端處理

Fusion 屬於當前難度的「失敗狀態」，solver 看到任何 entity 帶有 `fused_from` 即剪枝：

```python
active = new_ctrl.get_active_branch()
if any(e.fused_from for e in active.entities):
    continue
```

未來若設計含 fusion 解法的關卡，可透過 hints 控制此行為。

---

## 下一步方向

### 規則類剪枝（待實作）

**死局偵測（影響最大）**
- 方塊推入無法離開的死角（兩面或三面夾牆且無目標）
- 需要遊戲領域知識

### 更根本的搜尋改良

- **IDA\***：記憶體效率高，適合深度解
- **雙向 BFS**：深度砍半，但終態定義複雜

---

## 關鍵程式碼位置

- `solver_core.py` — `_state_key()`, `_canonical_direction()`, `_is_noop()`, `_legal_actions_for_state()`, `solve()`
- `game_controller.py` — `try_branch()`, `switch_focus()`, `_merge_branches()`, `check_victory()`, `clone_for_solver()`, `handle_adaptive_action()`
- `game_logic.py` — `can_move()`, `execute_move()`
- `timeline_system.py` — `BranchState.is_shadow()`, `Timeline.converge()`, `Timeline.try_fuse()`, `Timeline.resolve_fusion_toward_fusion/sources()`
- `render_arc.py` — fusion 顯示格式
- `level_constructor.py` — `MAIN_LEVELS`（含 hints 欄位）

