# 个人定制版本维护分析

分析日期：2026-11-12（Asia/Shanghai）。本文面向长期维护个人 fork，记录当前仓库结构、扩展入口、维护成本及建议顺序，不代表游戏内效果或完整测试已经验证。

## 分析与同步基线

- 个人仓库：<https://github.com/EmiliasamaEMT/ok-wuthering-waves>，对应 `origin`。
- 上游仓库：<https://github.com/ok-oldking/ok-wuthering-waves>，对应 `upstream`。
- 当前工作分支：`dev`。
- 同步前本地 `dev`、`master` 和 `origin/master` 均位于 `11c008a7f147a3674f0acb8c939d4208703c650c`，工作区干净。
- 本次获取上游 `master` 后，通过 `git merge --ff-only upstream/master` 将本地 `dev` 快进至 `1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f`，没有冲突。
- 本报告以该上游提交为分析基线，不包含随后创建的报告提交。远程 fork 的分支状态仍以推送结果为准。

同步包含两个提交：

| 提交 | 内容 |
| --- | --- |
| `3586ce5` | 新增莉莉角色自动化、识别素材和测试，支持关闭深境中的可选角色介绍界面 |
| `1a216d7` | 新增 `main_updater.py`，从当前检出目录打开 PyAppify 更新管理器 |

