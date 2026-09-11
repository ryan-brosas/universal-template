# File organization

Only visible routers live under `skills/`:

```text
skills/<name>-pack/
  SKILL.md             short intent-to-procedure router
  references/topics.md optional cold branch index

knowledge/playbooks/<name>/
  README.md            procedure with title/summary/kind metadata
  references/          details needed for particular questions
  scripts/             helpers that earned reuse
  assets/              optional supporting files
```

Keep one canonical procedure directory. Move helpers and their tests together;
update CI, prompt and documentation callers when paths change. Plain playbook
Markdown is not a skill-discovery root. Do not create SKILL.md aliases or symlinks
back into `skills/` to preserve old leaf commands.
