# GitHub 预发布与实际产物验证

日期：2026-11-12 至 2026-11-13。此记录区分云端发布、下载与静态检查，以及仍需交互确认的运行验收。

## 已发布版本

- [v0.1.0-beta.3](https://github.com/EmiliasamaEMT/ok-wuthering-waves/releases/tag/v0.1.0-beta.3)，应用提交 `a32aabef5629d5429821589dbd8f6ff90117fe48`。
- [v0.1.0-beta.4](https://github.com/EmiliasamaEMT/ok-wuthering-waves/releases/tag/v0.1.0-beta.4)，应用提交 `31875f23aa2c46955c60495c3fdf872da3966559`。
- [v0.1.0-beta.5](https://github.com/EmiliasamaEMT/ok-wuthering-waves/releases/tag/v0.1.0-beta.5)，应用提交 `c6beb96dc706053b61709bcd12ac3da7e8360f4b`。

beta.3、beta.4、beta.5 的 GitHub Actions 均完成 Validate、Build portable packages、Publish。beta.3 和 beta.4 各自通过 **58 个测试模块、559 项测试，0 跳过**；beta.5 通过 **59 个测试模块、568 项测试，0 跳过**。它们是预发布版本，尚未发布正式版。

| 标签 | 云端结果 | 原因或说明 |
| --- | --- | --- |
| `v0.1.0-beta.1` | 测试通过，打包失败，发布跳过 | 原生 EXE 已编译成功；准备 China 环境时，libgit2 检出一个长度为 271 字符的资源路径失败，报 `path too long`。 |
| `v0.1.0-beta.2` | 主动取消 | 已包含分卷修复，但仍缺少长路径配置，停止相同配置的重复构建。 |
| `v0.1.0-beta.3` | 发布成功 | runner 启用 `core.longpaths`，完成两个 profile 的环境准备、打包和发布。 |
| `v0.1.0-beta.4` | 发布成功 | 使用同一已修复流程构建，供真实跨版本更新验收。 |
| `v0.1.0-beta.5` | 发布成功 | 修复 tag-only 仓库的增量协商；已完成便携版真实升级、自动重启与原 CMD 冷启动。 |

已有标签均保留原指向。首次审计时 fork 没有标签或 Release；当前版本标签均为自己的 `v0.1.0` 系列。

构建记录：[beta.1](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43207473922)、[beta.2](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43211437089)、[beta.3](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43212654337)、[beta.4](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43222193398)、[beta.5](https://github.com/EmiliasamaEMT/ok-wuthering-waves/actions/runs/43358778865)。

## 发行产物

[GitHub 的单文件上限小于 2 GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)。本次完整包实际超过该限制，因此每个 profile 发布两个分卷：

| 版本与 profile | 第一卷字节数 | 第二卷字节数 |
| --- | --- | --- |
| beta.3 China | `1992294400` | `331216311` |
| beta.3 Global | `1992294400` | `331210051` |
| beta.4 China | `1992294400` | `331214117` |
| beta.4 Global | `1992294400` | `331205648` |
| beta.5 China | `1992294400` | `331220854` |
| beta.5 Global | `1992294400` | `331213865` |

每个 Release 共 8 项资产：四个便携分卷、原生启动器 ZIP、`release-manifest.json`、`SHA256SUMS`、`win32_sha256.txt`。同版本同 profile 的全部分卷应放在同一目录，从 `.001` 解压。

云端验证了原包与按序分卷重组的哈希一致，并用真实 7z 检查第一卷的完整性。保留完整 Python 环境、Git 数据和工作目录；客户端继续按 Git 标签更新。

`SHA256SUMS` 校验实际下载文件。已实测确认，`win32_sha256.txt` 对应 ZIP 内的 **EXE**，而非 ZIP 文件本身；ZIP 的哈希见 `SHA256SUMS` 或 manifest。

## 已完成的本地检查

- beta.3 China 两个分卷已从真实 GitHub Release 下载，分别校验 SHA-256，按顺序重组的哈希与原包 manifest 一致，并通过本机 7z 完整性检查及解压。
- beta.3、beta.4、beta.5 的 manifest、校验文件和原生启动器 ZIP 已实际下载并核对哈希；beta.4、beta.5 完整便携包由云端打包与完整性校验覆盖，本地未重复下载。beta.5 ZIP 内的 EXE 也与 `win32_sha256.txt` 核对一致。
- 从 beta.3 的真实产物准备了独立的便携版和原生启动器测试目录。两者实际 Git HEAD 均为 beta.3 的提交，origin 均为 `https://github.com/EmiliasamaEMT/ok-wuthering-waves.git`，启动前均没有 beta.4 标签。beta.4 提交产生于 beta.3 打包完成之后。
- 实际包内解释器为 **Python 3.12.10**；`ok-script==3.0.5b5`、`pyappify==1.0.20`。包内模块路径正确，`pip check` 通过，便携环境识别应用版本为 `v0.1.0-beta.3`。
- 原生 EXE 产品名和文件描述均为 `mc-helper`，启动器自身版本为 `1.2.7`，权限清单为 `requireAdministrator`。启动器版本与应用版本分开维护。
- beta.3 原生 EXE SHA-256 为 `2f51d3f95225f29abcd48d7fc2973d337581d05acbf706afd8e846d186cfb5f0`，与发布的 `win32_sha256.txt` 相符。
- 测试配置关闭自动启动游戏、MCP 和初次快捷方式创建，并预置 `Echo Key = f8`，供后续验证配置保留。

本地证据保存在 `build/qa/real-installations.json`、`build/qa/native-binary-info.json`、`build/qa/real-observations.jsonl`，以及 `build/real-download-v0.1.0-beta.3/` 和 `build/real-download-v0.1.0-beta.4/` 的下载结果文件中。

## 真实运行发现的更新问题与修复

用户确认 UAC 后，真实 China CMD 已启动包内 `pythonw.exe`，可见窗口标题为 `mc小帮手 v0.1.0-beta.3 China - mc小帮手`。随后用户关闭了该窗口。窗口工具无法操作管理员窗口，因此尚未完成界面点击更新的验收。

该次启动的自动检查在 120 秒后超时，但后台 Git 获取继续运行，约 7 分钟后取得 beta.4 标签，并重复写入约 1.095 GB 的 pack；应用 HEAD 仍为 beta.3。beta.4 只增加了更新说明，出现这一传输量并不正常。

已定位原因：原生构建产物中的 bare 仓库只有标签和 detached HEAD；固定版本 Dulwich 的默认 graph walker 从 `refs/heads` 出发，未向服务器报告已有对象。PyAppify 的 `fetch_tags` 因而重新下载已有快照。远程标签查询只需数秒，不能通过单纯增加超时解决。

应用修复位于 `src/update_repo.py`，在 `main.py` 和 `main_debug.py` 导入框架前运行。仅在确认属于 mc-helper 的托管目录中，将应用专用本地引用 `refs/heads/mc-helper-current` 同步至当前 HEAD，让原有更新器能够协商增量。它不修改标签、当前版本、远程地址或 shallow 边界；普通开发检出不受影响。所有权标记、精确引用锁、环境路径和并发 HEAD 检查用于避免覆盖其他引用，失败时记录警告并继续启动。

本地完整验证通过 **59 个测试模块、568 项测试，0 跳过**。新增的 9 项测试覆盖重复启动、升级和回退、冲突引用、锁竞争、路径重定向、非阻塞失败，以及使用真实 `git http-backend` 的 HTTP Git 实验：同一未变更的 512 KiB 随机资源，修复前新增 pack 为 **525146 字节**，修复后为 **487 字节**。

旧 beta.3、beta.4 在升级前尚无该启动修复，首次获取新版本仍可能重复下载。为继续验证，已对两个独立 QA 安装目录执行一次同等的本地引用迁移，确认 HEAD、标签、配置、shallow 文件和原有 pack 字节数均未变化。此迁移只作用于测试目录，不等同于已完成版本升级；普通用户可使用包含修复的新完整包，或等待旧版首次获取完成后更新。

修复提交 `c6beb96dc706053b61709bcd12ac3da7e8360f4b` 已推送到 dev，并创建新标签 `v0.1.0-beta.5`。该版本云端也通过 **59 个测试模块、568 项测试，0 跳过**，完整打包、分卷校验与发布成功。

已用 beta.3 包内的 Python、PyAppify 1.0.20 和 Dulwich 1.2.21，对迁移后的真实便携目录连接 fork 获取此前不存在的 beta.5 标签。耗时 **6.812 秒**，新增 pack **74155 字节**，标签指向修复提交；获取前后 HEAD、应用元数据、用户配置和 shallow 文件保持一致。此检查验证了真实 GitHub 的增量协商，尚未执行工作区升级。

另以普通权限直接启动包内解释器和原始 `main.py`，保持发行代码、更新后端和目录不变，以便进行界面验收。应用从 beta.3 检查测试版约 2.132 秒后返回 beta.5 及中文更新说明。该启动方式与原管理员 CMD 的冷启动分开记录；后续窗口点击交由用户完成，检查依据为日志、进程与版本文件。

证据：`build/qa/update-repo-tests.log`、`build/qa/full-tests-update-ref.log`、`build/qa/real-update-ref-migration.json`、`build/qa/real-github-fetch-beta5.json`、`build/qa/real-upgrade-before-portable.json`。

## 真实便携版升级验收：通过

2026-11-13 12:03，用户在真实 beta.3 包的应用主窗口中选择 beta.5 并点击更新。日志确认从 beta.3 检出 `c6beb96`、依赖无变化并跳过同步、自动重新启动。原应用进程 `11024` 退出，更新进程 `98448` 完成后退出，新应用进程为 `69160`；用户确认新窗口顶部显示 beta.5。

随后用户关闭应用，从原始 `build/p/mc-helper.cmd` 再次启动并确认管理员请求，确认顶部仍显示 beta.5。12:05 的新启动日志同样报告 beta.5。实际工作区关键文件与 beta.5 的 Git 对象内容一致，仅存在正常的 Windows CRLF 检出转换；应用专用协商引用已自动同步到新 HEAD。

升级前、自动重启后、从 CMD 冷启动后的 `Echo Key` 均为 `f8`，配置 SHA-256 均为 `66872d2d8015c13418960c6be1ce813ebddfe42cdd553f4ca0dd1f532f8d64de`。升级没有再增加 pack。独立调用包内 PyAppify，在不设置版本环境变量时也识别为 beta.5，且确认使用 standalone 更新后端。

便携模式下，`app.json.current_version` 仍保留初始 beta.3；实际运行版本由 Git HEAD 和启动状态解析得到。不能仅根据该静态字段判断便携版升级失败。另观察到 PyAppify 更新器刷新了当前用户开始菜单中的 `mc-helper.lnk`，目标为 QA 便携目录；应用自身关闭首次快捷方式创建的选项没有阻止更新器刷新快捷方式。

证据：`build/qa/real-upgrade-after-portable.json`、`build/qa/real-upgrade-after-portable-cold.json`、对应的 `verified-p-*.json`、`build/p/data/apps/mc-helper/pyappify-update/update.log`、主程序日志及进程观察记录。

## 原生版验收：已启动，预发布版本比较存在兼容问题

用户从真实 beta.3 原生 EXE 打开启动器并点击启动后，主程序进程为 `107356`，启动器进程为 `102760`。用户确认应用顶部为 beta.3；日志中的单实例 `--get-version-list` 调用确认实际使用了原生更新后端。

2026-11-13 12:11，原生后端已取得 beta.5 标签和更新说明，但应用的更新按钮显示“当前版本”且被禁用。日志确认 `update_available=False`，当前运行版本仍为 beta.3。

已定位：原生版本列表不带 standalone 的 `relation` 字段，`ok.ui.qt.about.UpdateCard` 因而调用公共 `pyappify.is_greater_version` 比较版本。固定的 PyAppify 1.0.20 实现只按点号拆分并转换整数，遇到 `beta` 字样即返回 false；beta.5 与 beta.3 在两个方向都返回 false，界面因此将其判为同一版本。该包现有 `version_tag_key` 则能够正确比较预发布编号。原生升级尚未通过，需兼容修复后继续验收。

兼容修复位于 `src/pyappify_compat.py`：仅在发行依赖确为 Python PyAppify 1.0.20 时，在框架导入前修正该进程的公共比较函数。有效版本标签使用现有 `version_tag_key` 排序，其余输入继续调用原实现；重复安装不会重复包装，其他依赖版本保持原行为。不修改 site-packages、版本列表协议或更新进程管理。该修复同时让公共的启动升级／回退判断能够识别预发布编号；直接调用 `pyappify.versions.is_greater_version` 的其他代码不在修复范围内。

本地完整测试通过 **60 个模块、576 项测试，0 跳过**。新增 8 项测试包括真实 `UpdateCard` 离屏组件：相同的原生列表在修复前按钮被禁用，修复后“更新”“当前版本”“降级”状态正确；另覆盖 beta.9／beta.10、alpha／beta／rc／正式版、关键字参数、旧输入回退、版本门控、缺失元数据、幂等与启动升级状态。证据为 `build/qa/pyappify-compat-tests.log` 和 `build/qa/full-tests-compat.log`。

该修复进入 beta.6。旧版被禁用的更新按钮无法自行取得修复，需先通过原生启动器的官方升级入口迁移；随后使用后续测试标签完成真实的应用内更新点击验收。既有标签保持原指向。

## 尚未完成的运行验收

待继续检查：

1. 修复预发布版本比较后，确认原生模式更新后的停止状态、配置保留和再次启动。

固定的 PyAppify v1.2.7 源码显示，原生 CLI 更新流程调用停止应用、安装版本和保存状态，未调用重新启动。该模式的手动启动应单独验收；不能把 Python standalone 更新器的自动重启结果套用于原生模式。这里是源码结论，真实原生升级仍待运行验证。

先前已完成的本地隔离 Git 更新实验见 [本地发布验证记录](release-validation.md)。正式版应在上述实际运行验收完成后再发布。
