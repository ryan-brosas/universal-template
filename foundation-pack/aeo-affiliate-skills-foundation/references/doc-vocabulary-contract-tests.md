<!-- capsule-v2 -->
# Documentation vocabulary contract tests — how do you stop field-name drift between docs, client code, and a renamed upstream?

**Source:** aeo-affiliate-skills MIT `main@ed17ef37bc167b52d9596cbe0292507f001c483d`; Codebase Memory `aeo-affiliate-skills`. **Question:** After migrating from a retired data source (list.affitor.com) to a new one (openaffiliate.dev), how do you make the old vocabulary and host stay dead and the normalized one stay documented — mechanically?

## Docs as executable rename-migration guard rails
**Path/Symbol:** `tests/test-doc-contracts.ts` (whole file; counters :4–11, Test 1 :20–25, Test 2 :27–30, Test 3 :32–42, fail exit :44–47).
**Signature:** `const read = (p: string): string => readFileSync(join(root, p), "utf8")`; `function assert(name: string, condition: boolean, detail = ""): void` (increments `failed`, exits 1 at end).
**Data Shape:** Reads three docs (`README.md`, `API.md`, `CLAUDE.md`) plus `tools/src/api.ts` as plain text; asserts substring presence/absence of exact strings.

### Decisive source
```ts
// Test 1: public docs enforce correct list field names
for (const needle of ["reward_value", "reward_type", "cookie_days", "stars_count"]) {
  assert(`README/API/CLAUDE mention ${needle}`,
    readme.includes(needle) || api.includes(needle) || claude.includes(needle), needle);
}
assert("CLAUDE.md explicitly bans wrong field names",
  claude.includes("NOT: `commission_rate`, `upvotes`, `cookie_duration`"));
assert("API.md explicitly bans wrong field names",
  api.includes("Do not substitute `commission_rate`, `upvotes`, or `cookie_duration`"));

// Test 3: data-source adapter contract
assert("api.ts points at the openaffiliate.dev API", apiClient.includes("openaffiliate.dev/api"));
assert("api.ts is NOT pointing at the retired list.affitor.com",
  !apiClient.includes("list.affitor.com"));
```

**Flow:** every CI run re-reads the shipped documentation and asserts (1) each normalized field name appears in at least one public doc, (2) the docs ban the retired synonyms by their EXACT pinned sentences, (3) README still points at the core artifacts (`registry.json`, `skills/{stage}/{skill-name}/SKILL.md`, `tools/src/`, `evals/`), and (4) the client reads the raw upstream fields AND produces the normalized ones while referencing only the new API host. Any drift — someone "simplifying" a doc sentence, reintroducing an old field name in api.ts, or repointing the host — fails `bun run test:docs` with a named assertion.
**Invariant:** Documentation is treated as part of the migration surface: renaming a concept requires updating the pinned strings in BOTH the docs and this test file in the same change. The banned-synonym assertions are presence-checks on anti-documentation ("do NOT use these names") — they encode the negative space of the vocabulary, which ordinary tests never cover.
**Probe:** Repository-owned runner executed at pin: `bun run tests/test-doc-contracts.ts` → all checks ✅ (see verification.md P2). Cross-pin: `grep -rn "commission_rate" CLAUDE.md API.md tools/src/` matches only the ban sentences/doc pins, never client logic.
**Coverage caveat:** none — `tests/test-doc-contracts.ts` checked `no_recorded_issue` at generation 2026-08-25T08:24:56Z.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "aeo-affiliate-skills", query: "doc contracts assert reward_type commission_rate", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt for any project that survived a data-source or schema rename: pin positive vocabulary, negative synonyms (exact ban sentences), artifact pointers, and host references into one fast zero-dep test that fails with named assertions. Adapt the pinned strings to your own migration history — they are intentionally brittle; brittleness IS the feature. Omit nothing from the negative assertions when extending: every retired name you leave unpinned is free to come back through review.
