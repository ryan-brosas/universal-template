---
title: writing-skills
summary: Use when creating or auditing skills and playbooks, improving task-based selection, or reducing instruction bloat; review meaning directly and judge usefulness from real work.
kind: playbook
---

# Writing skills

A skill should supply task-specific knowledge and improve decisions, not engineer
obedience. Start with `../../../templates/skill.md`. Describe the failure or missing
context it addresses before adding instructions; omit generic advice already
owned by the project or another procedure.

## Make selection work without named invocation

The description is visible before the body. Describe ordinary user intent,
affected artifacts and failure symptoms, the responsibility the skill owns, and
any consequential boundary. A model should understand why the skill applies
without knowing its name. Put task labels on router links, especially when the
procedure has an opaque tool name.

Distinguish three failures before editing: the host did not advertise the skill;
the description did not convey its relevance; or the router did not lead to the
useful procedure. Read the actual files and the relevant task history. Do not
respond to every miss by broadening the trigger or adding another rule.

Keep shared selection policy in `AGENTS.md`. Do not use keyword stuffing,
persuasion tactics, compulsory announcements, scripted selectors or compliance
gates. Do not create temporary validation scripts as a substitute for reviewing
skills or system instructions. Clear scope and useful guidance must do the work.

## Keep one owner

- Visible routers live at `../../../skills/<name>-pack/SKILL.md`, with a
  directory-matching `name`, a trigger-first `description` no longer than 1024
  characters, and `invocation: entry`. Keep descriptions concise without losing
  the distinction from neighboring skills.
- Specialists live at `../<name>/README.md` with `title`, `summary` and
  `kind: playbook`. Do not add skill-discovery fields or `SKILL.md` aliases.
- Link each specialist from one owning pack's cold index. Other packs may
  cross-link it with the owner identified; share the procedure rather than copy
  it. A new visible pack needs a routing need existing owners cannot cover.
- Preserve package-owned and private skills. Use supported host configuration
  for discovery changes, not edits to installed packages or copies of their
  instructions. Preserve attribution and license metadata.

A task may need several owners; a trivial task may need none. Indexes are
navigation, not instructions to load every entry. Resolve references from the
file containing them and keep assets and existing helpers with their procedure.

## Remove bloat without removing meaning

Keep the entrypoint useful on its own. Move detail to a reference only when it
serves a separate question; splitting every paragraph merely adds navigation.
Remove duplicated advice, obsolete procedures, unsupported claims and mandates
unrelated to the task. Trace callers before removing files. A long document is a
review candidate, not proof of waste; missing telemetry is not proof of disuse.

Explain the reason for a consequential constraint. Do not turn a preference into
an absolute rule or require a finding, deletion, tool call or ritual to make the
work appear successful. Preserve valid approaches and actual safety boundaries.

## Review the work, not compliance

Read the changed instructions with their callers, neighboring owners and
references. Check meaning, metadata, paths and host visibility directly. Use the
existing [house style](../house-writing-style/README.md) for prose review. Existing
product tests remain relevant when executable product behavior changes; they do
not certify skill quality.

For selection changes, inspect an ordinary task's actual reads and subsequent
work. Did the agent reach and use the relevant guidance without being told its
name? Did it avoid unrelated procedures and respect the task's boundaries?
Asking it to list the right skill is not evidence that it would use that skill.

When a material change needs comparison, use
[task-outcome evidence](references/lift-evaluation.md). Do not manufacture a
failure, perform unsafe external actions or build a scoring framework to obtain
a pass. Report direct findings separately from behavioral evidence. If real-task
behavior has not been observed, say so; text edits alone do not demonstrate lift.
