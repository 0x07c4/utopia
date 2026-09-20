# Utopia Ideas

这里保存还没有变成正式设计、任务或实验的想法。

灵感出现时，先用一句话写进 [`inbox.md`](inbox.md)，不要求补齐背景、论证或实现方案：

```sh
./scripts/capture-idea "把壁纸配色变成整个桌面的主题源"
```

使用 Utopia 的 Zsh 配置时，可以在任何目录直接记录：

```sh
灵感 "把壁纸配色变成整个桌面的主题源"
```

没有参数时，命令会用 `$EDITOR` 打开 inbox：

```sh
./scripts/capture-idea
```

## 从灵感到实现

1. **捕获**：立即追加到 `inbox.md`。
2. **展开**：值得继续研究时，复制 [`templates/idea.md`](templates/idea.md)，建立 `YYYY-MM-DD-short-name.md`。
3. **验证**：写清假设、问题、实验和已知限制。
4. **采纳**：形成稳定设计后，在正式文档或代码中实现，并从想法文档链接过去。
5. **归档**：没有继续价值的想法保留原因，不删除历史。

建议状态为 `seed`、`exploring`、`accepted` 或 `archived`。想法不是承诺，也不是当前系统状态；它允许不完整、矛盾和后续推翻。
