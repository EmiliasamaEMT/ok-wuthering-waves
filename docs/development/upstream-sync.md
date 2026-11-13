# 上游同步维护

本 fork 的默认维护分支为 `dev`。首页、下载说明和新 PR 的默认基线使用该分支；客户端仍按本 fork 的 Git 标签选择应用版本。最新正式版入口为 [Releases/latest](https://github.com/EmiliasamaEMT/ok-wuthering-waves/releases/latest)。

## 日常使用

[Sync upstream](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/workflows/upstream-sync.yml) 每天北京时间 **10:17** 检查 `ok-oldking/ok-wuthering-waves` 的 `master`；GitHub 定时任务可能延迟。也可在 Actions 中选择此工作流，点击 **Run workflow**，保持分支为 `dev` 手动运行。

流程将上游代码合并到以当前 `dev` 为基线的 `codex/upstream-sync` 候选分支，创建或更新指向 `dev` 的 **草稿 PR**。自动检查通过后，由维护者审查改动、将 PR 标记为可审查并合并。发布自己的版本另按 [发布与更新说明](releases.md) 操作。

上游已包含在 `dev` 中，或现有 PR 的上游与基线均未变化时，不重复创建提交和 PR。手动运行时勾选 `check_current`，可对当前代码或未变化的候选重新执行检查。手动关闭且尚无新上游提交的候选 PR 会保持关闭。

## 自动检查的范围

- `pyappify.yml`、Python 包名、窗口标题、日志名称仍为 `mc-helper`／`mc小帮手`。
- China、Global 两个 profile 的更新源和应用仓库链接均指向本 fork。上游文档和 FAQ 链接可以保留。
- 正常及调试入口仍在框架初始化前安装 Git 缓存和版本比较兼容修复，相关回归测试保留。
- `dulwich`、`pyappify`、`ok-script` 仍使用已验收的更新依赖版本。上游改动这些版本时，检查会明确要求审查兼容性；确认新版本后，在人工提交中更新静态检查的基线及相关测试。
- 上述检查通过后，在 Windows / Python 3.12 下安装候选依赖并逐模块运行测试。身份检查失败时提前停止，不把跳过的测试记为通过。

PR 的 `mc-helper/upstream-sync` 状态对应实际检查过的候选 SHA，并链接到运行日志。检查期间 `dev` 或 PR 的目标、提交发生变化时，会报告失败或过期，需重新运行。此状态用于辅助审查；本次未配置强制分支保护或自动合并。

GitHub 使用 `GITHUB_TOKEN` 创建的普通 PR 工作流可能显示等待批准，维护者可在 PR 页面批准运行。本同步流程另有独立的检查任务和提交状态，不依赖该批准来获取自动检查结果。参见 [GitHub 的令牌触发规则](https://docs.github.com/en/actions/concepts/security/github_token)。

## 冲突和人工修改

发生 Git 合并冲突时，流程报告冲突路径并停止，不推送这次候选、不替换已有 PR。维护者可在本地从 `dev` 创建工作分支，执行：

```powershell
git fetch --no-tags upstream master
git merge --no-ff upstream/master
```

解决冲突、检查定制内容和测试后，再提交自己的 PR。不要用整文件覆盖或一律选择某一侧来掩盖冲突。

如果直接向 `codex/upstream-sync` 增加人工提交、修改 PR 的归属或标记，自动流程会保留它并要求人工处理。自动更新使用明确的旧 SHA 租约，检查后发生的并发修改也不会被覆盖。PR 描述中的自动块之外可以添加审查笔记，这些笔记会保留。

## 权限与发布边界

准备任务仅运行来自 `dev` 的 Git／API 编排代码，具有同步分支和 PR 的写权限；候选依赖、应用和测试只在另一台只读 Windows runner 中运行。静态检查取自本次准备时的确切 `dev` 提交，候选代码无法替换该检查。状态发布任务只运行可信代码，具有提交状态写权限。

仓库的默认工作流权限保持只读；为让此流程创建 PR，启用 GitHub 的 “Allow GitHub Actions to create and approve pull requests” 设置。流程本身没有批准 PR、自动合并、创建标签或发行的代码。无需新增个人访问令牌或仓库密钥。

只获取上游 `master`，使用 `--no-tags`；只推送明确的同步分支，并禁用 follow-tags。上游 `v3.x` 等标签不会进入本 fork 的客户端更新列表。

## 首次上线验收：2026-11-13

实现提交为 `cd81f87a55a475b955af2d0bd39bf263807490c3`。GitHub 已确认默认分支为 `dev`，简介使用 mc-helper／mc小帮手，首页链接指向本 fork 的最新正式版；同步工作流状态为 active，自动创建 PR 所需设置已启用，默认工作流权限仍为只读。

本地 **20 项维护测试通过**，其中 8 项检查定制名称、更新源、入口修复和依赖基线；12 项使用小型真实 Git 仓库验证干净合并、冲突、无更新、人工提交保护、并发租约、关闭 PR 的保留、PR 创建失败后的恢复，以及失败／跳过／取消的检查和过期提交不能发布成功状态。另复核了开启 `push.followTags` 且存在本地注解标签时，仍不推送任何标签。

首次真实 [运行 43439555544](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43439555544) 获取到上游 `e04bfc3`（将 ok-script 更新为 3.0.5b7）。合并在 `requirements.txt` 发生冲突，准备任务报告路径后失败，检查和状态发布任务按条件跳过。未推送这次候选、未创建 PR，也未合并或发布版本。这验证了真实上游冲突时的停止行为；成功创建 PR 和发布状态的路径本轮由本地真实 Git＋模拟 API 测试覆盖，尚未完成云端成功路径验收。

当前上游更新仍需人工解决依赖清单冲突、验证新框架与更新兼容修复，再通过 PR 引入；本次未把 3.0.5b7 合入 `dev`。后续定时或手动运行继续使用同一保护规则，当前已发布的 v0.1.0 标签保持不变。
