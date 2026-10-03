---
title: subagent-delegation
summary: "Use when delegating work to OpenCode subagents or maintaining the agents/ roster: task-to-agent matching, briefing for distilled results, parallel and background patterns, and read-only boundaries."
kind: playbook
---

# Subagent delegation

Definitions live in `agents/` at the repository root, symlinked as
`~/.config/opencode/agents` so every project sees them. A subagent runs in a fresh
child session, holds no conversation context, is read-only, and returns only its
final answer. Delegation buys context isolation and parallelism, not authority:
check child claims against source before relying on them.

## Match the task

| Task | Agent |
| --- | --- |
| Locate definitions, usages, or matching files | `search` |
| Answer a library, API, or product question from docs, Context7, or Exa | `librarian` |
| Reason through one hard design decision | `plan-consultant` |
| Attack a proposed plan before implementation | `plan-reviewer` |
| Review a diff, commit, or uncommitted change | `review` |
| Reproduce a claim or run focused verification | `verify` |
| Root-cause a failure or crash | `debug` |
| Condense logs, diffs, documents, or threads | `summarize` |
| Critique a UI, Figma, or Paper design | `design-review` |
| Revise prose | `copy-edit` |
| Audit skills, packs, playbooks, or AGENTS.md | `instructions-audit` |

The built-in `explore` and `general` agents remain valid for generic recon and
multi-step work.

## Brief and verify

- State the exact question, the artifact paths or diff, and the output shape wanted.
  A subagent does not inherit the conversation unless the parent includes it.
- Ask for distilled results: findings with `file:line`, evidence, and uncertainty.
  Never ask a subagent for a transcript.
- Keep one writer per ownership area: files change in the primary session only.
- Run independent readers in parallel (several `search` calls feeding one `explore`,
  or `review` alongside `verify`). Use background only when the next step does not
  depend on the result.
- Treat child output as evidence to check, not as verification.

## Keep the roster

- Add or edit `agents/<name>.md`. Frontmatter: `description`, `mode: subagent`,
  optional `model`, `steps`, and `permissions`; the body is the system prompt.
- Keep jobs non-overlapping; the descriptions are what the orchestrator chooses from.
- Keep subagents read-only: deny `edit` and nested `subagent`, deny mutation-capable
  MCP servers, and either deny `shell` or narrow it with an allowlist or `ask`.
  Shell resources match raw command text; MCP actions are named `<server>_<tool>`.
- Give a design reviewer read allowlists (`paper_get_*`, `figma-bridge_get_*`) after
  the broad server deny. `execute` does not bypass nested tool rules.
- Fast lookup pins `omniroute/antigravity/gemini-3.7-flash-high`; research and
  visual review pin `omniroute/antigravity/gemini-3.8-flash-tiered`; judgment
  agents pin `coralbricks/glm-5.3-fp4`. Keep model ids consistent with the
  provider configuration and re-probe a route before repinning it.
- After a change, run the agent on a real task and confirm its permissions hold.
  `~/.config/opencode/agents` must remain a symlink to this repository's `agents/`.
