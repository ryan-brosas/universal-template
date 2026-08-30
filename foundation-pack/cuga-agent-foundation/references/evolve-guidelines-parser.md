<!-- capsule-v2 -->
# Evolve guidelines parser — how do you turn free-form LLM-generated guideline text into numbered items without losing non-list prose?

**Source:** cuga-agent Apache-2.0 `main@5de53ade77c36166da6ace906af488b2b445454f`; Codebase Memory `mnt-hdd-utopia-inspo-agents-cuga-agent`. **Question:** When the memory service returns arbitrary markdown (headers, bullets, numbered lists, paragraphs, a "Guidelines for: X" preamble), how do you extract clean numbered recommendations — and when do you keep raw text instead?

## parse_evolve_guideline_items two-tier parse
**Path/Symbol:** `src/cuga/backend/evolve/formatting.py:86-139` (`parse_evolve_guideline_items`), renderer `format_evolve_guidelines` :142-163, preference formatter :38-83, query pickers `get_first_human_message_content`/`get_latest_memory_query` :9-35.
**Signature:** `parse_evolve_guideline_items(raw_guidelines: str) -> list[str]`.
**Data Shape:** item regex `^(?:[-*]|\d+[.)])\s+(.*)$`; continuation lines join the CURRENT item with spaces; non-item prose accumulates in a separate fallback list.

### Decisive source
```python
if guideline_items:                       # tier 1: any bullet/numbered items won
    return guideline_items

fallback_text = "\n".join(fallback_lines).strip()
...
# strip the provenance preamble line, then split into paragraphs
fallback_text = re.sub(r"^Guidelines\s+for:\s*.+$", "", fallback_text, flags=re.IGNORECASE | re.MULTILINE)
paragraphs = [p.strip() for p in re.split(r"\n\s*\n", fallback_text) if p.strip()]
```

**Flow:** normalize CRLF → blank lines flush the current item → headers (`#`) dropped entirely → bullet/numbered starts begin new items, indented continuations append → if ANY items parsed, they win outright → otherwise prose mode: drop "Guidelines for:" lines, split on paragraph breaks, return paragraphs as pseudo-items → renderer wraps in a fixed prompt block that tells the model these are "hard earned experience … **Do not ignore them.**" ranked as important as instructions and few-shots.
**Invariant:** the two tiers never mix — one stray bullet must not fragment an otherwise-prose document (items-present ⇒ prose discarded); headers are removed but their TEXT is not promoted to items; empty result ⇒ section omitted entirely (caller appends nothing). The memory-query picker skips `"Execution output:"-prefixed` human messages so tool noise never becomes a retrieval query.
**Probe:** no direct unit test file for formatting.py (coverage caveat — deterministic checks: mixed bullet+prose ⇒ only bullets; pure prose ⇒ paragraphs; header-only ⇒ []). The composition wrapper's fail-open behavior is covered by evolve integration tests.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "mnt-hdd-utopia-inspo-agents-cuga-agent", query: "parse_evolve_guideline_items format_evolve_guidelines", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt the two-tier parse (structured-wins-else-paragraphs) for injecting LLM-generated recommendation text into prompts; adapt the item regex and preamble stripper to your service's output dialect; adopt the authority framing ("as important as instructions") deliberately — it measurably changes adherence; omit preference formatting if you have no user-facts surface. Coverage caveat: source-read verified, deterministic checks listed above.
