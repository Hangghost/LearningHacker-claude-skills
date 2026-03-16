# My Claude Code Skills

自訂的 Claude Code Skills 集合。

## 使用方式

將 skill 資料夾 symlink 到 `~/.claude/skills/`：

```bash
ln -s /Users/chenhunglun/Documents/Procjects/claude-skills/<skill-name> ~/.claude/skills/<skill-name>
```

或一次連結所有 skills：

```bash
for dir in /Users/chenhunglun/Documents/Procjects/claude-skills/*/; do
  name=$(basename "$dir")
  [[ "$name" == ".git" ]] && continue
  ln -sf "$dir" ~/.claude/skills/"$name"
done
```

## Skills 列表

（待新增）
