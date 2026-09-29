---
title: "让 Fcitx5 随壁纸变化"
captured: 2026-09-29
status: experiment
tags: [utopia, desktop, fcitx5, wallpaper, theming]
related: [../docs/vision.md, ../docs/handoff.md]
---

# 让 Fcitx5 随壁纸变化

## 当前结论（2026-09-30）

笔记本上的视觉 A/B 已接受，动态主题作为 laptop-only 的显式实验保留；
仓库默认仍使用经过来源核验的 Catppuccin 回退。暂不把它提升为 profile
默认值：当前 profile/artifact 解析器不能表达“先生成运行时主题、确认资源
完整后，再原子切换 `classicui.conf`”的部署顺序，直接修改共享配置会误伤
`cachyos-desktop`。等部署顺序和 host 映射具备可审查的 dry-run、回滚记录后，
再重新评估默认化。

## 火花

当前 Fcitx5 已经有经过来源核验的固定 Catppuccin 主题。下一步可以让它
与 Noctalia 使用同一个壁纸主题源：壁纸变化时，输入面板的强调色、选中
候选色和背景色随之更新，但仍保持 Utopia 的对比度与可读性约束。

## 为什么值得保留

输入法面板是高频出现的桌面表面。若它永远保持一套与 Niri、Kitty、
Starship 无关的绿色，动态主题就只完成了一半；如果 Fcitx 也消费同一个
语义色源，壁纸主题才真正贯穿工作流。

这不是把 Fcitx 配置直接绑定到某张壁纸，也不是把 Noctalia 的运行时缓存
纳入 Git，而是增加一个可回退的 Utopia 适配器。

## 当前假设

- Noctalia 的已解析语义色是唯一输入源；适配器不重复实现壁纸取色算法。
- Fcitx 的静态圆角形状资源可以保留，动态颜色通过运行时生成的
  `theme.conf` 与 SVG 资源表达。
- 生成结果写入 XDG 数据或缓存目录，不进入仓库；当前固定 Catppuccin
  主题始终是失败时的回退。
- 适配器至少生成 `surface`、`on_surface`、`primary` 和
  `on_primary`，并在应用前检查输入面板与候选文字的对比度。
- 壁纸事件需要去抖、原子替换和可恢复部署，不能让每一次预览或半成品
  下载都重启 Fcitx。

## 尚未回答的问题

- Noctalia 哪个稳定输出或事件接口最适合作为跨版本的主题输入？
- 使用 SVG 圆角资源时，Fcitx 对动态替换主题目录和重新加载的边界是什么？
- 当壁纸颜色过暗、过亮或只有单一色相时，如何选择固定回退和动态强调色？
- Fcitx 重载是否会打断正在进行的 Rime composition，是否需要只在会话空闲
  时应用？
- 动态主题是否应默认开启，还是先作为 profile 中的显式实验能力？

## 可以怎样验证

- 用当前三类主题 fixture 和真实壁纸生成 Fcitx 主题，检查稳定输出、
  对比度、圆角资源和路径隐私。
- 反复切换壁纸并记录事件到应用的延迟，确认去抖后不会产生重载风暴。
- 在中文候选、英文输入、长候选列表和深浅极端壁纸上做人工截图对比。
- 让生成失败、Noctalia 重启或主题目录替换中断，确认 Fcitx 仍回到固定
  Catppuccin 主题。
- 通过临时 profile 或 feature flag 进行 A/B，不修改默认笔记本体验。

## 已验证（2026-09-29）

- 当前 Noctalia 版本为 5.2.0；`noctalia theme` 可以从壁纸生成包含
  `primary`、`surface`、`on_surface` 等语义色的暗色 token map。
- `noctalia theme --render` 已在临时目录成功把这些 token 渲染成 Fcitx
  `theme.conf`，没有写入当前用户配置。
- Noctalia 的社区模板目录已经定义了 Fcitx5 模板入口，目标路径为
  `$XDG_DATA_HOME/fcitx5/themes/noctalia/theme.conf`，并支持 `post_hook`；
  这证明适配器可以接入现有模板流水线，而不必另起一套壁纸监听器。
