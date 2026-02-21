# DIV Timeline Puzzle - 打包說明

## 快速打包

### 方法 1: 使用批處理文件（推薦）

1. 雙擊運行 `build_exe.bat`
2. 等待打包完成
3. 可執行文件位於 `dist\DIV-Timeline-Puzzle.exe`

### 方法 2: 手動打包

1. 安裝 PyInstaller：
   ```bash
   pip install pyinstaller
   ```

2. 運行打包命令：
   ```bash
   pyinstaller DIV.spec
   ```

3. 可執行文件位於 `dist\DIV-Timeline-Puzzle.exe`

## 打包選項說明

### 當前配置（單文件模式）
- **單一執行檔**：所有內容打包成一個 .exe 文件
- **無控制台窗口**：只顯示遊戲窗口
- **包含所有依賴**：arcade, pyglet 等

### 如果需要修改打包方式

編輯 `DIV.spec` 文件：

**顯示控制台（用於調試）**
```python
console=True  # 改為 True
```

**文件夾模式（啟動更快）**
修改 `DIV.spec` 中的 EXE 部分，移除 `a.binaries, a.zipfiles, a.datas`

## 發布

打包完成後，發布以下文件：
- `dist\DIV-Timeline-Puzzle.exe` - 主程序

用戶首次運行後會自動創建：
- `progress.json` - 進度記錄文件

## 文件大小

預期大小：約 30-50 MB（包含 Python 運行時和所有庫）

## 故障排除

### 問題：打包失敗
解決：
1. 確保已安裝所有依賴：`pip install arcade pyglet pillow`
2. 更新 PyInstaller：`pip install --upgrade pyinstaller`

### 問題：exe 運行時出錯
解決：
1. 使用控制台模式打包查看錯誤信息（設置 `console=True`）
2. 檢查是否缺少隱藏導入（在 spec 文件中添加）

### 問題：文件太大
解決：
1. 使用 UPX 壓縮（已啟用）
2. 使用文件夾模式而非單文件模式
3. 排除不需要的模塊

## 進階選項

### 添加圖標
1. 準備 .ico 圖標文件
2. 在 `DIV.spec` 的 EXE 部分添加：
   ```python
   icon='icon.ico'
   ```

### 添加版本信息
在 `DIV.spec` 的 EXE 部分添加：
```python
version='version.txt'
```

## 測試

打包後請測試：
1. ✓ 關卡選擇器正常顯示
2. ✓ 可以選擇並進入關卡
3. ✓ 遊戲正常運行
4. ✓ 完成關卡可以返回選單
5. ✓ 進度正常保存
