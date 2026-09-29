# Idea Inbox

<!--
这里是低摩擦的临时入口。先记录，不在这里解决问题。
成熟后再移动到独立想法文档。
-->


- [2026-09-20T23:57:36+08:00]

  一致就是一种美

- [2026-09-29T18:43:23+08:00]

  让 Fcitx5 从当前壁纸与 Noctalia 共享主题源，动态更新输入面板，同时保留静态主题回退与可恢复部署。
  详见 [`2026-09-29-wallpaper-driven-fcitx-theme.md`](2026-09-29-wallpaper-driven-fcitx-theme.md)。

- [2026-09-30T01:00:00+08:00]

  盘点 GTK/Qt 的 Noctalia 适配边界：先验证 GTK3/GTK4 官方模板，Qt 等待明确的 qt5ct/qt6ct consumer 和包意图。
  详见 [`2026-09-30-gtk-qt-adapters.md`](2026-09-30-gtk-qt-adapters.md)。

- [2026-09-30T01:23:14+08:00]

  决定 GTK/Qt 动态主题暂不进入 Desktop v0.1 主线；稳定系统回退足够，只有具体 consumer 和工作流问题才重新打开适配器评估。

- [2026-09-30T01:35:00+08:00]

  盘点 Neovim 的外部能力：LaTeX 与 LM Studio 配置存在但依赖未闭环，先建立 capability contract，不因配置存在就安装或宣称可用。
  详见 [`2026-09-30-editor-capability-contracts.md`](2026-09-30-editor-capability-contracts.md)。

- [2026-09-30T01:46:45+08:00]

  已完成 LaTeX 与本地 AI 的 capability contract：两者均保持 optional，不改变共享 profile 或外部 Neovim 子模块；后续只有在明确日常工作流后才建立独立 capability bundle。
