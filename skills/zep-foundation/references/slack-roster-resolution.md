<!-- capsule-v2 -->
# Slack roster resolution — how do you turn opaque user IDs into mergeable entity names?

**Source:** zep Apache-2.0 @ `7de18dfa`; Codebase Memory `ext-zep`. **Question:** Which name does the loader pick from a Slack roster, and why is it the opposite of Slack's own precedence?

## _user_map / weak names
**Path/Symbol:** `ingestion/src/zep_ingest/loaders/slack.py:399` (`_user_map`), `:647` (`_resolve`), `:354` (`_summarize`), `:26` (`_looks_like_handle`); rosters `slack.py:47` (`ROSTER_FILES = ("users.json", "org_users.json")`).
**Signature:** `_user_map(roster) -> tuple[dict[id, name], frozenset[weak_ids]]`; precedence real_name > display_name > username > raw id.
**Data Shape:** Weak = any id whose best name is NOT a full human name (handle-like display_name, username slug, or bare id).

### Decisive source
```python
# _user_map docstring — the reason for the inverted precedence:
# ``real_name`` is preferred over ``display_name``. Zep merges entities by
# the names it sees in text, and a Slack display name is frequently a short
# handle ("morgan") that will not merge with the same person written in full
# ("Morgan Lee") in an email or document, splitting one person into two
# nodes. Slack's own precedence is the opposite, but it optimizes for how a
# name reads in a chat client, not for entity resolution.
```

**Flow:** read users.json else org_users.json (missing roster ⇒ warning that every author/mention lands as raw U012AB3CD ids, degrading extraction) → map each id to best name, tagging weak ones → `_parse` buffers weak-name sightings per message into `_pending_weak_names` → promoted to `_weak_names` ONLY once the message survives validation (`_load_conversation`) → `_summarize` (in `load()`'s finally, so abandoned preview generators still report) warns counts + suggests formatter=/real_name fixes.
**Invariant:** The two tallies claim different things and are recorded at different times: unresolved ids were "referenced in messages" (true even for dropped messages) while weak names are "named in ingested content" (only true for accepted messages). A porter who records both eagerly over-warns about content that never reached the graph.
**Probe:** `grep -c 'def test' ingestion/tests/test_slack_loader.py` → 82; roster-precedence cases pinned there.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "ext-zep", query: "SlackExportLoader user roster resolve weak name", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt real_name-first resolution + deferred weak-name promotion; adapt roster filenames/fields to your source; omit Slack-specific warning copy.
