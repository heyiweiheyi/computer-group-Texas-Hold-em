# 计算机小组

本仓库为「计算机小组」的协作仓库。

## 贡献规范

> **重要：本仓库的全部修改必须通过 Pull Request（PR）方式进行，禁止直接向 `main` 分支推送。**

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

- 禁止直接提交到 `main` 分支，所有改动一律走 PR。
- 每个 PR 尽量只做一件事，保持改动范围清晰。
- 提交信息请遵循 `feat:` / `fix:` / `docs:` / `chore:` 等前缀规范。
- 合并前请确保 PR 无冲突，并已通过 CI 检查。

## 成员

- 计算机小组
