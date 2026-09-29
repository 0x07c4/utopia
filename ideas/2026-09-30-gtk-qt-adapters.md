---
title: "让 GTK/Qt 消费 Noctalia 主题"
captured: 2026-09-30
status: deferred
tags: [utopia, desktop, gtk, qt, noctalia, theming]
related: [../docs/vision.md, ../docs/roadmap.md, ../docs/handoff.md]
---

# 让 GTK/Qt 消费 Noctalia 主题

## 决策（2026-09-30）

GTK/Qt 动态主题不属于当前 Desktop v0.1 的必需范围。当前使用稳定、可读
的系统回退：GTK 保持 Adwaita 深色外观，Qt 不生成 qt5ct/qt6ct 配置；不为
了让 audit 变绿或追求视觉对称而引入 consumer、包或运行时状态。只有出现
具体日常工作流问题，才重新评估一个有明确 consumer、来源、重载边界和回滚
路径的适配器。

## 当前证据

- 当前 laptop 没有用户级 GTK/Qt 主题文件；仓库中残留的旧
  `.config/Trolltech.conf` 已移除，因为它既不是 Noctalia 输出，也没有对应
  的 Utopia 行为。
- 当前安装的 Noctalia 5.2.0 提供内置 `gtk3`、`gtk4` 和 `qt` 模板。
  GTK 模板会生成 `noctalia.css`，再由官方 hook 在 `gtk.css` 中追加导入，
  同时尝试同步 GNOME appearance；Qt 模板输出 qt5ct/qt6ct 的色彩文件。
- 当前 package intent 没有 `qt5ct` 或 `qt6ct`，live 环境也没有这两个
  consumer。因此 Qt 模板现在没有可验证的应用目标，不能仅为统一外观引入
  新的配置或包。
- 当前 package intent 有 `nautilus`，但它是 GTK4/libadwaita consumer；没有
  已声明的 GTK3 应用，`fcitx5-gtk` 只是输入法模块，不是一个适合验证主题
  的 GTK3 窗口。因此 GTK3 目前只有渲染链证据，GTK4 还需要在 Nautilus
  这样的真实 consumer 中做一次视觉检查。

## 已停止的探索方向

- 已完成 GTK3/GTK4 官方模板的隔离渲染、导入 hook、深色/浅色切换和回退
  验证；不复制 Noctalia 的内置主题文件到仓库。
- Nautilus A/B 暴露了静态图标和应用重启边界，因此不在当前 Utopia 配置中
  显式启用 `gtk3`/`gtk4`。
- Qt 继续等待明确的 qt5ct/qt6ct 包意图和真实应用；不把 Noctalia 生成
  文件或 GUI 状态纳入 Git。
- Neovim 仍是独立子模块，另做适配器和 provenance 评估，不与 GTK/Qt
  变更混在一个实验里。

## 若重新打开时的验证入口

- 用真实 Noctalia palette 在临时 HOME 渲染 GTK3/GTK4 模板，运行官方 hook
  的隔离副本，确认只产生 CSS/import 文件，不写入当前 dconf 或 live 配置。
- 在一个 GTK3 和一个 GTK4 应用中观察壁纸切换后的颜色、字体、焦点和滚动
  状态；记录应用是否需要重启。
- 若没有可用的 GTK consumer 或主题包，保持模板关闭并记录原因，而不是
  为了让 audit 变绿而生成空配置。

## 隔离验证记录

- 2026-09-30：在临时 `HOME`、`XDG_CONFIG_HOME`、`XDG_DATA_HOME` 和
  `XDG_CACHE_HOME` 中，用当前安装的 Noctalia 5.2.0 和
  `/usr/share/noctalia/assets/noctalia-wallpaper.png` 渲染了官方 `gtk3`、
  `gtk4` 模板；深色和浅色两套输出均无未替换的模板占位符。
- 运行官方 `gtk/apply.sh` 的隔离副本后，GTK3/GTK4 各自只创建一个
  `@import url("noctalia.css");`。重复运行保持幂等；切换到浅色后 CSS
  更新而 import 数量不变。
- 使用临时 fake `gsettings`/`dconf` 记录 appearance 调用，确认只发出
  `color-scheme=prefer-dark/light`；测试环境没有 `adw-gtk3`，所以 hook
  没有伪造或写入 GTK 主题名。该演练未启用仓库模板，也未修改当前笔记本
  的 GTK、dconf 或 Qt 配置。
- 这只证明渲染和 hook 边界成立；仍需在真实 GTK3/GTK4 consumer 中观察
  壁纸切换、字体、焦点和重载行为，之后再决定是否把模板加入 Utopia 的
  host/profile 映射。
- 当前的最小真实验证目标是 GTK4/libadwaita 的 Nautilus；在确认它确实
  消费 `noctalia.css`、不会破坏 libadwaita 的可读性和交互后，才考虑启用
  `gtk4`。没有 GTK3 consumer 时，不为了对称而启用 `gtk3`；Qt 同理等待
  明确的 qt5ct/qt6ct 使用者。

## 当前现场 A/B

- 2026-09-30：笔记本已为 `~/.config/gtk-4.0` 建立时间戳备份，并临时生成
  当前壁纸的 GTK4 `noctalia.css`，追加一次 `gtk.css` import；随后通过
  Niri 托管启动 Nautilus 窗口供观察。蓝色与绿色色板在重启 Nautilus
  后确实改变了窗口背景、标题栏和文字；文件夹图标仍保持静态 Adwaita
  蓝色，已有进程不会热加载 CSS，必须重启应用。该 A/B 没有启用
  Noctalia 的 GTK 模板、没有写入 dconf，也没有改 GTK3/Qt；对比完成后
  已回滚，生成目录保留在时间戳备份中。
- 结论：GTK4 渲染边界成立，但当前 consumer 只得到部分动态效果且有应用
  重启边界，尚不足以作为默认 Utopia 体验。除非明确接受静态图标和重启
  约束，否则不应把 `gtk4` 加入 profile 默认模板。

这项探索保留为后续证据，不代表当前配置或 profile 已启用 GTK/Qt 适配。
