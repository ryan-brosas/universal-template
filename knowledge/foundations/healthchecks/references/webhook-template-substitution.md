<!-- capsule-v2 -->
# Webhook variable substitution — single-pass placeholder replacement immune to variable-variable injection

**Source:** healthchecks BSD-3-Clause `master@29b5ec25`; Codebase Memory `healthchecks`. **Question:** How do you expand user-authored URL/body/header templates with check data when the data itself may CONTAIN dollar-sign placeholders — and keep latin-1 headers from exploding?

## string.replace + webhook prepare
**Path/Symbol:** `hc/lib/string.py:replace` (:9-52, docstring carries the spec), `match_keywords` (:54-60); `hc/integrations/webhook/transport.py:Webhook.prepare/notify` (:14-93); shell twin `hc/integrations/shell/transport.py:Shell.prepare` (shlex.quote instead of urlencode).
**Signature:** `replace(template: str, ctx: dict[str, str]) -> str`; `prepare(template, flip, *, urlencode=False, latin1=False, allow_ping_body=False) -> str`.
**Data Shape:** Placeholder grammar `$NAME`, `$TAG1..$TAGn`, `$JSON`, `$BODY`/`$BODY_JSON` (materialized ONLY if referenced), `$EXITSTATUS` default "-1". Context values are pre-escaped per sink: URLs urlencode=True, JSON via json.dumps, headers latin-1 xmlcharrefreplace.

### Decisive source
```python
# hc/lib/string.py — split-on-$ walk; only ORIGINAL placeholders are expanded
"""This function explicitly ignores "variable variables".
>>> replace("Hello $FOO", {"$FOO": "$BAR", "$BAR": "World"})
Wrong: Hello World
Correct: Hello $BAR

In other words, this function only replaces placeholders that appear
in the original template. ... mainly to avoid unexpected behavior when
check names or tags contain dollar signs."""
parts = template.split("$")
result = [parts.pop(0)]
for part in parts:
    part = "$" + part
    for placeholder, value in ctx.items():
        if part.startswith(placeholder):
            part = part.replace(placeholder, value, 1)
            break      # first matching placeholder wins
    result.append(part)
```

**Flow:** notify() builds ctx once with sink-appropriate escaping ($CODE/$STATUS/$NOW raw or urlencoded for URLs; $NAME_JSON json.dumps so quotes survive; $TAGn per-tag). $EXITSTATUS resolves from the last ping's exitstatus, "-1" when the flip predates any ping. Body materialization is lazy: get_ping_body runs only when "$BODY" appears in template — a deliberate S3-fetch guard. Header values pass through encode("latin-1", "xmlcharrefreplace") because HTTP headers reject UTF-8. Test notifications skip retry (notification.owner None → retry=False) so a broken user webhook isn't hammered three times by a button click.
**Invariant:** Single-pass, original-template-only expansion is the security AND correctness core: substituting into the result would let a check named "$FOO" execute second-order expansion — the docstring's Wrong/Correct pair is the acceptance test. First-match-wins ordering means prefix collisions ($TAG1 vs $TAG10-style hazards) resolve deterministically by dict order; upstream keeps tags positional to sidestep it. is_noop checks the SPEC for empty url BEFORE any rows are written, and "Empty webhook URL" raises rather than silently GETting "".
**Probe:** `hc/integrations/webhook/tests/test_notify.py::test_webhooks_support_variables`, `test_webhooks_handle_variable_variables`, `test_webhooks_dollarsign_escaping`, `test_it_handles_missing_ping_object` sibling for last_ping(None); `hc/front/tests/test_hc_extras.py::test_hc_duration_works` twin discipline for pure helpers.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "healthchecks", query: "webhook prepare replace variables template", limit: 10 });
```

## Verdict
Adopt split-on-delimiter single-pass expansion with pre-escaped context values, lazy body fetch gated on template reference, and per-sink escaping selection. Adapt the placeholder grammar to your users' expectations. Omit nothing from the no-resubstitution rule — it is the difference between templating and template injection.
