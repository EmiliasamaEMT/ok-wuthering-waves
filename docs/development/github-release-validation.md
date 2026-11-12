# GitHub 预发布与实际产物验证

日期：2026-11-12。此记录区分云端发布、下载与静态检查，以及仍需交互确认的运行验收。

## 已发布版本

- [v0.1.0-beta.3](https://github.com/EmiliasamaEMT/ok-wuthering-waves/releases/tag/v0.1.0-beta.3)，应用提交 `a32aabef5629d5429821589dbd8f6ff90117fe48`。
- [v0.1.0-beta.4](https://github.com/EmiliasamaEMT/ok-wuthering-waves/releases/tag/v0.1.0-beta.4)，应用提交 `31875f23aa2c46955c60495c3fdf872da3966559`。

两个版本的 GitHub Actions 均完成 Validate、Build portable packages、Publish；各自通过 **58 个测试模块、559 项测试，0 跳过**。它们是预发布版本，尚未发布正式版。

| 标签 | 云端结果 | 原因或说明 |
| --- | --- | --- |
| `v0.1.0-beta.1` | 测试通过，打包失败，发布跳过 | 原生 EXE 已编译成功；准备 China 环境时，libgit2 检出一个长度为 271 字符的资源路径失败，报 `path too long`。 |
| `v0.1.0-beta.2` | 主动取消 | 已包含分卷修复，但仍缺少长路径配置，停止相同配置的重复构建。 |
| `v0.1.0-beta.3` | 发布成功 | runner 启用 `core.longpaths`，完成两个 profile 的环境准备、打包和发布。 |
| `v0.1.0-beta.4` | 发布成功 | 使用同一已修复流程构建，供真实跨版本更新验收。 |

已有标签均保留原指向。首次审计时 fork 没有标签或 Release；当前版本标签均为自己的 `v0.1.0` 系列。

构建记录：[beta.1](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43207473922)、[beta.2](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43211437089)、[beta.3](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43212654337)、[beta.4](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43222193398)。

## 发行产物

[GitHub 的单文件上限小于 2 GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)。本次完整包实际超过该限制，因此每个 profile 发布两个分卷：

| 版本与 profile | 第一卷字节数 | 第二卷字节数 |
| --- | --- | --- |
| beta.3 China | `1992294400` | `331216311` |
| beta.3 Global | `1992294400` | `331210051` |
| beta.4 China | `1992294400` | `331214117` |
| beta.4 Global | `1992294400` | `331205648` |

每个 Release 共 8 项资产：四个便携分卷、原生启动器 ZIP、`release-manifest.json`、`SHA256SUMS`、`win32_sha256.txt`。同版本同 profile 的全部分卷应放在同一目录，从 `.001` 解压。

云端验证了原包与按序分卷重组的哈希一致，并用真实 7z 检查第一卷的完整性。保留完整 Python 环境、Git 数据和工作目录；客户端继续按 Git 标签更新。

`SHA256SUMS` 校验实际下载文件。已实测确认，`win32_sha256.txt` 对应 ZIP 内的 **EXE**，而非 ZIP 文件本身；ZIP 的哈希见 `SHA256SUMS` 或 manifest。

## 已完成的本地检查

- beta.3 China 两个分卷已从真实 GitHub Release 下载，分别校验 SHA-256，按顺序重组的哈希与原包 manifest 一致，并通过本机 7z 完整性检查及解压。
- beta.3 与 beta.4 的 manifest、校验文件和原生启动器 ZIP 已实际下载并核对哈希；beta.4 完整便携包由云端打包与完整性校验覆盖，本地未重复下载。
- 从 beta.3 的真实产物准备了独立的便携版和原生启动器测试目录。两者实际 Git HEAD 均为 beta.3 的提交，origin 均为 `https://github.com/EmiliasamaEMT/ok-wuthering-waves.git`，启动前均没有 beta.4 标签。beta.4 提交产生于 beta.3 打包完成之后。
- 实际包内解释器为 **Python 3.12.10**；`ok-script==3.0.5b5`、`pyappify==1.0.20`。包内模块路径正确，`pip check` 通过，便携环境识别应用版本为 `v0.1.0-beta.3`。
- 原生 EXE 产品名和文件描述均为 `mc-helper`，启动器自身版本为 `1.2.7`，权限清单为 `requireAdministrator`。启动器版本与应用版本分开维护。
- beta.3 原生 EXE SHA-256 为 `2f51d3f95225f29abcd48d7fc2973d337581d05acbf706afd8e846d186cfb5f0`，与发布的 `win32_sha256.txt` 相符。
- 测试配置关闭自动启动游戏、MCP 和初次快捷方式创建，并预置 `Echo Key = f8`，供后续验证配置保留。

本地证据保存在 `build/qa/real-installations.json`、`build/qa/native-binary-info.json`、`build/qa/real-observations.jsonl`，以及 `build/real-download-v0.1.0-beta.3/` 和 `build/real-download-v0.1.0-beta.4/` 的下载结果文件中。

## 尚未完成的运行验收

本记录写入时，真实 China CMD 的启动请求已发出，正在等待用户手动确认 Windows UAC。调用脚本的等待超时不代表应用启动失败；尚未据此判定真实主窗口启动通过。

待继续检查：

1. 真实主窗口可见，中文名称和应用版本正确。
2. 从 beta.3 经真实 GitHub 更新到 beta.4，观察实际工作区提交、用户配置和进程生命周期。
3. 便携模式的自动重启，以及从原 CMD 再次冷启动后的版本正确性。
4. 原生模式更新后的停止状态、配置保留和再次启动。

固定的 PyAppify v1.2.7 源码显示，原生 CLI 更新流程调用停止应用、安装版本和保存状态，未调用重新启动。该模式的手动启动应单独验收；不能把 Python standalone 更新器的自动重启结果套用于原生模式。这里是源码结论，真实原生升级仍待运行验证。

先前已完成的本地隔离 Git 更新实验见 [本地发布验证记录](release-validation.md)。正式版应在上述实际运行验收完成后再发布。
