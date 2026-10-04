# Iter

[English](README.md) | **简体中文**

**把产品改进从「下一步做什么」推进到实现、验证和复盘。**

**MIT · 中英文支持。** 工具兼容性与验证范围见[安装指南](docs/harnesses.md)。

Iter 提供 `iterate-product` Skill，帮助 AI 编程工具完成一轮产品迭代：

- 探索：提出 2–3 个具体改进，说明收益、范围和验收方式。
- 实现：按选定范围完成研究、开发与验证。
- 复盘：记录结果与证据，支持从保存的位置继续。

缺少用户反馈时，可用已授权的本机场景验证，并明确真实用户价值仍待验证。

## 安装

在目标项目目录运行：

```sh
npx skills add drl990114/Iter --skill iterate-product --copy
```

按提示选择你的 AI 编程工具，安装后开启新会话即可使用 `iterate-product`。

**环境要求：**Python 3.10+、Node.js 22.20+ 和 Git，以及 AI 编程工具的文件读写与命令执行能力。`--copy` 同时覆盖全新项目中安装到多种工具的场景。

远程安装需要仓库访问权限。也可以在目标项目中从本地源码安装：

```sh
npx skills add /absolute/path/to/Iter --skill iterate-product --copy
```

原生插件、更新、旧名称迁移与各平台配置见[安装指南](docs/harnesses.md)。

## 使用

可以直接用自然语言指定 `iterate-product`。

报告语言跟随当前对话；旧中文周期在迁移存储后保留原语言。直接使用 Python CLI 新建周期时，默认英文，可传 `--language zh-CN`。

### 探索下一步

```text
使用 iterate-product，为这个产品提出 2–3 个具体改进，说明用户收益、范围和验收方式，推荐一个供我选择。
```

### 实现已确定的功能

```text
使用 iterate-product，为当前项目添加搜索历史，最多保存 10 条、支持清空。
允许实现上述范围，并在临时目录创建测试数据；验收去重、数量限制和清空行为，完成测试和复盘。
```

### 继续迭代

```text
使用 iterate-product，继续保存的产品迭代，在已批准的范围内推进，只在实质决策变化时问我。
```

状态、报告、方案输入和生成的证据默认保存在项目外的 `~/.iter`，按工作区真实路径分别存储。可将 `ITER_HOME` 设置为工作区之外的绝对目录，覆盖默认根目录。helper 的只读命令 `paths --workspace <路径>` 可在初始化前返回准确位置；项目源码和已有证据仍留在原处。

宿主需要当前工作区 `storage_root` 的写权限；无法写入时不会回退到项目目录。旧 `.product-loop/` 周期需显式 `migrate`，移动工作区后用 `relocate` 重关联，详见[存储与迁移说明](docs/storage.md)。范围不变时继续复用已保存的授权；发布、对外沟通和破坏性操作仍需相应授权。

### 取消或暂停

说「取消这一轮迭代」会结束当前周期并保留证据；说「先暂停，稍后继续」则保留活动状态。取消不会自动撤销代码改动。每个工作区只有一个活动周期，暂不支持多个会话同时写入。

## 完整案例

[Note Counter 试用案例](docs/note-counter.zh-CN.md)展示输入、选定范围、真实 CLI 结果与一分钟回放。可通过[试用反馈表](https://github.com/drl990114/Iter/issues/new?template=trial-feedback.yml)反馈体验。

## 更多说明

- [工具适配与排障](docs/harnesses.md)：支持的工具、原生插件、目录与安装问题。
- [开发验证与试用](docs/testing.md)：自动检查和可复现的本机样例。
- [存储、迁移与工作区移动](docs/storage.md)：外置目录、宿主权限、旧周期迁移和路径重关联。
- [发布流程](docs/releasing.md#中文)：手动触发，自动校验、更新版本与发布。
- [变更记录](CHANGELOG.md) · [发布记录](https://github.com/drl990114/Iter/releases) · [MIT 许可](LICENSE)
