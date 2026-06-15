# ADXRay Spy

ADXRay Spy 是一个不依赖大模型的 Windows 桌面工具。输入游戏名称后，它会使用用户自己的 ADXRay 登录状态，提取页面可见的广告投放数据、文案与素材链接，并生成文本报告和 Excel。

## 公开 Beta 功能

- 提取产品概览、渠道分布、热门文案、素材创意、达人营销和投放趋势
- 保存页面可见的图片、视频及落地页链接，不下载素材文件
- 多个同名产品出现时由用户明确选择
- 为每个模块记录成功、部分成功或失败状态
- 每个游戏生成独立目录，包含 `report.txt` 与 `report.xlsx`
- 支持取消任务、清除本地登录状态和导出脱敏诊断包
- 不需要大模型，不会上传 ADXRay 登录信息

## 下载与使用

从 [GitHub Releases](https://github.com/linirare/adxray-spy/releases) 下载以下任一版本：

- `adxray-spy-setup-win-x64.exe`：推荐给普通用户的安装器
- `adxray-spy-portable-win-x64.zip`：解压后直接运行的便携版

公开 Beta 暂未进行代码签名，Windows SmartScreen 可能显示警告。运行前可使用 Release 中的 `SHA256SUMS.txt` 校验下载文件。

首次使用：

1. 启动 ADXRay Spy。
2. 输入游戏名称，可用逗号分隔多个游戏。
3. 点击“开始提取”，在弹出的浏览器中登录自己的 ADXRay 账号。
4. 等待文本报告和 Excel 生成。

发布包已内置 Playwright Chromium，不需要安装 Python，也不需要首次下载浏览器。

## 输出

每个游戏会生成独立目录：

```text
output/
└── 游戏名_20260615_120000/
    ├── report.txt
    └── report.xlsx
```

Excel 固定包含以下工作表：

- 抓取状态
- 产品概览
- 渠道分布
- 热门文案
- 素材创意
- 达人营销
- 投放趋势
- 素材链接

当关键字段缺失或部分模块失败时，应用会明确显示“部分成功”，不会将不完整结果显示为全部完成。

## 隐私与账号

- 每位用户必须使用自己的有效 ADXRay 授权账号。
- 登录状态只保存在本机的 `~/.adxray_spy/browser_data`。
- “清除登录”会删除本机保存的 ADXRay 浏览器会话。
- 诊断包仅包含应用版本、抓取状态和脱敏日志，不包含 Cookie、密码或浏览器配置。
- 本工具仅提取账号在 ADXRay 页面中可见的数据，使用者应遵守 ADXRay 服务条款及适用法律。

## 源码运行

需要 Python 3.10 或更高版本：

```powershell
python -m pip install -r requirements.txt
python -m playwright install chromium
python adxray_spy_gui.py
```

命令行模式：

```powershell
python adxray_spy_core.py 游戏名称 --output output
```

## 测试与构建

运行测试：

```powershell
python -m unittest discover -s tests -v
```

生成包含 Chromium 的便携版和安装器：

```powershell
build_exe.bat
```

构建脚本需要 Python 3.12。安装 Inno Setup 6 后会同时生成安装器；未安装时仍会生成便携 ZIP。发布产物位于 `dist/release/`。

GitHub Actions 会在推送 `v*` 标签时运行测试、构建 Windows 安装器和便携版、生成 SHA-256 校验值，并创建未签名的预发布版本。

## 仓库说明

正式应用和发布包仅包含 `adxray_spy_core.py` 与 `adxray_spy_gui.py`。仓库根目录中的 MediaCrawler 和特定数据分析脚本属于研究实验，不会进入安装器或便携版。
