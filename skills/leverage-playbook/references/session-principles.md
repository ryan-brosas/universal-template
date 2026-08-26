# Session Principles — prewalk, context-first, code-as-truth

Source: Tom, 8/21/26 (verbatim block: `~/.agents/essentials/discord-material/raw/block-001-67778e9d9668.md`).

## Small models

- Small models (deepseek flash) are agentically the same as frontier models today — they lack *knowledge to work on*, not capability.
- `prewalk`/context injection is the best tool: the prompt planning phase matters, not hand-scripting every step, but giving it context and letting it **search context**.
- Ground truth is code and skills: "deepseek makes no mistakes, because the workflow is written in code or a skill somewhere."
- Cost-optimized: code + skills make even a cheap model reliable enough for real work (previously done with sol, now flash).

## Why no specs

- The moment you have an artifact markdown, you "throw away code definitions"; markdown exists for post-code stuff.
- The more you rely on markdown as a spec, the more you burn iterating things that could have been one-shotted with 1–2 examples.
- It's not that learning specs was worthless — it's that the chat session itself is already an artifact; you only need to burn it into a markdown when you expect the run to last 4–10 days.

## The stack

- Code foundations: work builds on the trail of previous code (terminal → browser → terminal code → dsh). "All of the new designs are quicker because it's from t3 code." New stuff costs time+tokens; existing stuff is a shortcut on both.
- Stack shortcuts: the more you stack, the faster work becomes (the goal: release every hour or so).
- Frameworks/patterns get reused everywhere (e.g. the last foundation for one product was the factory pattern; queue-based workflows; rarely worktrees for huge stuff).

## Applying here

- Session start: inject corpus context (OpenViking `*-foundation`, codebase-memory graph, own skills) as *context, not plan*.
- Implement in small gates-verified slices; let the agent drive; gate at the end.
- Capture every meaningful session into the global skill set before compaction loses the small stuff.