[本次上游变更对比](https://github.com/ok-oldking/ok-wuthering-waves/compare/11c008a7f147a3674f0acb8c939d4208703c650c...1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f)。

## 总体判断

仓库适合长期维护个人定制版。任务、角色和识别素材均有明确落点，也已有队伍自定义代码机制。主要维护成本来自游戏界面和角色机制变化、公共战斗逻辑的回归，以及与外部框架的兼容。

截图、键鼠输入、OCR、任务执行器和大部分界面基础能力由 `ok-script` 提供。维护这个 fork，主要是在维护游戏业务代码和识别素材，同时保持它们与框架版本兼容。

同步后的规模统计如下，仅统计 Git 跟踪的文件；源代码数量不含仓库根目录的入口、配置和构建脚本。

| 范围 | 规模 |
| --- | --- |
| `src/` 下 Python 文件 | 106 个，约 1.7 万行非空代码 |
| `src/char/` 下 Python 文件 | 61 个，包含角色实现及公共辅助模块，不等同于角色数量 |
| `src/task/` 下 Python 文件 | 33 个 |
| `tests/` 下 Python 文件 | 55 个，不等同于测试用例数量 |
| `tests/images/` 下素材文件 | 47 个；其他测试还使用 `ok_templates/` 中的截图 |

## 结构和主要入口

| 位置 | 职责 | 定制时的用途 |
| --- | --- | --- |
| [main.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/main.py)、[main_debug.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/main_debug.py) | 创建 `OK(config)` 并启动；调试入口开启 debug | 源码运行和调试 |
| [main_web.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/main_web.py) | 切换至 Web 界面后启动 | Web 界面入口；需要相应依赖 |
| [main_updater.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/main_updater.py) | 打开当前目录的 PyAppify 更新管理器 | 更新工具入口 |
| [config.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/config.py) | 注册任务、全局选项、窗口交互、识别配置和应用信息 | 调整默认行为、注册新增任务 |
| [src/task](https://github.com/EmiliasamaEMT/ok-wuthering-waves/tree/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/src/task) | 日常、刷声骸、副本、多账号等流程 | 增加或调整具体自动化流程 |
| [src/char](https://github.com/EmiliasamaEMT/ok-wuthering-waves/tree/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/src/char) | 角色识别、技能循环和切人策略 | 角色及队伍行为定制 |
| [src/combat/CombatCheck.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/src/combat/CombatCheck.py) | 战斗状态识别和公共状态处理 | 跨任务战斗行为 |
| [src/gui](https://github.com/EmiliasamaEMT/ok-wuthering-waves/tree/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/src/gui) | 队伍自定义代码、多账号等项目特有界面 | 功能配置和交互 |
| [ok_templates](https://github.com/EmiliasamaEMT/ok-wuthering-waves/tree/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/ok_templates)、[assets](https://github.com/EmiliasamaEMT/ok-wuthering-waves/tree/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/assets) | 原始图片、标注、生成模板及模型 | 图像识别适配 |
| [i18n](https://github.com/EmiliasamaEMT/ok-wuthering-waves/tree/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/i18n) | 翻译资源 | 用户可见文本的多语言维护 |
| [.github/workflows](https://github.com/EmiliasamaEMT/ok-wuthering-waves/tree/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/.github/workflows) | 测试、打包、发布、文档部署等 | 建立个人 fork 的 CI 和发布流程 |

自动战斗的主要继承关系为：

`AutoCombatTask → BaseCombatTask → CombatCheck → BaseWWTask → ok-script BaseTask`

[CharFactory.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/src/char/CharFactory.py) 根据识别结果创建角色实例，战斗任务调用 [BaseChar.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/src/char/BaseChar.py) 的 `perform()`，再进入具体角色的 `do_perform()` 等行为。修改单个角色通常可以局限在角色文件中；修改战斗基类则可能同时影响自动战斗、日常和刷声骸。

## 已有扩展能力

[CustomCharLoader.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/src/char/CustomCharLoader.py) 和 [CharacterCodeTab.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/src/gui/CharacterCodeTab.py) 已提供队伍自定义代码、导入导出及内置代码切换能力。`CharFactory.apply_team_char_classes()` 会在完整三人队伍识别完成后应用相应角色类。

个人队伍循环可以优先使用这个入口。需要注意，自定义队伍和角色代码位于配置目录下，而 [`.gitignore`](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/.gitignore) 忽略了 `configs/`。准备长期保留或随 fork 分发的代码，需要另行纳入版本管理；账号配置和执行历史继续保留在本地配置目录。

新增自动化任务可以放在 `src/task/`，再通过 `config.py` 注册为一次性任务或触发任务。现有 `custom_tasks` 开关也已开启，但具体加载规则属于框架能力，使用前应核对所固定框架版本的实现。

## 长期维护的重点

### 更新与发布仍依赖上游配置

[pyappify.yml](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/pyappify.yml) 的 China 和 Global 配置分别指向原作者的 CNB、GitHub 更新仓库。[config.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/config.py) 的 `update_pyappify` 也引用原作者发布的升级包。

[build.yml](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/.github/workflows/build.yml) 不只是打包：它先验证，再同步多个上游更新仓库，随后打包、发布并触发分发流程。同步阶段引用 `CNB_TOKEN`、`OK_GH` 等凭据，后续阶段依赖同步结果。MirrorChyan 工作流也包含原作者的仓库信息。目前主发布流程关闭了安装包构建和签名。

因此，首次分发自己的版本前，需要核对并调整更新目标、发布目标和凭据依赖，使安装后的程序能够持续获取个人版本的更新。仅修改应用名称不足以完成这件事。

### 公共基类承担较多职责

`BaseWWTask` 和 `BaseCombatTask` 各约 1200 行非空代码，`BaseChar` 约 890 行，集中处理导航、识别、冷却、切人及恢复等细节。这些文件是多个功能共用的修改点，也容易与上游持续开发产生重叠。

定制尽量落在具体任务、角色和配置中。确需修改公共逻辑时，保持提交主题单一，并根据受影响的调用方选择回归范围。

### 识别素材必须与代码一起维护

游戏更新、分辨率、语言和界面缩放都会影响识别。原始截图、标注和生成模板应成套保存，避免只有结果素材而缺少可重新生成的来源。[贡献指南](contributing.md) 已明确要求同时提交相关的 `ok_templates/` 和 `assets/` 修改。

### 框架版本是兼容边界

[pyproject.toml](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/pyproject.toml) 固定了 `ok-script[ocr,qt]==3.0.5b4`，[requirements.txt](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/requirements.txt) 锁定了运行依赖，这是复现环境的基础。框架承担的职责较多，升级时仍应单独验证，记录对应的游戏版本、Python 版本和依赖基线。

实际开发文档和 CI 使用 Python 3.12，但项目元数据声明 `requires-python = ">=3.11"`。建立个人维护规范时应核对并统一支持范围。

### 已有测试，但需要建立自己的可运行基线

现有测试包含模拟对象、截图识别、部分源码结构检查，以及角色、战斗状态、多账号、配置等逻辑测试。文件数量不能直接代表覆盖率，也不能替代游戏内验证。

[test.yml](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/.github/workflows/test.yml) 监听 PR 的打开和更新，普通分支推送没有对应测试触发；发布工作流会再次执行测试。如果主要通过直接提交维护 `dev`，建议增加该分支的推送测试。

标准测试入口是 [run_tests.ps1](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/run_tests.ps1)，它逐文件通过 [run_test.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/run_test.py) 运行测试；后者处理了 OCR 预热和测试环境翻译等问题。后续验证应优先沿用这个入口。

### 许可证元数据不一致

[LICENSE.txt](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/LICENSE.txt) 内容为 AGPL-3.0，而 [setup.py](https://github.com/EmiliasamaEMT/ok-wuthering-waves/blob/1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f/setup.py) 的分类写着 MIT。README 还包含用途声明。对外分发前需要核对这些声明并消除元数据矛盾；本文仅记录文件现状，不对授权范围作法律判断。

## 建议推进顺序

1. 使用 Python 3.12 建立仓库本地 `.venv`，安装锁定依赖和开发依赖，运行现有测试，形成可复现的起点。
2. 明确定制主分支和上游同步流程，把具体功能拆成主题清楚的小提交，便于合并、回归和回滚。
3. 按首次分发需求调整个人更新源、打包和发布流程，补充定制分支的自动测试。
4. 从一个具体角色或任务开始定制，优先利用现有扩展入口，同时保留对应测试或截图。
5. 游戏或框架升级时，分别验证任务流程、图像识别和角色循环，再形成新的可用基线。

## 本次验证与限制

- 已完成上游获取和快进同步，上游基线为 `1a216d79310eaa00d5c9c6ee4fbda842d5f31b0f`。
- 已对本次上游新增或修改的 7 个 Python 文件进行语法解析检查；最终检查使用 Python 3.13 的解析器并指定 Python 3.12 语法版本，不能替代 Python 3.12 的运行验证。
- 已检查报告中的本地文件链接和补丁空白格式。
- 当前没有仓库本地 `.venv`，现有全局解释器为 Python 3.13.9，缺少 `ok` 和 `pyappify`。因此未执行依赖这些组件的莉莉、深境相关测试，也未验证更新器界面或游戏内效果。
- 本次没有安装依赖或修改业务实现；报告中的维护建议尚未实施。
