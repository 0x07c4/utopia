---
title: "让 Utopia 成为 agent 可理解的工作站规范"
captured: 2026-09-20
status: seed
tags: [utopia, agents, rebuild, bootstrap, reproducibility]
related: [2026-09-19-utopia-linux-workstation.md]
---

# 让 Utopia 成为 agent 可理解的工作站规范

## 火花

Utopia 不仅要让人能够阅读和维护，还要让一个刚进入仓库、不了解历史的 agent 快速而安全地重建系统。Agent 不应依赖聊天记录猜测当前机器、文件归属、危险边界或验证命令。

## 为什么值得保留

普通 dotfiles 仓库往往只保存结果，没有表达来源、适用主机、依赖、部署顺序和回滚方式。这样的仓库可以手工复制，却无法可靠地自动重建。

如果 Utopia 能提供稳定的机器可读契约，agent 就能完成：

- 发现当前机器和目标 profile；
- 生成带来源说明的变更计划；
- 区分共享设置、主机差异和实验覆盖；
- 在危险操作前停在明确的审核边界；
- 分阶段部署、验证、恢复和继续执行；
- 用同一套事实回答“为什么系统现在是这样”。

## 当前假设

- `AGENTS.md` 应是 agent 的第一入口，但不能成为唯一事实来源。
- Profile、包选择、文件映射和实验参数应使用带 schema 的 TOML 或 JSON。
- 人类文档解释意图；机器清单表达可执行事实；两者必须相互链接。
- Capture、deploy、audit、recovery 和 bootstrap 必须共用同一个解析器，不能各自维护路径列表。
- 每个解析结果都应显示 provenance，例如某个 Niri 输出来自 `cachyos-desktop` host overlay。
- 配置存在不等于软件必须安装；包意图需要 `required`、`optional` 和 `disabled` 状态。
- 重建应是幂等、可恢复的阶段流水线，而不是只能从头执行的长脚本。

## 尚未回答的问题

- Profile schema 的最小稳定字段是什么？
- Agent 应如何识别真实硬件，同时避免把探测结果误写成目标配置？
- 如何记录上次部署 commit，并对两台机器的并行修改做三方冲突检测？
- 哪些阶段可以自动应用，哪些必须保留人工审核？
- 如何把大型 benchmark artifacts 与 Git 中的可复现报告关联？
- 安装失败后，如何让另一个 agent 从检查点继续，而不是重新猜测状态？

## 可以怎样验证

- 在空临时目录中，仅凭仓库和一个 profile 生成完整部署计划。
- 要求计划同时输出人类文本和稳定 JSON，并包含每项值的来源。
- 使用两个 host profile 渲染主目录，验证共享配置一致、显示配置不同。
- 在中间阶段故意中断 bootstrap，确认再次执行可以安全继续。
- 制造仓库和本机同时修改同一文件的情况，确认 capture 会报告冲突。
- 让一个没有历史上下文的新 agent 只读取仓库，检查它能否正确描述系统和安全边界。

## 后续去向

形成稳定方案后，应拆分为 profile schema、统一解析器、部署状态格式、阶段执行协议和正式架构决策。根目录 `AGENTS.md` 只保留简洁入口与当前有效命令。
