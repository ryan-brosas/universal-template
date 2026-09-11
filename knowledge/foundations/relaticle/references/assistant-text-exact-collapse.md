<!-- capsule-v2 -->
# Assistant text exact-collapse — when can an agent's repeated output be normalized without changing legitimate prose?

**Source:** relaticle AGPL-3.0 `main@6e3bf8dfb7c5dcc97765fcba6fdf62585c541e1b`; direct source/test read (Codebase Memory MCP unavailable this session). **Question:** How can a persistence layer remove a whole assistant response repeated by a multi-step stream while leaving non-periodic text byte-for-byte unchanged?

## Search the shortest byte-period, then apply the same pure rule at both persistence sites
**Path/Symbol:** `packages/Chat/src/Support/AssistantText.php:collapseRepeated` (:7-40); `packages/Chat/src/Storage/SupersededAwareConversationStore.php:storeAssistantMessage` (:62-76); `packages/Chat/src/Jobs/ProcessChatMessage.php:materializeAssistantDocument` (:637-648).
**Signature:** `collapseRepeated(string $text): string`.
**Data Shape:** Input and output are strings. Empty, one-byte, and non-periodic strings return unchanged. For each unit length from 1 through `floor(length/2)`, only exact divisors are tested; the first unit whose repetition reconstructs the entire original string is returned. The first persistence site rewrites `AgentResponse::$text` before the parent store writes `content`; the document materializer independently applies the same pure function before parsing TipTap output.

### Decisive source
```php
for ($unitLength = 1; $unitLength <= intdiv($length, 2); $unitLength++) {
    if ($length % $unitLength !== 0) {
        continue;
    }

    $unit = substr($text, 0, $unitLength);
    if (str_repeat($unit, intdiv($length, $unitLength)) === $text) {
        return $unit;
    }
}
return $text;
```

**Flow:** The multi-step provider response can concatenate the same acknowledgment around a tool call. The conversation store collapses only if the entire text is a repetition of one shortest unit. A normal sentence or a partial repetition is retained. The job's TipTap materialization repeats the normalization independently because `content` and `document` are built through separate paths; an already-collapsed response remains unchanged.
**Invariant:** Collapse is conservative and whole-string-only: no substring replacement, trimming, fuzzy matching, or punctuation repair. Both persisted representations must agree even if either path is invoked independently. A legitimate non-periodic assistant response is byte-preserved.
**Probe:** `tests/Feature/Chat/AssistantTextDedupeTest.php` (:44-70) pins repeated content collapsing to one copy and non-repeated content preservation; the job's document path is exercised by the adjacent process/materialization suites in the checkout. Live Pest remains blocked by missing `vendor/` and PHP/Pest executables.

## Get live surrounding code
**Retrieve:**
```ts
await mcp.codebase_memory.search_graph({ project: "relaticle", query: "AssistantText collapseRepeated storeAssistantMessage materializeAssistantDocument", limit: 10, fields: ["signature", "name", "file"] });
```

## Verdict
Adopt an exact periodic-string detector as a pure normalization step, and call it at every independently persisted representation. Adapt the stream/store/document layers. Omit assumptions that all repeated text is accidental: require full-string periodicity and preserve everything else. Direct tests confirm the store boundary; graph retrieval was unavailable in this pass.
