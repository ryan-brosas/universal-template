# Skills inside Ask Sourcebot

These are reusable Ask context, not locally discovered agent skills. Creating one
writes to Sourcebot. Confirm that the user wants that remote artifact and whether
it should be personal or shared; a request for a local skill is not permission
to publish workspace-wide instructions.

## Create or import

In Settings → Skills → Add skill, choose a new skill, a local Markdown import or
an indexed repository file. Each skill has a name, slash command, description
and Markdown instructions. Use a specific trigger description and procedural
knowledge; do not upload secrets or a dump of retrievable repository facts.

Sourcebot file imports recognize this front matter:

```yaml
---
name: Trace request authorization
slug: trace-authorization
description: Trace authorization checks and their tests in a named service.
---
```

`title` can replace `name`, and `command` can replace `slug`. This repository's
playbook `summary` field is not a documented substitute for `description`; review
and fill the import form rather than assuming metadata maps automatically.

A local-file import becomes editable Sourcebot content. A repository import keeps
a source link. Local edits survive until Update from source or Force sync replaces
the provided fields; fields absent from the source retain local values. Inspect
the overwrite warning. “Up to date” refers to the **indexed** source file, not
necessarily the current remote or working tree. Diagnose the displayed status:
**Up to date**, **Update available**, **Source file not found** (renamed/deleted or
unresolved revision), or **Source repo unavailable** (missing/inaccessible repo).
Do not force-sync over local edits just to clear a status badge.

## Use and manage

Type `/` at the start of an Ask prompt to choose a command. Sourcebot expands it
into instructions; file mentions add those files to the chat context. It may also
load a matching skill automatically; chat details show the loaded name/command.

### Interactive Ask versus programmatic Ask

Do not assume skill-management MCP tools imply that `ask_codebase` loads those
skills. In the inspected **v5.1.13** implementation, programmatic Ask omits the
requester context needed to build the skill catalog: it has no `load_skill` tool
and does not expand a literal `/command` like the interactive UI. This was also
observed in a scoped invocation. Native skills do not alter direct MCP search,
file reads or symbol navigation either.

Use the authenticated **Ask UI** and select the slash command to exercise native
skills. For another release, inspect its actual caller and skill registration
before promising automatic use in delegated research. A response that did not
load the candidate is not a with-skill evaluation.

Source: [programmatic caller](https://github.com/sourcebot-dev/sourcebot/blob/v5.1.13/packages/web/src/ee/features/mcp/askCodebase.ts#L179-L207)
and [catalog/tool gate](https://github.com/sourcebot-dev/sourcebot/blob/v5.1.13/packages/web/src/ee/features/chat/agent.ts#L661-L716).

### Catalog scope and management

Personal skills are private in the workspace. Shared skills enter the workspace
catalog. Owners can enable Auto for shared skills. Repository-synced skills are
visible according to source-repository access, with an owner-management exception;
check audience before sharing.

If using MCP, discover live schemas first:

- `create_skill` creates a personal, immediately enabled skill.
- `list_skills` returns metadata, not instructions. Inspect `slug`, `scope`,
  `enabled`, `isSynced` and `canEdit` before proposing an update.
- `update_skill` identifies a skill by `slug` and `scope`. Omitted fields stay
  unchanged. Shared-skill MCP updates require the caller to be its creator and
  the skill to be enabled; inspect `canEdit` rather than inferring UI Owner
  powers apply to this tool. It cannot update repository-synced skills,
  enable/disable skills or move them between personal/shared catalogs; use
  Settings for those workflows.

These tools require an authenticated user and Ask access; anonymous sessions and
repository-scoped access tokens cannot use them. A known license blocker is not
fixed by repeating discovery or trying a write.

Verify the saved content in Settings or its source, metadata in the intended
catalog, and invocation in a harmless scoped chat if authorized. Metadata alone
cannot verify instruction content because `list_skills` omits it.

## Official sources

- [Sourcebot Skills](https://docs.sourcebot.dev/docs/features/ask/skills)
- [MCP skill tools and permission limits](https://docs.sourcebot.dev/docs/features/mcp-server)
