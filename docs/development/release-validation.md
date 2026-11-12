# mc-helper 发布验证记录

验证日期：2026-11-12。应用源码基线为 `5738494c73ffe51087f71d4979bc30db9fdb8e55`；本次同时补充便携启动脚本的版本读取修复。

## Python 环境与应用启动

- Windows x64，Python **3.12.12**，使用仓库根目录的 `.venv`。
- 按 `requirements.txt` 安装完整锁定依赖，并安装 `.[dev]`；`pip check` 通过。
- 实际依赖包括 `ok-script==3.0.5b5`、`pyappify==1.0.20`。
- 按 `run_tests.ps1` 的逐文件方式执行现有测试：**57 个模块、550 项测试全部通过，0 跳过**。
- 启动真实 Qt 界面并正常退出，确认窗口可见、应用名称和窗口标题为「mc小帮手」、任务执行器保持暂停。

本地证据：`build/qa/full-tests-final.log`、`build/qa/test-summary-final.json`、`build/qa/source-smoke/result.json`。

## 便携包与更新验证方法

测试使用独立的本地 Git 更新源 `build/qa/origin.git`。测试标签只存在于该隔离仓库，未推送到 fork 的正式更新源。两个版本使用独立提交与递增的测试依赖版本，以同时观察源码切换和 pip 依赖安装。

完整包包含独立的 Python 3.12 运行时，并按发布 profile 的 `--no-deps` 配置重新安装锁定依赖。未复制开发用 `.venv`。压缩包由发布流程固定版本的 PyAppify 打包辅助函数生成，再调用本仓库的启动脚本修复器并校验 7z 完整性；本机将压缩线程数限制为 2。

测试专用 QA profile 使用相同应用代码和名称，将更新地址指向上述本地源，并关闭管理员权限要求。薄观察入口调用真实 `main.py`，记录实际 Git 提交、解释器和库路径、依赖版本、窗口标题、进程 PID 与配置文件哈希；通过真实界面的更新卡片调用 PyAppify 更新器。测试期间关闭自动启动游戏、快捷方式初次创建和 MCP，并保持任务暂停。

首轮在 pip 输出依赖安装成功后等待超过 180 秒，pip 仍有到 PyPI 的连接，观察器超时。该轮仅能证明代码切换和安装输出，不能证明 pip 成功退出或自动重启。已保留 `build/qa/first-attempt-diagnostic.json` 与原日志，并逐个终止对应的两个 QA 进程。

复测使用全新的第一版解压目录，仅向 QA 启动进程及子进程设置 `PIP_DISABLE_PIP_VERSION_CHECK=1`，关闭与本地更新验证无关的 pip 在线版本自检；真实依赖安装和更新器保持原实现。这个条件属于本地 QA 环境设置，没有写入生产配置。首轮阻塞的确切网络根因未确定。

随后允许测试进程正常访问网络，在第三个全新的第一版解压目录恢复默认 pip 自检设置，重复真实升级和冷启动链路，结果同样通过。独立的默认 pip 安装检查也以 0 退出。本地证据为 `build/qa/pip-default-network-correct-cwd.log`、`build/qa/verify-upgrade-network.log` 和 `build/qa/upgrade-result-network.json`。

## 跨版本检查结果

两个测试源码版本分别为：

| 版本 | Git 提交 | 测试依赖版本 |
| --- | --- | --- |
| `v0.1.0-beta.1` | `74fc919e32a39a81e2f62e06731a3a2ef7c108a0` | `1.0.0` |
| `v0.1.0-beta.2` | `f222104d8623e4a819a3581338e3d775df7e95b8` | `1.0.1` |

正常网络访问、默认 pip 设置下的观测为：

| 阶段 | 应用 PID | 当前版本 | 启动前版本 | 测试依赖 |
| --- | --- | --- | --- | --- |
| 第一版完整包冷启动 | `86228` | `v0.1.0-beta.1` | `v0.1.0-beta.1` | `1.0.0` |
| 真实更新器自动重启 | `96612` | `v0.1.0-beta.2` | `v0.1.0-beta.1` | `1.0.1` |
| 从原 CMD 再次冷启动 | `12516` | `v0.1.0-beta.2` | `v0.1.0-beta.2` | `1.0.1` |

