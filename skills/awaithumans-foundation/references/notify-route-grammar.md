<!-- capsule-v2 -->
# Notify Route Grammar & Implicit Assignee — how does one string field route reviews across channels?

**Source:** awaithumans Apache-2.0 `main@bc05b8e7`; Codebase Memory `mnt-hdd-utopia-inspo-awaithumans`. **Question:** What is the complete grammar of `notify=[...]`, its failure semantics, and the exact conditions under which it implies an assignee?

## `<channel>[+<identity>]:<target>` with None-means-skip-warn
**Path/Symbol:** `packages/python/awaithumans/server/channels/routing.py:parse_route/routes_for_channel` (:37–80); constants `SLACK_NOTIFY_PREFIX` etc. in `utils/constants.py`; consumers in notifiers + router (`task_router.derive_implicit_assignee`).
**Signature:** `parse_route(entry: str) -> ChannelRoute|None`; `routes_for_channel(notify, channel) -> list[ChannelRoute]`.
**Data Shape:** `email:alice@x.com`, `email+acme-prod:bob@x.com` (sender identity), `slack:#approvals`, `slack+T123456:@U123` (workspace installation); identity separator `+` chosen because it never precedes the first `:` naturally, yet MAY appear inside targets (plus-addressed email, channel names).

### Decisive source
```python
if ":" not in entry:
    return None                      # callers treat None as "skip, log warning" — NEVER raise
prefix, _, target = entry.partition(":")
if not prefix or not target:
    return None
if "+" in prefix:
    channel, _, identity = prefix.partition("+")
    if not channel or not identity:
        return None
return ChannelRoute(channel=channel.strip(), identity=identity.strip() or None, target=target.strip())
```

**Flow:** task create passes notify through verbatim → each channel filters via routes_for_channel → notifier resolves identity→credentials (default when absent) and target→recipient. In parallel the ROUTER consults entry[0] only for implicit assignment: exactly one entry AND DM-shaped target (`@handle`, email, or U/W user id — NOT `#chan`/C/G sigils which are claim-flow broadcasts) AND resolves to a real Slack user AND that user is active in the directory ⇒ assignee; anything else returns empty RoutingResult and the task stays unassigned.
**Invariant:** malformed routes degrade to logged skips — one bad string never fails a task creation; ambiguity (multiple entries) drops rather than guesses; Slack-only users not yet in the directory still GET the DM (notifier has its own resolution layer) but routing stays untracked until an operator adds them.
**Probe:** `tests/users/test_implicit_assignee.py` (:98–250 handle/email/user-id derive vs sigil/multi-entry/not-in-directory/inactive skips, email identity suffix handled); parser behavior exercised through task_router tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-awaithumans", query: "parse_route notify channel routing", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the compact prefix grammar, None-is-data failure mode, and the conservative single-target implicit-assignee contract. Adapt channel vocabulary. Omit per-channel delivery internals (Slack blocks renderer, SMTP transports — product surface).
