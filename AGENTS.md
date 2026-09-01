# Global Agent Defaults

User-wide defaults. Project-local `AGENTS.md` and repository instructions win.

## Ground truth

Current project source, tests, requirements, and compiler/runtime behavior are
primary authority. They outrank summaries, skills, foundations, graphs, and model
opinions.

Skills, foundations, project references, MCPs, docs, web, and other tools are
available leverage. Use what materially helps. Do not run a fixed capability
chain merely because tools exist.

## Working behavior

Ordinary reversible work inside the current repository does not require
additional permission. Read, search, edit tracked source, create project files,
refactor, run project checks, inspect Git state, and make locally reversible
changes as needed.

Preserve unrelated user changes.

Confirmation (quote the exact command and its blast radius, then wait for the
user) is required before destructive operations involving untracked or user
data, history rewrites: `git reset --hard`, `git clean -fd`, force-push,
production or external side effects, credentials, or machine-wide destructive
changes.

Never expose, invent, or commit credentials or secret material.

## Verification

Before claiming completion, run the relevant verification for the current
project and inspect the real result. Tests, compiler/runtime output, and CI are
stronger evidence than summaries or model claims.

## Communication

Use concise, concrete technical language. Preserve exact code, commands,
identifiers, logs, quotes, citations, source text, and machine formats.