- pip 进程 `79160` 和更新器进程 `72072` 的退出码均为 **0**；旧应用正常退出，新应用 PID 不同。
- 通过界面更新卡片实际发现第二版标签并请求升级，更新后源码提交、依赖版本、窗口版本及更新说明一致。
- `Game Hotkey.json` 中设置的 `Echo Key = f8` 保留，升级前后及再次启动后的文件哈希均为 `66872d2d8015c13418960c6be1ce813ebddfe42cdd553f4ca0dd1f532f8d64de`。
- 从无关的工作目录执行原 `mc-helper.cmd`，确认使用包内 `pythonw.exe`、包内库和 `data/apps/mc-helper/working`。CMD 自身哈希在升级前后不变，窗口标题持续使用「mc小帮手」。
- 第二版完整包另行解压后独立冷启动通过，应用 PID 为 `95100`，使用自己的包内解释器，当前版本和启动前版本均为 `v0.1.0-beta.2`，源码提交与第二版标签一致。
- 除界面观察器记录的依赖元数据外，另用两个已升级安装及第二版完整包各自的解释器实际导入 `mc_helper_qa_probe`，确认模块版本均为 `1.0.1`，模块路径均在各自包内。

完整检查结果保存在 `build/qa/upgrade-result.json`、`build/qa/upgrade-result-network.json` 和 `build/qa/dependency-imports.json`；两个完整包都执行了 7z 完整性校验。

## 本地产物

两个完整测试包保存在 `build/qa/artifacts/`，更新地址仅供本机 QA 使用。它们不属于正式分发版本。

| 文件 | 字节数 | SHA-256 |
| --- | --- | --- |
| `mc-helper-win32-QA-0.1.0-beta.1.7z` | `2335927109` | `e2b95a73054dfde2264a5db0bbdef724e7a62be87d14482656bc94f93a8386b2` |
| `mc-helper-win32-QA-0.1.0-beta.2.7z` | `2335931045` | `4fabbb8e9b98d27926fc62ad552dfc291992ce3cc91070dc57cd4fc820372620` |

`build/qa/manifest.json` 保存完整路径、源码提交、版本和哈希。测试包、隔离 Git 仓库及日志保留在本地忽略目录，未加入源码提交。

## 发现并修复的问题

固定版本的打包辅助函数会将 `PYAPPIFY_APP_VERSION` 和 `PYAPPIFY_APP_STARTING_VERSION` 设置为打包时的版本。PyAppify 1.0.20 优先读取这些变量，因此即使工作区已更新，原 CMD 再次启动仍可能报告初始版本。该问题已在真实受管 Git 工作区中复现。

新增的 `.github/scripts/fix_portable_versions.py` 在发布前清空便携 CMD 的这两个赋值，让手动启动从实际 Git 检出版本识别版本号。Python 更新器自动重启时直接传递目标版本、此前版本和更新说明，继续使用原有行为。修复器检查唯一脚本路径、唯一版本赋值和独立便携模式，更新后执行压缩包完整性和内容核对；原生启动器 ZIP 不在处理范围内。

新增 5 项回归测试覆盖实际 Windows CMD 在两个受管 Git 版本之间的冷启动，以及换行、编码、重复或缺失赋值和启动模式检查。修改后的工作流通过 `actionlint`。

## 验证范围

本记录覆盖 Windows 完整便携包、Python 独立更新器和本地 Git 更新源。原生 Tauri 启动器 ZIP、管理员权限提升、GitHub Actions 云端构建、GitHub HTTPS 下载及正式版本发布需要在各自环境中另外验证。运行这些本地检查没有创建正式 Release，也没有推送正式版本标签。

默认 pip 设置下的退出与重启已在允许正常网络访问的环境中验证；首轮受限环境中的阻塞根因仍未确定。
