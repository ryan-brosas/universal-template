---
name: notion-workspace
description: "Use when the user needs to search, read, create, update, organize, or synchronize Notion pages and databases, or wants a central workspace or second brain in Notion. Prefer this over driving Notion in a browser."
invocation: manual
disable-model-invocation: true
---

# Notion Workspace

## Core Principle

**Notion is the human dashboard, never the machine source of truth.** GitHub issues, pull requests, and milestones own code work identity. The local ryan-workspace repository owns registries, audits, clone state, and validation results. Notion records decisions, summaries, content, and flexible capture. Keep this split; do not copy machine state into Notion.

## When to Use / NOT

- **Use when:** searching, reading, creating, updating, organizing, or synchronizing
 Notion pages and databases; maintaining a central workspace or second brain in
 Notion; recording decisions, summaries, content, and flexible capture. Prefer this
 over driving Notion in a browser.
- **NOT when:** tracking code work identity (GitHub issues, pull requests, and
 milestones own that); storing registries, audits, clone state, or validation results
 (the local ryan-workspace repository owns those).

## Workflow

1. `notion-cli auth status`, if unauthenticated, have the user run `notion-cli auth`
 themselves; never ask for or expose credentials.
2. Search before fetch, fetch before edit: `notion-cli search <query>` →
 `notion-cli fetch <page-url-or-id>`. Never write to a page not fetched in this task.
3. Reuse existing structure, the single central Second Brain hub and Creator's
 Companion content system, instead of creating duplicates.
4. Edit surgically with `page edit --find/--replace` (file variants for multiline or
 batches); deliberate full rewrites only via `page update --content`.
5. Report per the Result Contract below: page URL, what changed, what still needs user
 action.

## Auth and First Moves

1. Run `notion-cli auth status`. If unauthenticated, tell the user to run `notion-cli auth` themselves; never ask for or expose credentials. Credentials live at `~/.config/notion-cli/credentials.json`.
2. **Search before fetch, fetch before edit.** `notion-cli search <query>` finds pages and databases. `notion-cli fetch <page-url-or-id>` reads a page fully. Never write to a page you have not fetched in this task.
3. Reuse existing structure. If a Projects, Tasks, Notes, or Second Brain system already exists, link to it. Never create a duplicate system when the existing one fits.

## Single Central Hub

The top-level Second Brain is the single central hub and the only central dashboard. Maximize it; never create a parallel hub or dashboard when Second Brain exists. Add any missing sections directly to Second Brain instead of nesting a new hub under it. Keep sections for Projects, Tasks, Notes, Content, Learning, Ideas, Principles and Preferences, GitHub Work, Workspace Audits, Source of Truth, and Review Cadence. The hub links existing databases; it does not replace them. Capture freely, organize later. Promote captured ideas to Projects when they become real.

## Content System

Reuse Creator's Companion as the content system. Content Ideas, Research & Swipes, Content Projects, Channels & Courses, and Wiki drive publishing. Capture raw material in Quick Capture and promote it into Creator's Companion. Never create or retain a second content system when Creator's Companion already exists.

## Editing

- Prefer `page edit` with `--find`/`--replace` for surgical text changes. Use `--find-file`/`--replace-file` for multiline sections and `--edits-file` for batches.
- Use `page update --content` only for deliberate full rewrites; it replaces the whole body and needs `--allow-deleting-content` when content is removed.
- Match sibling indentation: tab depth controls block nesting in Notion. Fetch the page first and match the tab depth at the insertion point.
- Create child pages with `page create --parent <id> --title "Title" --content "markdown"`.
- All commands return JSON. Pipe to `jq` for filtering.

## Safety

- Destructive operations such as `page remove-child` need explicit user approval first.
- Never expose tokens, cookies, credentials, or credential paths.
- Never delete or restructure an existing database without approval.
- When a request is ambiguous, fetch before guessing parents or database shape.

## Red Flags

- Copying machine state (registries, audits, clone state, validation results) into
 Notion, GitHub and the local ryan-workspace repository own those.
- Creating a parallel hub or dashboard when Second Brain exists, or a second content
 system when Creator's Companion exists.
- Writing to a page that was not fetched in this task.
- Running destructive operations (`page remove-child`, deleting or restructuring an
 existing database) without explicit user approval.
- Exposing tokens, cookies, credentials, or credential paths.

## Verification

- All commands return JSON; pipe to `jq` and confirm the expected page/database came
 back before proceeding.
- Re-fetch the edited page (`notion-cli fetch`) to confirm the change landed with the
 correct tab-depth nesting at the insertion point.
- Confirm no duplicate system was created: the single central hub and the single
 content system are intact.

## Result Contract

After acting, report the page URL, what changed, and what still needs user action (for example browser approval for a new page or destructive removal).

## References

N/A, no reference files; every command used by this skill is a `notion-cli` invocation documented in this file.
