# 计算机小组

本仓库为「计算机小组」的协作仓库。

## 贡献规范

> **重要：仓库所有者可直接向 `main` 分支推送；其他协作者必须通过 Pull Request（PR）提交修改。PR 至少需要一名成员 Review 通过。**

### 流程

1. 从最新的 `main` 分支创建功能分支：

   ```bash
   git checkout main
   git pull origin main
   git checkout -b feat/your-feature
   ```

2. 在功能分支上完成修改并提交：

   ```bash
   git add .
   git commit -m "feat: 描述你的修改"
   git push origin feat/your-feature
   ```

3. 在 GitHub 上发起 Pull Request，目标分支为 `main`。

4. 等待至少一名成员 Review 通过后，方可合并。

### CI 要求

> **重要：CI 测试必须通过。即使是直接推送到 `main` 分支，也必须先通过 CI 测试。**

- 所有推送（`main`）与 PR 都会自动触发 GitHub Actions CI（`.github/workflows/ci.yml`）。
- PR 只有在 CI 全部通过后，方可合并。
- 禁止在 CI 未通过的情况下合并或继续推送，请先修复失败项。

### 约定

- 仓库所有者可直接推送到 `main`；其他协作者的改动一律走 PR。
- 每个 PR 尽量只做一件事，保持改动范围清晰。
- 提交信息请遵循 `feat:` / `fix:` / `docs:` / `chore:` 等前缀规范。
- 合并前请确保 PR 无冲突，并已通过 CI 检查。

## 成员

- 计算机小组

## 德州扑克项目（Texas Hold'em）

本项目为计算机小组 Python 课程项目，包含 **Pygame 图形界面版** 与 **终端命令行版** 德州扑克，支持单挑（1v1）及多人圆桌（2~6 人），并配套单元测试与 GitHub Actions CI。

### 核心特性

- **Pygame 图形界面（[texas_holdem_gui.py](./texas_holdem_gui.py)）**：深绿绒布牌桌、矢量扑克牌与筹码堆、发牌动画、音效开关、对局日志抽屉与内置牌型速查表。
- **多电脑圆桌模式**：支持在右上角 `Table: N AI` 中选择 **1~5 台电脑**（最多 6 人同桌），可配置初始筹码与盲注；完整支持 `D / SB / BB` 轮转、淘汰出局与**主池 / 边池拆分结算**。
- **All-in 跑马体验**：全下亮牌后实时计算各家胜率百分比（`WIN %`）并逐街更新，支持选择 **Run Once（1x）** 或 **Run It Twice（2x）** 双排公共牌独立结算。
- **终端版本与完整测试**：保留原始命令行模式（[texas_holdem.py](./texas_holdem.py)）与 22 项 `unittest` 自动化测试。

### 快速开始

#### 方式一：Windows 一键启动（推荐）

1. 先获取完整仓库文件（任选其一）：
   - 在 GitHub 仓库页面右上角点击绿色 **`<> Code` → `Download ZIP`** 下载压缩包，并**全部解压**到一个文件夹中；
   - 或使用 `git clone` 克隆整个仓库到本地。
   > **注意**：请勿只单独下载 `play.bat` 一个文件，脚本需要与同目录下的 `texas_holdem_gui.py` 等文件一起运行。
2. 进入解压（或克隆）后的文件夹，直接双击 [play.bat](./play.bat) 即可：脚本会自动检测 Python 环境、安装缺失的 `requirements.txt` 依赖并启动图形界面。

#### 方式二：命令行启动

1. 安装依赖（Python 3.8+）：

   ```bash
   py -3 -m pip install -r requirements.txt
   ```

2. 启动图形界面（推荐）：

   ```bash
   py -3 texas_holdem_gui.py
   ```

3. 或运行终端命令行版：

   ```bash
   py -3 texas_holdem.py
   ```

4. 运行全部测试：

   ```bash
   py -3 -m unittest -v test_texas_holdem.py tests/test_ui_session.py
   ```

### 主要文件说明

- `texas_holdem.py`：核心牌型评估、电脑策略、主池/边池计算、命令行入口与状态驱动引擎 `TexasHoldemSession`
- `texas_holdem_gui.py`：Pygame 图形界面主程序、动画与交互事件循环
- `ui_theme.py` / `ui_assets.py` / `ui_widgets.py`：界面主题配色、矢量牌面与音效渲染、交互控件与设置弹窗
- `test_texas_holdem.py` / `tests/test_ui_session.py`：核心规则与多人状态机/无头 UI 单元测试
- `midterm_report/`：中期原型代码与汇报 PPT

更多英文规则细节与模块导读见 [TEXAS_HOLDEM_README.md](./TEXAS_HOLDEM_README.md)。
