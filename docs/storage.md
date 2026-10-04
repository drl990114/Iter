# 存储、迁移与工作区移动

[English](storage.en.md)

Iter 将流程文件保存在产品项目之外。默认根目录为 `~/.iter`，每个工作区按真实路径分别存储状态、报告、方案与执行输入，以及生成的证据。产品代码和已批准的测试样例仍写入它们应在的项目或临时目录；已有用户证据保留原位置。

## 查询准确位置

使用已安装 Skill 中的 helper，替换命令中的占位路径：

```sh
python3 "<skill-dir>/scripts/product_loop.py" paths --workspace "<workspace>"
python3 "<skill-dir>/scripts/product_loop.py" status --workspace "<workspace>"
```

两个命令均为只读，不创建存储目录。`paths` 返回 `iter_home`、`storage_root`、`state_path`、`inputs_dir`、`evidence_dir`、`exists`、`legacy_exists` 和 `migration_required`。没有外置状态时，`status` 返回 `exists: false`；创建新周期前仍需检查是否有旧状态等待迁移。

初始化前，`inputs_dir` 和 `evidence_dir` 位于 `storage_root` 下，便于 agent 先准备方案；初始化后指向当前 cycle。初始化或进入新一轮后应重新查询。直接使用返回路径，不根据项目名猜目录，也不自行计算 hash。

如需自定义，在宿主使用的环境中将 `ITER_HOME` 设置为工作区之外的绝对路径：

```sh
export ITER_HOME="/absolute/external/path/iter-data"
```

PowerShell 示例：

```powershell
$env:ITER_HOME = 'C:\external\iter-data'
```

后续会话保持相同配置。修改变量只会选择另一处存储，不会自动搬迁已有记录。工作区符号链接解析到真实路径；不同 clone、Git worktree 各自独立。每个工作区仍只支持一个活动周期，不支持同时写入。

## 宿主写权限

AI 编程宿主需要当前工作区返回的准确 `storage_root` 的写权限，包括初始化前保存方案输入。已有权限可直接复用；缺少时使用宿主本身的目录授权机制。设置 `ITER_HOME` 不会自动获得写权限。

无法获得权限时，Iter 应说明所需目录并停止依赖写入的步骤，不会回退到项目中的 `.product-loop/`，也不会把方案、报告或日志写到项目根目录。Skill 安装位置、产品代码修改权限与流程存储权限分别处理。

## 迁移已有周期

`migration_required` 为 true 时，先显式迁移再恢复。先暂停或结束所有仍可能写入当前工作区旧 `.product-loop/` 的会话，包括加载了旧版 Skill 的会话，迁移完成前不要恢复；暂不支持同时写入。

```sh
python3 "<skill-dir>/scripts/product_loop.py" migrate --workspace "<workspace>"
python3 "<skill-dir>/scripts/product_loop.py" status --workspace "<workspace>"
```

迁移会校验旧 `.product-loop/` 状态，保留项目外备份，将流程文件转入 schema 2 外置存储，并在成功后移除旧流程目录。不要预先删除旧目录，也不要用空白新周期覆盖它。已有外置状态冲突时应按提示处理，不能直接覆盖任一份记录。

保存的授权、方案摘要、报告正文与语言保持原样。旧 `.product-loop/...` 引用及旧管理目录的绝对路径通过记录的映射继续解析；项目中其他位置的已有证据不搬移。检查迁移后的 `status`，确认周期可用前保留返回的 `backup_path`。

迁移中断时，保持原工作区和 `ITER_HOME`，重新运行同一条 `migrate` 命令；它会核对事务记录、外置副本与备份，再继续清理。若提示文件变化或冲突，保留两处记录供检查，不删除事务文件、不手改状态，也不创建替代周期。未完成的事务需要先恢复，之后才能继续普通流程写入。

迁移存储不会授予新的产品开发或数据操作权限。批准范围发生实质变化时，仍通过 `revise` 和相应授权处理。

## 移动或重命名工作区

移动前先暂停或结束该工作区的活动会话，并用 `paths` 记下原 `storage_root`。移动后查询新工作区的 `paths`，让宿主获得在这两处准确存储位置之间转移数据的权限；仅有新工作区的日常写权限可能不足。随后显式关联旧记录：

```sh
python3 "<skill-dir>/scripts/product_loop.py" relocate --workspace "<new-workspace>" --from "<old-workspace>"
python3 "<skill-dir>/scripts/product_loop.py" paths --workspace "<new-workspace>"
python3 "<skill-dir>/scripts/product_loop.py" status --workspace "<new-workspace>"
```

旧工作区路径必须已不存在。这个操作用于搬家，不能合并两个仍存在的 clone 或 worktree。目标存储有冲突时，先核对记录，不手改状态或复制授权。中断后保持新旧路径与 `ITER_HOME`，重新运行同一条 `relocate` 命令；它会先校验保存的事务再完成归属更新。单纯路径变化保留授权和报告正文；范围、数据操作或风险变化时，继续执行前仍需 `revise`。

## 证据引用与分享

生成日志放入返回的 `evidence_dir`，方案和执行 JSON 放入 `inputs_dir`。证据可使用准确的绝对路径，或以 `storage:<相对路径>` 明确相对于 `storage_root`；源码和已有用户证据可用 `workspace:<相对路径>` 指定工作区根目录。仍支持报告相对引用和普通工作区相对引用，但同一引用对应不同已存在文件时会拒绝歧义。

迁移和重关联通过路径兼容保留旧引用，不重写历史正文，也不搬动无关用户证据。引用能找到文件不代表文件中的主张真实；应在适用授权内检查实际结果。

外置存储是本地流程数据，不是备份服务，也不会因此自动上传。报告和证据可能包含源码片段、用户决策与本机路径，分享前仍需检查。流程文件移出 Git 不会改变宿主和模型服务商的数据处理方式。
