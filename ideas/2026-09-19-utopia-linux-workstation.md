---
title: "从 dotfiles 到自己的 Linux workstation"
captured: 2026-09-19
status: seed
tags: [utopia, arch, cachyos, kernel, workstation]
related: [2026-09-20-agent-readable-utopia.md]
---

# 从 dotfiles 到自己的 Linux workstation

## 火花

> 不再追求别人替你设计好的 Linux，而是以 Arch 为底座，自己构建桌面，并把 CachyOS 当成进入真实 Linux 性能工程的入口。

理想的分层逐渐变成：

```text
Arch            → 稳定、透明的系统底座
Utopia          → 自己的桌面与工作流
CachyOS 技术    → 内核、调度器、编译优化实验层
```

CachyOS 值得研究的部分并不只是一套发行版默认配置，而是 BORE、EEVDF、sched-ext、Clang、LTO、AutoFDO、Propeller、x86-64-v3/v4，以及它们背后的性能测量方法。

`linux-cachyos-bore-lto` 可以成为入口，因为它把 CPU 调度、交互延迟、LLVM/Clang 和 LTO 连在了一起。问题应从“是否感觉更快”继续深入到补丁、构建参数、测量条件和可重复的延迟数据。

## 为什么值得保留

这让此前分散的兴趣形成一条连续路径：桌面体验、Arch、eBPF、Linux 内核、调度器与编译优化，都可以在每天使用的工作站上研究和验证。

Utopia 因此不应长期停留在 dotfiles 仓库。它可以逐渐覆盖：

```text
desktop/
editor/
shell/
kernel/
scheduler/
tuning/
benchmarks/
bootstrap/
```

Omarchy 和 CachyOS 可以作为两种工程方向的参照：前者偏桌面体验与工作流，后者偏内核、编译器、CPU 和性能工程。Utopia 可以吸收两者中可解释、可复现且适合自己的部分。

## 当前假设

- 桌面工作流与系统性能实验应该分层，不能由一次发行版迁移捆绑决定。
- Arch 笔记本适合验证“Arch 加选择性 CachyOS 技术”的路线。
- CachyOS 台式机适合作为完整集成环境和参考基线。
- 性能结论必须来自同一台机器上的受控对比，不能直接比较两台不同硬件。
- 内核、调优和调度器实验必须保留稳定内核、回滚方法与完整实验元数据。

## 尚未回答的问题

- Utopia 应如何表达系统底座、硬件、工作站能力和实验层的组合？
- 哪些 CachyOS 优化能独立移植到 Arch，哪些依赖完整发行版集成？
- 如何测量“桌面更流畅”，并区分调度器、编译优化和缓存带来的影响？
- 大型 benchmark trace、构建产物和长期报告应如何保存？
- 主题生成与性能实验如何共享同一套安全部署、审计和回滚机制？

## 可以怎样验证

- 记录两台机器经过清理的硬件、内核和软件栈基线。
- 在同一台机器上对默认内核与 BORE/LTO 变体进行重复测试。
- 为每项 tuning 保存默认值、实验值、应用方式、验证方式和回滚方式。
- 将桌面、Shell、编辑器与主机差异拆成可组合 profile，验证两台机器都能重复部署。

## 后续去向

这条想法将指导多层 profile、benchmark 框架和未来 bootstrap 的设计。形成稳定架构后，应链接到正式设计文档，而不是把本文件改写成当前事实说明。
