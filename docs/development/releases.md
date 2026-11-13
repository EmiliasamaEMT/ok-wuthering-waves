# mc-helper 发布与更新

本 fork 同时作为源码仓库和客户端更新源：

<https://github.com/EmiliasamaEMT/ok-wuthering-waves>

应用发行名为 `mc-helper`，界面标题为「mc小帮手」。`pyappify.yml` 中的 China 和 Global profile 都使用这个仓库的 Git 地址；保留两个 profile 名称，但它们目前没有不同的区域镜像。

## 更新内容与版本

客户端按 Git 版本标签更新，不会因为 `dev` 或 `master` 有新提交就自动切换版本。每个发布标签必须指向已经包含定制名称、更新配置和完整运行代码的提交。

运行依赖由根目录的 `requirements.txt` 提供，包括 `ok-script` 和 `pyappify[standalone]`。当前发布流程不再复制框架源码到仓库，也不再从依赖清单中移除这些包。保留完整锁定清单，尤其是 profile 使用 `pip_args: --no-deps` 时。

打包 Action 使用明确的 `app_version` 检出目标标签并准备 Python 环境，检查安装版本与该标签一致。发行包启动时，PyAppify 将应用版本传给框架，因此无需仅为发布而改写源码中的 `version = "dev"`。

`configs/`、日志等运行时文件继续由应用在本地生成，不应提交到 Git。

## 发布工作流

[Windows Release](../../.github/workflows/build.yml) 在推送 `v*` 标签时运行三个阶段：

1. **Validate**：检查版本标签格式，在 Windows / Python 3.12 下安装依赖并逐文件运行现有测试。
2. **Build portable packages**：使用固定的 PyAppify Action 和启动器版本，从本仓库的目标标签准备两个 profile 的完整环境并打包；随后修正便携启动脚本，让手动启动时从实际 Git 检出版本读取版本号，校验压缩包，并将可发布文件放入独立目录。
3. **Publish**：使用本仓库的 `GITHUB_TOKEN` 创建 GitHub Release，上传便携包、启动器 ZIP 和启动器哈希。GitHub 自动生成的发布说明附在 Release 中。

只有发布 job 需要 `contents: write`。流程不再同步原作者的 GitHub/CNB 更新仓库，也不需要原作者的同步、签名或 MirrorChyan 凭据。

主要产物为：

- `mc-helper-win32-China-<版本>.7z`
- `mc-helper-win32-Global-<版本>.7z`
- `mc-helper-win32.zip`
- `win32_sha256.txt`
- `release-manifest.json`
- `SHA256SUMS`

[GitHub 要求每个 Release 文件小于 2 GiB](https://docs.github.com/en/repositories/releasing-projects-on-github/about-releases)。完整便携包若达到该上限，会按 1900 MiB 分卷发布，例如 `mc-helper-win32-China-<版本>.7z.001`、`.7z.002`。下载同版本的全部分卷到同一目录，用 7-Zip 打开 `.001` 解压。低于上限的包继续使用单个 `.7z`。

分卷保留原压缩包的全部字节，客户端仍按 Git 标签更新。`release-manifest.json` 记录原包哈希、总大小、卷顺序和各卷哈希；`SHA256SUMS` 校验实际下载文件。`win32_sha256.txt` 校验 ZIP 内的原生启动器 EXE；ZIP 文件本身使用 `SHA256SUMS` 中对应的哈希。发布前会核对分卷重组哈希，并对第一卷执行真实 7z 完整性检查。

Windows 打包 job 在准备应用环境前启用 runner 的 `core.longpaths`，避免 libgit2 在嵌套的打包路径中检出长资源文件名时失败。客户端也建议使用较短的安装路径，例如 `C:\mc-helper`；较深目录仍可能触发 Windows 或 Git 的路径限制。

当前不构建安装程序、不执行签名。旧签名和分发工作流文件保留为仅手动触发、只输出停用说明的入口。`deploy.txt` 和 `.update_repo_gitignore` 保留用于兼容上游历史流程，当前发布不读取它们。

## 标签与同步上游

使用更新器支持的格式，例如 `v0.1.0`、`v0.1.1`、`v0.2.0-beta.1`、`v0.2.0-rc.1`。纯数字三段标签为正式版，带 alpha、beta 或 rc 后缀的标签为预发布版。自己的发布版本需要递增，已发布标签不应改指向其他提交。

本 fork 使用独立的 `v0.1.0` 起始系列，首个预发布标签为 `v0.1.0-beta.1`，第二个为 `v0.1.0-beta.2`。2026-11-12 首次发布前核查确认 origin 没有标签或 Release。现有 `deploy` 递增脚本要求已有稳定版标签，因此首次稳定版建立前手动指定本系列版本并核查远程重名，之后使用递增脚本。多语言更新说明保留上游自 `v3.0.0` 起的历史，客户端版本列表仅依据本 fork 实际存在的标签。

同步上游时使用 `git fetch --no-tags upstream master`，将上游代码合并到定制分支，保留名称和更新配置。推送自己的分支或明确指定的发布标签，避免把上游标签一并推入客户端更新源。首次发布前应核查远程已有标签。

默认维护分支为 `dev`。定时与手动同步通过草稿 PR 引入上游改动，身份和测试检查完成后再人工审核合并，具体操作见 [上游同步维护说明](upstream-sync.md)。

Git 标签一旦推送，客户端就可能发现该版本；本工作流只能保证 GitHub Release 在测试和打包通过后创建，不能隐藏已经推送的标签。因此应先完成本地或分支测试，再推送发布标签。Release 草稿状态也不会隐藏 Git 标签。

多语言 `CHANGELOG*.md` 应按自己的发布标签维护。客户端从目标提交读取对应说明；缺少匹配说明时，具体回退行为由所安装的 PyAppify 版本决定。

## 首次启用与后续验证

首次启用该更新来源时，应安装从本 fork 构建的发行包。已有官方安装的仓库来源属于单独的迁移问题，不能仅凭新配置文件就假定已经切换。

旧配置中指向官方启动器 ZIP 的自动迁移条目已移除。应用代码和 Python 依赖仍可更新；后续若要自动升级原生启动器，需要配置自己发布的启动器包，或者安装新版完整包。

Python 3.12 环境、完整测试及两个本地测试版本之间的便携更新验证记录见 [发布验证记录](release-validation.md)。正式发布前仍应验证原生启动器 ZIP、管理员权限提升和 GitHub 真实发布渠道；本地便携包的结果不代替这些检查。

真实 GitHub 发布、下载和产物检查的当前结果见 [GitHub 发行验证记录](github-release-validation.md)。首个正式版 v0.1.0 已发布；China 两种启动模式均已从 beta.7 实际升级至正式版，并完成启动及配置保留验收，具体升级路径见该记录。正式版用户说明见 [v0.1.0](../releases/v0.1.0.md)。
