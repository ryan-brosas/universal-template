<!-- capsule-v2 -->
# Browser downgrade guard — refusing a profile newer than the browser about to open it

**Source:** linkedin-mcp-server Apache-2.0 `main@cfcd9c9a`; Codebase Memory `linkedin-mcp-server`. **Question:** How do you detect that the installed Chromium is older than the one that wrote a profile, and why must the guard fail OPEN?

## refuse_a_downgrade — fail-open, one-shot evidence
**Path/Symbol:** `linkedin_mcp_server/browser_downgrade.py:refuse_a_downgrade()` (:377); helpers `profile_was_written_by` :293, `version_of` :319, `parse_version`/`parse_build` :251/:270.
**Signature:** `refuse_a_downgrade(profile_dir: Path, executable: str | None) -> None`.
**Data Shape:** Reads profile version markers (`Last Version`), asks `--version` of the candidate binary; compares component-wise. Every unreadable marker / unnameable binary / unparseable version = NO downgrade detected.

### Decisive source
```text
Every answer here fails open. Being unable to read a marker, name the
binary or parse a version is not evidence of a downgrade, and refusing to
start a browser on the strength of a missing file would turn a guard into
an outage.

That choice costs more than it looks: failing open once is not "we will
catch it next time" — the older browser runs and on its way out it REWRITES
`Last Version` down to its own number (measured: a launch on a profile
marked 1.0.0.0 left it reading 148.0.7778.96). The evidence is gone, so
every later launch sees no downgrade even after whatever made the version
unreadable is fixed. It is still the right trade, because the alternative
refuses working setups on the strength of not knowing — but the guard is
one-shot per profile and nothing downstream can recover it.
```
**Flow:** read profile marker → name+version the executable → comparable? (parse both; `is_compatible(product)` gates known-compatible families) → binary older ⇒ raise with both versions rendered → else proceed.
**Invariant:** Fail-open guards on destructively-self-modifying evidence are ONE-SHOT: the first miss consumes the evidence. Document the cost at the guard site, because reviewers cannot see it later. Chrome 150's backward-compat markers make this a snapshot until a store raises its floor — nothing warns when that happens.
**Probe:** `tests/test_browser_downgrade.py` (1,035L) pins refusal vs fail-open branches.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "linkedin-mcp-server", query: "refuse_a_downgrade profile_was_written_by Last Version", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt fail-open downgrade detection with documented one-shot cost for any app holding persistent stores written by versioned binaries. Adapt marker names. Omit Chrome-store specifics.
