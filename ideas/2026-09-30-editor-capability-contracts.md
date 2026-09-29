---
title: "把 Neovim 功能与外部能力分开声明"
captured: 2026-09-30
status: exploring
tags: [utopia, editor, neovim, dependencies, capabilities]
related: [../docs/vision.md, ../docs/roadmap.md, ../docs/handoff.md]
---

# 把 Neovim 功能与外部能力分开声明

## 当前证据

- `editor/nvim` 是独立的 `nvim-astro` gitlink；本轮不修改它，也不把它的
  外部模板或运行时状态混入 Utopia。
- 当前真正启用的 LaTeX 配置是 `lua/plugins/latex.lua`：VimTeX 使用
  `latexmk` 编译、`zathura` 预览，并通过 Mason 取得 `texlab`。笔记本有
  `latexmk`，但没有 `zathura` 或 `texlab` 命令，因此这条能力链只有部分
  可用；Mason 状态不属于仓库 package intent。
- 当前真正启用的 AI 配置是 `lua/plugins/ai.lua`：CodeCompanion 默认连接
  `http://127.0.0.1:1234` 的 LM Studio OpenAI-compatible endpoint，同时
  声明了 Copilot 插件。笔记本没有 LM Studio 命令或 1234 端口监听；这应
  被视为可选外部服务，不应因为配置存在就自动安装或宣称可用。
- `mason.lua`、`astrolsp.lua`、`none-ls.lua`、`treesitter.lua`、`user.lua`
  和 `polish.lua` 的示例/扩展目前由 `if true then return ...` 明确停用，
  不应把其中的语言服务器、formatter 或 debugger 当作当前依赖。

## 当前边界

- Neovim 的基本编辑器能力和 AstroNvim 运行时保持现状；不在 Utopia 仓库
  中复制、改写或重新授权 `nvim-astro`。
- 每个外部能力需要单独声明 `required`、`optional` 或 `disabled`，并区分
  系统包、Mason 管理工具、登录/授权服务和本地模型服务。
- 在没有明确使用场景前，不为了让配置“看起来完整”加入 `zathura`、整套
  TeX、`texlab`、LM Studio 或 Copilot 凭据；也不把 Mason 缓存纳入 Git。

## 能力契约（2026-09-30）

这里先把“能力是什么”和“是否安装它”分开。契约描述可接受的用户体验；
package intent 只表达是否要把它纳入某个 profile，不会因为配置存在就触发
安装。

### LaTeX

- **目标工作流**：在 `.tex` 文件中编辑；用 VimTeX 调用 `latexmk` 编译；
  用 `zathura` 打开 PDF；用 `texlab` 提供诊断和跳转。
- **提供者**：VimTeX、AstroLSP 和 Mason 的声明位于独立的 `editor/nvim`
  子模块；Utopia 不复制或改写该子模块。
- **外部依赖**：系统 TeX 工具链（`latexmk` 加至少一个
  `pdflatex`/`xelatex`/`lualatex` 引擎）、`zathura`、以及由 Mason 管理的
  `texlab`。当前笔记本已有 `latexmk`、三个引擎和其发行版包归属，缺少
  `zathura` 与 `texlab`。
- **推荐 intent**：`optional`，但暂不加入共享 profile 的 package 列表。
  只有明确要维护 LaTeX 文档时才建立独立 capability bundle；不为了让
  配置“闭环”而默认引入完整 TeX 发行版、预览器或 Mason 缓存。
- **验证入口**：`command -v latexmk pdflatex xelatex lualatex zathura
  texlab`；在一个临时 `.tex` fixture 上运行 `latexmk`，然后确认 PDF 可由
  `zathura` 打开；在 Neovim 内确认 `texlab` 已被 Mason 安装并能返回诊断。
- **缺失时降级**：Neovim 和纯文本编辑继续可用；没有 `latexmk`/引擎时不
  宣称可编译，没有 `zathura` 时不宣称可预览，没有 `texlab` 时不宣称有
  LSP 诊断。契约失败不得阻塞普通编辑器启动。
- **进入 profile 的门槛**：先记录 TeX 包拆分、版本和许可证，再用最小
  fixture 完成编译、预览、诊断三段验证，并为缺失依赖保留明确提示和回退。

### 本地 AI

- **目标工作流**：在 CodeCompanion 中使用 chat、inline 和 cmd 三类操作，
  默认调用本机 LM Studio 的 OpenAI-compatible API；Copilot 仅作为单独的
  登录型建议提供者。
- **提供者**：当前适配器地址为 `http://127.0.0.1:1234`，默认模型为
  `qwen/qwen3.5-4b`。LM Studio、模型文件、Copilot 登录状态和 token 都是
  外部运行时，不属于 Utopia 仓库。
- **推荐 intent**：`optional`/`external-service`，不加入 Arch package
  列表，也不在 bootstrap 中自动安装、启动或登录。配置存在只说明支持该
  接口，不说明本机拥有模型或网络授权。
- **验证入口**：先确认本机服务监听 `127.0.0.1:1234`，再以不含凭据的
  请求检查 `/v1/models`；确认返回模型包含配置的默认值后，分别验证 chat、
  inline 和 cmd。Copilot 单独验证登录和建议触发，不与 LM Studio 成功与否
  绑定。
- **缺失时降级**：没有 LM Studio 服务或模型时，CodeCompanion 操作应报告
  能力不可用而不影响 Neovim 启动和普通编辑；没有 Copilot 登录时保持插件
  未认证状态，不生成凭据、不写入仓库。
- **进入 profile 的门槛**：只有用户明确选择本地模型工作流后，才记录
  LM Studio 的安装来源、模型版本、资源需求和停止/回退步骤；服务不可用
  时必须有可见的错误而不是静默等待。Copilot 继续作为用户自行授权的独立
  可选项。

## 当前决策与下一步

两条能力都先保持 `optional`，不改变 `packages/*`、Neovim 子模块或当前
静态 Tokyo Night 回退。下一步不是安装依赖，而是等明确的日常工作流选择：

1. 若需要 LaTeX，新增一个可审查的 capability bundle 和最小 fixture，再
   评估包意图；
2. 若需要本地 AI，先确认 LM Studio/模型的来源与资源预算，再设计服务检查
   和提示，不把运行时状态纳入 Git；
3. 在选择发生前，继续把两条路径视为“配置支持、当前机器未闭环”的可选
   能力，而不是 Desktop v0.1 的必需依赖。

## 验证记录（2026-09-30）

- `command -v`：`nvim`、`latexmk` 存在；`zathura`、`texlab`、`lmstudio`、
  `lms` 不存在；本轮另外确认 `pdflatex`、`xelatex`、`lualatex` 均存在。
- `pacman -Qo` 显示 `latexmk` 来自 `texlive-binextra`，三个编译引擎来自
  `texlive-bin`；这只是当前主机事实，不等于已经声明了 profile 包意图。
- 当前会话没有发现 `127.0.0.1:1234` 的 LM Studio/llama 服务监听。
- 真实用户环境执行 `nvim --headless +qa`，退出码为 0；该校验不证明外部
  LaTeX/AI 能力已安装，只证明 Neovim 配置可以启动并退出。
