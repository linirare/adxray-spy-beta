# ADXRay Game Spy - GUI V2 优化方案

> V2 计划，供参考，未实现。

---

## 一、功能交互优化

### 1. 游戏队列 Treeview 面板（核心）

- 在进度条与日志之间插入 `ttk.LabelFrame` + `ttk.Treeview`
- 3 列：游戏 | 状态 | 进度
- 颜色标记：
  - 灰色 → 等待中
  - 蓝色 → 进行中
  - 绿色 → 已完成
  - 橙色 → 部分成功
  - 红色 → 失败
- 新增方法：`_init_game_queue()`、`_update_game_status()`、`_on_game_double_click()`
- 提取循环中每处理完一个游戏更新 Treeview 对应行
- 双击已完成行 → `os.startfile()` 打开该游戏输出目录

### 2. 输出快捷访问

- actions 栏新增"打开输出目录"按钮，提取完成后启用
- 点击打开根输出目录
- 双击 Treeview 行打开具体游戏输出目录

### 3. 快捷键

- `game_entry` 绑定 `<Return>` → 触发 `_start_extract()`
- 窗口绑定 `<Escape>` → 触发 `_cancel()`

### 4. 窗口几何持久化

- 关闭时保存 geometry 到 `~/.adxray_spy/gui_config.json`
- 启动时 `_load_config()` 恢复窗口位置大小
- 异常静默忽略（配置损坏、显示器移除）

---

## 二、视觉美化（评估中）

| 方案 | 效果 | 工作量 |
|------|------|--------|
| **ttk 主题切换** | `ttk.Style().theme_use("vista")` → Win10 原生风格 | 1 行 |
| **状态指示灯** | Canvas 画圆或 Label 背景色替代纯文字登录状态 | ~10 行 |
| **统一配色** | 定义 ttk.Style 全局色板、按钮 hover 色 | ~20 行 |
| **窗口图标** | 设置 `.ico` 图标文件 | ~3 行 |
| **分割线 + 间距** | ttk.Separator 区隔功能区，统一 padding | ~10 行 |
| **底部状态栏** | 显示当前状态摘要：就绪/提取中/已完成 N 个 | ~15 行 |
| **左侧导航栏** | 功能分区（登录/提取/结果）改用 Notebook 或 PanedWindow | 大改 |

推荐低成本高感知的：**状态指示灯 + 统一配色 + 窗口图标**。完整重新设计需要移植到 PyQt/PySide，超出当前范围。

---

## 三、改动范围

| 文件 | 改动 |
|------|------|
| `adxray_spy_gui.py` | ~130 行新增，~15 行修改 |
| `adxray_spy_core.py` | **不动** |

### 新增属性

- `self.game_tree` — Treeview 控件
- `self.game_outputs` — dict[iid → 输出目录路径]
- `self.open_output_btn` — 打开输出目录按钮

### 新增方法

- `_init_game_queue(games)` → 填充 Treeview，返回 iid 映射
- `_update_game_status(iid, status, progress, output_dir)` → 更新单行
- `_on_game_double_click(event)` → 打开对应游戏输出目录
- `_open_output_root()` → 打开根输出目录
- `_load_config()` → 读取窗口配置
- `_save_config()` → 保存窗口配置

### 修改方法

- `__init__` → 加 `_load_config()`
- `_build_ui` → 加 Treeview 面板、输出目录按钮、快捷键绑定
- `_set_busy` → 清空 Treeview、开关按钮状态
- `_start_extract` → 初始化游戏队列、循环中更新状态
- `_on_close` → 加 `_save_config()`

---

## 四、验证清单

- [ ] 输入"原神, 王者荣耀" → 队列显示 2 行等待中（灰色）
- [ ] 提取中 → 当前游戏蓝色进行中 + 进度 "3/7"
- [ ] 完成后 → 绿色已完成 / 橙色部分成功 / 红色失败
- [ ] 双击已完成行 → 打开对应输出目录
- [ ] "打开输出目录"按钮 → 提取完成后可用
- [ ] Enter 触发提取，Escape 取消
- [ ] 调整窗口 → 关闭 → 重开 → 大小恢复
- [ ] 原有功能不变（检查登录、重新登录、清除登录、诊断导出、进度条、版本检查）
- [ ] 所有 UI 更新线程安全

---

## 五、多产品汇总 Excel

> 批量提取多个游戏时，除了每个游戏独立的 Excel，额外生成一个合并汇总 Excel。

### 数据结构

```
输出目录/
├── 原神_20260615_120000/
│   ├── report.txt
│   └── report.xlsx
├── 王者荣耀_20260615_120001/
│   ├── report.txt
│   └── report.xlsx
└── 批量汇总_20260615_120000.xlsx   ← 新增
```

### 改动

**`adxray_spy_core.py`** — 新增 `@staticmethod generate_merged_excel(all_results, output_path)`

Sheet 结构：
- **汇总** — 每个游戏一行：游戏名 | ID | 总体状态 | 总素材数 | 总计划数 | 投放周期 | 渠道数 | 文案数 | 输出目录
- **{游戏名}** — 每个游戏独立 sheet（截断 ≤31 字符），结构与现有 `generate_excel` 一致（8个工作表）

**`adxray_spy_gui.py`** — 修改 `_start_extract`：
- 循环内收集 `all_game_data`
- 循环结束后若 `len > 1`，调用 `generate_merged_excel`
- 保存到输出根目录，文件名 `批量汇总_{时间戳}.xlsx`

### 规则

- 单游戏提取不生成汇总文件
- 不删除原有 per-game 独立目录和文件
- 游戏名含特殊字符时 sheet 名自动清理