- [Noctalia 官方 Fcitx5 模板](https://github.com/noctalia-dev/community-templates/tree/main/fcitx5)
  已经采用上述 addon 热重载思路；Utopia 只借鉴接口，不直接复制其未审计
  的主题文件或 hook。
- Fcitx5 自身的 [Controller1 DBus 实现](https://github.com/fcitx/fcitx5/blob/master/src/modules/dbus/dbusmodule.cpp)
  定义了 `ReloadAddonConfig(string)`，因此该调用不是桌面环境专属的旁路。
- Noctalia 官方 Fcitx5 社区模板文档记录了更窄的重载路径：通过 Fcitx
  自己的 session D-Bus `ReloadAddonConfig(classicui)` 只重载 Classic UI，
  不重启输入法；文档声称这不会清掉正在输入的 Rime preedit。Utopia
  仍需在本机真实会话中复测这一点，不能只依赖文档。
- `fcitx5-remote -r` 仍可作为较宽的回退路径，但不应成为首选。
- 在 `/tmp` 完成了候选目录与固定主题目录分离的回退演练：有效壁纸生成
  候选主题，失效壁纸返回错误且不产生输出，固定主题的校验和保持不变。
- 在当前桌面会话中调用 `ReloadAddonConfig(classicui)` 已成功返回；调用前后
  当前输入法均为 `rime`，固定主题仍为 `catppuccin-mocha-green`。这只证明
  接口可用，尚未覆盖“正在输入时保留 preedit”的人工观察。
- 一次性 A/B 暴露了实现边界：只安装并重载一次生成的主题不会订阅壁纸变化，
  因此换壁纸不会更新；候选面板在删除字符时才显示新颜色，只是延迟重绘，
  不是动态适配成功。正式实现必须挂在 Noctalia 的模板应用和 `post_hook`
  链路上，并明确生成失败时的静态回退。

## 已实现、临时 A/B 已验证（2026-09-30）

- 仓库新增了一个 Utopia-owned Noctalia 用户模板，输出到运行时的
  `$XDG_DATA_HOME/fcitx5/themes/utopia-wallpaper/theme.conf`，消费 Noctalia
  的 `surface`、`on_surface`、`primary`、`surface_container`、`tertiary` 和
  `outline_variant` 语义色。
- `post_hook` 在显式开关文件
  `~/.config/utopia/enable-fcitx-wallpaper` 不存在时立即退出；存在时才
  生成动态 `panel.svg`/`highlight.svg`，复用固定主题的 `arrow.png`/
  `radio.png`，并通过 session D-Bus 只重载 Classic UI。当前
  `classicui.conf` 在仓库中仍选择 `catppuccin-mocha-green`，因此仓库变更
  本身不会隐式改变其他主机的输入面板外观。
- Noctalia 5.2.0 配置校验、模板直接渲染、hook 的开启/关闭隔离测试均已
  通过。Noctalia 的用户模板校验不接受 `requires_path`，所以开关由 hook
  自己守卫，而不是写入无效的模板字段。
- 这是可审查的实验实现。2026-09-30 已在笔记本上完成带时间戳备份的临时
  A/B 启用，并验证蓝色与绿色壁纸会更新生成的 Fcitx 颜色和 SVG 时间戳；
  维护者已确认视觉效果可接受。当前笔记本可以保留显式开关，其他主机仍
  不应自动启用。若要把它提升为 profile 默认值，还需先演练启动/重建顺序、
  回滚和跨主机映射。
- 临时 HOME 的重建/回滚演练已通过：先部署固定 Catppuccin 和 Noctalia 模板，
  再渲染 `theme.conf`、生成动态 SVG 后切换；回滚恢复固定配置并删除生成
  目录，固定主题仍可用。这只证明顺序和恢复边界，不等于已经批准跨主机默认启用。

## 后续去向

保留为已验收的 laptop-only 实验，不改变当前仓库的固定回退主题。适配器
设计、生成器和显式开关已经落在仓库，笔记本视觉 A/B 和隔离重建/回滚演练
已通过；只有完成跨主机映射和真实启动顺序复核后，才考虑把它从实验能力
提升为 profile 默认体验。
