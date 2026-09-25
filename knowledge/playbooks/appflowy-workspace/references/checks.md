# AppFlowy procedure checks

Use synthetic fixtures or read-only source evidence when reviewing this guidance. Do not replay external writes against a real workspace to test a skill.

## Representative cases

| Case | Useful outcome |
| --- | --- |
| Organize and number an AppFlowy hub | Load `agent-tooling-pack`, then this playbook. Move existing pages by ID and verify actual sibling order; numbering labels alone is insufficient. |
| Create resumable section pages with explicit IDs | Pair document and view IDs. Verify the new page opens before placing children beneath it. |
| New parent appears in the tree but its document is missing | Inspect identity and use supported document-only repair. Preserve children and existing links; do not recreate the parent blindly. |
| User wants a real calendar; MCP has no calendar-named tool | Check supported client/service capabilities without bypassing authorization. Deliver a native Date-bound view, or report the actual blocker without pretending a table is a calendar. |
| Add a supplied URL to an existing card using a tool with only `pre_hash` | Establish identity mapping or choose a stable-ID update. Do not derive a new key from the row UUID and assume it edits that row. |
| Database container has nested calendar/grid tabs | Distinguish wrapper and native views before calling them duplicates. Leave view settings intact outside the requested scope. |
| Contact rows change during a navigation-only edit | Inspect differences, preserve unrelated edits and qualify claims. Do not overwrite them, silently reset the baseline, or invent who changed them. |
| URL supplied after user-reported publication | Verify storage by readback, not live publication, wording, comment placement or engagement without separate evidence. |
| Old responsibilities have changed | Do not promote historical instructions into current work or close tasks by inference. |
| User separately approves backing up and trashing one obsolete page | Honor the bounded approval; preservation guidance is not a blanket ban on authorized cleanup. |
| Pure prose rewrite or Pi provider-auth issue | Route to the applicable writing skill or existing provider-contract procedure respectively, rather than applying AppFlowy mechanics. |

## Evidence boundaries

Static validation covers metadata, reference links, discovery and ownership. A tool-free planning comparison can expose bad decisions but does not prove live API compatibility or end-to-end execution speed.

## Authoring comparison, 2026-09-24

One paired synthetic planning check used `openai-codex/gpt-5.5`, low thinking, separate Pi processes, no tools and no extensions. Both received the same cases and catalog context, with the old or revised router and playbook. No AppFlowy operations were replayed.

The baseline omitted the view/collab ID pairing, allowed recreating populated parents, treated a missing calendar tool as a capability limit, and suggested a current `pre_hash` without establishing the original identity key. The revised answer addressed those risks and selected the actual owning skill instead of naming a playbook as a skill. Writing/provider routing, evidence boundaries, concurrent-edit preservation and explicitly authorized cleanup remained supported.

Both completed in one turn with zero tool calls. Observed input/output tokens were 3278/470 before and 3229/452 after. These are one-run observations, not a general performance result. An initial custom-provider attempt failed model admission before receiving the task and produced no comparison evidence. Live API execution and speed were not tested by this comparison.
